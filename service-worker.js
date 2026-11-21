/* Offline reader for public, approved editions only. Never cache editor or approval data. */
const SHELL_CACHE = 'yoru9-shell-v50';
const ISSUE_CACHE = 'yoru9-released-issues-v3';
const IMAGE_CACHE = 'yoru9-generated-images-current-v2';
const GENERATED_IMAGE = /^assets\/news-generated\/(\d{4}-\d{2}-\d{2})\/[a-z0-9-]+\.webp$/;
const SCOPE = self.registration.scope;
async function expirePreviousGeneratedImages(day,activePaths=[]){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(day))return;
 const keep=new Set(activePaths);
 const cache=await caches.open(IMAGE_CACHE),requests=await cache.keys();
 await Promise.all(requests.filter(req=>{
  const path=new URL(req.url).pathname.slice(new URL(SCOPE).pathname.length);
  const match=path.match(GENERATED_IMAGE);
  return match&&(!keep.has(path)||match[1]!==day);
 }).map(req=>cache.delete(req)));
}
const SHELL = ['index.html', 'manifest.webmanifest', 'notifications.js', 'world-passport.js', 'assets/reading-focus.css', 'assets/reader-core.css', 'assets/reader-core.js', 'assets/reader-country-data.js', 'assets/reader-travel.js', 'country-catalog.json', 'country-highlights.json', 'travel-stops.json', 'assets/world-today-illustrated.svg', 'assets/icon.svg', 'assets/icon-192.png', 'assets/icon-512.png', 'assets/apple-touch-icon.png',
 'assets/news/coffee-rescue.svg', 'assets/news/road-typo.svg', 'assets/news/monkey-patrol.svg',
 'assets/news/own-goal-keeper.svg', 'assets/news/police-sweets-wanted.svg',
 'assets/news/mouse-83-tattoos.svg',
 'assets/news/ai-python-toilet.svg', 'assets/news/game-show-price-board.svg',
 'assets/news/drone-sewer-search.svg', 'assets/news/lost-handcuff-key.svg',
 'assets/news/uk-river-water-warning.svg', 'assets/news/spain-mussels-colander-pan.svg',
 'assets/news/japan-policy-youtuber-pr.svg', 'assets/news/nz-cricket-comeback.svg',
 'assets/travel/iguazu-rainbow-cover.jpg', 'assets/travel/mont-saint-michel-sunset-cover.jpg',
 'assets/travel/golden-gate-sunset-cover.jpg',
 // Restored country portrait, trivia and postcard photos: Italy and Germany.
 'assets/travel/italy-colosseum-cover.jpg', 'assets/travel/italy-pisa-tower.jpg',
 'assets/travel/italy-venice-grand-canal.jpg', 'assets/travel/germany-brandenburg-cover.jpg',
 'assets/travel/germany-cologne-cathedral.jpg', 'assets/travel/germany-neuschwanstein-castle.jpg',
 // Current-issue country guides must show their licensed photos offline too.
 'assets/travel/london-tower-bridge.jpg', 'assets/travel/edinburgh-castle.jpg',
 'assets/travel/wales-cardiff-castle.jpg', 'assets/travel/barcelona-sagrada.jpg',
 'assets/travel/fuji-cherry-blossom.jpg', 'assets/travel/tokyo-sensoji.jpg',
 'assets/travel/kyoto-kinkakuji.jpg', 'assets/travel/nz-milford-sound.jpg',
 // Correct-answer photographs should also work when installed readers are offline.
 'assets/travel/iguazu-argentina.jpg', 'assets/travel/argentina-mate-quiz.jpg',
 'assets/travel/france-mont-low-tide-quiz.jpg', 'assets/travel/france-nice-coast-quiz.jpg',
 'assets/travel/san-francisco-golden-gate.jpg', 'assets/travel/us-yosemite-granite-quiz.jpg',
 'assets/travel/spain-sagrada-nativity-quiz.jpg', 'assets/travel/spain-alhambra-quiz.jpg',
 'assets/travel/spain-park-guell-drac.jpg',
 'assets/travel/nz-milford-fiord-quiz.jpg', 'assets/travel/nz-aoraki-quiz.jpg',
 'assets/travel/nz-tekapo-church.jpg',
 'assets/travel/korea-bulguksa-quiz.jpg', 'assets/travel/korea-jeju-seongsan-quiz.jpg',
 'assets/travel/korea-bulguksa-stairs.jpg',
 // Brazil: exact-source Rio cover; distinct quiz photos; Brazil-side Iguaçu and museum tourist postcards.
 'assets/travel/brazil-rio-christ-cover.jpg', 'assets/travel/brazil-paulista-quiz.jpg', 'assets/travel/brazil-iguacu-brazil-side-quiz.jpg', 'assets/travel/brazil-iguacu-brazil-side-postcard.jpg', 'assets/travel/brazil-rio-museum-tomorrow.jpg',
 // Antigua and Barbuda: distinct licensed national cover, two answers, independent coastal tour.
 'assets/travel/antigua-english-harbour-cover.jpg', 'assets/travel/antigua-bettys-hope-quiz.jpg', 'assets/travel/antigua-devils-bridge-quiz.jpg', 'assets/travel/antigua-devils-bridge-coast.jpg', 'assets/travel/seoul-gyeongbokgung.jpg',
 'assets/news/category-work.svg', 'assets/news/category-company.svg',
 'assets/news/category-person.svg', 'assets/news/category-sports.svg'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL_CACHE).then(cache =>
    cache.addAll(SHELL.map(path => new URL(path, SCOPE).href))
  ).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys
    .filter(key => key.startsWith('yoru9-') && ![SHELL_CACHE, ISSUE_CACHE, IMAGE_CACHE].includes(key))
    .map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || !url.href.startsWith(SCOPE)) return;
  const relative = url.pathname.slice(new URL(SCOPE).pathname.length);
  // Private workflows, editor files and any unapproved data must never be served from this cache.
  if (relative.startsWith('data/approved/') || relative.startsWith('data/review/') ||
      relative === 'editor.html') return;

  if (relative === 'data/current.json' || relative === 'data/archive/index.json' ||
      /^data\/archive\/\d{4}-\d{2}-\d{2}\.json$/.test(relative)) {
    const canonical = new URL(relative, SCOPE).href;
    event.respondWith(fetch(req).then(response => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(ISSUE_CACHE).then(cache => cache.put(canonical, copy)));
        if(relative==='data/current.json'){
          event.waitUntil(response.clone().json()
            .then(issue=>expirePreviousGeneratedImages(issue.editionDate,(issue.stories||[]).map(s=>s.imagePath).filter(Boolean)))
            .catch(()=>{}));
        }
      }
      return response;
    }).catch(async () => (await caches.match(canonical)) || Response.error()));
    return;
  }

  if (req.mode === 'navigate') {
    event.respondWith(fetch(req).then(response => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(SHELL_CACHE).then(cache => cache.put(new URL('index.html', SCOPE).href, copy)));
      }
      return response;
    }).catch(async () => (await caches.match(new URL('index.html', SCOPE).href)) || Response.error()));
    return;
  }

  if(GENERATED_IMAGE.test(relative)){
    event.respondWith(fetch(req).then(response=>{
      if(response.ok){
        const copy=response.clone();
        event.waitUntil(caches.open(IMAGE_CACHE).then(cache=>cache.put(req,copy)));
      }
      return response;
    }).catch(async ()=>(await caches.match(req))||Response.error()));
    return;
  }
  // New countries may have licensed, build-bundled postcards not in the fixed
  // offline shell. Cache these on first use, then keep a last-known-good copy.
  if (/^assets\/travel\/[a-z0-9-]+\.jpg$/.test(relative)) {
    event.respondWith(fetch(req).then(response => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(SHELL_CACHE).then(cache => cache.put(req, copy)));
      }
      return response;
    }).catch(async () => (await caches.match(req)) || Response.error()));
    return;
  }

  if (SHELL.some(name => relative === name)) {
    // Prefer fresh app assets; fall back to offline copies only when disconnected.
    event.respondWith(fetch(req).then(response => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(SHELL_CACHE).then(cache => cache.put(req, copy)));
      }
      return response;
    }).catch(async () => (await caches.match(req)) || Response.error()));
  }
});


/* Push messages are shown only for an actual dispatched edition.
   Web Push is not active until a separate, private push backend is connected. */
self.addEventListener('push', event => {
  event.waitUntil((async()=>{
    let payload={};
    try{if(event.data)payload=event.data.json()}catch(_){payload={}}
    const title=typeof payload.title==='string'?payload.title.slice(0,90):'よる9じの世界便り';
    const body=typeof payload.body==='string'?payload.body.slice(0,180):'今夜の世界便りが届きました。';
    const editionDate=typeof payload.editionDate==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(payload.editionDate)?payload.editionDate:'latest';
    // Never follow URLs supplied in a remote push payload.
    const url=new URL('index.html',SCOPE).href;
    await self.registration.showNotification(title,{
      body,tag:'yoru9-release-'+editionDate,renotify:false,
      icon:new URL('assets/icon-192.png',SCOPE).href,
      data:{url},timestamp:Date.now()
    });
  })());
});

self.addEventListener('notificationclick',event=>{
  event.notification.close();
  event.waitUntil((async()=>{
    const target=new URL('index.html',SCOPE).href;
    const clientsList=await self.clients.matchAll({type:'window',includeUncontrolled:true});
    for(const c of clientsList){
      if(c.url.startsWith(SCOPE)&&'focus' in c){
        await c.focus();
        if('navigate' in c)await c.navigate(target);
        return;
      }
    }
    if(self.clients.openWindow)await self.clients.openWindow(target);
  })());
});
