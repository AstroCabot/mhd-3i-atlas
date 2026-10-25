// Playback visibility, idle work and provenance labels on failed transitions.
import {chromium,firefox} from 'playwright';
import assert from 'node:assert/strict';
const base=process.env.TEST_URL||'http://127.0.0.1:8080';
const engine=process.env.TEST_BROWSER==='firefox'?firefox:chromium;
const browser=await engine.launch({headless:true,...(engine===chromium?{args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']}:{})});
try {
 const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});
 await page.addInitScript(()=>{
  const schedule=window.setInterval.bind(window),cancel=window.clearInterval.bind(window);
  window.__playbackClocks=new Set();
  window.setInterval=(callback,delay,...args)=>{const id=schedule(callback,delay,...args);if(delay===33)window.__playbackClocks.add(id);return id;};
  window.clearInterval=id=>{window.__playbackClocks.delete(id);cancel(id);};
 });
 const errors=[],requests=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('request',request=>{if(request.url().includes('/frame-packs/'))requests.push(request.url());});
 await page.goto(base+'/#solar-wind',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.__HELIOS__?.player?.getState().status==='paused',null,{polling:50});
 assert.equal(await page.evaluate(()=>window.__playbackClocks.size),0,'A paused player must not keep a 30Hz fallback timer running');
 await page.evaluate(async()=>{await window.__HELIOS__.player.setProgress(.4);await window.__HELIOS__.player.play();});
 await page.waitForFunction(()=>window.__HELIOS__.player.getState().progress>.405,null,{polling:50});
 // Remote Chromium can defer compositor-generated scroll notifications. Emit
 // the notification after programmatic scrolling, as real scrolling would.
 const scrollTo=selector=>page.evaluate(selector=>{document.querySelector(selector).scrollIntoView();document.dispatchEvent(new Event('scroll'));},selector);
 await scrollTo('#comet-speed');
 await page.waitForFunction(()=>window.__HELIOS__.player.getState().status==='suspended',null,{polling:50});
 const stopped=await page.evaluate(()=>window.__HELIOS__.player.getState());
 const count=requests.length;
 await page.waitForTimeout(900);
 const sleeping=await page.evaluate(()=>window.__HELIOS__.player.getState());
 assert.equal(sleeping.progress,stopped.progress);assert.equal(sleeping.requestedPlaying,true);assert.equal(sleeping.playing,false);assert.equal(requests.length,count);
 assert.equal(await page.evaluate(()=>window.__playbackClocks.size),0,'Offscreen fields must release the fallback clock');
 await scrollTo('.canvas-wrap');
 await page.waitForFunction(()=>window.__HELIOS__.player.getState().playing,null,{polling:50});
 const resumed=await page.evaluate(()=>window.__HELIOS__.player.getState());
 assert.ok(resumed.progress-stopped.progress<.012,'Returning to the fields must not jump over the offscreen interval');
 await page.waitForFunction(progress=>window.__HELIOS__.player.getState().progress>progress+.01,resumed.progress,{polling:50});
 await page.evaluate(()=>window.__HELIOS__.player.pause());
 await scrollTo('#comet-speed');
 await page.waitForTimeout(150);
 await scrollTo('.canvas-wrap');
 await page.waitForTimeout(150);
 assert.equal(await page.evaluate(()=>window.__HELIOS__.player.getState().requestedPlaying),false);
 assert.equal(await page.evaluate(()=>window.__HELIOS__.player.getState().playing),false);
 console.log('PASS: offscreen fields stop clock and lookahead, resume without skipping UTC, and retain a manual pause');

 const labels=await page.locator('[data-bar-title]').allTextContents();
 const rejectContrast=route=>route.fulfill({status:503,body:'Unavailable'});
 await page.route(/\/contrast-\d+\.webp(?:\?.*)?$/,rejectContrast);
 await page.evaluate(()=>window.__HELIOS__.player.setField('contrast'));
 assert.equal(await page.evaluate(()=>window.__HELIOS__.player.getState().status),'error');
 assert.deepEqual(await page.locator('[data-bar-title]').allTextContents(),labels);
 assert.ok(await page.locator('[data-solar-image]').evaluateAll(images=>images.filter(image=>image.style.visibility==='visible'&&Number(image.style.opacity)>0).every(image=>image.dataset.frameUrl.includes('/flux-'))));
 await page.unroute(/\/contrast-\d+\.webp(?:\?.*)?$/,rejectContrast);
 await page.evaluate(()=>window.__HELIOS__.player.play());
 await page.evaluate(()=>window.__HELIOS__.player.pause());
 assert.ok((await page.locator('[data-bar-title]').allTextContents()).every(label=>label.includes('r²')));
 console.log('PASS: failed field loads preserve the visible field’s units, and successful retry commits the new units');

 // A fresh document gives this failure case a cold compressed-frame cache.
 await page.goto(base+'/?model-label-case=1#overview',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.__HELIOS__?.player?.getState().status==='paused',null,{polling:50});
 await scrollTo('.canvas-wrap');
 await page.evaluate(()=>window.__HELIOS__.player.setProgress(.72));
 const originalHeading=await page.locator('.canvas-label strong').innerText();
 const rejectClaude=route=>route.fulfill({status:503,body:'Unavailable'});
 await page.route(/\/claude-native30m\/flux-\d+\.webp(?:\?.*)?$/,rejectClaude);
 await page.evaluate(()=>window.__HELIOS__.player.setModel('claude'));
 assert.equal(await page.evaluate(()=>window.__HELIOS__.player.getState().status),'error');
 assert.equal(await page.locator('.canvas-label strong').innerText(),originalHeading);
 await page.unroute(/\/claude-native30m\/flux-\d+\.webp(?:\?.*)?$/,rejectClaude);
 await page.evaluate(()=>window.__HELIOS__.player.play());
 await page.evaluate(()=>window.__HELIOS__.player.pause());
 assert.equal(await page.locator('.canvas-label strong').innerText(),'Claude');
 console.log('PASS: failed model loads preserve the visible model’s identity, and successful retry commits the selected model');

 await page.goto(base+'/?seek-label-case=1#solar-wind',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.__HELIOS__?.player?.getState().status==='paused',null,{polling:50});
 await page.evaluate(()=>window.__HELIOS__.player.setProgress(.64));
 const displayed=()=>page.evaluate(()=>({
  utc:document.querySelector('[data-frame-time]').textContent,
  markers:[...document.querySelectorAll('[data-solar] g[transform]')].map(node=>node.getAttribute('transform')),
  images:[...document.querySelectorAll('[data-solar-image]')].filter(node=>node.style.visibility==='visible'&&Number(node.style.opacity)>0).map(node=>({url:node.dataset.frameUrl,opacity:node.style.opacity})),
 }));
 const retained=await displayed();
 const rejectSeek=route=>route.fulfill({status:503,body:'Unavailable'});
 await page.route(/\/flux-(?:040|041)\.webp(?:\?.*)?$/,rejectSeek);
 await page.evaluate(()=>window.__HELIOS__.player.setProgress(.11));
 const failed=await page.evaluate(()=>window.__HELIOS__.player.getState());
 assert.equal(failed.status,'error');assert.equal(failed.progress,.11);assert.equal(failed.displayedProgress,.64);
 assert.equal(await page.locator('.shared-controls [data-frame]').inputValue(),'110','The scrubber must retain its responsive requested position');
 assert.deepEqual(await displayed(),retained,'Failed scrubs must retain the visible pixels, UTC and spacecraft/comet positions together');
 await page.unroute(/\/flux-(?:040|041)\.webp(?:\?.*)?$/,rejectSeek);
 await scrollTo('.canvas-wrap');
 await page.waitForTimeout(60);
 await page.evaluate(async()=>{const player=window.__HELIOS__.player;const retry=player.play();player.pause();await retry;});
 const retried=await page.evaluate(()=>window.__HELIOS__.player.getState());
 assert.equal(retried.displayedProgress,.11,'Retry must show the requested epoch, rather than the previously retained one');
 assert.notEqual((await displayed()).utc,retained.utc);
 assert.deepEqual(errors,[]);
 console.log('PASS: failed cold scrubs retain displayed UTC and positions while the requested slider stays responsive; retry shows the latest target');
}finally{await browser.close();}
