/* Mobile-browser smoke test for the public nightly reader.
   Chromium's device emulation is useful but is NOT an iPhone Safari test. */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const url='https://ogasawaratouei1998-lgtm.github.io/yoru9-world-letter/';
await fs.mkdir('mobile-screenshots',{recursive:true});
const browser=await chromium.launch({headless:true});
try{
 for(const viewport of [{width:375,height:667,name:'small'},{width:393,height:852,name:'standard'}]){
  const context=await browser.newContext({
   viewport:{width:viewport.width,height:viewport.height},
   deviceScaleFactor:2,isMobile:true,hasTouch:true,
   locale:'ja-JP',timezoneId:'Asia/Tokyo'
  });
  try{
   const page=await context.newPage();
   const errors=[];
   page.on('pageerror',e=>errors.push(String(e)));
   const res=await page.goto(url,{waitUntil:'domcontentloaded',timeout:35000});
   assert.equal(res?.status(),200,'reader page must be reachable');
   await page.waitForFunction(()=>{
    const el=document.querySelector('#spotlightTitle');
    return el&&el.textContent&&!el.textContent.includes('準備中');
   },null,{timeout:30000});
   const article=page.locator('#monthCards .month-story').first();
   await article.waitFor({state:'attached',timeout:30000});
   const shelf=page.locator('#monthRetrospective > details');
   if((await shelf.getAttribute('open'))===null)await shelf.locator('summary').first().click();
   const details=article.locator('details').first();
   await details.locator('summary').first().click();
   await page.waitForFunction(()=>{
    const img=document.querySelector('#monthCards .month-story .travel-photo');
    return !!img&&img.complete&&img.naturalWidth>0;
   },null,{timeout:30000});
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
