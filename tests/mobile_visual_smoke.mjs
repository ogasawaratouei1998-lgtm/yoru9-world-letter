/* Mobile-browser smoke test for the public nightly reader.
   Chromium's device emulation is useful but is NOT an iPhone Safari test. */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const url='https://ogasawaratouei1998-lgtm.github.io/yoru9-world-letter/';
await fs.mkdir('mobile-screenshots',{recursive:true});
// GitHub's Ubuntu 24.04 runner already ships Google Chrome. Use that in CI
// instead of downloading a second browser and running a slow APT setup.
// Local developers continue to use Playwright's pinned Chromium.
const browser=await chromium.launch({headless:true,...(process.env.CI?{channel:'chrome'}:{})});
try{
 for(const viewport of [{width:320,height:667,name:'narrow'},{width:375,height:667,name:'small'},{width:393,height:852,name:'standard'}]){
  const context=await browser.newContext({
   viewport:{width:viewport.width,height:viewport.height},
   deviceScaleFactor:2,isMobile:true,hasTouch:true,
   serviceWorkers:'block', // Compare deployed HTML, not a cached PWA shell.
   reducedMotion:'reduce', // Stable capture and no forced motion on tests.
   locale:'ja-JP',timezoneId:'Asia/Tokyo'
  });
  try{
   const page=await context.newPage();
   const errors=[];
   page.on('pageerror',e=>errors.push(String(e)));
   // GitHub Pages can serve the previous deployment briefly after the
   // deployment workflow completes. Verify the expected version, rather than
   // misreporting a stale CDN page as a new-design regression.
   let res;
   let freshDesign=false;
   for(let attempt=0;attempt<16;attempt++){
    const freshUrl=new URL(url);
    freshUrl.searchParams.set('visual_smoke',String(Date.now())+'-'+attempt);
    res=await page.goto(freshUrl.toString(),{waitUntil:'domcontentloaded',timeout:35000});
    assert.equal(res?.status(),200,'reader page must be reachable');
    freshDesign=await page.locator('#coverWorldMap').count()===0&&
     await page.locator('#archiveExtras').count()===0&&
     await page.locator('#mapExtras').count()===0&&
     await page.locator('#todayMapSection').count()===1&&
     await page.locator('#monthRetrospective').count()===0&&
     await page.locator('#atlasHero .atlas-oops').count()===1&&
     await page.locator('#issueGallery[data-layout="mobile-grid-responsive"]').count()===1&&
     await page.locator('#todayCountryQuiz[hidden]').count()===1&&
     await page.locator('script[src="./world-passport.js"]').count()===1&&
     await page.locator('#quipTeaserLine').count()===1&&
     await page.locator('#articleReader[hidden]').count()===1&&
     await page.locator('#readerBack').count()===1&&
     await page.locator('#spotlightImage').count()===1;
    if(freshDesign)break;
    await page.waitForTimeout(6000);
   }
   assert.ok(freshDesign,'GitHub Pages must serve the latest simplified live news reader');
   await page.waitForFunction(()=>{
    const el=document.querySelector('#spotlightTitle');
    return el&&el.textContent&&!el.textContent.includes('準備中');
   },null,{timeout:30000});
   const editorialCover=await page.evaluate(()=>{
    const hero=document.querySelector('#atlasHero');
    const h2=hero?.querySelector('.atlas-title');
    const bubble=hero?.querySelector('.atlas-brand');
    const lede=hero?.querySelector('#atlasLede');
     const box=el=>el?.getBoundingClientRect();
    return {
      headline:h2?.textContent?.replace(/\s+/g,'').trim(),
      storyNumber:hero?.querySelector('#atlasStoryCount')?.textContent?.trim(),
      storyCount:document.querySelectorAll('#stories .story').length+1,
      lede:lede?.textContent?.trim(),
      real:hero?.querySelector('.atlas-real-stamp')?.textContent?.trim(),
      joke:hero?.querySelector('.atlas-bubble-tag')?.textContent?.trim(),
      bubble:bubble?.textContent?.trim(),
      bubbleVisible:getComputedStyle(bubble).display!=='none',
      bubbleFont:parseFloat(getComputedStyle(bubble).fontSize),
      headlineBottom:box(h2)?.bottom,
      conceptTop:box(hero?.querySelector('.atlas-concept'))?.top,
      conceptBottom:box(hero?.querySelector('.atlas-concept'))?.bottom,
      galleryTop:box(hero?.querySelector('#issueGallery'))?.top
    };
   });
   assert.equal(editorialCover.storyNumber,String(editorialCover.storyCount),
    'headline dynamically matches the number of published stories');
   assert.ok(editorialCover.headline.includes('世界の「やらかし」ニュース、')&&
    editorialCover.headline.endsWith('本。'),'first glance defines the humorous news category');
   assert.ok(editorialCover.lede?.includes('失敗')&&
    editorialCover.lede?.includes('珍事件'),'cover explains its reported-incident premise');
   assert.equal(editorialCover.real,'実話','reported facts are called real');
   assert.equal(editorialCover.joke,'AIツッコミ','AI humor is prominently labeled');
   assert.ok(editorialCover.bubbleVisible&&editorialCover.bubbleFont>=12,
    'the AI comedy promise must be legible even on iPhone');
   assert.ok(editorialCover.bubble.includes('創作の冗談'),
    'the condensed concept identifies the AI comment as fictional humor');
   assert.ok(editorialCover.headlineBottom<=editorialCover.conceptTop+2&&
    editorialCover.conceptBottom<=editorialCover.galleryTop+2,
    'the reader opens with the editorial concept and story gallery');
   // The three-comic gallery replaces a repeated always-visible article list.
   const articleReader=page.locator('#articleReader');
   assert.equal(await articleReader.isHidden(),true,
    'no second full news list appears before the reader chooses a picture');
   assert.equal(await page.locator('#spotlight').isHidden(),true,
    'lead reporting stays closed until requested');
   assert.equal(await page.locator('#stories').isHidden(),true,
    'supporting full stories stay closed until requested');
   const teaser=page.locator('#quipTeaser');
   assert.equal(await teaser.isVisible(),true,
    'the current approved issue has a real opening punchline');
   assert.equal(await page.locator('#quipTeaserLine').textContent(),
    await page.locator('#spotlightQuip').textContent(),
    'opening joke and actual article use precisely the same approved text');
   assert.equal(await teaser.locator('img').count(),0,
    'do not duplicate or tightly crop the gallery picture in the opening joke');
   assert.equal(await page.locator('#spotlightImage').count(),1,
    'the full article still has its own properly labeled cover');
   assert.ok((await page.locator('#quipTeaserTopic').textContent()).length>3,
    'the opening joke has its news context rather than an unexplained gag');
   const teaserGeometry=await page.evaluate(()=>{
    const r=id=>document.querySelector(id)?.getBoundingClientRect();
    const a=r('#atlasHero .atlas-concept'),t=r('#quipTeaser'),
          g=r('#issueGallery');
    const buttons=[...document.querySelectorAll('#quipTeaser .quip-teaser-actions button')]
      .map(el=>el.getBoundingClientRect());
    const teaser=t?.toJSON();
    const hero=r('#atlasHero')?.toJSON();
    return {conceptBottom:a?.bottom,teaserTop:t?.top,teaserBottom:t?.bottom,
      teaserHeight:t?.height,teaserLeft:t?.left,teaserRight:t?.right,
      galleryTop:g?.top,galleryBottom:g?.bottom,windowWidth:window.innerWidth,
      teaser,hero,buttons:buttons.map(x=>({left:x.left,right:x.right,top:x.top,bottom:x.bottom,height:x.height}))};
   });
   assert.ok(teaserGeometry.conceptBottom<=teaserGeometry.teaserTop+2&&
     teaserGeometry.teaserBottom<=teaserGeometry.galleryTop+2&&
     teaserGeometry.galleryBottom<=teaserGeometry.hero.bottom+2,
     'the comedy payoff and gallery are correctly ordered without a map');
   assert.ok(teaserGeometry.teaserHeight<=225,
    'opening laugh should be a compact speech bubble, not another full illustration card: '+
      teaserGeometry.teaserHeight+'px');
   assert.equal(teaserGeometry.buttons.length,2,'both opening controls remain usable');
   assert.ok(Math.abs(teaserGeometry.buttons[0].top-teaserGeometry.buttons[1].top)<2,
    'read and smile actions share the same row rather than stacking vertically');
   assert.ok(teaserGeometry.buttons.every(b=>b.height>=44&&
     b.left>=teaserGeometry.teaserLeft-1&&b.right<=teaserGeometry.teaserRight+1),
    'both actions stay inside their teaser and meet minimum touch size');
   assert.ok(teaserGeometry.teaser.left>=teaserGeometry.hero.left-2&&
     teaserGeometry.teaser.right<=teaserGeometry.hero.right+2,
    'opening speech bubble never overflows the phone viewport');
   assert.ok(await page.locator('#atlasHero .atlas-brand').evaluate(el=>
     getComputedStyle(el).display==='flex'),
    'the explanatory concept uses a compact row, not a second oversized bubble');
   assert.equal(await page.locator('#quipTeaserRead').evaluate(el=>
      el.getBoundingClientRect().height>=44),true,'first joke has a real thumb-size read action');
   await page.locator('#quipTeaserRead').click();
   assert.equal(await articleReader.isVisible(),true,
    'tapping a featured joke opens the on-demand article reader');
   assert.equal(await page.locator('#spotlightRead').getAttribute('aria-expanded'),'true',
    'first joke opens the real article with source, rather than inventing another page');
   assert.equal(await page.locator('#spotlight').isVisible(),true);
   assert.equal(await page.locator('#stories').isHidden(),true,
    'other news is not repeated when reading the first article');
   assert.equal(await page.locator('#storyHeading').isHidden(),true,
    'redundant "あと2本" heading is not displayed');
   assert.equal(await page.locator('#spotlightAward').textContent(),'このニュースの詳しい話',
    'redundant prior-edition label is replaced by a detail label');
   assert.equal(await page.locator('body').evaluate(el=>el.classList.contains('news-detail-mode')),true,
    'opening an article enters a dedicated reading screen');
   assert.equal(await page.locator('#atlasHero').isHidden(),true,
    'the news gallery cannot stack behind an opened article');
   assert.equal(await page.locator('#todayMapSection').isHidden(),true,
    'the country map cannot overlap with the separate article screen');
   const firstSmile=page.locator('#spotlightBody .smile');
   await firstSmile.click();
   assert.equal(await firstSmile.getAttribute('aria-pressed'),'true',
    'the article reaction follows the selected news item');
   assert.ok(!(await firstSmile.evaluate(el=>el.classList.contains('smile-burst'))),
    'reduced-motion users never get forced sparkle movement');
   await firstSmile.click();
   assert.equal(await firstSmile.getAttribute('aria-pressed'),'false');
   await page.screenshot({path:'mobile-screenshots/first-laugh-'+viewport.name+'.png',animations:'disabled'});
   await page.locator('#readerBack').click();
   assert.equal(await articleReader.isHidden(),true);
   assert.equal(await page.locator('#atlasHero').isVisible(),true);
   assert.equal(await page.locator('#quipTeaser .teaser-smile').getAttribute('aria-pressed'),'false');
   const gallery=page.locator('#issueGallery .gallery-tile');
   assert.equal(await page.locator('#galleryHeading').textContent(),
    '世界の「まさか」'+editorialCover.storyCount+'コマ劇場',
    'the stage label matches one/two/three or more actual published items');
   assert.equal(await page.locator('#issueGallery .gallery-kicker').count(),
    editorialCover.storyCount,'each visual article has an honest comic teaser');

   assert.equal(await gallery.count(),editorialCover.storyCount,
    'each published story has a prominent visual invitation');
   // A gallery must show *all* article pictures without hiding the next
   // image in a horizontal scroller. Test physical geometry, not CSS text.
   const grid=await page.evaluate(()=>{
    const track=document.querySelector('#issueGallery');
    const hero=document.querySelector('#atlasHero');
    const hint=document.querySelector('#atlasHero .gallery-heading span');
    const rect=el=>{
      const r=el.getBoundingClientRect();
      return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};
    };
    return {
      layout:getComputedStyle(track).gridAutoFlow,
      overflowX:getComputedStyle(track).overflowX,
      columns:getComputedStyle(track).gridTemplateColumns,
      scrollOverflow:track.scrollWidth-track.clientWidth,
      pageOverflow:document.documentElement.scrollWidth-window.innerWidth,
      track:rect(track),hero:rect(hero),hint:rect(hint),
      tiles:[...track.querySelectorAll('.gallery-tile')].map(el=>({
        tile:rect(el),image:rect(el.querySelector('.gallery-art'))
      }))
    };
   });
   assert.equal(grid.layout,'row','mobile illustrated articles use a real two-row grid');
   assert.equal(grid.overflowX,'visible','news illustrations are not hidden inside a carousel');
   assert.equal(grid.columns.split(' ').length,2,'mobile grid has exactly two columns');
   assert.ok(grid.scrollOverflow<=2,
    'no clipped/scrollable illustration inside gallery: '+grid.scrollOverflow+'px');
   assert.ok(grid.pageOverflow<2,'no page-wide horizontal overflow: '+grid.pageOverflow+'px');
   assert.ok(grid.hint.left>=grid.hero.left-2&&grid.hint.right<=grid.hero.right+2,
    'gallery header hint stays inside the hero: '+JSON.stringify({
      viewport:viewport.name,hero:grid.hero,hint:grid.hint
    }));
   for(const [i,item] of grid.tiles.entries()){
    assert.ok(item.tile.left>=grid.track.left-2&&item.tile.right<=grid.track.right+2,
     'every article tile fits inside the gallery: '+(i+1));
    assert.ok(item.image.left>=item.tile.left-2&&item.image.right<=item.tile.right+2,
     'every article illustration fits within its own tile: '+(i+1));
   }
   if(grid.tiles.length>=2){
    assert.ok(Math.abs(grid.tiles[0].tile.top-grid.tiles[1].tile.top)<=2,
     'two picture cards appear side-by-side in the first row');
    assert.ok(grid.tiles[1].tile.left>=grid.tiles[0].tile.right-2,
     'first two article cards do not overlap');
   }
   if(grid.tiles.length%2===1){
    const last=grid.tiles.at(-1).tile;
    assert.ok(last.width>=grid.track.width-2,
     'odd last article uses the full width of the gallery');
    if(grid.tiles.length>1){
     assert.ok(last.top>=grid.tiles[0].tile.bottom-2,
      'third article is on a new row, never cut off at the right edge');
    }
   }
   const note=page.locator('#atlasHero .gallery-clarity');
   assert.ok((await note.textContent()).includes('現場の写真ではありません'),
    'editorial illustrations cannot be mistaken for incident photographs');
   await page.waitForFunction(()=>{
    const image=document.querySelector('#issueGallery .gallery-art');
    return image&&image.complete&&image.naturalWidth>0;
   },null,{timeout:30000});
   await page.waitForFunction(()=>{
    const pictures=[...document.querySelectorAll('#issueGallery .gallery-art')];
    return pictures.length>0&&pictures.every(img=>img.complete&&img.naturalWidth>0);
   },null,{timeout:30000});
   const galleryArts=await page.locator('#issueGallery .gallery-art').evaluateAll(images=>
    images.map(img=>img.getAttribute('src')));
   assert.equal(new Set(galleryArts).size,galleryArts.length,
    'every current news card must show different artwork rather than duplicate clipboards');
   for(const path of galleryArts){
    assert.ok(path.startsWith('./assets/news/')||path.startsWith('data:image/svg+xml;charset=utf-8,'),
     'editorial illustration is local or generated offline, never an external photo');
    assert.ok(!path.includes('/category-work.svg')&&!path.includes('/category-sports.svg'),
     'current stories must not repeat category placeholders');
   }
   const currentStoryIds=await page.evaluate(()=>edition.stories.map(s=>s.id));
   const bespokeArt={
    'uk-french-weir-swimming-2026':'uk-river-water-warning.svg',
    'mussolini-colador-2026':'spain-mussels-colander-pan.svg',
    'jp-gov-youtuber-pr-2026':'japan-policy-youtuber-pr.svg',
    'nz-cricket-collapse-2026':'nz-cricket-comeback.svg'
   };
   for(const [index,id] of currentStoryIds.entries()){
    if(bespokeArt[id])assert.ok(galleryArts[index].endsWith('/'+bespokeArt[id]),
     'each news story uses its own matching illustration: '+id);
   }
   const firstImage=page.locator('#issueGallery .gallery-art').first();
   assert.ok((await firstImage.getAttribute('src')).startsWith('./assets/news/'),
    'visual assets are bundled locally, not from third-party news photos');
   assert.ok((await gallery.first().getAttribute('aria-label')).includes('を読む'),
    'a picture alone has a meaningful accessible reading action');
   const leadImage=page.locator('#spotlightImage');
   assert.equal(await leadImage.isHidden(),true,
    'news illustration is already visible in the gallery and must not repeat in detail');
   assert.ok((await page.locator('#spotlightVisual figcaption').textContent()).includes('現場写真ではありません'),
    'hidden original image still has an accurate source disclaimer');
   assert.ok((await gallery.first().locator('.gallery-art').evaluate(el=>el.naturalWidth))>0,
    'the gallery retains the visible, fully loaded first illustration');
   if(await gallery.count()>1){
    const expectedTitle=await page.locator('#stories [data-story-index="1"] .story-headline h3').textContent();
    await gallery.nth(1).click();
    assert.equal(await page.locator('#spotlightTitle').textContent(),expectedTitle,
     'second gallery card opens its own story screen');
    assert.equal(await page.locator('#spotlight').isVisible(),true);
    assert.equal(await page.locator('#stories').isHidden(),true,
     'no other articles stack under the selected news');
    assert.equal(await page.locator('#atlasHero').isHidden(),true);
    assert.equal(await page.locator('#spotlightImage').isVisible(),true);
    assert.equal(await page.locator('#readerSelected').textContent(),
     'ニュース 2 / '+editorialCover.storyCount);
    assert.equal(await page.locator('#spotlightBody').isVisible(),true);
    if(await gallery.count()>2){
     await page.locator('#readerNext').click();
     assert.equal(await page.locator('#readerSelected').textContent(),
      'ニュース 3 / '+editorialCover.storyCount);
     await page.locator('#readerPrev').click();
     assert.equal(await page.locator('#spotlightTitle').textContent(),expectedTitle);
    }
    await page.screenshot({path:'mobile-screenshots/selected-story-'+viewport.name+'.png',animations:'disabled'});
    await page.locator('#readerBack').click();
    assert.equal(await articleReader.isHidden(),true);
    assert.equal(await gallery.nth(1).getAttribute('aria-expanded'),'false');
   }
   await page.locator('#issueGallery').scrollIntoViewIfNeeded();
   await page.screenshot({path:'mobile-screenshots/visual-gallery-'+viewport.name+'.png',animations:'disabled'});
   const appIcon=page.locator('header.nav .logo-mark');
   assert.equal(await appIcon.count(),1,'the redesigned home-screen mark is shown');
   await appIcon.evaluate(img=>img.decode());
   assert.equal(await appIcon.evaluate(img=>img.naturalWidth>0),true,'brand icon loads');
   // The retired archive and map are absent, while the gallery still works.
   for(const removed of ['#archiveExtras','#mapExtras','#coverWorldMap',
                          '#coverWorldLink','#worldInvitation','#atlasPreview']){
    assert.equal(await page.locator(removed).count(),0,
      'retired map/archive control must not exist: '+removed);
   }
   await gallery.first().click();
   assert.equal(await articleReader.isVisible(),true,
    'gallery opens the selected full article in a separate reading screen');
   assert.equal(await page.locator('#spotlight').isVisible(),true);
   await page.evaluate(()=>window.scrollTo(0,0));
   const png=await page.request.get(new URL('assets/apple-touch-icon.png',url).toString());
   assert.equal(png.status(),200,'iPhone home screen PNG is deployed');
   // Phase 2: typography, editorial labeling and touch targets.
   const articleHierarchy=await page.evaluate(()=>{
    const title=document.querySelector('#spotlightTitle');
    const fact=document.querySelector('.spotlight-fact');
    const story=document.querySelector('#spotlightBody');
    const narrative=document.querySelector('#spotlightBody .article-narrative');
    const quip=document.querySelector('.spotlight-joke');
    const read=document.querySelector('#spotlightRead');
    return {
     titleBottom:title?.getBoundingClientRect().bottom,
     articleTop:story?.getBoundingClientRect().top,
     articleBottom:story?.getBoundingClientRect().bottom,
     quipTop:quip?.getBoundingClientRect().top,
     factHidden:getComputedStyle(fact).display==='none',
     readHidden:getComputedStyle(read).display==='none',
     quipDisclaimer:quip?.querySelector('.humor-marker')?.textContent?.trim(),
     paragraphCount:narrative?.querySelectorAll('.detailtext').length,
     repeatedSummaries:story?.querySelectorAll('p.summary').length,
     repeatedDates:story?.querySelectorAll('p.reported').length,
     sourceRepeated:story?.querySelector('.source')?.textContent?.includes('報道時期：')
    };
   });
   assert.ok(articleHierarchy.titleBottom<=articleHierarchy.articleTop+2,
    'the headline leads straight into the full article instead of a second synopsis');
   assert.equal(articleHierarchy.factHidden,true,
    'no short summary is repeated above the full article');
   assert.equal(articleHierarchy.readHidden,true,
    'the fully opened article needs no redundant read-more button');
   assert.equal(articleHierarchy.repeatedSummaries,0,
    'summary appears on the overview card only, never a second time in the article');
   assert.ok(articleHierarchy.paragraphCount>=1,
    'each opened story has one complete editorial narrative');
   assert.equal(articleHierarchy.repeatedDates,1,
    'reported date appears only once');
   assert.equal(articleHierarchy.sourceRepeated,false,
    'the source link does not repeat a second reported-date header');
   assert.ok(articleHierarchy.articleBottom<=articleHierarchy.quipTop+2,
    'the complete factual story precedes the separate AI joke');
   assert.equal(articleHierarchy.quipDisclaimer,'創作の冗談',
    'the creative joke is clearly distinct from reporting');
   if(await gallery.count()>1){
    const expectedTitle=await page.locator('#stories [data-story-index="1"] h3').textContent();
    await page.locator('#readerNext').click();
    assert.equal(await page.locator('#spotlightTitle').textContent(),expectedTitle,
     'next-news opens the second story in its own view');
    assert.equal(await page.locator('#spotlight .spotlight-fact .fact-kicker').textContent(),'起きたこと');
    assert.equal(await page.locator('#spotlight .spotlight-joke .humor-marker').textContent(),'創作の冗談');
    assert.equal(await page.locator('#stories').isHidden(),true,
     'second story is never stacked as an extra card');
    await page.locator('#readerPrev').click();
   }
   assert.equal(await page.locator('#spotlightRead').isHidden(),true,
    'the old expand/collapse control is absent on an already-open full article');
   const backHeight=await page.locator('#readerBack').evaluate(el=>el.getBoundingClientRect().height);
   assert.ok(backHeight>=44,'the news-list back control remains touch-friendly');
   const shortEdition=await page.evaluate(()=>document.querySelectorAll('#stories .story').length+1<=3);
   if(shortEdition){
    const hidden=await page.locator('.filters').evaluate(el=>getComputedStyle(el).display==='none');
    assert.ok(hidden,'1–3 article editions do not need five category filters');
   }
   await page.screenshot({path:'mobile-screenshots/cover-'+viewport.name+'.png',animations:'disabled'});
   await page.locator('#readerBack').click();
   assert.equal(await page.locator('#atlasHero').isVisible(),true,
    'overview returns before moving to the closing note and country map');
   const closing=page.locator('#closing');
   assert.equal(await closing.locator('h2').textContent(),'世界からの便りは、ここまで。',
    'closing works for both day and night, today and archive');
   assert.equal(await closing.locator('.closing-afterword').textContent(),
    '次の「まさか」も、世界のどこかから。');
   assert.equal(await closing.locator('.bye').textContent(),'また、次の便りで。');
   const quoteHidden=await page.locator('#closingQuote').isHidden();
   if(quoteHidden){
    const compactHeight=await closing.evaluate(el=>el.getBoundingClientRect().height);
    assert.ok(compactHeight<=220,
     'empty nightly joke should leave a quiet compact closing: '+compactHeight+'px');
   }
   await closing.scrollIntoViewIfNeeded();
   await page.screenshot({path:'mobile-screenshots/closing-'+viewport.name+'.png',animations:'disabled'});
   // Only the current edition is mapped: real country centroids over a
   // pastel illustrated map; neither monthly shelf nor past issue map exists.
   const today=page.locator('#todayMapSection');
   assert.equal(await today.count(),1,'current-edition map is visible');
   assert.equal(await page.locator('#monthRetrospective').count(),0,
    'monthly shelf is fully removed');
   await page.waitForFunction(()=>document.querySelectorAll('#todayMapLegend .today-map-country').length>0,
    null,{timeout:30000});
   const mapArt=today.locator('.today-map-art');
   await mapArt.evaluate(img=>img.decode());
   assert.equal(await mapArt.evaluate(img=>img.naturalWidth>0),true,
    'bundled map artwork must load on mobile');
   const pins=today.locator('.today-map-pin');
   const countryButtons=today.locator('.today-map-country');
   assert.ok(await pins.count()>=1,'published countries have visible map pins');
   assert.equal(await pins.count(),await countryButtons.count(),
    'one country pin corresponds to one named country button');
   assert.ok((await today.locator('#todayMapNote').textContent()).includes('ニュースの発生現場'),
    'centroid pins are not misrepresented as news incident locations');
   await today.screenshot({path:'mobile-screenshots/today-map-'+viewport.name+'.png',
    animations:'disabled'});
   // The country introduction is a separate, substantial visual feature.
   // Its iconic photo must actually render, not merely appear in the HTML.
   const countryCoverAssets=new Map();
   // Two nearby country centroids (e.g. UK and Spain) must not overlap as
   // finger targets on narrow iPhones. Only their markers may be nudged;
   // small leader lines preserve the exact representative map locations.
   const pinCenters=[];
   for(let i=0;i<await pins.count();i++){
    const bounds=await pins.nth(i).boundingBox();
    assert.ok(bounds,'map pin has a bounding box');
    const center={x:bounds.x+bounds.width/2,y:bounds.y+bounds.height/2};
    for(const other of pinCenters){
     assert.ok(Math.hypot(center.x-other.x,center.y-other.y)>=43,
      'country pins must not overlap on mobile: '+JSON.stringify({center,other}));
    }
    pinCenters.push(center);
   }
   for(let i=0;i<await pins.count();i++){
    const pin=pins.nth(i);
    const code=await pin.getAttribute('data-country-code');
    await pin.evaluate(element=>element.scrollIntoView({block:'center'}));
    await pin.click();
    const intro=today.locator('#todayMapIntro');
    assert.equal(await intro.isVisible(),true,'map pin opens the country guide: '+code);
    assert.ok((await intro.locator('#todayMapIntroBody').textContent()).length>35,
     'country guide explains the place, not just the name: '+code);
    if(['AR','FR','US'].includes(code)){
     await page.waitForFunction(expected=>{
      const intro=document.querySelector('#todayMapIntro');
      const img=document.querySelector('#todayMapIntroImage');
      return intro?.dataset.countryCode===expected&&img?.complete&&img.naturalWidth>0&&
       !document.querySelector('#todayMapIntroFigure').hidden;
     },code,{timeout:30000});
     const img=intro.locator('#todayMapIntroImage');
     const src=await img.getAttribute('src');
     assert.ok(src?.startsWith('./assets/travel/'),
      'country hero uses the packaged iconic photo: '+code+' '+src);
     const bounds=await img.boundingBox();
     assert.ok(bounds?.width>=240&&bounds?.height>=190,
      'country photo is large enough to enjoy on mobile: '+code+' '+JSON.stringify(bounds));
     assert.ok((await intro.locator('#todayMapIntroBody').textContent()).length>140,
      'featured country has a detailed, useful introduction: '+code);
     assert.ok((await intro.locator('#todayMapIntroCaption').textContent()).includes('撮影：'),
      'country photo identifies the photographer: '+code);
     countryCoverAssets.set(code,src);
     if(viewport.name==='standard'){
      await intro.screenshot({path:'mobile-screenshots/country-'+code+'.png',
       animations:'disabled'});
     }
    }
    await intro.locator('#todayMapIntroClose').click();
   }
   // The stamp album is always visible and interactive, even before the first quiz.
   const album=today.locator('#todayPassportBoard');
   const stamps=album.locator('.today-passport-stamp');
   const countryTotal=await countryButtons.count();
   assert.equal(await album.isVisible(),true,'the passport collection is permanently visible');
   assert.equal(await stamps.count(),countryTotal,'every quiz country has its own visible stamp slot');
   assert.equal((await album.locator('#todayPassportCount').textContent()).trim(),'0 / '+countryTotal,
    'the passport begins with a visible zero count');
   assert.equal(await album.locator('#todayPassportMeter').getAttribute('aria-valuenow'),'0',
    'the accessible collection meter starts at zero');
   // The stamp album is the only visible quiz launcher; hidden country buttons track completion.
   const previouslySelected=await page.locator('#readerSelected').textContent();
   const quiz=today.locator('#todayCountryQuiz');
   for(let index=0;index<await countryButtons.count();index++){
    const chip=countryButtons.nth(index);
    const code=await chip.getAttribute('data-country-code');
    await stamps.nth(index).click();
    assert.equal(await quiz.isVisible(),true,
     'visible passport stamp opens the country quiz: '+code);
    assert.equal(await quiz.locator('#todayQuizChoices button').count(),3,
     'the quiz has three real answer choices: '+code);
    assert.ok(await quiz.locator('#todayQuizSteps .today-quiz-step').count()>=1,
     'question-by-question progress is visible: '+code);
    assert.equal(await quiz.locator('#todayQuizStampReward').isHidden(),true,
     'no stamp is awarded before answering: '+code);
    assert.equal(await quiz.locator('#todayQuizPhotoFigure').isHidden(),true,
     'answer photos must never reveal the solution before a choice: '+code);
    assert.equal(await page.locator('#readerSelected').textContent(),previouslySelected,
     'quiz button never selects an article');
    const curated=['AR','FR','US','GB','ES','JP','NZ'].includes(code);
    const totalRounds=await quiz.locator('#todayQuizSteps .today-quiz-step').count();
    assert.equal(totalRounds,curated?2:1,
     'curated destinations have two meaningful quiz rounds: '+code);
    for(let round=0;round<totalRounds;round++){
     // Play a genuinely correct answer: its immediate sparkle action must
     // happen on every question, not just after the passport stamp is awarded.
     const correctIndex=await page.evaluate(({code,round})=>{
      const item=worldPassportActive?.questions?.[round];
      return Number.isInteger(item?.answer)?item.answer:0;
     },{code,round});
     const animateCorrect=viewport.name==='standard'&&index===0&&round===0;
     if(animateCorrect)await page.emulateMedia({reducedMotion:'no-preference'});
     await quiz.locator('#todayQuizChoices button').nth(correctIndex).click();
     if(animateCorrect){
      const sparkle=quiz.locator('.quiz-answer-sparks span').first();
      const motionName=await sparkle.evaluate(el=>getComputedStyle(el).animationName);
      assert.ok(motionName.includes('quiz-sparkle-fly'),
       'normal-motion users see real flying sparkles on each correct answer');
      const bounce=await quiz.locator('#todayQuizChoices button[data-popped="true"]')
       .evaluate(el=>getComputedStyle(el).animationName);
      assert.ok(bounce.includes('quiz-choice-pop'),
       'the correct button physically bounces rather than only changing text');
      await page.emulateMedia({reducedMotion:'reduce'});
     }
     assert.equal(await quiz.locator('#todayQuizCorrectFlash').isVisible(),true,
      'every correct answer immediately celebrates: '+code+' / '+round);
     assert.equal(await quiz.locator('#todayQuizChoices button[data-popped="true"]').count(),1,
      'exactly the chosen correct option gets a bounce: '+code+' / '+round);
     assert.equal(await quiz.locator('#todayQuizChoices .quiz-answer-sparks span').count(),10,
      'the answer creates ten noninteractive sparkle particles: '+code+' / '+round);
     assert.equal(await quiz.locator('#todayQuizResult').isVisible(),true,
      'answer reveals the result');
     assert.ok((await quiz.locator('#todayQuizExplanation').textContent()).length>14,
      'answer includes factual local context');
     assert.ok((await quiz.locator('#todayQuizJoke').textContent()).includes('創作の冗談'),
      'fictional humor is clearly labeled');
     const hasPhoto=curated&&!(['ES','NZ'].includes(code)&&round===1);
     if(hasPhoto){
      await page.waitForFunction(()=>{
       const image=document.querySelector('#todayQuizPhotoImage');
       const frame=document.querySelector('#todayQuizPhotoFigure');
       return image&&image.complete&&image.naturalWidth>0&&frame&&!frame.hidden;
      },null,{timeout:30000});
      const frame=quiz.locator('#todayQuizPhotoFigure');
      const src=await frame.locator('img').getAttribute('src');
      assert.ok(src.startsWith('./assets/travel/'),
       'answer uses a bundled authentic photo: '+code+' / '+round+' '+src);
      assert.ok((await frame.locator('#todayQuizPhotoCaption').textContent()).includes('正解'),
       'answer picture has a meaningful caption');
      assert.ok((await frame.locator('#todayQuizPhotoSource').getAttribute('href')).startsWith('https://commons.wikimedia.org/wiki/File:'),
       'photo has linked original creator attribution');
      assert.ok((await frame.locator('#todayQuizPhotoLicense').getAttribute('href')).startsWith('https://creativecommons.org/'),
       'photo has linked reuse license');
      assert.notEqual(src,countryCoverAssets.get(code),
       'quiz photograph must differ from the country feature cover');
      if(viewport.name==='standard'){
       await frame.screenshot({path:'mobile-screenshots/quiz-'+code+'-'+round+'.png',
        animations:'disabled'});
      }
      await frame.locator('#todayQuizPhotoZoom').click();
      assert.equal(await page.locator('#todayQuizPhotoDialog').isVisible(),true,
       'photo can be enlarged in an accessible modal');
      await page.locator('#todayQuizPhotoDialogClose').click();
      assert.equal(await page.locator('#todayQuizPhotoDialog').isHidden(),true,
       'photo modal closes');
     }else if(curated){
      assert.equal(await quiz.locator('#todayQuizPhotoNotice').isVisible(),true,
       'when no verified image exists, the quiz explains the omission without a fake photo');
     }
     const next=quiz.locator('#todayQuizNext');
     if((await next.textContent()).includes('次の問題へ'))await next.click();
     else break;
    }
    assert.equal(await quiz.locator('#todayQuizStampReward').isVisible(),true,
     'finishing the challenge displays a large tangible stamp reward: '+code);
    assert.equal(await quiz.locator('#todayQuizStampReward').getAttribute('data-perfect'),'true',
     'a perfect two-round run receives the stronger gold celebration');
    assert.equal(await quiz.locator('#todayQuizStampReward').getAttribute('data-new'),'true',
     'the first country completion has a distinct earned-stamp moment: '+code);
    assert.equal(await album.locator('#todayPassportCount').textContent(),(index+1)+' / '+countryTotal,
     'passport count increases immediately with every stamp');
    assert.equal(await album.locator('#todayPassportMeter').getAttribute('aria-valuenow'),String(index+1),
     'accessible passport meter matches the visible collection');
    assert.equal(await album.locator('.today-passport-stamp[data-country-code="'+code+'"]').getAttribute('data-earned'),'true',
     'the country stamp changes visibly from blank to earned');
    assert.equal(await chip.getAttribute('data-quiz-done'),'true',
     'country earns its stamp after the final question: '+code);
    await quiz.locator('#todayQuizClose').click();
    assert.equal(await quiz.isHidden(),true,'quiz can be closed');
   }
   assert.ok((await quiz.locator('#todayQuizPassport').textContent()).includes('世界パスポート完成'),
    'all mapped countries collected to finish the passport');
   assert.equal(await album.getAttribute('data-complete'),'true',
    'the completed stamp book is visibly distinct');
   assert.equal(await album.getAttribute('data-celebrate'),'true',
    'collecting the final country triggers a separate full-passport celebration');
   assert.equal(await album.locator('#todayPassportMeter').getAttribute('aria-valuenow'),String(countryTotal),
    'the collection meter reaches the complete number of countries');
   assert.ok((await album.locator('#todayPassportMessage').textContent()).includes('世界パスポート完成'),
    'the fully collected album announces the milestone');
   if(viewport.name==='standard'){
    await album.screenshot({path:'mobile-screenshots/stamp-album-complete.png',animations:'disabled'});
   }
   await gallery.first().click();
   const travelButton=page.locator('#spotlight .travel-open');
   assert.equal(await travelButton.getAttribute('aria-expanded'),'false',
    'today article travel is optional and initially closed');
   await travelButton.click();
   await page.waitForFunction(()=>{
    const img=document.querySelector('#spotlight .travel-photo');
    return !!img&&img.complete&&img.naturalWidth>0;
   },null,{timeout:30000});
   const postcard=page.locator('#spotlight .travel-card');
   assert.equal(await postcard.count(),1,'today article has its travel photo');
   assert.ok((await postcard.locator('.travel-trust').textContent()).includes('ニュース現場の記録ではなく'),
    'tourist photography is labeled separately from actual reportage');
   const photoSource=await postcard.locator('.travel-photo').getAttribute('src');
   assert.ok(photoSource?.includes('assets/travel/'),'travel photo is locally bundled');
   const firstCountryCode=await pins.first().getAttribute('data-country-code');
   if(countryCoverAssets.has(firstCountryCode)){
    assert.notEqual(photoSource,countryCoverAssets.get(firstCountryCode),
     'country introduction and 30-second travel must use DIFFERENT real photographs');
   }
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
   assert.ok(overflow<2,'no horizontal overflow: '+overflow+'px');
   assert.deepEqual(errors,[],'no JavaScript uncaught errors');
   process.stdout.write('Mobile smoke OK: '+viewport.width+'px; '+photoSource+'\n');
  }finally{await context.close();}
 }
}finally{await browser.close();}
