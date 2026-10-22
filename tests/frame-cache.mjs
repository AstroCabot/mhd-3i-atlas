// Exercise real packaged batches, corruption recovery, reuse and cancellation.
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const base=process.env.TEST_URL||'http://127.0.0.1:8080';
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
try {
  const page=await browser.newPage({reducedMotion:'reduce'});
  const errors=[],requests=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{if(request.url().includes('/frame-packs/'))requests.push(request.url());});
  await page.goto(base+'/assets/favicon.svg');
  const result=await page.evaluate(async()=>{
    const {createFrameCache}=await import('/frame-cache.js');
    const manifest=await (await fetch('/data/animation-playback.json')).json();
    const original=await (await fetch('/data/animation-v2.json')).json();
    window.manifest=manifest;
    const rows=manifest.models.argon.frameSequence.fields.flux;
    window.cache=createFrameCache(manifest,()=>{});
    await window.cache.prefetch([rows[0].url]);
    const actual=await Promise.all(rows.slice(0,8).map(async row=>{
      const bytes=await window.cache.source(row.url).arrayBuffer();
      return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),value=>value.toString(16).padStart(2,'0')).join('');
    }));
    window.cache.destroy();
    window.cache=createFrameCache(manifest,()=>{});
    await window.cache.prefetch([rows[0].url]);
    return {actual,expected:original.models.argon.frameSequence.fields.flux.slice(0,8).map(row=>row.sha256),reused:window.cache.has(rows[0].url)};
  });
  assert.deepEqual(result.actual,result.expected);assert.ok(result.reused);assert.equal(requests.length,1);
  console.log('PASS: every extracted frame matches its original checksum; completed batches survive player replacement');
  await page.route('**/frame-packs/codex-flux-000-*.bin',async route=>{
    const response=await route.fetch(),body=await response.body();
    body[0]^=255;await route.fulfill({response,body});
  });
  const corrupt=await page.evaluate(async()=>{
    const row=window.manifest.models.codex.frameSequence.fields.flux[0];
    await window.cache.prefetch([row.url]);
    return {available:window.cache.has(row.url),failed:window.cache.failed(row.url)};
  });
  assert.deepEqual(corrupt,{available:false,failed:true});
  console.log('PASS: a corrupted batch is rejected before any frame can be displayed');
  let held;
  await page.route('**/frame-packs/claude-flux-000-*.bin',route=>{held=route;});
  const requested=page.waitForRequest('**/frame-packs/claude-flux-000-*.bin');
  await page.evaluate(()=>{const row=window.manifest.models.claude.frameSequence.fields.flux[0];window.waiting=window.cache.prefetch([row.url]);});
  await requested;
  const started=Date.now();
  await page.evaluate(async()=>{window.cache.destroy();await window.waiting;});
  assert.ok(Date.now()-started<1000);
  if(held)await held.abort();
  console.log('PASS: disposing a player immediately releases an outstanding batch wait');
  await page.close();

  const fallback=await browser.newPage({reducedMotion:'reduce'});
  fallback.on('pageerror',error=>errors.push(error.message));
  await fallback.route('**/frame-packs/*.bin',route=>route.fulfill({status:503,body:'Unavailable'}));
  await fallback.goto(base+'/#solar-wind',{waitUntil:'domcontentloaded'});
  await fallback.waitForFunction(()=>window.__HELIOS__?.player?.getState().status==='paused',null,{polling:50});
  const before=await fallback.evaluate(()=>window.__HELIOS__.player.getState().progress);
  await fallback.evaluate(()=>window.__HELIOS__.player.play());
  await fallback.waitForFunction(before=>window.__HELIOS__.player.getState().progress>before+.015,before,{polling:50});
  await fallback.evaluate(()=>window.__HELIOS__.player.pause());
  assert.equal(await fallback.locator('[data-image-ready=true]').count(),4);
  assert.deepEqual(errors,[]);
  console.log('PASS: unavailable batches fall back to the original full-resolution images and continue playing');
}finally{await browser.close();}
