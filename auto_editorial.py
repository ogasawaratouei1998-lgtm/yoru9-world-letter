#!/usr/bin/env python3
"""Free-tier AI editorial pipeline. Fail closed: no key, no verified five, no publication."""
import json, os, re, sys, ipaddress, socket
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

JST=ZoneInfo("Asia/Tokyo")
MODEL=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite")
KEY=os.getenv("GEMINI_API_KEY","")
REQUIRED=("id","country","category","categoryLabel","label","title","summary","detail","quip","sourceName","sourceUrl","reported")
BLOCK=re.compile(r"死亡|殺害|負傷|災害|差別|自殺|銃撃|戦争|死者|犠牲者|killed|murder|fatal|death|died|suicide|rape|shooting|injured|hospitalized|war|bombing|disaster",re.I)

def host(url):
    try:
        p=urlsplit(url)
        return p.hostname.lower().removeprefix("www.") if p.scheme=="https" and p.hostname and not p.username else ""
    except ValueError:return ""

class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript","svg"):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","svg"):self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden and data.strip():self.parts.append(data.strip())

def public_host(url):
    domain=host(url)
    if not domain or domain in ("localhost",) or domain.endswith((".local",".internal")):return False
    try:
        addresses=socket.getaddrinfo(domain,443,type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(x[4][0]).is_global for x in addresses)
    except (OSError,ValueError):return False

def source_text(url):
    # Only URLs already found in the trusted lead list may be fetched.
    if not public_host(url):return ""
    class SafeRedirect(__import__("urllib.request",fromlist=["HTTPRedirectHandler"]).HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            if not public_host(newurl):raise ValueError("unsafe_redirect")
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    from urllib.request import build_opener
    opener=build_opener(SafeRedirect)
    req=Request(url,headers={"User-Agent":"Yoru9EditorialResearch/1.0","Accept":"text/html"})
    try:
        with opener.open(req,timeout=7) as response:
            if "text/html" not in response.headers.get("Content-Type",""):return ""
            raw=response.read(180000)
        parser=ArticleText()
        parser.feed(raw.decode("utf-8",errors="replace"))
        text=" ".join(parser.parts)
        return text[:13000] if len(text)>=600 else ""
    except (OSError,ValueError,HTTPError,URLError):return ""

def available_models():
    """List supported models, with a bounded preference order and no paid fallback."""
    endpoint="https://generativelanguage.googleapis.com/v1beta/models?pageSize=100"
    req=Request(endpoint,headers={"x-goog-api-key":KEY})
    with urlopen(req,timeout=25) as response:
        catalog=json.load(response)
    models=[m["name"] for m in catalog.get("models",[])
            if "generateContent" in m.get("supportedGenerationMethods",[])
            and m.get("name","").startswith("models/gemini-")]
    preferred=[MODEL,"gemini-3.5-flash-lite","gemini-3.5-flash","gemini-2.5-flash-lite","gemini-2.5-flash",
               "gemini-2.0-flash-lite","gemini-2.0-flash"]
    result=[]
    for name in preferred:
        full="models/"+name
        if full in models and full not in result:result.append(full)
    if not result:raise RuntimeError("No supported Gemini model found; safe stop")
    return result[:3]

def available_model():
    return available_models()[0]

ACTIVE_MODEL=None

def ai(prompt):
    global ACTIVE_MODEL
    if not KEY:raise RuntimeError("GEMINI_API_KEY not configured; no publication")
    models=[ACTIVE_MODEL] if ACTIVE_MODEL else available_models()
    data={"contents":[{"parts":[{"text":prompt}]}],
          "generationConfig":{"responseMimeType":"application/json","temperature":0.1}}
    last_error=None
    for model in models:
        for version in ("v1beta","v1"):
            url="https://generativelanguage.googleapis.com/"+version+"/"+model+":generateContent"
            req=Request(url,data=json.dumps(data).encode(),
                        headers={"Content-Type":"application/json","x-goog-api-key":KEY},method="POST")
            try:
                with urlopen(req,timeout=90) as response:result=json.load(response)
                raw=result["candidates"][0]["content"]["parts"][0]["text"]
                ACTIVE_MODEL=model
                print("Gemini generation succeeded:",model,version,flush=True)
                return json.loads(raw)
            except HTTPError as exc:
                # Print only status and sanitized provider reason, never headers or key.
                try:
                    err=json.loads(exc.read(4096).decode("utf-8"))
                    status=str(err.get("error",{}).get("status","UNKNOWN"))[:50]
                    message=str(err.get("error",{}).get("message",""))[:320]
                    message=re.sub(r"AIza[A-Za-z0-9_-]{20,}", "[REDACTED_KEY]", message)
                    message=re.sub(r"key=[^&\\s]+", "key=[REDACTED]", message,flags=re.I)
                except (ValueError,UnicodeError,AttributeError):status="UNKNOWN";message="unavailable"
                print("Gemini generation failed:",model,version,"HTTP",exc.code,status,"reason:",message,flush=True)
                last_error=exc.code
                if exc.code not in (404,400):raise RuntimeError("Gemini API HTTP "+str(exc.code))
    raise RuntimeError("No available model/version generated content; last HTTP "+str(last_error))

def archive_summaries():
    result=[]
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            for story in json.loads(file.read_text()).get("stories",[]):
                result.append({"title":story.get("title",""),"summary":story.get("summary",""),"country":story.get("country","")})
        except (ValueError,OSError):continue
    return result[-250:]

def previous_events():
    seen=set()
    for file in Path("data/archive").glob("????-??-??.json"):
        try:
            for story in json.loads(file.read_text()).get("stories",[]):
                seen.add(story.get("sourceUrl",""))
                seen.add(story.get("id",""))
        except (ValueError,OSError):continue
    return seen

# Similar headlines help discovery, but are not proof of corroboration.
STOPWORDS=set("the a an and or of to in on for with from at by as is are was were after before new latest says say report reports news world today update video live how why what who where this that about into over under amid".split())

def title_terms(title):
    return {w for w in re.findall(r"[a-z0-9]{3,}",title.lower()) if w not in STOPWORDS}

def corroboration_groups(items):
    """Group potentially matching incidents across distinct publisher domains."""
    groups=[]
    for i,item in enumerate(items):
        terms=title_terms(item["title"])
        if len(terms)<3:continue
        matches=[item]
        for other in items[i+1:]:
            if host(other["url"])==host(item["url"]):continue
            other_terms=title_terms(other["title"])
            shared=terms & other_terms
            if len(shared)>=3 and len(shared)/max(1,min(len(terms),len(other_terms)))>=0.45:
                matches.append(other)
        if len(matches)>=2:groups.append(matches[:4])
    unique={}
    for group in groups:
        key=tuple(sorted(x["url"] for x in group))
        unique[key]=group
    return list(unique.values())[:16]

def main():
    now=datetime.now(JST)
    day=now.date().isoformat()
    if not KEY:
        print("No free-tier AI key configured. Safe skip.");return 0
    leads=json.loads(Path("data/candidates.json").read_text()).get("candidates",[])
    today=[]
    for lead in leads:
        try:
            raw=lead["seendate"]
            if re.fullmatch(r"\\d{8}T\\d{6}Z",raw):
                stamp=datetime.strptime(raw,"%Y%m%dT%H%M%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(JST)
            else:
                stamp=datetime.fromisoformat(raw.replace("Z","+00:00")).astimezone(JST)
            if stamp.date()!=now.date():continue
        except (KeyError,ValueError,TypeError):continue
        if host(lead.get("url","")) and not BLOCK.search(lead.get("title","")):today.append(lead)
    if len(today)<5:
        print("Not enough same-day leads; safe skip.");return 0
    # Collect actual article bodies before asking the model to draft.
    cache={}
    source_leads=[]
    # Interleave publishers instead of letting one feed dominate the 36 fetch slots.
    buckets={}
    for lead in today:
        buckets.setdefault(host(lead['url']),[]).append(lead)
    ordered=[]
    while buckets and len(ordered)<60:
        for domain in list(buckets):
            if buckets[domain]:ordered.append(buckets[domain].pop(0))
            if not buckets[domain]:del buckets[domain]
            if len(ordered)>=60:break
    for lead in ordered:
        url=lead['url']
        if url not in cache:cache[url]=source_text(url)
        if cache[url]:source_leads.append({'title':lead['title'],'url':url,'publisher':lead.get('domain',''),'text':cache[url][:6500]})
    print('Evidence collection:',len(today),'same-day leads,',len(source_leads),'fetchable article bodies',flush=True)
    if len(source_leads)<2:
        print('Fewer than two article bodies; safe skip before AI generation.');return 0
    groups=corroboration_groups(source_leads)
    print('Cross-publisher headline groups:',len(groups),flush=True)
    if not groups:
        print('No independent cross-publisher candidate groups; safe skip.');return 0
    grouped_urls={item["url"] for group in groups for item in group}
    grouped_sources=[item for item in source_leads if item["url"] in grouped_urls]
    prompt=('You are editor A. Return JSON object with stories array of up to 8 candidate Japanese lighthearted mistake news stories. '
      'Use ONLY supplied fetched article texts, never external knowledge. Only draft stories corroborated by TWO independent publisher articles describing the SAME incident. '
      'verificationUrls must be exact URLs present in evidence, on distinct domains. Do not invent facts, URLs or unsupported details. '
      'For each include required fields '+str(REQUIRED)+', verificationUrls (2 URLs), eventKey (normalized incident identifier), evidence (facts corroborated by both). '
      'No death, injuries, abuse or humiliation. Today JST: '+day+'. Possible same-event headline groups (NOT proof): '+json.dumps([[x['url'] for x in group] for group in groups],ensure_ascii=False)+'. Original article bodies: '+json.dumps(grouped_sources,ensure_ascii=False))
    draft=ai(prompt).get("stories",[])
    if not isinstance(draft,list):return 0
    seen=previous_events()
    selected=[]
    past=archive_summaries()
    accepted_summaries=[]
    lead_urls={x['url'] for x in source_leads}
    for story in draft:
        if not isinstance(story,dict) or any(not isinstance(story.get(k),str) or not story[k].strip() for k in REQUIRED):continue
        if story["reported"].replace(".","-")!=day or story["category"] not in ("person","work","company"):continue
        urls=story.get("verificationUrls",[])
        if not isinstance(urls,list) or len(urls)<2 or len(set(host(u) for u in urls))<2 or not all(host(u) for u in urls):continue
        if story["sourceUrl"] not in urls or any(u not in lead_urls for u in urls):continue
        if story["sourceUrl"] in seen or story["id"] in seen or BLOCK.search(" ".join(str(story[k]) for k in ("title","summary","detail","quip"))):continue
        event=story.get("eventKey")
        if not isinstance(event,str) or len(event)<12 or event in seen:continue
        # Both independent source pages must be actually retrieved, not merely named by AI.
        evidence=[]
        for url in urls[:3]:
            if cache[url]:evidence.append({"url":url,"text":cache[url]})
        if len(evidence)<2 or len({host(x["url"]) for x in evidence})<2:continue
        audit=ai("You are independent adversarial fact checker B. You must verify every concrete "
          "claim in this Japanese article against the TWO separately fetched source article texts below. "
          "Reject unsupported claims, syndicated duplicate reporting, mismatched dates, invented quotes, "
          "unsafe jokes, and repeated events. Compare against the prior published events and already selected events, "
          "reject the same underlying incident even if the title, source, language or URL differs. "
          "Reject if evidence is insufficient or unclear. "
          "Output only JSON {approved:boolean,reason:string}. Article: "
          +json.dumps(story,ensure_ascii=False)+" Previously published events: "
          +json.dumps(past,ensure_ascii=False)+" Already selected today: "
          +json.dumps(accepted_summaries,ensure_ascii=False)+" Independently fetched sources: "
          +json.dumps(evidence,ensure_ascii=False))
        if audit.get("approved") is not True:continue
        story["editorVerified"]=True
        story["humorSafe"]=True
        seen.update((story["sourceUrl"],story["id"],event))
        selected.append(story)
        accepted_summaries.append({"title":story["title"],"summary":story["summary"],"country":story["country"]})
        if len(selected)==5:break
    if len(selected)!=5:
        print("Two-stage verification did not approve exactly five; no publication.");return 0
    payload={"status":"approved","editionDate":day,"editionType":"regular","title":day+"｜世界の大失敗５連発",
      "editorApproved":True,"factChecked":True,"humorReviewed":True,"approvedBy":"automated-two-stage-review","stories":selected}
    target=Path("data/approved")/(day+".json")
    if target.exists():return 0
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    print("Created five-stage-gated AI issue",day)
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("Fail-closed AI review:",type(e).__name__,str(e),file=sys.stderr)
        sys.exit(1)
