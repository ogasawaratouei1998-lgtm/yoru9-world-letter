import { createClient } from "npm:@supabase/supabase-js@2.119.0";
import { sendPushNotification } from "npm:@mmmike/web-push@1.5.0/send";
import { READER_ORIGIN, validEndpoint, validSubscription, safeEditionDate, fixedTimeEqual, validPushSettings } from "./validation.ts";

const MAX_SUBSCRIBERS_PER_DISPATCH = 200; // Refuse partial broadcasts; scale with a queue before exceeding this.
const MAX_BODY = 4600;
const NO_STORE: Record<string, string> = { "Content-Type":"application/json; charset=utf-8", "Cache-Control":"no-store" };

function response(data: unknown, status = 200, extra: Record<string,string> = {}) {
  return new Response(JSON.stringify(data),{status,headers:{...NO_STORE,...extra}});
}
function cors(req:Request):Record<string,string> {
  return req.headers.get("origin") === READER_ORIGIN
    ? {"Access-Control-Allow-Origin":READER_ORIGIN,
       "Access-Control-Allow-Methods":"POST, OPTIONS",
       "Access-Control-Allow-Headers":"content-type",
       "Vary":"Origin"} : {"Vary":"Origin"};
}
function pub(req:Request, value:unknown, status=200) { return response(value,status,cors(req)); }
async function jsonBody(req:Request): Promise<Record<string,unknown>> {
  const length=Number(req.headers.get("content-length")||0);
  if (length>MAX_BODY) throw Error("body_too_large");
  const text=await req.text();
  if (text.length>MAX_BODY) throw Error("body_too_large");
  const data=JSON.parse(text);
  if(!data||typeof data!=="object"||Array.isArray(data)) throw Error("invalid_body");
  return data;
}
async function sha256(s:string):Promise<string> {
  const out=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(s));
  return Array.from(new Uint8Array(out),b=>b.toString(16).padStart(2,"0")).join("");
}
// The dedicated table schema is installed by schema.sql at provision time.
// Runtime data from clients is validated before any privileged write.
type DB = ReturnType<typeof createClient<any>>;
function database():DB|null {
  const url=Deno.env.get("SUPABASE_URL");
  const key=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  return url&&key?createClient<any>(url,key,{auth:{persistSession:false,autoRefreshToken:false}}):null;
}
function ready():boolean {
  return Boolean(database() && validPushSettings({
    publicKey:Deno.env.get("VAPID_PUBLIC_KEY")||"",
    privateKey:Deno.env.get("VAPID_PRIVATE_KEY")||"",
    subject:Deno.env.get("VAPID_SUBJECT")||"",
    token:Deno.env.get("PUSH_DISPATCH_TOKEN")||"",
    salt:Deno.env.get("PUSH_RATE_SALT")||""
  }));
}
async function allowedRate(req:Request,db:DB):Promise<boolean> {
  const salt=Deno.env.get("PUSH_RATE_SALT");
  if (!salt || salt.length<32) return false;
  const forwarded=req.headers.get("x-forwarded-for")||"unknown";
  // Do not keep a raw IP address in the database.
  const ip=forwarded.split(",").pop()?.trim().slice(0,100)||"unknown";
  const ipHash=await sha256(salt+":"+ip);
  const {data,error}=await db.rpc("yoru9_push_allow_request",{p_hash:ipHash,p_limit:8});
  if(error) throw Error("rate_limit_unavailable");
  return data===true;
}
function allowOrigin(req:Request):boolean {
  // Public subscribe/unsubscribe are available only through the configured site.
  return req.headers.get("origin")===READER_ORIGIN &&
    req.headers.get("content-type")?.toLowerCase().startsWith("application/json")===true;
}

async function subscribe(req:Request,db:DB):Promise<Response> {
  if (!allowOrigin(req))return pub(req,{error:"origin_not_allowed"},403);
  if (Deno.env.get("PUSH_SIGNUPS_ENABLED")!=="true")
    return pub(req,{error:"subscriptions_temporarily_closed"},503);
  if (!await allowedRate(req,db)) return pub(req,{error:"rate_limited"},429);
  const payload=await jsonBody(req);
  if(!validSubscription(payload.subscription))return pub(req,{error:"invalid_push_subscription"},400);
  const sub=payload.subscription;
  const hash=await sha256(sub.endpoint);
  // Do not accept more readers than this version can safely notify.
  // Allow existing subscriptions to refresh keys even when at capacity.
  const existing=await db.from("yoru9_push_subscriptions")
    .select("endpoint_hash").eq("endpoint_hash",hash).maybeSingle();
  if(existing.error)throw Error("subscription_lookup_failed");
  if(!existing.data){
    const count=await db.from("yoru9_push_subscriptions").select("endpoint_hash",{head:true,count:"exact"});
    if(count.error)throw Error("subscription_count_failed");
    if((count.count||0)>=MAX_SUBSCRIBERS_PER_DISPATCH)
      return pub(req,{error:"subscription_capacity_reached"},503);
  }
  const {error}=await db.from("yoru9_push_subscriptions").upsert({
    endpoint_hash:hash,endpoint:sub.endpoint,p256dh:sub.keys.p256dh,
    auth:sub.keys.auth,updated_at:new Date().toISOString()
  },{onConflict:"endpoint_hash"});
  if(error)throw Error("subscription_write_failed");
  return pub(req,{ok:true},201);
}
async function unsubscribe(req:Request,db:DB):Promise<Response> {
  if(!allowOrigin(req))return pub(req,{error:"origin_not_allowed"},403);
  if(!await allowedRate(req,db))return pub(req,{error:"rate_limited"},429);
  const payload=await jsonBody(req);
  if(!validEndpoint(payload.endpoint))return pub(req,{error:"invalid_endpoint"},400);
  const hash=await sha256(payload.endpoint);
  const {error}=await db.from("yoru9_push_subscriptions").delete()
    .eq("endpoint_hash",hash).eq("endpoint",payload.endpoint);
  if(error)throw Error("unsubscribe_failed");
  return pub(req,{ok:true});
}
type StoredRow = {endpoint_hash:string,endpoint:string,p256dh:string,auth:string};

async function dispatch(req:Request,db:DB):Promise<Response> {
  const authorization=req.headers.get("authorization")||"";
  const token=authorization.startsWith("Bearer ")?authorization.slice(7):"";
  if(!fixedTimeEqual(token,Deno.env.get("PUSH_DISPATCH_TOKEN")||""))
    return response({error:"unauthorized"},401);
  const payload=await jsonBody(req);
  if(!safeEditionDate(payload.editionDate))
    return response({error:"edition_not_published_today_or_too_early"},422);
  const day=payload.editionDate as string;

  // Refuse to claim a dispatch if it cannot fit into this short serverless invocation.
  // This avoids silently omitting subscribers and flags the need for a queued fan-out.
  const countResult=await db.from("yoru9_push_subscriptions")
    .select("endpoint_hash",{count:"exact",head:true});
  if(countResult.error)throw Error("subscription_count_failed");
  if((countResult.count||0)>MAX_SUBSCRIBERS_PER_DISPATCH)
    return response({error:"needs_queued_fanout",subscribers:countResult.count},503);

  // The database unique key makes a release dispatch at most once even on CI retries.
  const claim=await db.from("yoru9_push_dispatches")
    .insert({edition_date:day,state:"processing"});
  if(claim.error){
    if(claim.error.code==="23505")return response({ok:true,duplicate:true});
    throw Error("dispatch_claim_failed");
  }

  const {data:subscribers,error}=await db.from("yoru9_push_subscriptions")
    .select("endpoint_hash,endpoint,p256dh,auth").limit(MAX_SUBSCRIBERS_PER_DISPATCH);
  if(error)throw Error("subscription_read_failed");
  const publicKey=Deno.env.get("VAPID_PUBLIC_KEY")||"";
  const privateKey=Deno.env.get("VAPID_PRIVATE_KEY")||"";
  const subject=Deno.env.get("VAPID_SUBJECT")||"";
  const notification={
    title:"よる9じの世界便り",
    body:typeof payload.body==="string"?payload.body.slice(0,170):"今夜の世界便りが届きました。",
    url:"https://ogasawaratouei1998-lgtm.github.io/yoru9-world-letter/"
  };
  const rows=(subscribers||[]) as StoredRow[];
  let delivered=0,gone=0,failed=0;
  const groups=[];
  for(let i=0;i<rows.length;i+=8)groups.push(rows.slice(i,i+8));
  for(const group of groups){
    const statuses=await Promise.all(group.map(async row=>{
      try{
        const ok=await sendPushNotification({
          endpoint:row.endpoint,keys:{p256dh:row.p256dh,auth:row.auth}
        },notification,{publicKey,privateKey,subject});
        if(!ok){
          await db.from("yoru9_push_subscriptions").delete().eq("endpoint_hash",row.endpoint_hash);
          return "gone";
        }
        await db.from("yoru9_push_subscriptions").update({last_notified_date:day})
          .eq("endpoint_hash",row.endpoint_hash);
        return "delivered";
      }catch(_){return "failed"}
    }));
    for(const status of statuses){
      if(status==="delivered")delivered++;
      else if(status==="gone")gone++;
      else failed++;
    }
  }
  const state=failed?"partial":"complete";
  const update=await db.from("yoru9_push_dispatches").update({
    state,total:rows.length,delivered,gone,failed,finished_at:new Date().toISOString()
  }).eq("edition_date",day);
  if(update.error)throw Error("dispatch_result_write_failed");
  // No endpoint URLs, private keys or subscription records in the response.
  return response({ok:failed===0,day,delivered,gone,failed,state},failed?207:200);
}
Deno.serve(async(req:Request)=>{
  const parsed=new URL(req.url);
  const operation=parsed.pathname.split("/").pop()||"";
  if(req.method==="OPTIONS"){
    return req.headers.get("origin")===READER_ORIGIN
      ? new Response(null,{status:204,headers:{...cors(req),"Access-Control-Max-Age":"3600"}})
      : response({error:"origin_not_allowed"},403);
  }
  if(req.method==="GET"&&operation==="health")return response({
    service:"yoru9-push",ready:ready(),
    signupsOpen:Deno.env.get("PUSH_SIGNUPS_ENABLED")==="true"
  });
  if(req.method!=="POST"||!["subscribe","unsubscribe","dispatch","verify-auth"].includes(operation))
    return response({error:"not_found"},404);
  if(!ready())return response({error:"server_not_configured"},503);
  const db=database();
  if(!db)return response({error:"database_not_configured"},503);
  try{
    if(operation==="verify-auth"){
      const bearer=req.headers.get("authorization")||"";
      const token=bearer.startsWith("Bearer ")?bearer.slice(7):"";
      return fixedTimeEqual(token,Deno.env.get("PUSH_DISPATCH_TOKEN")||"")
        ? response({ok:true,notificationSent:false})
        : response({error:"unauthorized"},401);
    }
    if(operation==="subscribe")return await subscribe(req,db);
    if(operation==="unsubscribe")return await unsubscribe(req,db);
    return await dispatch(req,db);
  }catch(error){
    const msg=error instanceof Error?error.message:"unknown";
    if(msg==="body_too_large"||msg==="invalid_body"||error instanceof SyntaxError)
      return operation==="dispatch"?response({error:"invalid_body"},400):pub(req,{error:"invalid_body"},400);
    // Avoid leaking internal exception messages or stored endpoints.
    console.error("Yoru9 push operation failed:",operation,msg);
    return operation==="dispatch"?response({error:"server_error"},500):pub(req,{error:"server_error"},500);
  }
});
