// Interaction regressions against the real application, including slow HTTP images.
import {chromium, firefox} from 'playwright';
import assert from 'node:assert/strict';
import {createServer, request} from 'node:http';
import {writeFileSync} from 'node:fs';

const upstream=process.env.TEST_URL||'http://127.0.0.1:8080';
const engine=process.env.TEST_BROWSER==='firefox'?firefox:chromium;
const browser=await engine.launch({headless:true,...(engine===chromium?{args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']}:{})});
const results=[],errors=[];
let cancelled=0,held=0,failOnce=false;
const proxy=createServer((req,res)=>{
  const frame=/\/(?:flux|contrast)-(\d+)\.webp/.exec(req.url);
  const delayed=frame&&[40,41].includes(Number(frame[1]));
  let remote,timer;
  res.on('close',()=>{clearTimeout(timer);remote?.destroy();if(delayed&&!res.writableEnded)cancelled++;});
  const forward=()=>{
    if(res.destroyed)return;
    if(failOnce&&frame&&[167,168].includes(Number(frame[1]))){failOnce=false;res.writeHead(503).end();return;}
    remote=request(upstream+req.url,{method:req.method},response=>{
      res.writeHead(response.statusCode,response.headers);response.pipe(res);
    });
    remote.on('error',()=>{if(!res.destroyed)res.writeHead(502).end();});remote.end();
  };
  if(delayed){held++;timer=setTimeout(forward,10000);}else forward();
});
await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
const base=`http://127.0.0.1:${proxy.address().port}`;
const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
page.on('pageerror',error=>errors.push(error.message));
const state=()=>page.evaluate(()=>window.__HELIOS__.player.getState());
const ready=()=>page.waitForFunction(()=>window.__HELIOS__?.player?.getState().status==='paused',null,{polling:30,timeout:15000});
const bounds=()=>page.locator('.shared-controls [data-frame]').boundingBox();
function record(message){results.push(message);console.log('PASS',message);}
try {
  await page.goto(base+'/#solar-wind',{waitUntil:'domcontentloaded'});await ready();
  if(process.env.INTERACTION_CASE!=='seeking') {
    for(const width of [1280,1024,768,390]) {
      await page.setViewportSize({width,height:900});await page.evaluate(()=>document.fonts.ready);
      const paused=await bounds();
      await page.evaluate(()=>window.__HELIOS__.player.play());const playing=await bounds();
      await page.evaluate(()=>window.__HELIOS__.player.pause());
      assert.ok(Math.abs(paused.x-playing.x)<.5&&Math.abs(paused.width-playing.width)<.5,`Slider moves with status at ${width}px: ${JSON.stringify({paused,playing})}`);
      assert.ok(await page.locator('.shared-controls').evaluate(root=>{
        const nodes=[...root.children].map(node=>node.getBoundingClientRect());
        return nodes.every((a,i)=>nodes.slice(i+1).every(b=>Math.min(a.right,b.right)-Math.max(a.left,b.left)<.5||Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)<.5));
      }),`Playback controls overlap at ${width}px`);
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Page overflow at ${width}px`);
    }
    record('Slider position and width stay fixed across playback states at four viewport widths');
  }
  await page.evaluate(()=>{window.__HELIOS__.player.play();window.pendingSeek=window.__HELIOS__.player.setProgress(.11);});
  await page.waitForFunction(()=>window.__HELIOS__.player.getState().status==='seeking',null,{polling:20});
  const started=Date.now();
  await page.waitForTimeout(100);assert.ok(held>0,'The test must hold genuine image requests');
  assert.ok(await page.locator('.canvas-wrap').evaluateAll(panels=>panels.every(panel=>[...panel.querySelectorAll('[data-solar-image]')].some(image=>image.complete&&image.naturalWidth===768&&image.style.visibility==='visible'&&Number(image.style.opacity)>0))),'A slow seek must preserve a decoded visible image in every panel');
  await page.evaluate(async()=>{
    const player=window.__HELIOS__.player;
    for(let i=0;i<24;i++){
      const input=document.querySelector('[data-frame]');input.value=String(350+i*10);
      input.dispatchEvent(new Event('input',{bubbles:true}));
    }
    player.pause();await player.setProgress(.63);
  });
  await ready();
  assert.ok(Date.now()-started<2000,'A new seek must not wait for obsolete 10-second downloads');
  assert.ok(cancelled>0,'Superseded HTTP downloads must be cancelled');
  assert.equal((await state()).requestedPlaying,false);assert.equal((await state()).progress,.63);
  assert.ok(await page.evaluate(()=>[...document.querySelectorAll('[data-solar-image]')].every(image=>{
    const number=Number(/-(\d+)\.webp$/.exec(image.dataset.frameUrl)?.[1]);
    return [234,235].includes(number)&&image.complete&&image.naturalWidth===768;
  })),'Every panel must display the latest requested frame pair');
  record('Rapid scrubbing cancels obsolete downloads and settles all four paused panels at the latest epoch');
  // A failed request must be recoverable through the ordinary play control.
  await page.evaluate(()=>window.__HELIOS__.player.play());
  failOnce=true;
  await page.evaluate(()=>window.__HELIOS__.player.setProgress(.45));
  assert.equal((await state()).status,'error');
  await page.locator('[data-play]').evaluate(button=>button.click());
  await page.waitForFunction(()=>window.__HELIOS__.player.getState().playing,null,{polling:30,timeout:3000});
  await page.evaluate(()=>window.__HELIOS__.player.pause());
  record('Play retries a failed frame request and resumes without remounting the player');
  await page.evaluate(async()=>{
    const player=window.__HELIOS__.player;
    const requests=[player.setProgress(.22),player.setField('contrast'),player.setProgress(.72),player.setProgress(.81)];
    player.pause();await Promise.all(requests);
  });
  await ready();assert.equal((await state()).field,'contrast');assert.equal((await state()).progress,.81);
  assert.ok(await page.locator('[data-solar-image]').evaluateAll(images=>images.every(image=>image.dataset.frameUrl.includes('contrast'))));
  assert.deepEqual(errors,[]);
  record('Overlapping seek, field change and pause settle consistently without JavaScript errors');
  writeFileSync('tests/solar-interaction-results.json',JSON.stringify({passed:true,browser:process.env.TEST_BROWSER||'chromium',date:new Date().toISOString(),checks:results},null,2)+'\n');
} finally {
  await browser.close();proxy.closeAllConnections();await new Promise(resolve=>proxy.close(resolve));
}
