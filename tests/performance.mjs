// Cold-cache playback measurement under a repeatable, high-latency connection.
// PERF_URL selects an already served build; PERF_OUTPUT saves the measurements.
import {chromium} from 'playwright';
import {writeFileSync} from 'node:fs';

const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
try {
  const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
  const network=await page.context().newCDPSession(page);
  await network.send('Network.enable');
  await network.send('Network.setCacheDisabled',{cacheDisabled:true});
  await network.send('Network.emulateNetworkConditions',{offline:false,latency:250,downloadThroughput:750000,uploadThroughput:125000});
  const errors=[],requests=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>requests.push(request.url()));
  const started=Date.now();
  await page.goto((process.env.PERF_URL||'http://127.0.0.1:8080')+'/#solar-wind',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>window.__HELIOS__?.player?.getState().status==='paused',null,{polling:50,timeout:60000});
  const readyMs=Date.now()-started;
  const initial=await page.evaluate(()=>window.__HELIOS__.player.getState().progress);
  const playStarted=Date.now();
  await page.evaluate(()=>window.__HELIOS__.player.play());
  const playMs=Date.now()-playStarted;
  const samples=[];
  for(let i=0;i<100;i++){
    await page.waitForTimeout(100);
    samples.push(await page.evaluate(()=>window.__HELIOS__.player.getState()));
  }
  await page.evaluate(()=>window.__HELIOS__.player.pause());
  const final=samples.at(-1);
  const secondsAdvanced=((final.progress-initial+1)%1)*48;
  const report={readyMs,playMs,secondsAdvanced,bufferingSamples:samples.filter(sample=>!sample.playing).length,
    frameRequests:requests.filter(url=>/\.(webp|bin)(?:\?|$)/.test(url)).length,
    packRequests:requests.filter(url=>url.includes('/frame-packs/')).length,errors};
  console.log(JSON.stringify(report,null,2));
  if(process.env.PERF_OUTPUT)writeFileSync(process.env.PERF_OUTPUT,JSON.stringify(report,null,2)+'\n');
  if(process.env.PERF_ASSERT==='1'){
    if(errors.length||secondsAdvanced<9||report.bufferingSamples>15)throw new Error('Playback is not keeping pace on the test connection.');
    if(samples.some(sample=>sample.cache&&(sample.cache.retainedBytes>32*1024*1024||sample.cache.decodedFrames>48)))throw new Error('The playback cache exceeded its memory budget.');
  }
}finally{await browser.close();}
