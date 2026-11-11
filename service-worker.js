/* Offline reader for public, approved editions only. Never cache editor or approval data. */
const SHELL_CACHE = 'yoru9-shell-v1';
const ISSUE_CACHE = 'yoru9-released-issues-v1';
const SCOPE = self.registration.scope;
const SHELL = ['index.html', 'manifest.webmanifest', 'notifications.js', 'assets/icon.svg'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL_CACHE).then(cache =>
    cache.addAll(SHELL.map(path => new URL(path, SCOPE).href))
  ).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys
    .filter(key => key.startsWith('yoru9-') && ![SHELL_CACHE, ISSUE_CACHE].includes(key))
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

  if (SHELL.some(name => relative === name)) {
    event.respondWith(caches.match(req).then(cached => cached || fetch(req)));
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
      icon:new URL('assets/icon.svg',SCOPE).href,
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
