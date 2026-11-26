/* Optional 30-second journey: photo assets load only if the reader chooses to open it.
   Curated locations belong to incident IDs, not the publisher's country. */
let travelStopsPromise=null;
// Reserve one different postcard per article in the current reading session.
const travelSelections=new Map();
const TODAY_COUNTRY_PHOTO_RULES=Object.freeze({
 IT:[['ローマのコロッセオ',115],['ピサの斜塔',100],['ヴェネツィアの大運河',95]],
 DE:[['ベルリンのブランデンブルク門',115],['ケルン大聖堂',100],['ノイシュヴァンシュタイン城',95]],
 AR:[['イグアスの滝・虹の大瀑布',115],['イグアスの滝',100],['カサ・ロサダ',85],['オベリスコ',80]],
 FR:[['モン・サン＝ミシェルの夕景',115],['エッフェル塔',100],['モン・サン＝ミシェル',70]],
 US:[['ゴールデンゲートブリッジ・夕景',115],['ニューヨークの街並み',100],['ゴールデンゲートブリッジ',90],['ヨセミテ国立公園',90],['グランドキャニオン',90],['ワイキキ',85]],
 GB:[['ロンドン・タワーブリッジ',115],['エディンバラ城',100],['カーディフ城',90]],
 ES:[['サグラダ・ファミリア',115]],
 JP:[['富士山と桜',115],['東京・浅草寺',100],['京都・金閣寺',100]],
 NZ:[['ミルフォード・サウンド',115]]
});

function countryPhotoPriority(code,photo){
 const rules=TODAY_COUNTRY_PHOTO_RULES[code]||[];
 const match=rules.find(([landmark])=>photo.place.includes(landmark));
 return match?match[1]:0;
}

const travelUsedPhotos=new Set();
const travelFailedPhotos=new Set();
// Rotate within each verified country, not just within one page visit. A
// session-only random choice could show Grand Canyon twice on successive days.
const TRAVEL_PHOTO_HISTORY_KEY='yoru9-travel-photo-rotation-v1';
function restoreTravelPhotoHistory(){
 try{
  if(typeof localStorage==='undefined')return {};
  const saved=JSON.parse(localStorage.getItem(TRAVEL_PHOTO_HISTORY_KEY)||'{}');
  if(!saved||typeof saved!=='object'||Array.isArray(saved))return {};
  const result={};
  for(const [country,items] of Object.entries(saved)){
   if(typeof country==='string'&&Array.isArray(items)){
    result[country]=items.filter(x=>typeof x==='string'&&
     /^assets\/travel\/[a-z0-9-]+\.jpg$/.test(x)).slice(-40);
   }
  }
  return result;
 }catch(_){return {};}
}
const travelPhotoHistory=restoreTravelPhotoHistory();
function rememberTravelPhoto(country,asset){
 const old=Array.isArray(travelPhotoHistory[country])?travelPhotoHistory[country]:[];
 travelPhotoHistory[country]=[...old.filter(x=>x!==asset),asset].slice(-40);
 try{
  if(typeof localStorage!=='undefined')
   localStorage.setItem(TRAVEL_PHOTO_HISTORY_KEY,JSON.stringify(travelPhotoHistory));
 }catch(_){/* Private mode or disabled storage: still rotate within this visit. */}
}
function loadTravelStops(){
 if(!travelStopsPromise)travelStopsPromise=fetch('./travel-stops.json',{cache:'no-store'})
  .then(r=>{if(!r.ok)throw Error('travel stops unavailable');return r.json()})
  .then(v=>v&&typeof v==='object'&&!Array.isArray(v)?v:{})
  .catch(()=>{travelStopsPromise=null;return {}});
 return travelStopsPromise;
}
function renderTravelSlots(){
 document.querySelectorAll('[data-travel-slot]').forEach(slot=>{
  const i=Number(slot.dataset.travelSlot);
  if(!Number.isInteger(i)||!edition.stories[i])return;
  slot.innerHTML='<button type="button" class="travel-open" data-travel="'+i+
   '" aria-expanded="false" aria-controls="travel-panel-'+i+
   '">ニュースの余韻で、名所への小旅行 <span aria-hidden="true">⌄</span></button>'+
   '<div class="travel-panel" id="travel-panel-'+i+'" hidden></div>';
 });
}
function travelCountryNames(raw){
 const text=String(raw||'');
 // Country aliases and combined reported locations must not make photos disappear.
 if(text.includes('イギリス')&&text.includes('アメリカ'))return ['イギリス','アメリカ合衆国'];
 if(text.includes('アメリカ'))return ['アメリカ合衆国'];
 if(text.includes('イギリス')||text.includes('ウェールズ'))return ['イギリス'];
 if(text.includes('韓国'))return ['韓国'];
 if(text.includes('ブラジル'))return ['ブラジル'];
 if(text.includes('日本'))return ['日本'];
 if(text.includes('スペイン'))return ['スペイン'];
 if(text.includes('アンティグア'))return ['アンティグア・バーブーダ'];
 // The same catalog as the atlas covers all 196 countries and territories.
 // Unknown labels are never guessed to be a different country.
 const canonical=countryKeys(text);
 return canonical.length?canonical.map(code=>countryLabel(code)):(text?[text]:[]);
}
function travelPhotoOptions(stops){
 // Several article IDs can refer to the same photograph; never count it twice.
 const seen=new Set();
 return Object.values(stops||{}).filter(stop=>{
  if(!stop||typeof stop!=='object'||stop.coverOnly===true||stop.quizOnly===true||typeof stop.country!=='string'||
     typeof stop.place!=='string'||!Number.isFinite(stop.latitude)||
     !Number.isFinite(stop.longitude)||Math.abs(stop.latitude)>90||
     Math.abs(stop.longitude)>180||
     typeof stop.photo!=='string'||
     !stop.photo.startsWith('https://thumb.wikimedia.org/wikipedia/commons/thumb/')||
     typeof stop.photoAsset!=='string'||
     !/^assets\/travel\/[a-z0-9-]+\.jpg$/.test(stop.photoAsset)||
     typeof stop.photoPage!=='string'||
     !stop.photoPage.startsWith('https://commons.wikimedia.org/wiki/File:')||
     typeof stop.licenseUrl!=='string'||
     !stop.licenseUrl.startsWith('https://creativecommons.org/')||
     seen.has(stop.photoAsset))return false;
  seen.add(stop.photoAsset);
  return true;
 });
}
// The microtravel module is a destination guide, NOT an extension of
// Country Portrait. Only explicitly approved, recognizable attractions
// can be selected, even when a less famous licensed street photo exists.
const FAMOUS_TOURIST_LANDMARKS=Object.freeze({
 'イタリア':['コロッセオ','ピサの斜塔','ヴェネツィアの大運河'],
 'ドイツ':['ブランデンブルク門','ケルン大聖堂','ノイシュヴァンシュタイン城'],
 'アルゼンチン':['イグアスの滝','カサ・ロサダ','オベリスコ'],
 'フランス':['エッフェル塔','モン・サン＝ミシェル'],
 'アメリカ合衆国':['グランドキャニオン','ヨセミテ','ゴールデンゲートブリッジ','ワイキキビーチ','ニューヨークの街並み'],
 'イギリス':['タワーブリッジ','エディンバラ城','カーディフ城','ウィンダミア湖'],
 'スペイン':['サグラダ・ファミリア'],
 '日本':['富士山','浅草寺','金閣寺'],
 'ニュージーランド':['ミルフォード・サウンド'],
 '韓国':['景福宮'],
 'ブラジル':['イグアスの滝'],
 'アンティグア・バーブーダ':['ネルソンズ・ドックヤード']
});
function famousAttractionScore(stop){
 if(!stop||typeof stop.place!=='string')return 0;
 const landmark=(FAMOUS_TOURIST_LANDMARKS[stop.country]||[])
  .find(name=>stop.place.includes(name));
 return landmark?100:stop.famousTourist===true?80:0;
}
function travelStoryKey(story){
 return String(story.id||story.title||'')+'|'+String(story.country||'');
}
// Apply the same visual-quality gate to photographs in already-published
// travel postcards, not only the map's country-introduction cover.
function approvedTravelCover(stop){
 if(!stop||stop.coverOnly===true||!stop.country||!stop.place||famousAttractionScore(stop)<80)return false;
 const code=stop.country==='アルゼンチン'?'AR':stop.country==='フランス'?'FR':
  stop.country==='アメリカ合衆国'?'US':null;
 if(!code)return true;
 // Travel postcards are a separate visual experience from the country hero.
 // A secondary licensed landmark may score below the hero's stricter threshold.
 return countryPhotoPriority(code,stop)>=70;
}
function countryHeroAsset(country){
 const code=country==='アルゼンチン'?'AR':country==='フランス'?'FR':
  country==='アメリカ合衆国'?'US':null;
 if(!code)return null;
 const candidates=((typeof TODAY_COUNTRY_PHOTOS==='undefined'?{}:TODAY_COUNTRY_PHOTOS)[code]||[]).filter(p=>
  p.asset&&p.url&&p.author&&p.license&&p.place&&p.caption&&countryPhotoPriority(code,p)>=80);
 candidates.sort((a,b)=>countryPhotoPriority(code,b)-countryPhotoPriority(code,a));
 return candidates[0]?.asset||null;
}
function conflictsWithCountryCover(stop){
 const code=stop.country==='アルゼンチン'?'AR':stop.country==='フランス'?'FR':
  stop.country==='アメリカ合衆国'?'US':null;
 const coverLandmark=code==='AR'?'イグアスの滝':code==='FR'?'モン・サン＝ミシェル':
  code==='US'?'ゴールデンゲートブリッジ':null;
 return stop.photoAsset===countryHeroAsset(stop.country)||
  (coverLandmark&&stop.place.includes(coverLandmark))||
  (code&&typeof displayedCountryCoverAssets!=='undefined'&&
   stop.photoAsset===displayedCountryCoverAssets.get(code));
}
function chooseTravelPhoto(story,stops){
 const key=travelStoryKey(story),prior=travelSelections.get(key);
 if(prior&&!travelFailedPhotos.has(prior.photoAsset)&&approvedTravelCover(prior)&&!conflictsWithCountryCover(prior))return prior;
 const available=travelPhotoOptions(stops).filter(s=>!travelFailedPhotos.has(s.photoAsset)&&approvedTravelCover(s)&&!conflictsWithCountryCover(s));
 if(!available.length)return null;
 const countries=travelCountryNames(story.country);
 const sameCountry=available.filter(s=>countries.includes(s.country)&&
   (typeof APPROVED_COUNTRY_CODES==='undefined'||countryKeys(s.country).some(code=>APPROVED_COUNTRY_CODES.includes(code))));
 // Always retain authentic article-country alignment; no fake foreign photo.
 if(!sameCountry.length)return null;
 // Avoid two copies in one session, unless it is the ONLY available photograph.
 // Prefer destinations backed by a separate historical/cultural reference.
 // A photo's CC license is not evidence for claims in the travel essay.
 // Never repeat a country's photo before exhausting available vetted images.
 // Source links enrich reading, but cannot override the trusted rotation.
 let pool=sameCountry.filter(s=>!travelUsedPhotos.has(s.photoAsset));
 if(!pool.length)pool=sameCountry;
 // First exhaust every licensed photo within the country across page reloads.
 const unseen=pool.filter(s=>!(travelPhotoHistory[s.country]||[]).includes(s.photoAsset));
 if(unseen.length){
  pool=unseen;
 }else{
  // A full cycle is exhausted: take the least recently shown photo, never
  // the immediately preceding image when alternatives exist.
  const age=s=>{
   const order=travelPhotoHistory[s.country]||[];
   return order.indexOf(s.photoAsset);
  };
  const oldest=Math.min(...pool.map(age));
  pool=pool.filter(s=>age(s)===oldest);
 }
 // A documented same-town destination can be preferred only until it has
 // been seen. Later visits rotate to different pictures of the same country.
 const curated=pool.find(stop=>stop===stops?.[story.id]);
 if(curated)pool=[curated];
 else{
  // Prefer evergreen postcards before recycled illustrations from old news
  // editions, including the repeatedly shown Grand Canyon. Once the public
  // postcards have been seen, remaining unshown old photos join the rotation.
  // "countryOnly" also marks old news-specific cards (e.g. Grand Canyon).
  // Prefer the explicitly evergreen -postcard catalog keys instead.
  const evergreen=pool.filter(stop=>Object.entries(stops||{}).some(
   ([id,value])=>value===stop&&id.endsWith('-postcard')));
  if(evergreen.length)pool=evergreen;
  if(String(story.country||'').includes('ウェールズ')){
   const welsh=pool.filter(s=>String(s.region).includes('ウェールズ'));
   if(welsh.length)pool=welsh;
  }
 }
 const picked=pool[Math.floor(Math.random()*pool.length)];
 travelSelections.set(key,picked);
 travelUsedPhotos.add(picked.photoAsset);
 rememberTravelPhoto(picked.country,picked.photoAsset);
 return picked;
}
function travelPostcardHtml(story,stop,standalone=false){

 const known=stop&&Number.isFinite(stop.latitude)&&Number.isFinite(stop.longitude)&&
  Math.abs(stop.latitude)<=90&&Math.abs(stop.longitude)<=180;
 const sameCountry=known&&travelCountryNames(story.country).includes(stop.country);
 const reportCountry=countryLabel(story.country||'');
 const place=known?stop.place:reportCountry;
 const fallbackCountry=countryRecord(story.country)||
  countryRecord(countryKeys(story.country)[0]||'');
 const locator=known?{lat:stop.latitude,lon:stop.longitude,zoom:11}:fallbackCountry
  ?{lat:fallbackCountry.lat,lon:fallbackCountry.lon,zoom:4}:null;
 const mapUrl=locator?'https://www.openstreetmap.org/?mlat='+locator.lat+'&mlon='+locator.lon+
  '#map='+locator.zoom+'/'+locator.lat+'/'+locator.lon:'';
 const photo=known&&typeof stop.photo==='string'&&
  stop.photo.startsWith('https://thumb.wikimedia.org/wikipedia/commons/thumb/')&&
  typeof stop.photoAsset==='string'&&/^assets\/travel\/[a-z0-9-]+\.jpg$/.test(stop.photoAsset)&&
  typeof stop.photoPage==='string'&&stop.photoPage.startsWith('https://commons.wikimedia.org/wiki/File:')&&
  typeof stop.licenseUrl==='string'&&stop.licenseUrl.startsWith('https://creativecommons.org/');
 const heritage=stop&&Array.isArray(stop.historicalSources)?
  stop.historicalSources.find(source=>source&&source.name&&
   typeof source.url==='string'&&source.url.startsWith('https://')):null;
 // Keep the published news template explicit and independently testable.
 // The standalone country view must not claim a fictitious article's stage.
 const storyContext='<div class="travel-context" aria-label="記事と旅先の違い">'+
  '<span class="travel-context-story">記事の舞台（国） '+escapeHtml(reportCountry)+'</span>'+
  '<span class="travel-context-destination">旅先 '+escapeHtml(known?stop.country:'未準備')+'</span></div>';
 const countryContext='<div class="travel-context" aria-label="国紹介と旅先の関係">'+
  '<span class="travel-context-story">国紹介：'+escapeHtml(reportCountry)+'</span>'+
  '<span class="travel-context-destination">旅先 '+escapeHtml(known?stop.country:'未準備')+'</span></div>';
 return '<section class="travel-card" aria-label="'+
   (standalone?'出典確認済みの国紹介からの小旅行':'ニュースとは別の旅先を紹介する小旅行')+'">'+
  '<p class="travel-kicker">WORLD POSTCARD · 有名観光地の小旅行</p>'+
  (standalone?countryContext:storyContext)+
  '<h4>'+escapeHtml(place)+(known?' · '+escapeHtml(stop.region):'')+'</h4>'+
  '<p class="travel-trust" role="note">'+
   (photo?'この写真はニュース現場の記録ではなく、旅先の風景です。':'この国の有名観光地の写真はまだ準備中です。ニュースの現場を示すものではありません。')+
  '</p>'+
  (known&&!sameCountry?'<p class="travel-elsewhere">ニュースの舞台とは異なる国の旅先：'+escapeHtml(stop.country)+'</p>':'')+
  (photo?'<figure class="travel-figure"><img class="travel-photo" loading="lazy" decoding="async" src="./'+
   escapeHtml(stop.photoAsset)+'" data-remote-photo="'+escapeHtml(stop.photo)+'" alt="'+escapeHtml(stop.photoCaption)+'">'+
   '<p class="travel-photo-error" hidden>写真を表示できませんでした。撮影元リンクから写真を開くことができます。</p>'+
   '<figcaption><span class="travel-caption-label">この景色の見どころ</span>'+escapeHtml(stop.note||stop.photoCaption)+'</figcaption></figure>':
   '<p class="travel-empty">'+(known?'写真を読み込めませんでした。撮影元と地図を確認できます。':'この国の有名観光地は確認中。無名の写真や別の国の景色では代用しません。')+'</p>')+
  (known&&Array.isArray(stop.travelStory)&&stop.travelStory.length===2?
   '<section class="travel-story" aria-label="名所の魅力と歴史">'+
    '<h5>景色の向こう側へ</h5>'+
    stop.travelStory.map(paragraph=>'<p>'+escapeHtml(paragraph)+'</p>').join('')+
   '</section>':'')+
  '<div class="travel-links">'+
   (mapUrl?'<a href="'+escapeHtml(mapUrl)+'" target="_blank" rel="noopener noreferrer">'+(known?'旅先を地図で見る ↗':'掲載国を地図で見る ↗')+'</a>':'')+
   (photo?'<a href="'+escapeHtml(stop.photoPage)+'" target="_blank" rel="noopener noreferrer">写真の撮影元 ↗</a>':'')+
   (heritage?'<a href="'+escapeHtml(safeUrl(heritage.url))+'" target="_blank" rel="noopener noreferrer">歴史・文化の資料：'+escapeHtml(heritage.name)+' ↗</a>':
    '<span class="travel-source-pending">歴史・文化の出典は編集中</span>')+
  '</div>'+
  (photo?'<p class="travel-credit">写真：'+escapeHtml(stop.author)+' / <a href="'+escapeHtml(stop.licenseUrl)+
   '" target="_blank" rel="noopener noreferrer">'+escapeHtml(stop.license)+'</a>（表示範囲を調整）</p>':'')+
  '</section>';
}
document.querySelector('main').addEventListener('click',async event=>{
 const control=event.target.closest('[data-travel]');
 if(!control)return;
 const i=Number(control.dataset.travel);
 const story=edition.stories[i];
 const panel=control.nextElementSibling;
 if(!Number.isInteger(i)||!story||!panel||!panel.classList.contains('travel-panel'))return;
 const opening=panel.hidden;
 panel.hidden=!opening;
 control.setAttribute('aria-expanded',String(opening));
 control.firstChild.textContent=opening?'小旅行を閉じる ':'ニュースの余韻で、名所への小旅行 ';
 const arrow=control.querySelector('span[aria-hidden="true"]');
 if(arrow)arrow.textContent=opening?'⌃':'⌄';
 if(!opening)return;
 panel.innerHTML='<p class="travel-loading" role="status">小さな旅の準備中…</p>';
 const stops=await loadTravelStops();
 // Never insert a postcard into a card that has already been closed/replaced.
 if(!panel.isConnected||panel.hidden||edition.stories[i]!==story||!document.body.classList.contains('news-detail-mode')||selectedArticleIndex!==i)return;
 const maxRetries=travelPhotoOptions(stops).length;
 function mountPhoto(stop,attempt=0){
  panel.innerHTML=travelPostcardHtml(story,stop);
  const img=panel.querySelector('.travel-photo');
  if(!img)return;
  img.addEventListener('error',()=>{
   if(!img.isConnected||!panel.isConnected||panel.hidden)return;
   // Try the original Commons thumbnail if the bundled copy cannot load.
   if(!img.dataset.remoteTried&&img.dataset.remotePhoto){
    img.dataset.remoteTried='true';
    img.src=img.dataset.remotePhoto;
    return;
   }
   // If both URLs failed, pick a *different* photo, not the same fallback.
   travelFailedPhotos.add(stop.photoAsset);
   travelSelections.delete(travelStoryKey(story));
   travelUsedPhotos.delete(stop.photoAsset);
   const next=chooseTravelPhoto(story,stops);
   if(next&&attempt+1<maxRetries&&next.photoAsset!==stop.photoAsset){
    mountPhoto(next,attempt+1);
   }else{
    img.hidden=true;
    const errorText=panel.querySelector('.travel-photo-error');
    if(errorText)errorText.hidden=false;
   }
  });
 }
 mountPhoto(chooseTravelPhoto(story,stops));
});
