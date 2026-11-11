/* Explicit opt-in to native Web Push; never active without a configured private backend. */
(function(){
'use strict';
const area=document.getElementById('notificationSection');
if(!area)return;
const status=document.getElementById('notificationStatus');
const button=document.getElementById('notificationButton');
const info=document.getElementById('notificationInfo');
let configuration=null;
const message=s=>{status.textContent=s};
function validConfig(x){
  if(!x||x.enabled!==true||!x.vapidPublicKey||!x.backendUrl)return false;
  try{let u=new URL(x.backendUrl);return u.protocol==='https:'&&!u.username&&!u.password&&!u.search&&!u.hash}
  catch(_){return false}
}
function b64ToArray(value){
  const padded=value.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-value.length%4)%4);
  const decoded=atob(padded);
  return Uint8Array.from(decoded,c=>c.charCodeAt(0));
}
function isIosStandalone(){
  const apple=/iPhone|iPad|iPod/.test(navigator.userAgent);
  const standalone=window.matchMedia('(display-mode: standalone)').matches || navigator.standalone===true;
  return !apple||standalone;
}
async function refresh(){
  if(!('serviceWorker' in navigator)||!('PushManager' in window)||!('Notification' in window)){
    button.disabled=true;message('この環境ではプッシュ通知を利用できません。');return;
  }
  if(!isIosStandalone()){
    button.disabled=true;message('iPhone・iPadでは、Safariなどからホーム画面に追加し、そのアイコンから開いてください。');return;
  }
  const reg=await navigator.serviceWorker.ready;
  const sub=await reg.pushManager.getSubscription();
  button.textContent=sub?'通知を解除する':'夜9時の通知を受け取る';
  button.dataset.action=sub?'unsubscribe':'subscribe';
  button.disabled=false;
  message(sub?'この端末は通知を購読しています。不要なら解除できます。':'許可すると、新しい配信号の公開後に通知を受け取れます。');
}
async function post(action,body){
  const base=configuration.backendUrl.replace(/\/+$/,'');
  const response=await fetch(base+'/'+action,{
    method:'POST',mode:'cors',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body),cache:'no-store'
  });
  if(!response.ok)throw Error('通知サーバーへの登録に失敗しました ('+response.status+')');
}
button.addEventListener('click',async()=>{
  if(!configuration||button.disabled)return;
  button.disabled=true;
  try{
    const reg=await navigator.serviceWorker.ready;
    const current=await reg.pushManager.getSubscription();
    if(current){
      await post('unsubscribe',{endpoint:current.endpoint});
      await current.unsubscribe();
      message('通知を解除しました。');
    }else{
      // Permission request must be initiated by a direct user click (not on page load).
      const permission=await Notification.requestPermission();
      if(permission!=='granted'){message('通知の許可はありません。端末の設定から変更できます。');return}
      const created=await reg.pushManager.subscribe({
        userVisibleOnly:true,applicationServerKey:b64ToArray(configuration.vapidPublicKey)
      });
      try{await post('subscribe',{subscription:created.toJSON()})}
      catch(error){await created.unsubscribe();throw error}
      message('通知の購読を登録しました。');
    }
  }catch(error){message('通知の設定が完了しませんでした。通信状況を確認してください。')}
  finally{await refresh().catch(()=>{button.disabled=false})}
});
fetch('./notification-config.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('disabled');return r.json()}).then(async x=>{
  if(!validConfig(x))return; // Hide the button until a real service is configured.
  configuration=x;area.hidden=false;
  info.textContent='通知は任意です。iPhoneではホーム画面への追加が必要です。';
  await refresh();
}).catch(()=>{});
})();