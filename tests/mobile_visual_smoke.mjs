/* Mobile-browser smoke test for the public nightly reader.
   Chromium's device emulation is useful but is NOT an iPhone Safari test. */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

// Release candidates run against their pre-deployment local bundle. The
// post-deploy smoke keeps checking the actual public GitHub Pages origin.
const previewUrl=process.env.READER_SITE_URL||'';
if(previewUrl&&!/^http:\/\/127\.0\.0\.1:\d+\/$/.test(previewUrl))
 throw new Error('Pre-release smoke URL must be a local loopback HTTP server');
const url=previewUrl||'https://ogasawaratouei1998-lgtm.github.io/yoru9-world-letter/';
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
   for(let attempt=0;attempt<(previewUrl?1:16);attempt++){
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
     await page.locator('#quipTeaser').count()===0&&
      await page.locator('.reader-first-link').count()===0&&
     await page.locator('#articleReader[hidden]').count()===1&&
     await page.locator('#readerBack').count()===1&&
     await page.locator('#spotlightImage').count()===1;
    if(freshDesign)break;
    await page.waitForTimeout(6000);
   }
   assert.ok(freshDesign,'GitHub Pages must serve the latest simplified live news reader');
   // The embedded historical demo is rendered before the async published
   // issue arrives. A headline is not proof that the real issue has loaded.
   // Wait for the same published record to drive the title and both galleries.
   await page.waitForFunction(()=>{
    if(typeof edition==='undefined'||edition.status!=='published'||
       !Array.isArray(edition.stories)||!edition.stories.length)return false;
    const n=edition.stories.length;
    return document.querySelector('#spotlightTitle')?.textContent===edition.stories[0]?.title&&
     document.querySelector('#atlasStoryCount')?.textContent?.trim()===String(n)&&
     document.querySelectorAll('#issueGallery .gallery-tile').length===n&&
     document.querySelectorAll('#stories .story').length===Math.max(0,n-1)&&
     document.querySelector('#galleryHeading')?.textContent===
      '世界の「まさか」'+n+'コマ劇場';
   },null,{timeout:35000});
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
   // The visual gallery replaces a repeated always-visible article list.
   const articleReader=page.locator('#articleReader');
   assert.equal(await articleReader.isHidden(),true,
    'no second full news list appears before the reader chooses a picture');
   assert.equal(await page.locator('#spotlight').isHidden(),true,
    'lead reporting stays closed until requested');
   assert.equal(await page.locator('#stories').isHidden(),true,
    'supporting full stories stay closed until requested');
   assert.equal(await page.locator('#quipTeaser').count(),0,
    'the introductory AI quip card is removed');
   assert.equal(await page.locator('.reader-first-link').count(),0,
    'the redundant choose-news button is removed');
   assert.equal(await page.locator('#spotlightImage').count(),1);
   const geometry=await page.evaluate(()=>{
    const a=document.querySelector('#atlasHero .atlas-concept')?.getBoundingClientRect();
    const g=document.querySelector('#issueGallery')?.getBoundingClientRect();
    const h=document.querySelector('#atlasHero')?.getBoundingClientRect();
    return {conceptBottom:a?.bottom,galleryTop:g?.top,galleryBottom:g?.bottom,heroBottom:h?.bottom};
   });
   assert.ok(geometry.conceptBottom<=geometry.galleryTop+2&&
    geometry.galleryBottom<=geometry.heroBottom+2,
    'the visual gallery follows the explanatory concept directly');
   assert.ok(await page.locator('#atlasHero .atlas-brand').evaluate(el=>
      getComputedStyle(el).display==='flex'),
    'the real reporting / AI fiction labels remain visible');
   const firstTile=page.locator('#issueGallery .gallery-tile').first();
   assert.ok(await firstTile.evaluate(el=>el.getBoundingClientRect().height>=44),
    'the first visual news tile is touch-friendly');
   await firstTile.click();
   assert.equal(await articleReader.isVisible(),true,
    'tapping the news tile opens the on-demand article reader');
   assert.equal(await page.locator('#spotlightRead').getAttribute('aria-expanded'),'true',
    'the gallery opens the real article with its source');
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
   // The simplified reader no longer shows a reaction button. Instead,
   // verify the source citation and one usable sharing action.
   const articleSource=page.locator('#spotlightBody .source a');
   assert.equal(await articleSource.count(),1,
    'the article retains its original reporting source');
   assert.ok((await articleSource.getAttribute('href')).startsWith('https://'),
    'the source citation links to an HTTPS original');
   assert.equal(await page.locator('#spotlightBody button.share').count(),1,
    'the simplified reader keeps its share action');
   await page.screenshot({path:'mobile-screenshots/first-laugh-'+viewport.name+'.png',animations:'disabled'});
   await page.locator('#readerBack').click();
   assert.equal(await articleReader.isHidden(),true);
   assert.equal(await page.locator('#atlasHero').isVisible(),true);
   assert.equal(await page.locator('#issueGallery .gallery-tile').first().isVisible(),true,
    'the visual gallery remains available after returning from an article');
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
   const newSvgIssue=await page.evaluate(()=>
    edition.editionType==='regular'&&edition.editionDate>='2026-11-21');
   for(const path of galleryArts){
    assert.ok(path.startsWith('./assets/news/')||
     path.startsWith('./assets/news-generated/')||
     path.startsWith('data:image/svg+xml;charset=utf-8,'),
     'editorial artwork is bundled locally or rendered offline, not fetched from news sites');
    assert.ok(!path.includes('/category-work.svg')&&!path.includes('/category-sports.svg'),
     'current stories must not repeat category placeholders');
   }
   if(newSvgIssue){
    assert.ok(editorialCover.storyCount>=4&&editorialCover.storyCount<=5,
     'new regular issues must have four or five verified stories');
    assert.ok(galleryArts.every(path=>path.startsWith('./assets/news/')||
      path.startsWith('data:image/svg+xml;charset=utf-8,')),
     'free illustrated news must not depend on paid generated WebPs');
    assert.equal(await page.locator('#issueGallery .gallery-image-label').count(),0,
     'non-AI illustrations must not be labeled AI-generated');
   }
   const currentStoryIds=await page.evaluate(()=>edition.stories.map(s=>s.id));
   const bespokeArt={
    'uk-french-weir-swimming-2026':'uk-river-water-warning.svg',
    'mussolini-colador-2026':'spain-mussels-colander-pan.svg',
    'jp-gov-youtuber-pr-2026':'japan-policy-youtuber-pr.svg',
    'nz-cricket-collapse-2026':'nz-cricket-comeback.svg',
    'italy-toilet-ai-python-48-hour-search-2026':'ai-python-toilet.svg',
    'drew-carey-price-right-early-reveal-2026':'game-show-price-board.svg',
    'mainz-sewer-search-lost-drone-2026':'drone-sewer-search.svg',
    'kusel-lost-handcuff-key-police-help-2026':'lost-handcuff-key.svg'
   };
   for(const [index,id] of currentStoryIds.entries()){
    if(bespokeArt[id])assert.ok(galleryArts[index].endsWith('/'+bespokeArt[id]),
     'each news story uses its own matching illustration: '+id);
   }
   const firstImage=page.locator('#issueGallery .gallery-art').first();
   const firstArtSrc=await firstImage.getAttribute('src');
   assert.ok(firstArtSrc.startsWith('./assets/news/')||
    firstArtSrc.startsWith('data:image/svg+xml;charset=utf-8,'),
    'first visual is a local WebP, bundled SVG or inline offline-safe illustration');
   assert.ok((await gallery.first().getAttribute('aria-label')).includes('を読む'),
    'a picture alone has a meaningful accessible reading action');
   const leadImage=page.locator('#spotlightImage');
   assert.equal(await leadImage.isHidden(),true,
    'news illustration is already visible in the gallery and must not repeat in detail');
   const caption=await page.locator('#spotlightVisual figcaption').textContent();
   assert.ok(caption.includes('報道写真ではありません')||caption.includes('現場写真ではありません'),
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
   const explore=page.locator('#worldExplore');
   assert.equal(await today.count(),1,'current-edition map is retained');
   assert.equal(await explore.evaluate(el=>el.open),false,'optional world exploration is initially collapsed');
   assert.equal(await today.isHidden(),true,'map does not compete with the news gallery');
   assert.equal(await gallery.first().isVisible(),true,'news remains directly accessible');
   await explore.locator('summary').first().click();
   await today.waitFor({state:'visible'});
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   assert.equal(await explore.evaluate(el=>el.open),true);
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
   const uniqueMappedCountries=await countryButtons.count();
   const issueStoryCount=await page.evaluate(()=>edition.stories.length);
   const mapExplanation=await today.locator('#todayMapNote').textContent();
   assert.ok(mapExplanation.includes('実話'+issueStoryCount+'本・'+uniqueMappedCountries+'カ国'),
    'map states both published story count and deduplicated country count');
   assert.ok(mapExplanation.includes('重複を除いた国数'),
    'deduplicated country buttons are not mistaken for separate news articles');
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
    assert.equal(await page.locator('body').evaluate(el=>el.classList.contains('country-detail-mode')),true);
    assert.equal(await gallery.first().isVisible(),false,'country guide must not overlap the gallery');
    assert.equal(await page.locator('.nav').isVisible(),false,'home header must not cover country');
    assert.equal(await today.locator('#todayMapPins').isVisible(),false,'map hidden in country guide');
    assert.ok((await intro.locator('#todayMapIntroBody').textContent()).length>35,
     'country guide explains the place, not just the name: '+code);
    if(['AR','FR','US','IT','DE'].includes(code)){
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
     const nativeSize=await img.evaluate(image=>({width:image.naturalWidth,height:image.naturalHeight}));
     assert.ok(nativeSize.width>=1000&&nativeSize.height>=540,
      'country cover must be a sharp, locally packaged high-resolution photograph: '+
       code+' '+JSON.stringify(nativeSize));
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
    assert.equal(await page.locator('body').evaluate(el=>el.classList.contains('country-detail-mode')),false);
    assert.equal(await gallery.first().isVisible(),true,'closing country restores home gallery');
   }
   // Stamps, scores and the album have been retired. Country-specific
   // photographic trivia stays available via the visible map country chips.
   assert.equal(await today.locator('#todayPassportBoard').count(),0,
    'no obsolete passport collection is visible or mounted');
   assert.equal(await today.locator('.today-passport-stamp').count(),0,
    'no stamp controls remain');
   const quiz=today.locator('#todayCountryQuiz');
   const previouslySelected=await page.locator('#readerSelected').textContent();
   const countryTotal=await countryButtons.count();
   assert.equal(await pins.count(),countryTotal);
   for(let index=0;index<countryTotal;index++){
    const chip=countryButtons.nth(index);
    const code=await chip.getAttribute('data-country-code');
    assert.equal(await chip.isVisible(),true,'country quiz launcher visible: '+code);
    assert.ok((await chip.textContent()).includes('クイズ'),'button invites trivia, not stamp collection');
    await chip.click();
    assert.equal(await quiz.isVisible(),true,'country chip opens standalone trivia: '+code);
    assert.equal(await page.locator('body').evaluate(el=>el.classList.contains('quiz-detail-mode')),true);
    assert.equal(await gallery.first().isVisible(),false,'quiz must not overlap home gallery');
    assert.equal(await page.locator('.nav').isVisible(),false,'home header must not cover quiz');
    assert.equal(await today.locator('#todayMapPins').isVisible(),false,'map hidden while quiz active');
    assert.equal(await quiz.locator('#todayQuizChoices button').count(),3);
    assert.equal(await quiz.locator('#todayQuizPhotoFigure').isHidden(),true,
     'quiz answer photo is hidden until answer choice');
    assert.equal(await page.locator('#readerSelected').textContent(),previouslySelected,
     'quiz never opens a different news article');
    const curated=['AR','FR','US','GB','ES','JP','NZ','IT','DE'].includes(code);
    const totalRounds=await quiz.locator('#todayQuizSteps .today-quiz-step').count();
    assert.equal(totalRounds,curated?2:1,'curated country has two real quizzes: '+code);
    for(let round=0;round<totalRounds;round++){
     const correctIndex=await page.evaluate(({round})=>{
      const question=worldPassportActive?.questions?.[round];
      return Number.isInteger(question?.answer)?question.answer:0;
     },{round});
     const animateCorrect=viewport.name==='standard'&&index===0&&round===0;
     if(animateCorrect)await page.emulateMedia({reducedMotion:'no-preference'});
     await quiz.locator('#todayQuizChoices button').nth(correctIndex).click();
     if(animateCorrect){
      const sparkle=quiz.locator('.quiz-answer-sparks span').first();
      assert.ok((await sparkle.evaluate(el=>getComputedStyle(el).animationName)).includes('quiz-sparkle-fly'));
      await page.emulateMedia({reducedMotion:'reduce'});
     }
     assert.equal(await quiz.locator('#todayQuizCorrectFlash').isVisible(),true,
      'correct answers are celebrated without stamps');
     assert.equal(await quiz.locator('#todayQuizResult').isVisible(),true);
     assert.ok((await quiz.locator('#todayQuizExplanation').textContent()).length>14);
     assert.ok((await quiz.locator('#todayQuizJoke').textContent()).includes('創作の冗談'));
     const hasPhoto=curated&&!(['ES','NZ'].includes(code)&&round===1);
     if(hasPhoto){
      await page.waitForFunction(()=>{
       const img=document.querySelector('#todayQuizPhotoImage'),frame=document.querySelector('#todayQuizPhotoFigure');
       return img&&img.complete&&img.naturalWidth>0&&frame&&!frame.hidden;
      },null,{timeout:30000});
      const frame=quiz.locator('#todayQuizPhotoFigure');
      const src=await frame.locator('img').getAttribute('src');
      assert.ok(src?.startsWith('./assets/travel/'),'quiz answer uses authentic bundled photo: '+code);
      assert.notEqual(src,countryCoverAssets.get(code),
       'quiz photo must not repeat country portrait cover');
      assert.ok((await frame.locator('#todayQuizPhotoSource').getAttribute('href'))
       .startsWith('https://commons.wikimedia.org/wiki/File:'));
      assert.ok((await frame.locator('#todayQuizPhotoLicense').getAttribute('href'))
       .startsWith('https://creativecommons.org/'));
      if(viewport.name==='standard'){
       await frame.screenshot({path:'mobile-screenshots/quiz-'+code+'-'+round+'.png',animations:'disabled'});
      }
     }else if(curated){
      assert.equal(await quiz.locator('#todayQuizPhotoNotice').isVisible(),true,
       'quiz explains when vetted answer photograph is not yet ready');
     }
     const next=quiz.locator('#todayQuizNext');
     if(round<totalRounds-1){
      assert.equal((await next.textContent()).trim(),'次の問題へ →');
      await next.click();
      assert.equal(await quiz.isVisible(),true,'quiz moves directly to the next question');
      assert.equal(await page.evaluate(()=>worldPassportActive?.step),round+1);
      assert.equal(await quiz.locator('#todayQuizResult').isHidden(),true);
     }else{
      assert.equal((await next.textContent()).trim(),'閉じる');
      await next.click();
      assert.equal(await quiz.isHidden(),true,'last answer returns to country map');
       assert.equal(await page.locator('body').evaluate(el=>el.classList.contains('quiz-detail-mode')),false);
       assert.equal(await gallery.first().isVisible(),true,'closing quiz restores home gallery');
     }
    }
   }
   assert.equal(await today.locator('#todayPassportCount').count(),0,
    'no completion counter is reintroduced');
   if(viewport.name==='standard'){
    await today.screenshot({path:'mobile-screenshots/map-without-stamp-book.png',animations:'disabled'});
   }
   await gallery.first().click();
   const travelButton=page.locator('#spotlight .travel-open');
   assert.equal(await travelButton.getAttribute('aria-expanded'),'false',
    'today article travel is optional and initially closed');
   await travelButton.click();
   await page.waitForFunction(()=>{
    const card=document.querySelector('#spotlight .travel-card');
    if(!card)return false;
    const img=card.querySelector('.travel-photo');
    return img?img.complete&&img.naturalWidth>0:!!card.querySelector('.travel-empty');
   },null,{timeout:30000});
   const postcard=page.locator('#spotlight .travel-card');
   assert.equal(await postcard.count(),1,'optional detailed journey opens');
   let photoSource='not-yet-curated';
   if(await postcard.locator('.travel-photo').count()){
    assert.ok((await postcard.locator('.travel-trust').textContent()).includes('ニュース現場の記録ではなく'),
     'tourist photography is labeled separately from actual reportage');
    photoSource=await postcard.locator('.travel-photo').getAttribute('src');
    assert.ok(photoSource?.startsWith('./assets/travel/'),'travel photo is locally bundled');
    const detail=postcard.locator('.travel-story');
    assert.equal(await detail.count(),1,'a complete destination has an extended travel essay');
    assert.equal(await detail.locator('p').count(),2,
     'every curated destination has two distinct explanatory paragraphs');
    const paragraphs=await detail.locator('p').allTextContents();
    assert.ok(paragraphs.every(text=>text.length>=70),
     'landmark background and visitor viewpoint must be detailed, not one-line filler');
    assert.ok((await detail.locator('h5').textContent()).includes('景色の向こう側へ'));
    const firstCountryCode=await pins.first().getAttribute('data-country-code');
    if(countryCoverAssets.has(firstCountryCode)){
     assert.notEqual(photoSource,countryCoverAssets.get(firstCountryCode),
      'country introduction and travel story must use DIFFERENT real photographs');
    }
   }else{
    // Newly sourced incidents may be from countries without licensed,
    // locally bundled tourist photos (e.g. Italy or Germany). No unrelated
    // foreign-country photo or unverified image may be substituted.
    assert.equal(await postcard.locator('.travel-empty').count(),1,
     'uncurated country has an explicit and truthful no-photo state');
    assert.ok((await postcard.locator('.travel-empty').textContent()).includes('別の国の景色では代用しません'),
     'the reader never fabricates a foreign destination postcard');
    assert.ok((await postcard.locator('.travel-trust').textContent()).includes('写真はまだ準備中'),
     'the missing photo is distinguished from real news evidence');
   }
   // Previously the visual smoke tested only the lead story's postcard.
   // Cover EVERY published article, especially when several reports share a country.
   for(let storyIndex=1;storyIndex<editorialCover.storyCount;storyIndex++){
    await page.locator('#readerBack').click();
    await gallery.nth(storyIndex).click();
    const expected=await page.evaluate(index=>{
     const story=edition.stories[index];
     return {id:story.id,code:countryKeys(story.country)[0],
      country:countryLabel(story.country),title:story.title};
    },storyIndex);
    assert.equal(await page.locator('#spotlightTitle').textContent(),expected.title,
     'postcard must belong to the correct published article: '+expected.id);
    const trigger=page.locator('#spotlight .travel-open');
    assert.equal(await trigger.count(),1,
     'every article must offer its optional postcard: '+expected.id);
    assert.equal(await trigger.getAttribute('aria-expanded'),'false');
    await trigger.click();
    await page.waitForFunction(()=>{
     const card=document.querySelector('#spotlight .travel-card');
     if(!card)return false;
     const img=card.querySelector('.travel-photo');
     return img?img.complete&&img.naturalWidth>0:!!card.querySelector('.travel-empty');
    },null,{timeout:30000});
    const card=page.locator('#spotlight .travel-card');
    assert.equal(await card.count(),1,
     'each opened article shows precisely one postcard: '+expected.id);
    assert.ok((await card.locator('.travel-context-story').textContent()).includes(expected.country),
     'article-country label must remain attached to its own article: '+expected.id);
    const photo=card.locator('.travel-photo');
    assert.equal(await photo.count(),1,
     'a fully curated country must not silently lose its tourist photo: '+expected.id);
    const src=await photo.getAttribute('src');
    assert.ok(src?.startsWith('./assets/travel/'),
     'postcard photograph must be locally packaged: '+expected.id);
    const matches=await page.evaluate(async asset=>{
     const entries=await loadTravelStops();
     return Object.values(entries).filter(s=>s.photoAsset===asset)
      .map(s=>({country:s.country,page:s.photoPage,license:s.licenseUrl,author:s.author}));
    },src.slice(2));
    assert.ok(matches.length>0&&matches.every(s=>
     s.country===expected.country&&
     s.page.startsWith('https://commons.wikimedia.org/wiki/File:')&&
     s.license.startsWith('https://creativecommons.org/')&&s.author),
     'photo provenance MUST belong to actual news country: '+expected.id);
    const cover=countryCoverAssets.get(expected.code);
    if(cover)assert.notEqual(src,cover,
     'the country portrait and story postcard must have different photos: '+expected.id);
    const essay=card.locator('.travel-story');
    assert.equal(await essay.locator('p').count(),2,
     'every article postcard needs both sourced travel paragraphs: '+expected.id);
    assert.ok((await essay.locator('p').allTextContents()).every(p=>p.length>=70),
     'no one-line postcard copy is accepted: '+expected.id);
    assert.ok((await card.locator('.travel-links a').allTextContents())
     .some(line=>line.includes('歴史・文化の資料')),
     'every postcard needs a separate historical/cultural source: '+expected.id);
   }
   // Validate original news layout before using the optional atlas.
   // Country introduction scrolls should not change initial hero geometry.
   await page.locator('#readerBack').click();
   assert.equal(await page.locator('#todayMapSection').isVisible(),true);
   // Browse source-approved country stories even when a country has no story
   // in the latest issue. This is deliberately NOT an extra news-map pin.
   await page.waitForFunction(()=>{
    const list=document.querySelector('#approvedAtlasList');
    return list?.querySelectorAll('.approved-atlas-country').length>=12;
   },null,{timeout:10000});
   const countryCount=await page.locator('#approvedAtlasList .approved-atlas-country').count();
   assert.ok(countryCount>=12,'all twelve approved country guides remain discoverable');
   const issuePins=await page.locator('#todayMapPins .today-map-pin').count();
   const reportedCountryCount=await page.evaluate(()=>currentIssueCountries().length);
   assert.ok(issuePins<=reportedCountryCount,
     'standalone country browse must not create extra published-issue pins');
   await page.locator('#approvedAtlasChooser summary').click();
   const chosen=viewport.width===320?'AG':viewport.width===375?'DE':'FR';
   await page.locator('#approvedAtlasList .approved-atlas-country[data-country-code="'+chosen+'"]').click();
   assert.equal(await page.locator('#todayMapIntro').isVisible(),true);
   assert.equal(await page.locator('#todayMapIntroRead').textContent(),
    'この国の写真付き3択クイズに挑戦','standalone destinations have no fabricated news button');
   await page.locator('#todayMapIntroTravel .travel-story p').first().waitFor({state:'visible',timeout:12000});
   assert.equal(await page.locator('#todayMapIntroTravel .travel-story p').count(),2,
    'the standalone country trip has two real historical paragraphs');
   const trip=await page.locator('#todayMapIntroTravel').textContent();
   assert.ok(trip.includes('歴史・文化の資料：')&&trip.includes('写真：'),
    'travel experience provides its historical source and exact photo credit');
   await page.locator('#todayMapIntroRead').click();
   assert.equal(await page.locator('#todayCountryQuiz').isVisible(),true);
   assert.ok((await page.locator('#todayQuizQuestion').textContent()).length>=7);
   await page.locator('#todayQuizClose').click();
   assert.equal(await page.locator('#todayCountryQuiz').isHidden(),true);
   await explore.locator('summary').first().click();
   assert.equal(await today.isHidden(),true,'world exploration can be closed again');
   assert.equal(await gallery.first().isVisible(),true,'closing exploration preserves news');
   await explore.locator('summary').first().click();
   await today.waitFor({state:'visible'});
   assert.equal(await pins.count(),uniqueMappedCountries,'reopening preserves exact issue countries');
   assert.equal(await page.locator('#todayCountryQuiz').isHidden(),true,'closed quiz does not reappear');
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
   assert.ok(overflow<2,'no horizontal overflow: '+overflow+'px');
   assert.deepEqual(errors,[],'no JavaScript uncaught errors');
   process.stdout.write('Mobile smoke OK: '+viewport.width+'px; '+photoSource+'\n');
  }finally{await context.close();}
 }
}finally{await browser.close();}
