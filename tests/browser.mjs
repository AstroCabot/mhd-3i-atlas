import { chromium, firefox } from 'playwright';
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
const base=process.env.TEST_URL||'http://127.0.0.1:8080';
const engine=process.env.TEST_BROWSER==='firefox'?firefox:chromium;
const browser=await engine.launch({...(engine===chromium&&process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),headless:true,...(engine===chromium?{args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']}:{})});
const errors=[];const results=[];
async function takeShot(page,path){if(process.env.CAPTURE_SCREENSHOTS!=='1')return;await page.screenshot({path,fullPage:true,animations:'disabled',timeout:10000});}mkdirSync('tests/screenshots',{recursive:true});
try {
 const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
 page.on('pageerror',e=>{console.log('Browser error:',e.message);errors.push(e.message)});
 page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});
 await page.goto(base,{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>!!window.__HELIOS__,{},{timeout:30000,polling:100});
 await page.waitForFunction(()=>window.__HELIOS__.player?.getState().status==='paused',{},{timeout:15000,polling:100});
 await page.evaluate(()=>window.testFieldImage=document.querySelector('[data-solar-image]'));
 console.log('App ready');assert.match(await page.locator('h1').innerText(),/Solar-wind reconstructions at 3I\/ATLAS/);
 assert.equal(await page.locator('[data-model-toggle][aria-pressed=true]').count(),3);
 assert.deepEqual(await page.locator('#common-results thead th').allTextContents(),['Quantity / convention',' Argon',' Codex',' Claude']);
 assert.deepEqual(await page.locator('#common-results tbody tr').last().locator('td').allTextContents(),['Absent','Absent','DONKI cones']);
 assert.equal(await page.locator('.record-entrypoints a').count(),3);
 await page.locator('[data-model-toggle=codex]').evaluate(el=>el.click());
 assert.equal(await page.locator('[data-model-toggle=codex]').getAttribute('aria-pressed'),'false');
 await page.locator('[data-model-toggle=codex]').evaluate(el=>el.click());
 assert.equal(await page.evaluate(()=>window.testFieldImage===document.querySelector('[data-solar-image]')),true,'Model visibility controls must preserve field image nodes');
 await page.waitForFunction(()=>document.querySelector('[data-image-ready=true]')&&window.__HELIOS__.player?.getState().status==='paused',null,{polling:100});
 // A theme change must recolour the current view without remounting playback.
 const darkAxis=await page.evaluate(()=>window.__HELIOS__.state.charts[0].chart.getOption().xAxis[0].axisLabel.color);
 await page.locator('#theme-toggle').focus();await page.keyboard.press('Space');
 assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
 assert.equal(await page.locator('#theme-toggle').getAttribute('aria-checked'),'true');
 assert.equal(await page.evaluate(()=>localStorage.getItem('3i-atlas-theme')),'light');
 assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),'rgb(234, 215, 177)');
 assert.equal(await page.evaluate(()=>window.testFieldImage===document.querySelector('[data-solar-image]')),true,'Theme switch must preserve the field image');
 assert.notEqual(await page.evaluate(()=>window.__HELIOS__.state.charts[0].chart.getOption().xAxis[0].axisLabel.color),darkAxis);
 assert.equal(await page.evaluate(()=>window.__HELIOS__.state.charts[0].chart.getOption().series[0].itemStyle.color),await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--argon').trim()));
 await takeShot(page,'tests/screenshots/overview-light-desktop.png');
 await page.reload({waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.__HELIOS__?.player?.getState().status==='paused',null,{polling:100});
 assert.equal(await page.locator('html').getAttribute('data-theme'),'light','Light mode must survive a page reload');
 assert.equal(await page.locator('meta[name=theme-color]').getAttribute('content'),'#ead7b1');
 await page.locator('#theme-toggle').evaluate(el=>el.click());
 assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
 results.push('keyboard theme switch, persistent preference and uninterrupted field view');
 await takeShot(page,'tests/screenshots/overview-desktop.png');results.push('overview and model visibility');console.log('Checked overview');
 for(const route of ['solar-wind','verification','observations','xray','methods','resources','transcripts']){
  await page.locator(`[data-nav=${route}]`).evaluate(el=>el.click());
  await page.waitForFunction(r=>window.__HELIOS__.state.route===r,route,{polling:100});
  assert.equal(await page.locator('h1').count(),1);assert.equal(await page.locator('[data-math-error]').count(),0);
  if(route==='solar-wind'){
   await page.waitForFunction(()=>document.querySelectorAll('[data-image-ready=true]').length===3&&window.__HELIOS__.player?.getState().status==='paused',null,{polling:100});
   await page.locator('[data-frame]').evaluate(el=>{el.value='340';el.dispatchEvent(new Event('input',{bubbles:true}));});
   await page.waitForFunction(()=>window.__HELIOS__.player.getState().status==='paused'&&Math.abs(window.__HELIOS__.state.progress-.34)<.0001,null,{polling:100});
   assert.equal(await page.locator('[data-solar-image]').count(),6);assert.equal(await page.locator('video').count(),0);
   await page.locator('[data-play]').evaluate(el=>el.click());
   await page.waitForFunction(()=>window.__HELIOS__.state.progress>.35,null,{polling:100});
   await page.locator('[data-play]').evaluate(el=>el.click());
   assert.equal(await page.evaluate(()=>window.__HELIOS__.state.playing),false);
   await page.locator('[data-field=fluxR2]').evaluate(el=>el.click());
   await page.waitForFunction(()=>window.__HELIOS__.player?.getState().field==='contrast'&&window.__HELIOS__.player?.getState().status==='paused',null,{polling:100});
   assert.equal(await page.evaluate(()=>window.__HELIOS__.state.field),'fluxR2');assert.equal(await page.locator('a[download][href$=\".mp4\"]').count(),6);
   await page.locator('#design-band').evaluate(el=>el.click());assert.equal(await page.evaluate(()=>window.__HELIOS__.state.band),true);
   await page.waitForFunction(()=>document.querySelectorAll('[data-image-ready=true]').length===3&&window.__HELIOS__.player?.getState().status==='paused',null,{polling:100});
  }
  if(route==='verification'){
   await page.locator('[data-bench=linear-waves]').evaluate(el=>el.click());
   assert.match(await page.locator('.panel-title').first().innerText(),/linear MHD waves/i);
   await page.locator('[data-bench=brio-wu]').evaluate(el=>el.click());
  }
  if(route==='observations'){
   const selectors=page.locator('[data-craft]');
   if(await selectors.count()>1)await selectors.nth(1).evaluate(el=>el.click());
   assert.equal(await page.locator('#craft-speed svg').count(),1);
  }
  if(route==='methods'){
   for(const model of ['argon','codex','claude']){
    await page.locator(`[data-method=${model}]`).evaluate(el=>el.click());
    assert.equal(await page.locator('[data-math-error]').count(),0);
    assert.ok(await page.locator('.katex').count()>=8);
   }
  }
  if(route==='transcripts'){
   await page.waitForSelector('.message');
   await page.locator('#record-search').fill('solar');
   await page.locator('#record-search-form button').evaluate(el=>el.click());
   await page.waitForSelector('[data-jump]');
   await page.locator('[data-jump]').first().evaluate(el=>el.click());
   await page.waitForSelector('.message');
   await page.locator('[data-record-mode=notes]').evaluate(el=>el.click());
   await page.waitForSelector('.note-card');
   await page.locator('#record-role').selectOption('directed');
   await page.waitForFunction(()=>document.querySelectorAll('.note-card').length>0,null,{polling:100});
   assert.ok(await page.locator('.note-card').count()>0);
   await page.locator('[data-record-view=exchanges]').evaluate(el=>el.click());
   await page.waitForFunction(()=>window.__HELIOS__.state.recordMode==='notes'&&window.__HELIOS__.state.role==='directed',null,{polling:100});
   await page.waitForSelector('.note-card');
   assert.equal(await page.locator('.note-card').count(),14);
   assert.match(await page.locator('#note-claude_20261016T2244Z_reply_codex_argon .note-meta').innerText(),/CLAUDE/);
   await page.locator('.record-guide a').evaluate(el=>el.click());
   await page.waitForFunction(()=>window.__HELIOS__.state.recordThread==='cme',null,{polling:100});
   await page.waitForSelector('.note-card');
   assert.equal(await page.locator('.note-card').count(),4);
   assert.match(await page.locator('.record-guide').innerText(),/provisional claims/);
   await page.goto(base+'/#transcripts?mode=sessions&agent=claude',{waitUntil:'domcontentloaded'});
   await page.waitForFunction(()=>window.__HELIOS__.state.recordAgent==='claude'&&window.__HELIOS__.state.recordMode==='sessions',null,{polling:100});
   await page.waitForSelector('.message');
   assert.equal(await page.locator('#record-agent').inputValue(),'claude');
   results.push('agent exchanges, corrected note attribution and direct conversation links');

  }
  if(route==='resources'){assert.equal(await page.locator('.source-manifest [role=region][tabindex="0"]').count(),1);assert.ok(await page.locator('.source-manifest tr').count()>100);}
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,`${route} desktop overflow`);
  const beforeTheme=await page.evaluate(()=>{
   const charts=window.__HELIOS__.state.charts;
   if(window.__HELIOS__.state.route==='solar-wind')charts[0].chart.dispatchAction({type:'dataZoom',start:20,end:70});
   window.themePlayer=window.__HELIOS__.player;window.themeImages=[...document.querySelectorAll('[data-solar-image]')];
   return charts.map(({chart})=>{const o=chart.getOption();return {data:o.series.map(s=>s.data.map(p=>p?.value??p)),zoom:o.dataZoom?.map(z=>({start:z.start,end:z.end,startValue:z.startValue,endValue:z.endValue})),map:o.visualMap?.map(v=>v.inRange.color)};});
  });
  await page.locator('#theme-toggle').evaluate(el=>el.click());
  assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
  const afterTheme=await page.evaluate(()=>window.__HELIOS__.state.charts.map(({chart})=>{const o=chart.getOption();return {data:o.series.map(s=>s.data.map(p=>p?.value??p)),zoom:o.dataZoom?.map(z=>({start:z.start,end:z.end,startValue:z.startValue,endValue:z.endValue})),map:o.visualMap?.map(v=>v.inRange.color)};}));
  assert.deepEqual(afterTheme,beforeTheme,`${route} theme change must preserve data, zoom and scientific colour maps`);
  assert.equal(await page.evaluate(()=>window.themePlayer===window.__HELIOS__.player&&window.themeImages.every((img,i)=>img===document.querySelectorAll('[data-solar-image]')[i])),true);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,`${route} light mode overflow`);
  await takeShot(page,`tests/screenshots/${route}-light-desktop.png`);
  await page.locator('#theme-toggle').evaluate(el=>el.click());
  await takeShot(page,`tests/screenshots/${route}-desktop.png`);results.push(route);console.log('Checked',route);
 }
 const download=page.waitForEvent('download');await page.locator('[data-export]').first().evaluate(el=>el.click());assert.ok((await download).suggestedFilename().endsWith('.json'));results.push('dataset export');
 await page.setViewportSize({width:390,height:844});
 await page.goto(base+'/#overview',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>!!window.__HELIOS__,null,{polling:100});
 await page.waitForFunction(()=>window.__HELIOS__.player?.getState().status==='paused',null,{polling:100});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,'Overview must not overflow horizontally');
 await page.locator('#theme-toggle').evaluate(el=>el.click());
 assert.equal(await page.locator('#theme-toggle').isVisible(),true);
 await takeShot(page,'tests/screenshots/overview-light-mobile.png');
 await page.locator('#theme-toggle').evaluate(el=>el.click());
 await takeShot(page,'tests/screenshots/overview-mobile.png');
 await page.waitForFunction(()=>window.__HELIOS__.state.route==='overview',null,{polling:100});await page.locator('#menu').evaluate(el=>el.click());assert.equal(await page.locator('#menu').getAttribute('aria-expanded'),'true');
 await page.locator('[data-nav=methods]').evaluate(el=>el.click());await page.waitForFunction(()=>window.__HELIOS__.state.route==='methods',null,{polling:100});assert.equal(await page.locator('#menu').getAttribute('aria-expanded'),'false');
 await page.locator('[data-method=codex]').evaluate(el=>el.click());assert.equal(await page.locator('[data-math-error]').count(),0);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,'Methods must not overflow horizontally');
 await takeShot(page,'tests/screenshots/methods-mobile.png');results.push('mobile navigation, layout and equations');
 assert.deepEqual(errors,[],'Browser or HTTP failures');
 writeFileSync('tests/browser-results.json',JSON.stringify({passed:true,checks:results,errors,date:new Date().toISOString()},null,2));
 console.log(`PASS: ${results.length} browser checks; no JavaScript or HTTP failures.`);
} finally {await browser.close();}
