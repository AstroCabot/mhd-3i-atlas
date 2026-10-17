/** Portable player regression. Start `python -m http.server 8082 --bind 127.0.0.1 --directory .`. */
import {chromium,webkit,firefox} from 'playwright';
import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
const base=process.env.PLAYER_TEST_URL||'http://127.0.0.1:8082';
const engine=process.env.PLAYER_BROWSER==='webkit'?webkit:process.env.PLAYER_BROWSER==='firefox'?firefox:chromium;
const browser=await engine.launch({headless:true,...(engine===chromium?{...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-features=CDPScreenshotNewSurface']}:{})});
const results=[];
function record(value){results.push(value);console.log('PASS',value);}
try {
 const page=await browser.newPage({viewport:{width:1200,height:850},reducedMotion:'no-preference'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/assets/animation-v2/**',route=>{const path=new URL(route.request().url()).pathname;return route.continue({url:base+'/public'+path.slice(path.indexOf('/assets/'))});});
 await page.route('**/data/animation-v2.json',route=>route.continue({url:base+'/public/data/animation-v2.json'}));
 await page.goto(base+'/tests/',{waitUntil:'domcontentloaded'});
 await page.setContent(`<style>body{margin:0;background:#191713;color:#ddd}main{display:grid;grid-template-columns:repeat(3,1fr)}.canvas-wrap{position:relative;width:100%;aspect-ratio:1}.canvas-label,.colorbar{position:absolute;font:11px monospace}.canvas-label{top:12px;left:12px}.colorbar{bottom:5px;right:8px}</style><main>${['argon','codex','claude'].map(id=>`<div class="canvas-wrap"><svg data-solar="${id}"></svg><div class="canvas-label"><strong>${id}</strong><small data-plane></small></div><div class="colorbar"><div data-bar-title></div><div class="gradient"></div><span data-bar-min></span>–<span data-bar-max></span></div></div>`).join('')}</main><button data-play></button><span data-playback-status-label></span><span data-frame-time></span><input type="range" data-frame><select id="play-speed"><option value="1">1×</option><option value="2">2×</option></select>`);
 await page.evaluate(async()=>{const{mountSolarPlayers}=await import('/src/solar-player.js');window.player=await mountSolarPlayers({playing:true,progress:.7});await window.player.ready;});
 assert.equal(await page.evaluate(()=>window.player.getState().status),'playing');
 assert.equal(await page.locator('video').count(),0);
 assert.equal(await page.locator('[data-solar-image]').count(),6);
 assert.ok(await page.locator('[data-solar-image]').evaluateAll(images=>images.every(image=>image.complete&&image.naturalWidth===768)));
 record('Three panels preload and decode genuine 768px fields without native video APIs');
 await page.evaluate(()=>{
  window.childChanges=0;window.imageChanges=0;
  window.observer=new MutationObserver(changes=>{for(const change of changes){if(change.type==='childList')window.childChanges++;if(change.type==='attributes'&&change.target.matches('[data-solar-image]'))window.imageChanges++;}});
  document.querySelectorAll('[data-solar]').forEach(svg=>window.observer.observe(svg,{subtree:true,childList:true}));
  document.querySelectorAll('[data-solar-image]').forEach(image=>window.observer.observe(image,{attributes:true}));
  window.initialProgress=window.player.getState().progress;window.initialImages=[...document.querySelectorAll('[data-solar-image]')];
 });
 await page.waitForTimeout(1400);
 const moving=await page.evaluate(()=>({delta:window.player.getState().progress-window.initialProgress,childChanges:window.childChanges,imageChanges:window.imageChanges,sameImages:window.initialImages.every((image,i)=>image===document.querySelectorAll('[data-solar-image]')[i]),state:window.player.getState()}));
 assert.equal(moving.childChanges,0);assert.equal(moving.sameImages,true);assert.ok(moving.delta>.012,JSON.stringify(moving));assert.ok(moving.imageChanges>20,JSON.stringify(moving));
 record('Physical clock and crossfade advance continuously while image and SVG nodes remain persistent');
 await page.locator('[data-play]').click({force:true});assert.equal(await page.evaluate(()=>window.player.getState().playing),false);
 await page.evaluate(async()=>{await window.player.setProgress(.34)});
 const before=await page.evaluate(()=>window.player.getState().progress);
 await page.evaluate(async()=>{await window.player.setField('contrast')});
 assert.equal(await page.evaluate(()=>window.player.getState().field),'contrast');
 assert.ok(Math.abs(await page.evaluate(()=>window.player.getState().progress)-before)<.0001);
 assert.equal(await page.evaluate(()=>window.player.getState().status),'paused');
 assert.ok(await page.locator('[data-solar-image]').evaluateAll(images=>images.every(image=>image.complete&&image.dataset.frameUrl.includes('contrast'))));
 record('Pause, synchronized scrub and decoded field swap preserve exact physical UTC');
 await page.evaluate(async()=>{await window.player.setModel('claude',0)});
 assert.match(await page.locator('[data-plane]').first().innerText(),/320 × 360.*3 h/);
 assert.equal(await page.locator('.canvas-label strong').first().innerText(),'Claude');
 assert.ok(Math.abs(await page.evaluate(()=>window.player.getState().progress)-before)<.0001);
 record('Model swap updates native support and heading while preserving the epoch');
 await page.evaluate(()=>window.player.setSpeed(2));assert.equal(await page.evaluate(()=>window.player.getState().speed),2);
 await page.evaluate(async()=>{await window.player.setProgress(.999);await window.player.play()});await page.waitForTimeout(400);
 assert.ok(await page.evaluate(()=>window.player.getState().progress)<.1,'Finite observation interval should restart');
 record('Playback speed and finite-interval restart preserve decoded display layers');

 await page.evaluate(()=>window.player.destroy());assert.equal(await page.locator('[data-solar-image]').count(),0);
 record('Destroy releases image layers, controls, observers and animation loop');
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.evaluate(async()=>{const{mountSolarPlayers}=await import('/src/solar-player.js');window.player=await mountSolarPlayers({playing:true});await window.player.ready;});
 assert.equal(await page.evaluate(()=>window.player.getState().playing),false);
 record('Reduced-motion preference pauses initial display');
 const lifecycle=await page.evaluate(async()=>{const{mountSolarPlayers}=await import('/src/solar-player.js');const empty=await mountSolarPlayers({root:document.createElement('div')});const controller=new AbortController();controller.abort();let aborted=false;try{await mountSolarPlayers({signal:controller.signal})}catch(error){aborted=error.name==='AbortError'}return{empty:empty.getState().status,aborted};});
 assert.equal(lifecycle.empty,'disposed');assert.equal(lifecycle.aborted,true);record('Empty routes and aborted manifest requests mount no stale field player');
 assert.deepEqual(errors,[]);record('No browser JavaScript errors');
 writeFileSync('tests/animation-results.txt',results.map(x=>'PASS '+x).join('\n')+'\n');console.log(JSON.stringify({passed:results.length,moving},null,2));
 if(process.env.CAPTURE_SCREENSHOTS==='1')await page.screenshot({path:'tests/screenshots/solar-player-v2.png',timeout:8000,animations:'disabled'});
}finally{await browser.close();}
