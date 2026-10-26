// Check inner panel geometry as well as page overflow: overflow:hidden can mask
// a cropped map or control even while document.scrollWidth looks correct.
import {chromium,firefox} from 'playwright';
import assert from 'node:assert/strict';

const base=process.env.TEST_URL||'http://127.0.0.1:8080';
const engine=process.env.TEST_BROWSER==='firefox'?firefox:chromium;
const browser=await engine.launch({headless:true,...(engine===chromium?{args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']}:{})});
const selectors={overview:'.fact-list','solar-wind':'.solar-grid',verification:'[data-bench]',observations:'[data-craft]',nasa:'#reference-metrics',xray:'#xray-shape',transcripts:'.message',methods:'.model-tabs',code:'.source-line',writeups:'.writeup-body',resources:'.source-manifest',cooperation:'.cooperation-article',summary:'.summary-article'};
try{
  const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>!!window.__HELIOS__,null,{polling:50});
  for(const width of [320,390,768,1280,1600]){
    await page.setViewportSize({width,height:900});
    for(const theme of ['dark','light']){
      if(await page.locator('html').getAttribute('data-theme')!==theme)await page.locator('#theme-toggle').evaluate(button=>button.click());
      for(const [route,selector]of Object.entries(selectors)){
        await page.evaluate(route=>{location.hash=route;},route);
        await page.waitForFunction(route=>window.__HELIOS__.state.route===route,route,{polling:50});
        await page.locator(selector).first().waitFor();
        await page.evaluate(()=>document.fonts.ready);
        if(route==='overview'||route==='solar-wind')await page.waitForFunction(()=>window.__HELIOS__.player?.getState().status==='paused',null,{polling:50});
        const geometry=await page.evaluate(()=>{
          const maps=[...document.querySelectorAll('.canvas-wrap')].map(map=>({width:map.getBoundingClientRect().width,panel:map.parentElement.getBoundingClientRect().width}));
          const method=document.querySelector('.source-method-label select');
          const selectFits=!method||method.getBoundingClientRect().right<=method.closest('.source-tools').getBoundingClientRect().right+1;
          const overlaps=[];
          const box=node=>node.getBoundingClientRect();
          const intersects=(a,b)=>Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1;
          for(const map of document.querySelectorAll('.canvas-wrap')){
            const labels=[...map.querySelectorAll('svg text')].filter(node=>box(node).width>0);
            const overlays=[...map.querySelectorAll('.canvas-label,.canvas-date,.colorbar')].filter(node=>box(node).width>0);
            const sun=map.querySelector('svg > circle[cx="384"][cy="384"]');
            for(let i=0;i<labels.length;i++){
              for(let j=i+1;j<labels.length;j++)if(intersects(box(labels[i]),box(labels[j])))overlaps.push([labels[i].textContent,labels[j].textContent]);
              for(const overlay of overlays)if(intersects(box(labels[i]),box(overlay)))overlaps.push([labels[i].textContent,overlay.className]);
              if(sun&&intersects(box(labels[i]),box(sun)))overlaps.push([labels[i].textContent,'Sun']);
            }
          }
          return {overflow:document.documentElement.scrollWidth>innerWidth+1,maps,selectFits,overlaps};
        });
        assert.equal(geometry.overflow,false,`${route} at ${width}px in ${theme}: page overflow`);
        for(const map of geometry.maps)assert.ok(map.width<=map.panel+1,`${route} at ${width}px in ${theme}: ${map.width}px map is cropped by ${map.panel}px panel`);
        assert.ok(geometry.selectFits,`${route} at ${width}px in ${theme}: method selector is clipped`);
        assert.deepEqual(geometry.overlaps,[],`${route} at ${width}px in ${theme}: map labels overlap`);
      }
    }
  }
  assert.deepEqual(errors,[]);
  console.log('PASS: thirteen views, both themes and five viewport widths; maps and source controls fit their panels');
}finally{await browser.close();}
