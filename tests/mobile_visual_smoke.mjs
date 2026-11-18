/* Mobile-browser smoke test for the public nightly reader.
   Chromium's device emulation is useful but is NOT an iPhone Safari test. */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const url='https://ogasawaratouei1998-lgtm.github.io/yoru9-world-letter/';
await fs.mkdir('mobile-screenshots',{recursive:true});
const browser=await chromium.launch({headless:true});
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
    freshDesign=await page.locator('#coverWorldMap').count()===1&&
     await page.locator('#atlasHero .atlas-oops').count()===1&&
     await page.locator('#issueGallery[data-layout="mobile-grid-2plus1"]').count()===1&&
     await page.locator('#quipTeaserLine').count()===1&&
     await page.locator('#spotlightImage').count()===1;
    if(freshDesign)break;
    await page.waitForTimeout(6000);
   }
   assert.ok(freshDesign,'GitHub Pages must serve the latest world-atlas cover');
   await page.waitForFunction(()=>{
    const el=document.querySelector('#spotlightTitle');
    return el&&el.textContent&&!el.textContent.includes('準備中');
   },null,{timeout:30000});
   const editorialCover=await page.evaluate(()=>{
    const hero=document.querySelector('#atlasHero');
    const h2=hero?.querySelector('.atlas-title');
    const bubble=hero?.querySelector('.atlas-brand');
    const lede=hero?.querySelector('#atlasLede');
    const map=hero?.querySelector('#coverWorldMap');
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
      mapTop:box(map)?.top
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
   assert.ok(editorialCover.bubble.includes('AIが本気でツッコむ。'),
    'the core joke premise appears on the screen');
   assert.ok(editorialCover.headlineBottom<=editorialCover.conceptTop+2&&
    editorialCover.conceptBottom<=editorialCover.mapTop+2,
    'the reading order is concept, joke, then countries');
   // A first-time visitor sees an actual verified quip BEFORE the map.
   const teaser=page.locator('#quipTeaser');
   assert.equal(await teaser.isVisible(),true,
    'the current approved issue has a real opening punchline');
   assert.equal(await page.locator('#quipTeaserLine').textContent(),
    await page.locator('#spotlightQuip').textContent(),
    'opening joke and actual article use precisely the same approved text');
   assert.equal(await page.locator('#quipTeaserImage').getAttribute('src'),
    await page.locator('#spotlightImage').getAttribute('src'),
    'the early joke uses the right published article illustration');
   assert.ok((await page.locator('#quipTeaserTopic').textContent()).length>3,
    'the opening joke has its news context rather than an unexplained gag');
   const teaserGeometry=await page.evaluate(()=>{
    const r=id=>document.querySelector(id)?.getBoundingClientRect();
    const a=r('#atlasHero .atlas-concept'),t=r('#quipTeaser'),
          g=r('#issueGallery'),m=r('#coverWorldMap');
    return {conceptBottom:a?.bottom,teaserTop:t?.top,teaserBottom:t?.bottom,
      galleryTop:g?.top,galleryBottom:g?.bottom,mapTop:m?.top,
      mapHeight:m?.height,windowWidth:window.innerWidth};
   });
   assert.ok(teaserGeometry.conceptBottom<=teaserGeometry.teaserTop+2&&
     teaserGeometry.teaserBottom<=teaserGeometry.galleryTop+2&&
     teaserGeometry.galleryBottom<=teaserGeometry.mapTop+2,
     'the comedy payoff is visible before choosing a picture or visiting a map');
   assert.ok(teaserGeometry.mapHeight<=168,
    'the small mobile atlas is compressed so readers reach a story sooner');
   assert.equal(await page.locator('#quipTeaserRead').evaluate(el=>
      el.getBoundingClientRect().height>=44),true,'first joke has a real thumb-size read action');
   await page.locator('#quipTeaserRead').click();
   assert.equal(await page.locator('#spotlightRead').getAttribute('aria-expanded'),'true',
    'first joke opens the real article with source, rather than inventing another page');
   const earlySmile=page.locator('#quipTeaser .teaser-smile');
   await earlySmile.click();
   assert.equal(await earlySmile.getAttribute('aria-pressed'),'true',
    'a happy reaction persists using the already existing reader state');
   assert.ok(!(await earlySmile.evaluate(el=>el.classList.contains('smile-burst'))),
    'reduced-motion mobile users never get forced sparkle movement');
   await earlySmile.click();
   assert.equal(await earlySmile.getAttribute('aria-pressed'),'false',
    'the opt-in reaction can be undone without a fake vote count');
   await teaser.scrollIntoViewIfNeeded();
   await page.screenshot({path:'mobile-screenshots/first-laugh-'+viewport.name+'.png',
     animations:'disabled'});
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
   assert.ok(grid.hint.right<=grid.hero.right+2,
    'gallery header hint stays entirely inside the hero');
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
   const firstImage=page.locator('#issueGallery .gallery-art').first();
   assert.ok((await firstImage.getAttribute('src')).startsWith('./assets/news/'),
    'visual assets are bundled locally, not from third-party news photos');
   assert.ok((await gallery.first().getAttribute('aria-label')).includes('を読む'),
    'a picture alone has a meaningful accessible reading action');
   const leadImage=page.locator('#spotlightImage');
   await leadImage.scrollIntoViewIfNeeded();
   await leadImage.evaluate(async img=>{if(!img.complete)await new Promise((resolve,reject)=>{
    img.addEventListener('load',resolve,{once:true});
    img.addEventListener('error',()=>reject(Error('lead illustration failed')),{once:true});
   });});
   assert.ok(await leadImage.evaluate(el=>el.naturalWidth>0),
    'the lead story has an actual visual instead of a colored placeholder');
   assert.ok((await page.locator('#spotlightVisual figcaption').textContent()).includes('現場写真ではありません'),
    'lead illustration is explicitly labeled');
   if(await gallery.count()>1){
    await gallery.nth(1).click();
    assert.equal(await page.locator('#stories [data-story-index="1"] [data-open="1"]').getAttribute('aria-expanded'),
     'true','gallery opens the exact supporting story, not unrelated articles');
    const art=page.locator('#stories [data-story-index="1"] .story-art');
    await art.scrollIntoViewIfNeeded();
    await page.waitForFunction(()=>{
      const image=document.querySelector('#stories [data-story-index="1"] .story-art');
      return image&&image.complete&&image.naturalWidth>0;
    },null,{timeout:30000});
    assert.ok((await page.locator('#stories .story-visual figcaption').first().textContent()).includes('イメージイラスト'),
     'secondary story art is not presented as documentary photography');
    assert.ok(await page.locator('#stories [data-story-index="1"] .readbtn').evaluate(el=>
      el.getBoundingClientRect().height>=44),'illustrated story retains an easy touch target');
    await page.screenshot({path:'mobile-screenshots/illustrated-story-'+viewport.name+'.png',animations:'disabled'});
   }
   await page.locator('#issueGallery').scrollIntoViewIfNeeded();
   await page.screenshot({path:'mobile-screenshots/visual-gallery-'+viewport.name+'.png',animations:'disabled'});
   const appIcon=page.locator('header.nav .logo-mark');
   assert.equal(await appIcon.count(),1,'the redesigned home-screen mark is shown');
   await appIcon.evaluate(img=>img.decode());
   assert.equal(await appIcon.evaluate(img=>img.naturalWidth>0),true,'brand icon loads');
   await page.waitForFunction(()=>{
    const pagePins=document.querySelectorAll('#coverMapPins .atlas-pin');
    return pagePins.length>0&&document.querySelector('#coverMapCaption')?.textContent.includes('ニュースの現場ではありません');
   },null,{timeout:30000});
   const pins=page.locator('#coverMapPins .atlas-pin');
   assert.ok(await pins.count()>=1,'published story locations are represented');
   const preview=page.locator('#atlasPreview');
   assert.equal(await preview.isHidden(),true,'country preview starts closed');
   await pins.first().click();
   assert.equal(await preview.isVisible(),true,'country pin previews this edition without leaving atlas');
   assert.ok(await preview.locator('.atlas-preview-title').count()>=1,'preview has a real news title');
   assert.equal(await pins.first().getAttribute('aria-pressed'),'true',
    'active map selection is accessible');
   const firstCountry=await preview.locator('.atlas-preview-heading h3').textContent();
   if(await pins.count()>1){
    await pins.nth(1).click();
    assert.equal(await pins.nth(1).getAttribute('aria-pressed'),'true');
    assert.notEqual(await preview.locator('.atlas-preview-heading h3').textContent(),firstCountry,
     'different country pin selects its own country, even for multi-country stories');
   }
   const read=preview.locator('[data-atlas-read]').first();
   const storyIndex=Number(await read.getAttribute('data-atlas-read'));
   await read.click();
   assert.equal(await preview.isHidden(),true,'preview closes when a story opens');
   if(storyIndex===0){
    assert.equal(await page.locator('#spotlightRead').getAttribute('aria-expanded'),'true',
     'lead preview expands the original lead article');
   }else{
    assert.equal(await page.locator('#stories [data-story-index="'+storyIndex+'"] [data-open]').getAttribute('aria-expanded'),'true',
     'country preview opens the exact supporting article');
   }
   await page.locator('#coverWorldLink').click();
   assert.equal(await page.locator('#mapExtras').getAttribute('open'),'',
    'full country archive remains reachable independently');
   await page.evaluate(()=>window.scrollTo(0,0));
   const png=await page.request.get(new URL('assets/apple-touch-icon.png',url).toString());
   assert.equal(png.status(),200,'iPhone home screen PNG is deployed');
   // Phase 2: typography, editorial labeling and touch targets.
   const leadHierarchy=await page.evaluate(()=>{
    const title=document.querySelector('#spotlightTitle');
    const facts=document.querySelector('.spotlight-fact');
    const quip=document.querySelector('.spotlight-joke');
    return {
      titleBottom:title?.getBoundingClientRect().bottom,
      factTop:facts?.getBoundingClientRect().top,
      factBottom:facts?.getBoundingClientRect().bottom,
      quipTop:quip?.getBoundingClientRect().top,
      quipBottom:quip?.getBoundingClientRect().bottom,
      label:facts?.querySelector('.fact-kicker')?.textContent?.trim(),
      disclaimer:quip?.querySelector('.humor-marker')?.textContent?.trim(),
      factBackground:getComputedStyle(facts).backgroundImage,
      quipBackground:getComputedStyle(quip).backgroundImage
    };
   });
   assert.equal(leadHierarchy.label,'起きたこと','reporting is clearly labeled');
   assert.equal(leadHierarchy.disclaimer,'創作の冗談','AI quip is explicitly marked as humor');
   assert.ok(leadHierarchy.titleBottom<=leadHierarchy.factTop+2,
    'headline precedes fact summary');
   assert.ok(leadHierarchy.factBottom<leadHierarchy.quipTop,
    'facts and AI punchline are visually separated');
   assert.notEqual(leadHierarchy.factBackground,leadHierarchy.quipBackground,
    'AI joke uses a distinct editorial surface');
   const supportingCards=page.locator('#stories .story');
   if(await supportingCards.count()>0){
    const firstCard=supportingCards.first();
    assert.equal(await firstCard.locator('.story-fact .fact-kicker').textContent(),'起きたこと');
    assert.equal(await firstCard.locator('.teaserquip .humor-marker').textContent(),'創作の冗談');
    assert.ok(await firstCard.locator('[data-open]').evaluate(
      el=>el.getBoundingClientRect().height>=44),
     'secondary story reading action is touch-friendly');
    assert.ok(await firstCard.locator('.story-fact').evaluate(el=>
      el.getBoundingClientRect().bottom<el.closest('.story').querySelector('.teaserquip').getBoundingClientRect().top),
     'secondary facts precede and remain separate from AI humor');
   }
   const primaryButton=page.locator('#spotlightRead');
   const buttonHeight=await primaryButton.evaluate(el=>el.getBoundingClientRect().height);
   assert.ok(buttonHeight>=44,'lead article action must be touch-friendly');
   const shortEdition=await page.evaluate(()=>document.querySelectorAll('#stories .story').length+1<=3);
   if(shortEdition){
    const hidden=await page.locator('.filters').evaluate(el=>getComputedStyle(el).display==='none');
    assert.ok(hidden,'1–3 article editions do not need five category filters');
   }
   await page.screenshot({path:'mobile-screenshots/cover-'+viewport.name+'.png',animations:'disabled'});
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
   const article=page.locator('#monthCards .month-story').first();
   await article.waitFor({state:'attached',timeout:30000});
   const shelf=page.locator('#monthRetrospective > details');
   assert.equal(await shelf.getAttribute('open'),null,'monthly shelf begins closed');
   await shelf.locator('summary').first().click();
   const details=article.locator('details').first();
   await details.locator('summary').first().click();
   const travelButton=article.locator('[data-month-travel]').first();
   const travelPanel=article.locator('.travel-panel').first();
   assert.equal(await travelButton.getAttribute('aria-expanded'),'false',
    'monthly travel remains closed when an article opens');
   assert.equal(await travelPanel.isHidden(),true,
    'travel photos are opt-in rather than auto-shown');
   await travelButton.click();
   assert.equal(await travelButton.getAttribute('aria-expanded'),'true',
    'tapping the travel button opens its postcard');
   await page.waitForFunction(()=>{
    const img=document.querySelector('#monthCards .month-story .travel-photo');
    return !!img&&img.complete&&img.naturalWidth>0;
   },null,{timeout:30000});
   const postcard=article.locator('.travel-card');
   assert.equal(await postcard.count(),1,'one optional postcard for selected story');
   assert.ok((await postcard.locator('.travel-context-story').textContent()).includes('記事の舞台（国）'),
    'article-country geography is labeled separately');
   assert.ok((await postcard.locator('.travel-context-destination').textContent()).includes('旅先'),
    'tourist destination has a separate country label');
   assert.ok((await postcard.locator('.travel-trust').textContent()).includes('ニュース現場の記録ではなく'),
    'every photograph is explicitly distinguished from incident footage');
   assert.ok((await postcard.locator('.travel-links a').first().getAttribute('href')).includes('openstreetmap.org'),
    'map opens the destination rather than inventing news-site coordinates');
   const photo=article.locator('.travel-photo');
   const photoSource=await photo.getAttribute('src');
   assert.ok(photoSource?.includes('assets/travel/'),'must use bundled photo');
   await photo.scrollIntoViewIfNeeded();
   await page.screenshot({path:'mobile-screenshots/monthly-'+viewport.name+'.png',animations:'disabled'});
   await details.locator('summary').first().click();
   assert.equal(await details.getAttribute('open'),null,'article collapses');
   await details.locator('summary').first().click();
   assert.equal(await photo.getAttribute('src'),photoSource,'reopening keeps same photo');
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
   assert.ok(overflow<2,'no horizontal overflow: '+overflow+'px');
   assert.deepEqual(errors,[],'no JavaScript uncaught errors');
   process.stdout.write('Mobile smoke OK: '+viewport.width+'px; '+photoSource+'\n');
  }finally{await context.close();}
 }
}finally{await browser.close();}
