'use strict';
const demo=JSON.parse(document.querySelector('#embedded-demo').textContent);
const $=id=>document.getElementById(id);
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeUrl=url=>{try{const u=new URL(url);return ['https:','http:'].includes(u.protocol)?u.href:'#'}catch(_){return '#'}};
const japanTime=d=>{const x=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',hourCycle:'h23'}).formatToParts(d).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));return {date:`${x.year}-${x.month}-${x.day}`,hour:Number(x.hour)};};
const localDate=d=>japanTime(d).date;
let edition=demo,filter='all',state={read:[]};
let lastRenderedLocalDate=null;
function editionKey(){return 'yoru9:v4:'+String(edition.editionDate||'demo')}
function loadState(){try{const x=JSON.parse(localStorage.getItem(editionKey())||'{}');state={read:Array.isArray(x.read)?x.read:[]}}catch(_){state={read:[]}}}
function saveState(){try{localStorage.setItem(editionKey(),JSON.stringify(state))}catch(_){}}
let toastTimer;
function toast(s){$('toast').textContent=s;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,2300)}
// Approximate country centroids, not article-event coordinates.
let countryCatalog=[];
function countryRecord(name){
 const key=String(name||'').trim().toLocaleLowerCase();
 return countryCatalog.find(item=>item.code.toLowerCase()===key||item.name.toLocaleLowerCase()===key||item.aliases.some(alias=>alias.toLocaleLowerCase()===key))||null;
}
function countryKeys(name){
 const full=countryRecord(name);if(full)return [full.code];
 const value=String(name||'').trim();
 // Historical cross-border incidents: never split an exact compound country.
 for(const sep of ['・','／','/','、',' and ']){
  if(!value.includes(sep))continue;
  const parts=value.split(sep).map(x=>countryRecord(x.trim())?.code);
  if(parts.length>1&&parts.every(Boolean))return [...new Set(parts)];
 }
 return [];
}
function countryKey(name){return countryRecord(name)?.code||String(name||'').trim()}
function countryLabel(name){return countryRecord(name)?.name||String(name||'').trim()}
function mapPoint(name){
 const record=countryRecord(name);
 return record?[((record.lon+180)/360)*100,((90-record.lat)/180)*100]:null;
}
async function loadCountryCatalog(){
 try{
  const response=await fetch('./country-catalog.json',{cache:'no-store'});
  if(!response.ok)throw Error('country catalog unavailable');
  const records=await response.json();
  if(!Array.isArray(records)||!records.length)throw Error('invalid country catalog');
  countryCatalog=records;
 }catch(err){console.info('国・地域の一覧を読み込めませんでした',err)}
}
loadCountryCatalog().then(()=>renderTodayMap());
// Today's/current published issue only. Pins are real country centroids,
// never invented article locations or a route to past editions.
function currentIssueCountries(){
 const result=new Map();
 if(!Array.isArray(edition.stories))return [];
 edition.stories.forEach((story,index)=>{
  const codes=countryKeys(story.country);
  if(!codes.length){
   const key='unmapped:'+String(story.country||'国名未登録');
   if(!result.has(key))result.set(key,{code:key,name:countryLabel(story.country),point:null,indices:[]});
   result.get(key).indices.push(index);
   return;
  }
  codes.forEach(code=>{
   const record=countryRecord(code);
   if(!result.has(code))result.set(code,{
    code,name:record?.name||code,
    point:record&&Number.isFinite(record.lon)&&Number.isFinite(record.lat)
      ?{x:(record.lon+180)/360*100,y:(90-record.lat)/180*100}:null,
    indices:[]
   });
   result.get(code).indices.push(index);
  });
 });
 return [...result.values()];
}
const TODAY_MAP_COLORS=Object.freeze(['#FFF0C9','#B5EBD6','#FFCFB8','#E4D3EE','#F6CFDC']);
const TODAY_COUNTRY_INTROS=Object.freeze({
 AR:'南アメリカ南部に広がる国。西にはアンデス山脈が連なり、広大な草原パンパもあります。',
 FR:'ヨーロッパ西部に位置し、大西洋と地中海の両方に面しています。地域ごとに文化や風景が多彩です。',
 US:'北アメリカに広がり、大西洋と太平洋に面する国。大都市から山岳地帯まで、地域によって風景が大きく異なります。',
 GB:'イングランド、スコットランド、ウェールズ、北アイルランドからなる国。歴史ある都市と起伏に富む風景が各地に広がります。',
 ES:'イベリア半島の大部分を占め、地中海と大西洋に面する国。地域によって建築、言語、食文化にも違いがあります。',
 JP:'東アジアの太平洋に位置する島国。南北に長い列島には、山地、海辺、四季折々の景色が広がります。',
 NZ:'南太平洋に位置し、北島と南島を中心に構成される国。火山地形、湖、フィヨルドなどの自然景観で知られます。'
});
/* @reader-country-data@ */
// Track the photograph that actually loaded, including a fallback after failure.
const displayedCountryCoverAssets=new Map();
// Editorial photo selection standard (v2): recognition > scenic ambiguity.
// All approved country-cover photographs must be licensed and attributed.
// Rank within each country; never let JSON insertion order choose the cover.
// 100 = iconic, instantly identifiable landmark; 80 = recognizable national
// landscape; below 60 = contextual only, unsuitable as a lead image.
// Maintain at least two high-quality, independently hosted options per country.

// Every catalogued country has a substantive, evidence-based introduction.
// Curated guides remain richer; new countries use the released article and
// geographic catalog rather than returning to the old one-line placeholder.
// Country Portrait: culture and everyday appeal, with a separately
// verified, time-bounded current topic. Tourist destinations live ONLY in
// the article's independent 30-second microtravel module.
let todayCountryIntroRequest=0;
let countryHighlightsPromise=null;
function loadCountryHighlights(){
 if(!countryHighlightsPromise)countryHighlightsPromise=fetch('./country-highlights.json',{cache:'no-store'})
  .then(response=>{if(!response.ok)throw Error('country highlights unavailable');return response.json();})
  .then(data=>data&&data.version===1&&data.highlights&&typeof data.highlights==='object'
   &&!Array.isArray(data.highlights)?data.highlights:{})
  .catch(()=>{countryHighlightsPromise=null;return {}});
 return countryHighlightsPromise;
}
function currentCountryHighlight(highlights,code,today=localDate(new Date())){
 const rows=highlights?.[code];
 if(!Array.isArray(rows))return null;
 // Reject stale/future-dated stories, invalid sources, and unsigned editorial claims.
 const valid=rows.filter(item=>item&&typeof item.title==='string'&&item.title.trim()
  &&typeof item.body==='string'&&item.body.trim()
  &&/^\d{4}-\d{2}-\d{2}$/.test(item.validFrom||'')
  &&/^\d{4}-\d{2}-\d{2}$/.test(item.validThrough||'')
  &&/^\d{4}-\d{2}-\d{2}$/.test(item.checkedOn||'')
  &&item.validFrom<=today&&today<=item.validThrough&&item.checkedOn<=today
  &&item.checkedOn<=item.validThrough
  &&(Date.parse(today+'T00:00:00Z')-Date.parse(item.checkedOn+'T00:00:00Z'))/86400000<=30
  &&typeof item.sourceName==='string'&&item.sourceName.trim()
  &&typeof item.sourceUrl==='string'&&/^https:\/\//.test(item.sourceUrl)
  &&safeUrl(item.sourceUrl)!=='#');
 return valid.sort((a,b)=>b.checkedOn.localeCompare(a.checkedOn))[0]||null;
}
function todayCountryIntro(item){
 if(TODAY_COUNTRY_INTROS[item.code])return TODAY_COUNTRY_INTROS[item.code];
 const region=countryRecord(item.code)?.region;
 return region
  ?item.name+'は'+region+'に位置しています。文化や日常の魅力について、確かな資料を確認しながら紹介を充実させています。'
  :item.name+'の暮らしや文化について、確認できた情報から紹介を準備しています。';
}
let countryReturnTarget=null;
let countryReturnScrollY=0;
function hideTodayCountryIntro(restoreMap=true){
 const wasOpen=document.body.classList.contains('country-detail-mode');
 todayCountryIntroRequest++;
 $('todayMapIntro').hidden=true;
 document.body.classList.remove('country-detail-mode');
 document.querySelectorAll('.today-map-pin').forEach(pin=>pin.setAttribute('aria-expanded','false'));
 if(wasOpen&&restoreMap===true){
  const target=countryReturnTarget?.isConnected?countryReturnTarget:$('todayMapSection');
  const returnY=countryReturnScrollY;
  requestAnimationFrame(()=>{
   if(document.body.classList.contains('country-detail-mode'))return;
   target.focus?.({preventScroll:true});
   // Do not jump to a map or list: recover the exact position before opening.
   const root=document.documentElement,oldBehavior=root.style.scrollBehavior;
   root.style.scrollBehavior='auto';
   window.scrollTo(0,returnY);
   requestAnimationFrame(()=>{root.style.scrollBehavior=oldBehavior;});
  });
 }
}
// Country portraits use the locally bundled, rights-checked photo first.
// Never replace an available packaged photograph with a remote thumbnail.
// The UK remote-only legacy item remains explicitly marked remoteOnly.
function countryPhotoSourceUrls(item){
 if(item.asset&&/^assets\/travel\/[a-z0-9-]+\.jpg$/.test(item.asset))
  return ['./'+item.asset];
 if(item.remoteOnly){
  const highRes=item.hiResUrl||item.url;
  return typeof highRes==='string'&&/^https:\/\//.test(highRes)?[highRes]:[];
 }
 return [];
}
function countryPhotoIsSharpEnough(image){
 // Country portraits should be sharp on high-density phones.
 // The publisher now prefers locally bundled 1280px photographs for every
 // vetted country cover; a 500px image is not stretched into a large hero.
 return image.naturalWidth>=1000&&image.naturalHeight>=540;
}
function showTodayCountryIntro(item){
 closeWorldPassport(false);
 countryReturnTarget=document.activeElement;
 countryReturnScrollY=window.scrollY;
 $('worldExplore').open=true;
 const requestId=++todayCountryIntroRequest,currentCode=item.code;
 const guide=TODAY_COUNTRY_GUIDES[currentCode];
 $('todayMapIntro').dataset.countryCode=currentCode;
 $('todayMapIntroName').textContent=item.name;
 $('todayMapIntroLead').textContent=guide?guide.lead:item.name+'の魅力を、文化と暮らしから';
 $('todayMapIntroBody').textContent=guide
  ?guide.body
  :todayCountryIntro(item)+' 観光名所を案内する「30秒の小旅行」とは別に、この国の特色を紹介します。';
 const facts=$('todayMapIntroFacts');
 facts.replaceChildren();
 const guideSource=$('todayMapIntroGuideSource');
 guideSource.hidden=!guide?.sourceUrl||safeUrl(guide.sourceUrl)==='#';
 if(!guideSource.hidden){guideSource.href=safeUrl(guide.sourceUrl);guideSource.textContent='国紹介の参考資料：'+(guide.sourceName||'公式観光情報');}
 else guideSource.removeAttribute('href');
 (guide?guide.facts:['地域：'+(countryRecord(currentCode)?.region||'確認中')])
  .forEach(value=>{const chip=document.createElement('span');chip.textContent=value;facts.append(chip);});
 // News articles are never silently repurposed into a cultural description.
 // A current topic appears only after date/source verification.
 const current=$('todayMapIntroCurrent');
 current.hidden=true;
 $('todayMapIntroCurrentTitle').textContent='';
 $('todayMapIntroCurrentBody').textContent='';
 $('todayMapIntroCurrentSource').removeAttribute('href');
 const source=$('todayMapIntroCurrentSource');
 loadCountryHighlights().then(all=>{
  if(requestId!==todayCountryIntroRequest||$('todayMapIntro').hidden||
     $('todayMapIntro').dataset.countryCode!==currentCode)return;
  const topic=currentCountryHighlight(all,currentCode);
  if(!topic)return;
  $('todayMapIntroCurrentTitle').textContent=topic.title;
  $('todayMapIntroCurrentBody').textContent=topic.body;
  $('todayMapIntroCurrentDate').textContent='確認：'+topic.checkedOn+' ／ 掲載期限：'+topic.validThrough;
  source.href=safeUrl(topic.sourceUrl);
  source.textContent='出典：'+topic.sourceName;
  current.hidden=false;
 });
 // National portrait photographs are an independently reviewed editorial
 // collection. NEVER import travel-stops here: those show famous attractions
 // in a different module and are not the same as a national portrait.
 const figure=$('todayMapIntroFigure'),photo=$('todayMapIntroImage');
 const status=$('todayMapIntroPhotoStatus');
 photo.onload=null;photo.onerror=null;
 photo.removeAttribute('src');
 const approvedPhotos=(TODAY_COUNTRY_PHOTOS[currentCode]||[])
  .filter(p=>(p.asset||p.remoteOnly)&&p.url&&p.author&&p.license&&p.place&&p.caption
    &&!p.avoidCover&&countryPhotoPriority(currentCode,p)>=80)
  .slice().sort((a,b)=>countryPhotoPriority(currentCode,b)-countryPhotoPriority(currentCode,a));
 displayedCountryCoverAssets.delete(currentCode);
 figure.hidden=true;
 status.hidden=false;
 status.textContent=approvedPhotos.length?'高画質の写真を読み込み中…':'国の写真は準備中です。文化の紹介はご覧いただけます。';
 let photoIndex=0,sourceIndex=0;
 function loadNextCountryPhoto(){
  if(requestId!==todayCountryIntroRequest||$('todayMapIntro').hidden||
     $('todayMapIntro').dataset.countryCode!==currentCode)return;
  const chosen=approvedPhotos[photoIndex];
  if(!chosen){
   figure.hidden=true;
   status.hidden=false;
   status.textContent='鮮明な写真を読み込めませんでした。国の紹介は引き続きご覧いただけます。';
   return;
  }
  const sources=countryPhotoSourceUrls(chosen);
  if(sourceIndex>=sources.length){
   sourceIndex=0;photoIndex++;
   loadNextCountryPhoto();
   return;
  }
  photo.alt=chosen.place+'の風景写真';
  photo.onload=()=>{
   if(requestId!==todayCountryIntroRequest)return;
   if(!countryPhotoIsSharpEnough(photo)){
    sourceIndex++;
    loadNextCountryPhoto();
    return;
   }
   figure.hidden=false;
   status.hidden=true;
   displayedCountryCoverAssets.set(currentCode,chosen.asset||'');
   const caption=$('todayMapIntroCaption');
   caption.textContent=chosen.caption+'　撮影：'+chosen.author+' ／ '+chosen.license;
   if(chosen.sourcePage&&safeUrl(chosen.sourcePage)!=='#'){
    const link=document.createElement('a');
    link.href=safeUrl(chosen.sourcePage);
    link.target='_blank';link.rel='noopener noreferrer';
    link.textContent=' ／ 写真の出典';
    caption.append(link);
   }
  };
  photo.onerror=()=>{
   if(requestId!==todayCountryIntroRequest)return;
   sourceIndex++;
   loadNextCountryPhoto();
  };
  photo.src=sources[sourceIndex];
 }
 const read=$('todayMapIntroRead');
 const hasNews=Array.isArray(item.indices)&&item.indices.length>0;
 read.dataset.action=hasNews?'news':'quiz';
 read.dataset.countryCode=currentCode;
 if(hasNews){
  read.textContent=item.name+'のニュースを読む（'+item.indices.length+'本）';
  read.dataset.storyIndex=String(item.indices[0]);
 }else{
  read.textContent='この国の写真付き3択クイズに挑戦';
  read.removeAttribute('data-story-index');
 }
 const trip=$('todayMapIntroTravel');
 trip.hidden=true;
 trip.replaceChildren();
 $('todayMapIntro').hidden=false;
 document.body.classList.add('country-detail-mode');
 if(!hasNews)renderApprovedCountryTrip(item,requestId);
 document.querySelectorAll('.today-map-pin').forEach(pin=>
  pin.setAttribute('aria-expanded',String(pin.dataset.countryCode===currentCode)));
 if(approvedPhotos.length)loadNextCountryPhoto();
 $('todayMapIntro').scrollTop=0;
 $('todayMapIntroName').focus({preventScroll:true});
}
// Country centroid pins stay geographically anchored. On narrow displays,
// push only the visible marker aside when two 44px tap targets would overlap,
// then draw a leader from the true representative point to its displaced pin.
function approvedAtlasItems(){
 // Only the exact, canonical approval list can create standalone country links.
 // A geographical catalog entry by itself does not authorize any content.
 return APPROVED_COUNTRY_CODES.map(code=>{
  const record=countryRecord(code);
  return record?{code:record.code,name:record.name,indices:[]}:null;
 }).filter(Boolean);
}
function renderApprovedAtlas(){
 const list=$('approvedAtlasList');
 list.replaceChildren();
 const countries=approvedAtlasItems();
 $('approvedAtlasCount').textContent=countries.length
  ?'出典確認済み '+countries.length+'か国から選ぶ':'公開承認済みの国を読み込み中…';
 countries.forEach(item=>{
  const button=document.createElement('button');
  button.type='button';
  button.className='approved-atlas-country';
  button.textContent=item.name+'の国紹介';
  button.dataset.countryCode=item.code;
  button.setAttribute('aria-controls','todayMapIntro');
  button.setAttribute('aria-label',item.name+'の国紹介と小旅行を開く');
  button.addEventListener('click',()=>showTodayCountryIntro(item));
  list.append(button);
 });
}
function approvedAtlasTravelOptions(item,stops){
 const primaryCover=(TODAY_COUNTRY_PHOTOS[item.code]||[])
  .filter(p=>p.asset&&!p.avoidCover&&!p.remoteOnly)
  .sort((a,b)=>countryPhotoPriority(item.code,b)-countryPhotoPriority(item.code,a))[0]?.asset;
 const chosenCover=displayedCountryCoverAssets.get(item.code)||primaryCover;
 const questions=typeof WORLD_PASSPORT_QUIZZES==='undefined'?[]:
  (WORLD_PASSPORT_QUIZZES[item.code]||[]);
 const quizKeys=new Set(questions.map(q=>q.photoKey));
 const options=Object.entries(stops||{}).filter(([key,stop])=>
  stop&&stop.country===item.name&&!stop.coverOnly&&!stop.quizOnly
  &&stop.photoAsset!==chosenCover&&approvedTravelCover(stop)
  &&/^assets\/travel\/[a-z0-9-]+\.jpg$/.test(stop.photoAsset||'')
  &&String(stop.photo||'').startsWith('https://thumb.wikimedia.org/wikipedia/commons/thumb/')
  &&String(stop.photoPage||'').startsWith('https://commons.wikimedia.org/wiki/File:')
  &&String(stop.licenseUrl||'').startsWith('https://creativecommons.org/')
  &&stop.author&&stop.license&&stop.photoCaption
  &&Array.isArray(stop.travelStory)&&stop.travelStory.length===2
  &&stop.travelStory.every(text=>typeof text==='string'&&text.trim().length>=110)
  &&Array.isArray(stop.historicalSources)&&stop.historicalSources.some(source=>
    source?.name&&String(source.url||'').startsWith('https://')));
 const independent=options.filter(([key])=>!quizKeys.has(key));
 const choices=independent.length?independent:options;
 // The named travel postcard is preferred to a photograph attached to an
 // unrelated old news story; credits always come from the exact same stop.
 return choices.sort((a,b)=>Number(b[0].endsWith('-postcard'))-
  Number(a[0].endsWith('-postcard'))||a[0].localeCompare(b[0]));
}
async function renderApprovedCountryTrip(item,requestId){
 const panel=$('todayMapIntroTravel');
 panel.hidden=false;
 panel.textContent='歴史資料を添えた小旅行を読み込み中…';
 const stops=await loadTravelStops();
 if(requestId!==todayCountryIntroRequest||$('todayMapIntro').hidden||
    $('todayMapIntro').dataset.countryCode!==item.code)return;
 const options=approvedAtlasTravelOptions(item,stops);
 if(!options.length){
  panel.textContent='この国の出典確認済みの小旅行は準備中です。';
  return;
 }
 function mount(at){
  if(requestId!==todayCountryIntroRequest||!panel.isConnected||panel.hidden)return;
  const stop=options[at]?.[1];
  if(!stop){panel.textContent='旅行写真を読み込めませんでした。';return;}
  panel.innerHTML=travelPostcardHtml({country:item.name},stop,true);
  const img=panel.querySelector('.travel-photo');
  if(!img)return;
  img.addEventListener('error',()=>{
   if(requestId!==todayCountryIntroRequest||!img.isConnected||panel.hidden)return;
   if(!img.dataset.remoteTried&&img.dataset.remotePhoto){
    img.dataset.remoteTried='true';
    img.src=img.dataset.remotePhoto;
    return;
   }
   if(at+1<options.length){mount(at+1);return;}
   img.hidden=true;
   const message=panel.querySelector('.travel-photo-error');
   if(message)message.hidden=false;
  });
 }
 mount(0);
}
function positionTodayMapPins(){
 const layer=$('todayMapPins');
 if(!layer||!layer.clientWidth||!layer.clientHeight)return;
 layer.querySelectorAll('.today-map-tether').forEach(element=>element.remove());
 const width=layer.clientWidth,height=layer.clientHeight;
 const used=[];
 const offsets=[[0,0],[24,30],[-24,30],[24,-30],[-24,-30],
  [-49,0],[49,0],[0,49],[0,-49],[50,30],[-50,30],
  [50,-30],[-50,-30],[0,74],[0,-74],[74,0],[-74,0]];
 for(const pin of layer.querySelectorAll('.today-map-pin')){
  const anchorX=Number(pin.dataset.mapX)*width/100;
  const anchorY=Number(pin.dataset.mapY)*height/100;
  const radius=22;
  let chosen=null;
  for(const [dx,dy] of offsets){
   const x=anchorX+dx,y=anchorY+dy;
   if(x<radius||y<radius||x>width-radius||y>height-radius)continue;
   if(used.every(point=>Math.hypot(point.x-x,point.y-y)>=46)){
    chosen={x,y,dx,dy};break;
   }
  }
  if(!chosen){
   // Fallback for unusually crowded editions: keep the marker within the
   // map and choose the largest separation instead of covering another pin.
   const options=offsets.map(([dx,dy])=>({
    x:Math.max(radius,Math.min(width-radius,anchorX+dx)),
    y:Math.max(radius,Math.min(height-radius,anchorY+dy))
   }));
   options.sort((a,b)=>{
    const gap=point=>used.length?Math.min(...used.map(p=>Math.hypot(p.x-point.x,p.y-point.y))):10000;
    return gap(b)-gap(a);
   });
   chosen={...options[0],dx:options[0].x-anchorX,dy:options[0].y-anchorY};
  }
  used.push(chosen);
  pin.style.setProperty('--map-dx',chosen.dx+'px');
  pin.style.setProperty('--map-dy',chosen.dy+'px');
  if(Math.hypot(chosen.dx,chosen.dy)<2){
   pin.removeAttribute('aria-description');
   continue;
  }
  pin.setAttribute('aria-description','近接する国との重複を避けています。線の起点が国の代表位置です。');
  const tether=document.createElement('span');
  tether.className='today-map-tether';
  tether.setAttribute('aria-hidden','true');
  tether.style.left=anchorX+'px';tether.style.top=anchorY+'px';
  tether.style.width=Math.hypot(chosen.dx,chosen.dy)+'px';
  tether.style.transform='rotate('+Math.atan2(chosen.dy,chosen.dx)+'rad)';
  layer.insertBefore(tether,pin);
 }
}
if(typeof window!=='undefined')window.addEventListener('resize',()=>requestAnimationFrame(positionTodayMapPins));
function renderTodayMap(){
 const section=$('todayMapSection');
 if(!section)return;
 const published=edition.status==='published';
 const actuallyToday=published&&edition.editionDate===localDate(new Date());
 $('todayMapTitle').textContent=actuallyToday?'本日の配信国':published?'最新配信号の国':'体験版のニュースの舞台';
 $('todayMapDate').textContent=published?edition.editionDate+' 発行':'体験版';
 const pins=$('todayMapPins'),legend=$('todayMapLegend');
 pins.replaceChildren();legend.replaceChildren();hideTodayCountryIntro();closeWorldPassport();
 renderApprovedAtlas();
 if(!countryCatalog.length){
  $('todayMapNote').textContent='国の位置情報を読み込んでいます。';
  return;
 }
 const countries=currentIssueCountries();
 // A four-story issue can legitimately cover only three distinct countries.
 // Explain the deduplicated mapping instead of inventing a fourth country pin.
 const repeated=countries.filter(c=>c.indices.length>1)
  .map(c=>c.name+' '+c.indices.length+'本');
 const countNote='実話'+edition.stories.length+'本・'+countries.length+'カ国'+
   (repeated.length?'（'+repeated.join('、')+'）':'');
 $('todayMapTitle').textContent=(actuallyToday?'本日の配信国':published?'最新配信号の国':'体験版のニュースの舞台')+
  ' · '+countries.length+'カ国';
 let marked=0;
 countries.forEach((item,i)=>{
  const color=TODAY_MAP_COLORS[i%TODAY_MAP_COLORS.length];
  if(item.point){
   marked++;
   const pin=document.createElement('button');
   pin.type='button';
   pin.className='today-map-pin';
   pin.dataset.countryCode=item.code;
   pin.textContent=String(i+1);
   pin.title=item.name+'の紹介を表示';
   pin.setAttribute('aria-label',item.name+'の紹介を表示');
   pin.setAttribute('aria-controls','todayMapIntro');
   pin.setAttribute('aria-expanded','false');
   pin.style.setProperty('--country-color',color);
   pin.style.left=item.point.x.toFixed(3)+'%';
   pin.style.top=item.point.y.toFixed(3)+'%';
   pin.dataset.mapX=String(item.point.x);
   pin.dataset.mapY=String(item.point.y);
   pin.addEventListener('click',()=>showTodayCountryIntro(item));
   pins.append(pin);
  }
  const button=document.createElement('button');
  button.type='button';button.className='today-map-country';
  button.style.setProperty('--country-color',color);
  button.dataset.countryCode=item.code;
  button.dataset.countryName=item.name;
  button.dataset.countryLabel=(i+1)+' · '+item.name;
  button.setAttribute('aria-controls','todayCountryQuiz');
  button.setAttribute('aria-expanded','false');
  button.addEventListener('click',()=>startWorldPassport(item));
  legend.append(button);
 });
 if(!countries.length){
  $('todayMapNote').textContent='掲載国を特定できる記事はありません。';
 }else{
  const extra=marked<countries.length?' 一部の国は位置が未登録でも、国名ボタンのクイズには参加できます。':'';
  $('todayMapNote').textContent=countNote+'。地図のピンと国別クイズのボタンは、重複を除いた国数です。写真付きの国紹介やクイズを楽しめます。位置は国・地域の代表地点で、ニュースの発生現場ではありません。'+extra;
 }
 updateWorldPassportButtons();
 positionTodayMapPins();
}
function setReleaseStatus(message){$('releaseStatus').textContent=message}
// Bind UI events outside the pure country-coordinate module used by regression tests.
$('worldExplore').addEventListener('toggle',()=>{
 if($('worldExplore').open){
  // Closed details have zero map dimensions; recompute after layout on opening.
  requestAnimationFrame(positionTodayMapPins);
 }else{
  hideTodayCountryIntro(false);
  closeWorldPassport(false);
 }
});
$('todayMapIntroClose').addEventListener('click',()=>hideTodayCountryIntro());
$('todayMapIntroCloseBottom').addEventListener('click',()=>hideTodayCountryIntro());
$('todayMapIntro').addEventListener('keydown',event=>{
 if(event.key==='Escape'){
  event.preventDefault();hideTodayCountryIntro();return;
 }
 if(event.key!=='Tab')return;
 const focusables=[...$('todayMapIntro').querySelectorAll('a[href],button:not([disabled])')]
  .filter(element=>!element.closest('[hidden]')&&element.getClientRects().length);
 if(!focusables.length)return;
 const first=focusables[0],last=focusables[focusables.length-1];
 if(event.shiftKey&&(document.activeElement===first||
    !focusables.includes(document.activeElement))){
  event.preventDefault();last.focus();
 }else if(!event.shiftKey&&document.activeElement===last){
  event.preventDefault();first.focus();
 }
});
$('todayMapIntroRead').addEventListener('click',()=>{
 const read=$('todayMapIntroRead');
 if(read.dataset.action==='quiz'){
  const item=approvedAtlasItems().find(row=>row.code===read.dataset.countryCode);
  if(item)startWorldPassport(item);
  return;
 }
 const index=Number(read.dataset.storyIndex);
 if(read.dataset.action==='news'&&Number.isInteger(index)&&
    index>=0&&index<edition.stories.length)openAtlasStory(index);
});

function displayReleaseStatus(){
 const today=localDate(new Date());
 if(edition.status==='demo'){setReleaseStatus('公開号を確認できないため、体験版を表示しています。');return}
 const date=edition.editionDate||'日付不明';
 if(date===today){setReleaseStatus('本日 '+date+' 公開 · '+edition.stories.length+'本。公開後の更新を自動確認します。');return}
 setReleaseStatus('前回の公開号 '+date+' · '+edition.stories.length+'本。本日分の公開後に自動更新します。');
}
// English-only supplementary text is not a verified Japanese translation.
function isJapaneseText(value){return /[ぁ-んァ-ヶ一-龯々]/.test(String(value||''))}
function storyDetailHtml(story){
 // Keep the reporting separate from legacy "AI's view" paragraphs.
 const detail=String(story.detail||'').trim()
  .replace(/\n\s*\n\s*ここからはAIの見方。[\s\S]*$/,'').trim();
 if(isJapaneseText(detail))return detail.split(/\n\s*\n/).map(part=>part.trim()).filter(Boolean)
  .map(part=>'<p class="detailtext">'+escapeHtml(part)+'</p>').join('');
 const overview=String(story.summary||'').trim();
 return '<p class="detail-language-note">日本語の詳しい本文は準備中です。以下は掲載済みの日本語概要です。英語の補足文は必要な場合のみ開いて確認できます。</p>'
  +'<p class="detailtext">'+escapeHtml(overview)+'</p>'
  +(detail?'<details class="original-detail"><summary>英語の補足文を表示</summary><p class="original-warning">登録された英語の補足文です。日本語概要の翻訳ではなく、出典で確認できない解釈や表現を含む場合があります。</p><p lang="en" class="detailtext">'+escapeHtml(detail)+'</p></details>':'');
}
function storyEvidenceHtml(story){
 const supplied=Array.isArray(story.verificationUrls)?story.verificationUrls:[];
 const sources=[...new Set(supplied.filter(u=>typeof u==='string'&&safeUrl(u)!=='#'&&u!==story.sourceUrl))];
 if(!sources.length)return '';
 return '<details class="source-evidence"><summary>追加の確認資料（'+sources.length+'件）</summary><ul>'+
  sources.map(url=>'<li><a href="'+escapeHtml(safeUrl(url))+'" target="_blank" rel="noopener noreferrer">'+escapeHtml(new URL(url).hostname.replace(/^www\./,''))+' ↗</a></li>').join('')+
  '</ul></details>';
}
function storyCorrectionHtml(story){
 const note=typeof story.correctionNote==='string'?story.correctionNote.trim():'';
 return note?'<p class="correction-note"><strong>編集訂正：</strong>'+escapeHtml(note)+'</p>':'';
}
function storyAttributionHtml(story){
 const note=story.sourceBasis==='original-report'&&typeof story.attributionNote==='string'
  ?story.attributionNote.trim():'';
 return note?'<p class="source-attribution"><strong>情報源について：</strong>'+escapeHtml(note)+'</p>':'';
}
// Safe, locally bundled editorial illustrations. None are documentary
// photos; never substitute travel photography or publisher portraits.
const NEWS_ARTWORK=Object.freeze({
 'uk-french-weir-swimming-2026':'uk-river-water-warning.svg',
 'mussolini-colador-2026':'spain-mussels-colander-pan.svg',
 'jp-gov-youtuber-pr-2026':'japan-policy-youtuber-pr.svg',
 'nz-cricket-collapse-2026':'nz-cricket-comeback.svg',
 'cheonan-painters-coffee-rescue-2026':'coffee-rescue.svg',
 'guaira-degavar-road-marking-2026':'road-typo.svg',
 'albert-lea-mcnugget-monkey-diaper-police-2026':'monkey-patrol.svg',
 'argentina-goalkeeper-throws-own-goal-2026':'own-goal-keeper.svg',
 'france-candy-police-mock-wanted-2026':'police-sweets-wanted.svg',
 'mickey-83-tattoos-disney-unvisited-2026':'mouse-83-tattoos.svg',
 'italy-toilet-ai-python-48-hour-search-2026':'ai-python-toilet.svg',
 'drew-carey-price-right-early-reveal-2026':'game-show-price-board.svg',
 'mainz-sewer-search-lost-drone-2026':'drone-sewer-search.svg',
 'kusel-lost-handcuff-key-police-help-2026':'lost-handcuff-key.svg'
});
const NEWS_ART_FALLBACK=Object.freeze({
 work:'category-work.svg',company:'category-company.svg',
 person:'category-person.svg',sports:'category-sports.svg'
});
const NEWS_COMIC_KICKERS=Object.freeze({
 'uk-french-weir-swimming-2026':'遊泳禁止でも川へ',
 'mussolini-colador-2026':'ざるもフライパンも',
 'jp-gov-youtuber-pr-2026':'政府PRに都市伝説',
 'nz-cricket-collapse-2026':'逆転のクリケット',
 'cheonan-painters-coffee-rescue-2026':'注文がSOS',
 'guaira-degavar-road-marking-2026':'道路に誤字',
 'albert-lea-mcnugget-monkey-diaper-police-2026':'不審者はサル',
 'argentina-goalkeeper-throws-own-goal-2026':'ゴールに投げちゃった',
 'france-candy-police-mock-wanted-2026':'お礼が指名手配!?',
 'mickey-83-tattoos-disney-unvisited-2026':'タトゥー83個で未訪問'
});
function shortComicKicker(story){
 // New editions use the editor-verified article label, never invented details.
 const line=NEWS_COMIC_KICKERS[story?.id]||story?.label||story?.categoryLabel||'世界の実話';
 return String(line).trim().slice(0,18);
}
/* Unmapped nightly stories get a distinct, offline-safe, generated vector.
   This is symbolic editorial artwork, never a supposed scene photograph. */
function fallbackNewsArt(story){
 const key=String(story?.id||story?.title||'world-letter');
 let hash=2166136261;
 for(let i=0;i<key.length;i++)hash=Math.imul(hash^key.charCodeAt(i),16777619)>>>0;
 const themes=[
  ['#F9E2AB','#EFA1B9','#284D6B'],['#BEE7DF','#91C9DF','#264D69'],
  ['#CEC6F6','#F3B8BD','#414575'],['#D8E7AD','#F7C59D','#476C5E'],
  ['#A9E1EE','#E3C3F2','#375C75'],['#FBD7AF','#FFC4D1','#635076'],
  ['#CCE5F4','#F6D7A3','#36566B'],['#A4DFCC','#F5AF99','#375E6B']
 ];
 const [a,b,ink]=themes[hash%themes.length];
 const detail=String(story?.title||'')+' '+String(story?.summary||'');
 const motifs=[
  // Bubbles and waves.
  '<path d="M130 312q62-31 124 0t125 0t125 0" fill="none" stroke="#7DC7C8" stroke-width="25" stroke-linecap="round"/><circle cx="340" cy="150" r="63" fill="#C3F2E9" stroke="#31536D" stroke-width="11"/><circle cx="580" cy="200" r="36" fill="#fff" opacity=".7"/>',
  // Cooking pot and steam.
  '<path d="M172 235h390q-9 139-180 139T172 235Z" fill="#FFF4DD" stroke="#31536D" stroke-width="13"/><path d="M174 234h394" stroke="#31536D" stroke-width="18"/><path d="M255 183q-28-36 3-65m97 67q-27-37 3-69m94 66q-27-38 3-69" fill="none" stroke="#E39C75" stroke-width="13" stroke-linecap="round"/>',
  // Question mark and speech panel.
  '<rect x="170" y="114" width="370" height="225" rx="37" fill="#FFF9EA" stroke="#31536D" stroke-width="13"/><path d="m330 335-25 58 91-59" fill="#FFF9EA" stroke="#31536D" stroke-width="13" stroke-linejoin="round"/><text x="365" y="282" font-family="system-ui,sans-serif" text-anchor="middle" font-size="205" font-weight="900" fill="#DC7481">?</text>',
  // Score and moving ball.
  '<rect x="135" y="110" width="281" height="179" rx="30" fill="#31536D"/><path d="m190 236 66-61 52 29 47-76" fill="none" stroke="#C1E9CC" stroke-width="17" stroke-linecap="round"/><circle cx="554" cy="260" r="89" fill="#fff" stroke="#31536D" stroke-width="14"/><path d="m516 217 40-14 44 38-13 50-48 11-39-36z" fill="#31536D"/>',
  // Public transport and arrow.
  '<rect x="147" y="148" width="382" height="189" rx="34" fill="#FFF6E3" stroke="#31536D" stroke-width="14"/><path d="M205 184h265M216 338v35m237-35v35" stroke="#31536D" stroke-width="16" stroke-linecap="round"/><circle cx="233" cy="329" r="26" fill="#31536D"/><circle cx="444" cy="329" r="26" fill="#31536D"/><path d="m526 130 69 45-68 42" fill="none" stroke="#D86D7B" stroke-width="20" stroke-linecap="round" stroke-linejoin="round"/>',
  // Office document and notification.
  '<rect x="205" y="86" width="289" height="290" rx="24" fill="#FFF8EC" stroke="#31536D" stroke-width="13"/><path d="M250 156h190m-190 57h155m-155 55h174" stroke="#7CB7B6" stroke-width="17" stroke-linecap="round"/><circle cx="553" cy="320" r="80" fill="#F4C18D" stroke="#31536D" stroke-width="11"/><path d="M553 270v66" stroke="#31536D" stroke-width="18" stroke-linecap="round"/><circle cx="553" cy="366" r="10" fill="#31536D"/>'
 ];
 let motif=hash%motifs.length;
 if(/川|水質|遊泳|泳|洪水|水浴/.test(detail))motif=0;
 else if(/料理|調理|魚|食|レシピ|鍋|フライパン/.test(detail))motif=1;
 else if(/動画|YouTub|SNS|広報|都市伝説/.test(detail))motif=2;
 else if(story?.category==='sports'||/試合|得点|選手|大会/.test(detail))motif=3;
 else if(/列車|鉄道|飛行機|車|道路|トンネル/.test(detail))motif=4;
 const label=escapeHtml(String(story?.label||'世界のまさか').slice(0,14));
 const country=escapeHtml(String(story?.country||'世界').slice(0,14));
 const svg=[
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 480" role="img" aria-label="記事内容を象徴する創作イラスト">',
  '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="',a,'"/><stop offset="1" stop-color="',b,'"/></linearGradient></defs>',
  '<rect width="800" height="480" rx="28" fill="url(#bg)"/>',
  '<circle cx="690" cy="70" r="141" fill="#fff" opacity=".22"/>',
  '<path d="M0 426Q200 381 407 428T800 394V480H0Z" fill="',ink,'" opacity=".12"/>',
  motifs[motif],
  '<rect x="33" y="397" width="734" height="67" rx="20" fill="',ink,'" opacity=".95"/>',
  '<text x="59" y="438" font-family="system-ui,sans-serif" font-size="29" font-weight="800" fill="#fff">',
  country,' · ',label,'</text>',
  '<path d="M87 76h45m-22-22v45M718 333h38m-19-19v38" stroke="#fff" stroke-width="9" stroke-linecap="round" opacity=".8"/>',
  '</svg>'
 ].join('');
 return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
}
function hasDailyGeneratedImage(story){
 const date=String(typeof edition==='undefined'?'':edition?.editionDate||'');
 return Boolean(story?.imageType==='ai-generated-photorealistic-impression'&&
  typeof story.imagePath==='string'&&
  /^\d{4}-\d{2}-\d{2}$/.test(date)&&
  story.imagePath.startsWith('assets/news-generated/'+date+'/')&&
  /^assets\/news-generated\/\d{4}-\d{2}-\d{2}\/[a-z0-9-]+\.webp$/.test(story.imagePath));
}
function newsArt(story){
 if(hasDailyGeneratedImage(story))return './'+story.imagePath;
 const name=NEWS_ARTWORK[story?.id]||NEWS_ART_FALLBACK[story?.category]||NEWS_ART_FALLBACK.person;
 if(NEWS_ARTWORK[story?.id])return './assets/news/'+name;
 return fallbackNewsArt(story);
}
function renderIssueGallery(){
 const target=$('issueGallery');
 $('galleryHeading').textContent='世界の「まさか」'+edition.stories.length+'コマ劇場';
 target.replaceChildren();
 for(const [index,story] of edition.stories.entries()){
  const button=document.createElement('button');
  button.type='button';button.className='gallery-tile';
  button.setAttribute('aria-controls','articleReader');
  button.setAttribute('aria-expanded','false');
  button.setAttribute('aria-label',(index+1)+'本目：'+String(story.title||'掲載記事')+'を読む');
  const img=document.createElement('img');
  img.className='gallery-art';img.src=newsArt(story);
   img.addEventListener('error',()=>{img.src=fallbackNewsArt(story)},{once:true});
  img.alt='';img.loading=index===0?'eager':'lazy';img.decoding='async';
  img.width=800;img.height=480;
  const country=document.createElement('span');country.className='gallery-country';
  country.textContent=(index+1)+' · '+countryLabel(story.country);
  const kicker=document.createElement('span');kicker.className='gallery-kicker';
  kicker.textContent=shortComicKicker(story);
  const label=document.createElement('span');label.className='gallery-label';
  label.textContent=story.title||'世界のまさか';
  button.append(img);
   if(hasDailyGeneratedImage(story)){
    const imageLabel=document.createElement('span');
    imageLabel.className='gallery-image-label';
    imageLabel.textContent='イメージ画像（AI生成）';
    button.append(imageLabel);
   }
   button.append(country,kicker,label);
  button.addEventListener('click',()=>openAtlasStory(index));
  target.append(button);
 }
}
// News navigation is a separate reading screen with a shareable URL.
// Only the selected story's original evidence, humor and microtravel display.
let selectedArticleIndex=0;
// Reveal the one AI punchline as it enters the viewport, including after paging.
const quipRevealObserver='IntersectionObserver' in window
 ?new IntersectionObserver(entries=>{
   for(const entry of entries)if(entry.isIntersecting)entry.target.classList.add('quip-revealed');
  },{threshold:.35})
 :null;
function articleRouteHash(story){
 return '#story/'+encodeURIComponent(String(story.id||''));
}
function articleIndexFromRoute(){
 if(!location.hash.startsWith('#story/'))return -1;
 let id='';
 try{id=decodeURIComponent(location.hash.slice('#story/'.length));}
 catch(_){return -1;}
 return edition.stories.findIndex(story=>String(story.id||'')===id);
}
function openAtlasStory(index,fromRoute=false){
 if(!Number.isInteger(index)||index<0||index>=edition.stories.length)return;
 if(document.body.classList.contains('country-detail-mode'))hideTodayCountryIntro(false);
 if(document.body.classList.contains('quiz-detail-mode'))closeWorldPassport(false);
 const stage=$('articleReader');
 selectedArticleIndex=index;
 // A postcard remains optional and never survives navigation to another news story.
 closeOptionalTravelPanels();
 document.body.classList.add('news-detail-mode');
 stage.hidden=false;
 $('readerSelected').textContent='ニュース '+(index+1)+' / '+edition.stories.length;
 $('readerPrev').disabled=index===0;
 $('readerNext').disabled=index===edition.stories.length-1;
 $('readerPrev').setAttribute('aria-label','前のニュースへ');
 $('readerNext').setAttribute('aria-label','次のニュースへ');
 $('spotlight').hidden=false;
 // Keep the legacy article DOM available for release regression coverage,
 // but never show its overlapping list inside the dedicated reading screen.
 $('stories').hidden=true;
 document.querySelector('.sectionhead').hidden=true;
 $('intro').hidden=true;
 document.querySelector('.filters').hidden=true;
 $('empty').hidden=true;
 filter='all';applyFilter();
 $('empty').hidden=true;
 updateSpotlight();
 const quipCard=$('spotlight').querySelector('.spotlight-joke');
 if(quipCard){
  quipCard.classList.remove('quip-revealed');
  if(quipRevealObserver){quipRevealObserver.unobserve(quipCard);quipRevealObserver.observe(quipCard)}
  else quipCard.classList.add('quip-revealed');
 }
 $('spotlightAward').textContent='このニュースの詳しい話';
 const travel=$('spotlight').querySelector('[data-travel-slot]');
 if(travel)travel.dataset.travelSlot=String(index);
 renderTravelSlots();
 const body=$('spotlightBody');
 body.hidden=false;
 $('spotlightRead').setAttribute('aria-expanded','true');
 $('spotlightRead').textContent='本文を閉じる ↑';
 for(const [i,tile] of [...$('issueGallery').querySelectorAll('.gallery-tile')].entries()){
  tile.setAttribute('aria-expanded',String(i===index));
 }
 markRead(index);
 update();
 if(!fromRoute&&location.hash!==articleRouteHash(edition.stories[index])){
  history.pushState({newsArticleId:edition.stories[index].id},'',articleRouteHash(edition.stories[index]));
 }
 window.scrollTo(0,0);
 $('spotlightTitle').setAttribute('tabindex','-1');
 $('spotlightTitle').focus({preventScroll:true});
}
function closeArticleReader(fromRoute=false){
 const stage=$('articleReader');
 const selected=[...$('issueGallery').querySelectorAll('.gallery-tile')]
  .find(tile=>tile.getAttribute('aria-expanded')==='true');
 stage.hidden=true;
 document.body.classList.remove('news-detail-mode');
 for(const tile of $('issueGallery').querySelectorAll('.gallery-tile')){
  tile.setAttribute('aria-expanded','false');
 }
 if(!fromRoute&&location.hash.startsWith('#story/')){
  history.replaceState(null,'','#issueGallery');
 }
 if(!fromRoute){
  const target=selected||$('issueGallery');
  target.focus?.({preventScroll:true});
  $('issueGallery').scrollIntoView({
   behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',
   block:'start'
  });
 }
}
function syncArticleRoute(){
 const index=articleIndexFromRoute();
 if(index>=0)openAtlasStory(index,true);
 else closeArticleReader(true);
}
window.addEventListener('popstate',syncArticleRoute);
window.addEventListener('hashchange',syncArticleRoute);
$('readerBack').addEventListener('click',()=>closeArticleReader());
$('readerPrev').addEventListener('click',()=>openAtlasStory(selectedArticleIndex-1));
$('readerNext').addEventListener('click',()=>openAtlasStory(selectedArticleIndex+1));
function updateSpotlight(){
 const first=Array.isArray(edition.stories)?edition.stories[selectedArticleIndex]:null;
 $('spotlight').hidden=!first;
 if(!first)return;
 $('spotlightAward').textContent=edition.status==='demo'?'体験版の実話':edition.editionDate!==localDate(new Date())?'公開済みの便りから':'今夜の便りから';
 // This is the checked incident location, never the publisher's search market.
 $('spotlightLocation').textContent=first.country?'舞台：'+countryLabel(first.country):'舞台を確認中';
 $('spotlightTitle').textContent=first.title||'世界の実話';
 $('spotlightImage').onerror=()=>{$('spotlightImage').onerror=null;$('spotlightImage').src=fallbackNewsArt(first);$('spotlightImageCaption').textContent='イメージイラスト'};
 $('spotlightImage').src=newsArt(first);
 $('spotlightImageCaption').textContent=hasDailyGeneratedImage(first)?
   'イメージ画像（AI生成） · 報道写真ではありません':'イメージイラスト · 報道写真ではありません';
 const summary=String(first.summary||'').trim(),firstSentence=summary.split('。')[0].trim();
 $('spotlightBrief').textContent=firstSentence?firstSentence+(summary.includes('。')?'。':''):'実際に報じられた出来事を短く紹介します。';
 $('spotlightQuip').textContent=first.quip||'人間のやらかしに、AIが鋭くツッコミます。';
 $('spotlightRead').textContent=edition.status==='demo'?'体験版の話の続きへ ↓':'この話の続きへ ↓';
 $('spotlightRead').setAttribute('aria-expanded','false');
 const body=$('spotlightBody');
 body.hidden=true;
 body.innerHTML=`<p class="reported">報道日：${escapeHtml(String(first.reported||'出典を確認').replaceAll('.','-'))}</p><div class="article-narrative" aria-label="記事本文">${storyDetailHtml(first)}</div><p class="source">出典：<a href="${escapeHtml(safeUrl(first.sourceUrl))}" target="_blank" rel="noopener noreferrer">${escapeHtml(first.sourceName||'元記事を読む')} ↗</a></p>${storyEvidenceHtml(first)}${storyCorrectionHtml(first)}<div class="actions"><button type="button" class="share" data-share="${selectedArticleIndex}">この記事を共有</button></div>`;
}
$('spotlightRead').addEventListener('click',()=>{
 const panel=$('spotlightBody'),show=panel.hidden;
 panel.hidden=!show;
 $('spotlightRead').setAttribute('aria-expanded',String(show));
 $('spotlightRead').textContent=show?'閉じる ↑':(edition.status==='demo'?'体験版の話の続きへ ↓':'この話の続きへ ↓');
 if(show){markRead(selectedArticleIndex);panel.scrollIntoView({behavior:'smooth',block:'nearest'})}
});
/* @reader-travel@ */
function updateFilters(){
 const available=new Set(edition.stories.slice(1).map(s=>s.category));
 const controls=document.querySelector('.filters');
 controls.hidden=edition.stories.length<=3||available.size<=1;
 controls.querySelectorAll('[data-filter]').forEach(button=>{
  button.hidden=button.dataset.filter!=='all'&&!available.has(button.dataset.filter);
 });
 if(filter!=='all'&&!available.has(filter))filter='all';
}
// Source-verified quotations; reader-facing Japanese is an interpretive translation.
const DAILY_FAILURE_QUOTES=Object.freeze([{"ja":"失敗とは、より賢くやり直す機会にすぎない。","person":"ヘンリー・フォード","original":"Failure is only the opportunity more intelligently to begin again.","source":"『My Life and Work』","url":"https://www.gutenberg.org/cache/epub/7213/pg7213.html"},{"ja":"失敗はつらい。しかし、成功を目指して挑まないほうが、もっとつらい。","person":"セオドア・ルーズベルト","original":"It is hard to fail, but it is worse never to have tried to succeed.","source":"セオドア・ルーズベルト・センター","url":"https://www.theodorerooseveltcenter.org/quote/it-is-hard-to-fail-but-it-is-worse-never-to-have-tried-to-succeed-in-this-life-we-get-nothing-save-by-effort/"},{"ja":"望む結果を得ると決めたら、実現するまで試行を重ねる。","person":"トーマス・エジソン","original":"I go about it, and make trial after trial, until it comes.","source":"『Little Visits with Great Americans』","url":"https://www.gutenberg.org/files/48174/48174-h/48174-h.htm"},{"ja":"苦闘なくして、前進はない。","person":"フレデリック・ダグラス","original":"If there is no struggle, there is no progress.","source":"米国議会図書館","url":"https://www.loc.gov/item/2023632628/"},{"ja":"人生では、何かに失敗することは避けられない。","person":"J・K・ローリング","original":"Some failure in life is inevitable.","source":"ハーバード大学・2008年卒業式演説","url":"https://news.harvard.edu/gazette/story/2008/06/text-of-j-k-rowling-speech/"},{"ja":"失敗していないなら、そもそも挑戦していないのかもしれない。","person":"デンゼル・ワシントン","original":"If you don’t fail… you’re not even trying.","source":"ペンシルベニア大学・2011年卒業式演説","url":"https://almanac.upenn.edu/archive/volumes/v57/n34/comm-washington.html"},{"ja":"人生に打ちのめされることがあっても、信念を失うな。","person":"スティーブ・ジョブズ","original":"Sometimes life’s gonna hit you in the head with a brick. Don’t lose faith.","source":"スタンフォード大学・2005年卒業式演説","url":"https://news.stanford.edu/stories/2005/06/youve-got-find-love-jobs-says"},{"ja":"明日を実現する可能性を狭めるのは、今日の疑念だ。","person":"フランクリン・D・ルーズベルト","original":"The only limit to our realization of tomorrow will be our doubts of today.","source":"FDR大統領図書館・1945年演説草稿","url":"https://www.fdrlibrary.org/documents/356632/390886/wwguide_b-gPSEC7Ot.pdf/de6ade9d-0465-4e9e-aeda-ae118965f996"},{"ja":"大きく失敗する覚悟を持つ人だけが、大きなことを成し遂げられる。","person":"ロバート・F・ケネディ","original":"Only those who dare to fail greatly, can ever achieve greatly.","source":"ロバート・F・ケネディ人権センター・1966年演説","url":"https://kennedyhumanrights.org/speech/day-of-affirmation-address/"},{"ja":"正直に挑んだ末の失敗を恥じることはない。恥じるべきは、失敗を恐れることだ。","person":"ヘンリー・フォード","original":"There is no disgrace in honest failure; there is disgrace in fearing to fail.","source":"『My Life and Work』","url":"https://www.gutenberg.org/cache/epub/7213/pg7213.html"},{"ja":"失敗は、ほかの方法では学べなかった自分自身のことを教えてくれた。","person":"J・K・ローリング","original":"Failure taught me things about myself that I could have learned no other way.","source":"ハーバード大学・2008年卒業式演説","url":"https://news.harvard.edu/gazette/story/2008/06/text-of-j-k-rowling-speech/"},{"ja":"失敗した実験の一つひとつが、成功に一歩近づくことになる。","person":"デンゼル・ワシントン","original":"Every failed experiment is one step closer to success.","source":"ペンシルベニア大学・2011年卒業式演説","url":"https://almanac.upenn.edu/archive/volumes/v57/n34/comm-washington.html"}]);
function failureQuoteForDate(jstDate){
 const day=Date.parse(jstDate+'T00:00:00Z')/86400000;
 const index=Number.isFinite(day)?((Math.floor(day)%DAILY_FAILURE_QUOTES.length)+DAILY_FAILURE_QUOTES.length)%DAILY_FAILURE_QUOTES.length:0;
 return DAILY_FAILURE_QUOTES[index];
}
// No fictional past editions: the rotating quote feature began on 2026-11-20.
const DAILY_FAILURE_QUOTES_FIRST_DAY='2026-11-20';
const PAST_QUOTES_BATCH_SIZE=12;
let pastQuotesDate='',pastQuotesRendered=0;
function pastQuoteTotalDays(jstDate){
 const current=Date.parse(jstDate+'T00:00:00Z');
 const first=Date.parse(DAILY_FAILURE_QUOTES_FIRST_DAY+'T00:00:00Z');
 return Number.isFinite(current)?Math.max(0,Math.floor((current-first)/86400000)):0;
}
function pastQuoteEntries(jstDate,offset=0,limit=PAST_QUOTES_BATCH_SIZE){
 const current=Date.parse(jstDate+'T00:00:00Z');
 const total=pastQuoteTotalDays(jstDate);
 const start=Math.max(0,Math.floor(offset));
 const count=Math.min(Math.max(0,Math.floor(limit)),Math.max(0,total-start));
 return Array.from({length:count},(_,i)=>{
  const date=new Date(current-(start+i+1)*86400000).toISOString().slice(0,10);
  return {date,quote:failureQuoteForDate(date)};
 });
}
function appendPastQuoteBatch(){
 const items=pastQuoteEntries(pastQuotesDate,pastQuotesRendered);
 const list=$('pastQuoteList');
 for(const {date,quote} of items){
  const item=document.createElement('li');
  const when=document.createElement('time');
  when.dateTime=date;
  when.textContent=date.replaceAll('-','.')+' 掲載';
  const saying=document.createElement('p');
  saying.className='archive-quote-text';
  saying.textContent='「'+quote.ja+'」';
  const author=document.createElement('p');
  author.className='archive-quote-author';
  author.textContent='— '+quote.person;
  const source=document.createElement('p');
  source.className='archive-quote-source';
  source.append('出典：');
  const link=document.createElement('a');
  link.textContent=quote.source+'（日本語意訳）';
  link.href=safeUrl(quote.url);
  link.target='_blank';
  link.rel='noopener noreferrer';
  source.append(link);
  item.append(when,saying,author,source);
  list.append(item);
 }
 pastQuotesRendered+=items.length;
 $('pastQuoteMore').hidden=pastQuotesRendered>=pastQuoteTotalDays(pastQuotesDate);
}
function updatePastQuoteArchive(jstDate){
 const total=pastQuoteTotalDays(jstDate);
 pastQuotesDate=jstDate;
 pastQuotesRendered=0;
 $('pastQuoteList').replaceChildren();
 $('pastQuoteCount').textContent=total?'（'+total+'日分）':'';
 $('pastQuoteStatus').textContent=total?
  '過去の日替わり名言を新しい日付から表示しています。出典から原文も確認できます。':
  '名言の記録は2026年11月20日から。翌日以降、ここに過去の言葉が増えていきます。';
 $('pastQuoteMore').hidden=true;
 if(total&&$('pastQuoteArchive').open)appendPastQuoteBatch();
}
function updateDailyFailureQuote(jstDate){
 const quote=failureQuoteForDate(jstDate);
 $('nightlyMessage').textContent='「'+quote.ja+'」';
 $('dailyQuoteAuthor').textContent='— '+quote.person;
 $('dailyQuoteSource').textContent=quote.source+'（日本語意訳）';
 $('dailyQuoteSource').href=safeUrl(quote.url);
 $('dailyQuoteDate').textContent=jstDate.replaceAll('-','.')+' / 今日のひと言';
 $('closingQuote').hidden=false;
 $('closingJump').hidden=false;
 updatePastQuoteArchive(jstDate);
}
$('pastQuoteArchive').addEventListener('toggle',()=>{
 if($('pastQuoteArchive').open && pastQuotesRendered===0 && pastQuoteTotalDays(pastQuotesDate)>0)
  appendPastQuoteBatch();
});
$('pastQuoteMore').addEventListener('click',appendPastQuoteBatch);
function render(){const d=edition.stories;
 selectedArticleIndex=0;
 $('articleReader').hidden=true;
 $('atlasStoryCount').textContent=d.length===1?'1':String(d.length);
 // This quote belongs to today's JST date, not an archived edition's gag.
 updateDailyFailureQuote(localDate(new Date()));
 $('editionTitle').textContent=edition.title||'今夜の世界の大失敗';
 const archive=edition.status==='demo'; const now=new Date();
 const currentIssue=!archive&&edition.editionDate===localDate(now);
 const special=!archive&&(edition.editionType==='special'||/創刊|特集/.test(edition.title||''));
 const datedPrevious=!archive&&!currentIssue;
 $('atlasLede').textContent=archive?'体験版に収録された、世界の失敗・勘違い・珍事件。':currentIssue?'世界で報じられた、思わず「まさか」な失敗と珍事件。':'この号に収録された、世界の失敗・勘違い・珍事件。';
 lastRenderedLocalDate=localDate(now);
 displayReleaseStatus();
 $('editionTag').textContent=archive?`保存済みの体験版 · 実話${d.length}本`:datedPrevious?`前回の配信号 · 実話${d.length}本`:special?`創刊特集号 · 実話${d.length}本`:`今夜の配信号 · 実話${d.length}本`;
 $('storyHeading').textContent=archive?'体験版のほかのニュース':d.length===2?'世界の「やらかし」、もう1本。':`世界の「やらかし」、あと${Math.max(0,d.length-1)}本。`;
 document.querySelector('.sectionhead').hidden=d.length<=1;
 $('intro').textContent='続きも、報道に基づく小さな「まさか」です。';
 $('intro').hidden=d.length<=1;
 const reportedDates=d.map(s=>String(s.reported||'').replaceAll('.','-')).filter(x=>/^\d{4}-\d{2}-\d{2}$/.test(x)).sort();
 const range=reportedDates.length?reportedDates[0]+(reportedDates.length>1?' 〜 '+reportedDates[reportedDates.length-1]:''):'記事中の出典を参照';
 $('editionMessage').textContent=archive?'過去の実話を使った体験版':`${edition.editionDate} 発行 · ${d.length}本${special?'（特集）':''}`;
 $('dateGuide').textContent=archive?'過去に報道された実話の体験版です。各記事の「報道日」は配信日とは異なります。':datedPrevious?`これは${edition.editionDate}発行の前回・過去号です。今日発生したニュースではありません。掲載記事の報道期間：${range}。`:special?`創刊特集号です。過去の出来事から選んだ実話${d.length}本で、今日起きたニュースという意味ではありません。報道期間：${range}。`:`今夜お届けするのは原則直近7日間に報道された実話です。発生日と配信日は異なる場合があります。報道期間：${range}。`;
 $('disclosure').innerHTML=archive?'<strong>創刊準備号です。</strong> 収録したのは過去に報道された実話です。21時自動更新・プッシュ通知はまだ稼働していません。': `<strong>${datedPrevious?'前回・過去の配信号です。':special?'創刊特集号です。':'公開済み配信号です。'}</strong> 掲載日と出来事の発生日は異なります。編集者が確認済みとして登録した記事ですが、真偽の自動保証ではありません。記事本文は独自の紹介、AIツッコミは創作の冗談です。プッシュ通知は読者の任意設定です。通知を受け取る端末で登録できます。`;
 $('stories').innerHTML=d.slice(1).map((s,offset)=>{const i=offset+1;const art=newsArt(s);return `<li class="story" data-story-index="${i}" data-type="${escapeHtml(s.category)}"><div class="storytop"><span class="number">${i+1}</span><span>${escapeHtml(s.flag||'🌍')} ${escapeHtml(s.country)}</span><span class="type">${escapeHtml(s.categoryLabel||'大失敗')}</span></div><div class="story-cover"><figure class="story-visual"><img class="story-art" src="${escapeHtml(art)}" alt="記事を象徴した創作イラスト。報道写真ではありません。" loading="lazy" decoding="async" width="800" height="480"><figcaption>${hasDailyGeneratedImage(s)?'イメージ画像（AI生成）':'イメージイラスト'}</figcaption></figure><div class="story-headline"><div class="label">${escapeHtml(s.label||'世界のまさか')}</div><h3>${escapeHtml(s.title)}</h3></div></div><div class="story-fact"><span class="fact-kicker">起きたこと</span><p class="summary">${escapeHtml(s.summary)}</p></div>${s.correctionNote?'<span class="correction-flag">編集訂正あり</span>':''}<p class="reported">報道日：${escapeHtml(String(s.reported||'出典を確認').replaceAll('.','-'))}</p>${s.quip?`<div class="teaserquip" role="note" aria-label="AIによる創作の冗談"><span>AIツッコミ <small class="humor-marker">創作の冗談</small></span>${escapeHtml(s.quip)}</div>`:""}<div class="travel-slot" data-travel-slot="${i}"></div><button type="button" class="readbtn" data-open="${i}" aria-expanded="false" aria-controls="details-${i}">詳しく読む ↓</button><div class="details" hidden id="details-${i}">${storyDetailHtml(s)}<p class="source">報道時期：${escapeHtml(s.reported||'出典に記載')}<br>出典：<a href="${escapeHtml(safeUrl(s.sourceUrl))}" target="_blank" rel="noopener noreferrer">${escapeHtml(s.sourceName||'元記事を読む')} ↗</a></p>${storyEvidenceHtml(s)}${storyAttributionHtml(s)}${storyCorrectionHtml(s)}<div class="actions"><button type="button" class="share" data-share="${i}">この記事を共有</button></div></div></li>`}).join('');
 $('stories').querySelectorAll('li.story').forEach((li,index)=>{
  const img=li.querySelector('.story-art'),story=d[index+1];
  if(img&&story)img.addEventListener('error',()=>{
   img.src=fallbackNewsArt(story);
   const caption=li.querySelector('.story-visual figcaption');
   if(caption)caption.textContent='イメージイラスト';
  },{once:true});
 });
 renderIssueGallery();updateSpotlight();renderTravelSlots();renderTodayMap();updateFilters();applyFilter();update();observeStories();syncArticleRoute();}
function update(){const count=Math.max(0,edition.stories.length-1);$('progress').hidden=count<=3;$('progress').textContent=count>3?`ほかに${count}本`:'';$('endprogress').textContent='';}
// Count an article as read when its summary has been visible long enough to read.
let readObserver=null;
const readTimers=new Map();
function markRead(i){
 if(state.read.includes(i))return;
 state.read.push(i);saveState();update();
}
function observeStories(){
 if(readObserver)readObserver.disconnect();
 readTimers.forEach(timer=>clearTimeout(timer));readTimers.clear();
 if(!('IntersectionObserver' in window))return;
 readObserver=new IntersectionObserver(entries=>{
  entries.forEach(entry=>{
   const i=Number(entry.target.dataset.readIndex);
   if(entry.isIntersecting&&entry.intersectionRatio>=0.65&&!state.read.includes(i)){
    if(!readTimers.has(i))readTimers.set(i,setTimeout(()=>{
     readTimers.delete(i);
     if(entry.target.isConnected&&!entry.target.closest('.story')?.hidden)markRead(i);
    },1800));
   }else if(readTimers.has(i)){clearTimeout(readTimers.get(i));readTimers.delete(i)}
  });
 },{threshold:[0,0.65,1]});
 document.querySelectorAll('.story .summary').forEach(el=>{el.dataset.readIndex=el.closest('.story').dataset.storyIndex;readObserver.observe(el)});
}
function applyFilter(){let count=0;document.querySelectorAll('.story').forEach(el=>{const show=filter==='all'||el.dataset.type===filter;el.hidden=!show;if(show)count++});$('empty').hidden=count!==0;document.querySelectorAll('[data-filter]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.filter===filter)))}
async function handleStoryAction(e){const open=e.target.closest('[data-open]');if(open){const i=Number(open.dataset.open),details=$('details-'+i),show=details.hidden;details.hidden=!show;open.closest('.story').classList.toggle('expanded',show);open.textContent=show?'閉じる ↑':'詳しく読む ↓';open.setAttribute('aria-expanded',String(show));if(show&&!state.read.includes(i)){markRead(i)}return}
 const share=e.target.closest('[data-share]');if(share){const s=edition.stories[Number(share.dataset.share)];if(!s)return;const articleUrl=new URL(articleRouteHash(s),location.href).href;const txt=`${s.title}\n記事：${articleUrl}\n出典：${s.sourceUrl}\nよる9じの世界便り`;try{if(navigator.share)await navigator.share({title:s.title,text:txt,url:articleUrl});else if(navigator.clipboard){await navigator.clipboard.writeText(txt);toast('記事の情報をコピーしました')}else toast('共有できない環境です')}catch(err){if(err.name!=='AbortError')toast('共有できない環境です')}}}
$('stories').addEventListener('click',handleStoryAction);
$('spotlightBody').addEventListener('click',handleStoryAction);
$('atlasHero').addEventListener('click',handleStoryAction);
document.querySelector('.filters').addEventListener('click',e=>{const btn=e.target.closest('[data-filter]');if(btn){filter=btn.dataset.filter;applyFilter()}});
function updateClock(){const now=new Date();$('clock').textContent=`日本時間 ${new Intl.DateTimeFormat('ja-JP',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hour12:false}).format(now)} / 21:00`;if(lastRenderedLocalDate&&lastRenderedLocalDate!==localDate(now))render()}updateClock();setInterval(updateClock,60000);
loadState();render();
let newestPublished=null;
let issueRefreshInFlight=null;
function isPublicEdition(x,today){
 return x?.status==='published'&&typeof x.editionDate==='string'&&
  /^\d{4}-\d{2}-\d{2}$/.test(x.editionDate)&&x.editionDate<=today&&
  Array.isArray(x.stories)&&x.stories.length>=1;
}
function applyPublishedEdition(x){
 if(!isPublicEdition(x,localDate(new Date())))return false;
 // A late CDN response or cached offline copy cannot roll back a newer issue.
 if(newestPublished&&x.editionDate<newestPublished.editionDate)return false;
 const fresh=!newestPublished||JSON.stringify(newestPublished)!==JSON.stringify(x);
 newestPublished=x;
 if(fresh){edition=x;filter='all';loadState();render()}
 else displayReleaseStatus();
 return true;
}
async function fetchPublishedIssue(path){
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),15000);
 try{
  const response=await fetch(path+'?no-cache='+Date.now(),{cache:'no-store',signal:controller.signal});
  if(!response.ok)return null;
  return await response.json();
 }finally{clearTimeout(timer)}
}
function checkPublished(){
 if(location.protocol==='file:')return Promise.resolve(false);
 if(issueRefreshInFlight)return issueRefreshInFlight;
 const button=$('refreshIssue'),status=$('issueFreshness');
 button.disabled=true;
 status.textContent='最新号を確認中…';
 issueRefreshInFlight=(async()=>{
  try{
   const today=localDate(new Date());
   let x=await fetchPublishedIssue('./data/current.json');
   if(!isPublicEdition(x,today))throw Error('invalid public issue');
   // Current may lag briefly behind its immutable published archive.
   // Only a published archive for the exact date may supersede it.
   if(x.editionDate<today&&new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tokyo',hour:'2-digit',hourCycle:'h23'}).format(new Date())>='21'){
    try{
     const archived=await fetchPublishedIssue('./data/archive/'+today+'.json');
     if(isPublicEdition(archived,today)&&archived.editionDate===today)x=archived;
    }catch(_){}
   }
   applyPublishedEdition(x);
   status.textContent=edition.status==='published'?(edition.editionDate+'号を表示中'):'公開号を確認できません';
   return true;
  }catch(err){
   status.textContent=edition.status==='published'?(edition.editionDate+'号・更新確認に失敗'):'最新号を取得できません';
   console.info('最新の公開号を取得できませんでした',err);
   return false;
  }finally{button.disabled=false;issueRefreshInFlight=null}
 })();
 return issueRefreshInFlight;
}
$('refreshIssue').addEventListener('click',checkPublished);
checkPublished();
function updateOnlineState(){$('offlineNotice').hidden=navigator.onLine!==false}
window.addEventListener('online',()=>{updateOnlineState();checkPublished()});
window.addEventListener('offline',updateOnlineState);
updateOnlineState();
if('serviceWorker' in navigator&&location.protocol==='https:'){
 navigator.serviceWorker.register('./service-worker.js',{scope:'./',updateViaCache:'none'}).then(reg=>{
  // iOS standalone apps often resume an existing page rather than navigating.
  // Ask for updated app shell code when returning to the foreground.
  reg.update().catch(()=>{});
  let refreshing=false;
  navigator.serviceWorker.addEventListener('controllerchange',()=>{
   if(refreshing)return;
   refreshing=true;
   location.reload();
  });
 }).catch(err=>console.info('オフライン保存は現在利用できません',err));
}
// Optional travel is closed at the start of every reader visit, including
// when iOS reuses a previously open PWA page from its suspended memory.
function closeOptionalTravelPanels(){
 document.querySelectorAll('.travel-slot').forEach(slot=>{
  const control=slot.querySelector('button.travel-open');
  const panel=slot.querySelector('.travel-panel');
  if(!control||!panel)return;
  panel.hidden=true;
  panel.replaceChildren();
  control.setAttribute('aria-expanded','false');
  if(control.firstChild?.nodeType===Node.TEXT_NODE)
   control.firstChild.textContent='ニュースの余韻で、30秒の小旅行 ';
  const arrow=control.querySelector('span[aria-hidden="true"]');
  if(arrow)arrow.textContent='⌄';
 });
}
let lastForegroundCheck=0;
async function refreshOnForeground(){
 if(document.visibilityState==='hidden')return;
 // Do not carry an expanded postcard into the next app visit.
 closeOptionalTravelPanels();
 if(!navigator.onLine)return;
 const now=Date.now();
 if(now-lastForegroundCheck<15000)return;
 lastForegroundCheck=now;
 await checkPublished();
 if('serviceWorker' in navigator){
  navigator.serviceWorker.getRegistration('./').then(reg=>reg?.update()).catch(()=>{});
 }
}
// iOS may freeze the same live page: clear expanded optional cards before
// suspension as well as when the app becomes visible again.
document.addEventListener('visibilitychange',()=>{
 if(document.visibilityState==='hidden')closeOptionalTravelPanels();
 refreshOnForeground();
});
window.addEventListener('pagehide',closeOptionalTravelPanels);
window.addEventListener('pageshow',refreshOnForeground);
window.addEventListener('focus',refreshOnForeground);
// Also check periodically while the reader remains open.
setInterval(checkPublished,180000);
