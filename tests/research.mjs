// Exercise the new research views on a strict, repository-prefixed static host.
import {chromium,firefox} from 'playwright';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {createReadStream,mkdirSync,writeFileSync} from 'node:fs';
import {stat} from 'node:fs/promises';
import {resolve,sep,extname} from 'node:path';

const directory=resolve(process.env.PAGES_TEST_DIR||'dist'),prefix='/example-repo/';
const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.otf':'font/otf','.woff2':'font/woff2','.woff':'font/woff','.md':'text/plain','.txt':'text/plain'};
const server=createServer(async(req,res)=>{
  try{
    const path=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if(!path.startsWith(prefix))throw Error();
    const file=resolve(directory,path.slice(prefix.length)||'index.html');
    if(!file.startsWith(directory+sep))throw Error();
    const info=await stat(file);if(!info.isFile())throw Error();
    res.writeHead(200,{'Content-Type':types[extname(file)]||'application/octet-stream','Content-Length':info.size});
    if(req.method==='HEAD')res.end();else createReadStream(file).pipe(res);
  }catch{res.writeHead(404).end();}
});
await new Promise(done=>server.listen(0,'127.0.0.1',done));
const base=`http://127.0.0.1:${server.address().port}${prefix}`;
const engine=process.env.TEST_BROWSER==='chromium'?chromium:firefox;
const browser=await engine.launch({headless:true,...(engine===chromium?{args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']}:{})});
const errors=[],results=[];
try{
  const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
  page.on('pageerror',error=>errors.push(error.message));
  page.on('response',response=>{if(response.status()>=400)errors.push(`${response.status()} ${response.url()}`);});
  const open=async(route,selector)=>{
    await page.goto(base+'#'+route,{waitUntil:'domcontentloaded'});
    await page.waitForFunction(route=>window.__HELIOS__?.state.route===route.split('?')[0],route,{polling:100});
    if(route.includes('agent='))await page.waitForSelector(`.model-tab.active[href="#${route.split('?')[0]}?agent=${new URLSearchParams(route.split('?')[1]).get('agent')}"]`);
    await page.waitForSelector(selector);
  };
  const shot=async(name)=>{if(process.env.CAPTURE_SCREENSHOTS==='1'){mkdirSync('tests/screenshots',{recursive:true});await page.screenshot({path:`tests/screenshots/${name}.png`,fullPage:true,animations:'disabled',timeout:10000});}};
  const checkAgentSpacing=async()=>{
    const gaps=await page.locator('.model-tab .agent-cell').evaluateAll(cells=>cells.map(cell=>{
      const text=[...cell.childNodes].find(node=>node.nodeType===Node.TEXT_NODE&&node.textContent.trim());
      const range=document.createRange();range.selectNodeContents(text);
      return range.getBoundingClientRect().left-cell.querySelector('.color-dot').getBoundingClientRect().right;
    }));
    assert.equal(gaps.length,3);assert.ok(gaps.every(gap=>gap>=7.9),'Agent colour swatches need an 8px gap before their names');
    const tops=await page.locator('.model-tab').evaluateAll(tabs=>tabs.map(tab=>tab.getBoundingClientRect().top));
    assert.ok(Math.max(...tops)-Math.min(...tops)<1,'The three agent selectors should fit on one row');
  };
  const checkReportLayout=async(agent,width)=>{
    await page.evaluate(()=>document.fonts.ready);
    const layout=await page.evaluate(()=>{
      const column=document.querySelector('.writeup-column').getBoundingClientRect();
      const main=document.getElementById('main').getBoundingClientRect();
      const body=document.querySelector('.writeup-body').getBoundingClientRect();
      return {
        centered:Math.abs((column.left+column.right-main.left-main.right)/2)<1,
        width:column.width,
        headings:document.querySelectorAll('.writeup-article h1,.writeup-article h2,.writeup-article h3,.writeup-article h4').length,
        gap:parseFloat(getComputedStyle(document.querySelector('.writeup-body p')).marginBottom),
        overflow:[...document.querySelectorAll('.writeup-body .table-scroll,.writeup-body pre,.writeup-equation')].filter(node=>node.scrollWidth>node.clientWidth+1).map(node=>({type:node.className,width:node.clientWidth,scroll:node.scrollWidth})),
        math:[...document.querySelectorAll('.writeup-equation-line')].map(node=>{
          const box=node.getBoundingClientRect();
          const parts=[...node.querySelectorAll('.katex-display > .katex > .katex-html > :is(.base,.katex-base)')].map(part=>part.getBoundingClientRect());
          const left=Math.min(...parts.map(part=>part.left)),right=Math.max(...parts.map(part=>part.right));
          return {tex:node.closest('[data-writeup-math]').dataset.writeupMath.slice(0,50),fits:left>=body.left-1&&right<=body.right+1,center:Math.abs((left+right-box.left-box.right)/2),...(!parts.length?{html:node.innerHTML.slice(0,500)}:{})};
        }),
      };
    });
    assert.ok(layout.centered&&layout.width<=780.5,`${agent}: single centered column at ${width}px`);
    assert.equal(layout.headings,0,'Report bodies should have no headings or submission banners');
    assert.ok(layout.gap>=22,`${agent} at ${width}px: report paragraphs need clear separation (${layout.gap}px)`);
    assert.deepEqual(layout.overflow,[],`${agent}: clipped or horizontally scrolling report material at ${width}px`);
    for(const math of layout.math){assert.ok(math.fits,`${agent} at ${width}px: equation leaves the reading column: ${JSON.stringify(math)}`);assert.ok(math.center<=1.5,`${agent}: equation is off-center: ${JSON.stringify(math)}`);}
  };
  await open('solar-wind','[data-orbit=mars]');
  await page.waitForFunction(()=>window.__HELIOS__.player.getState().status==='paused',null,{polling:100});
  assert.equal(await page.locator('[data-nav]').count(),11);
  for(const [id,r]of Object.entries({mercury:.38709927,venus:.72333566,earth:1.00000261,mars:1.52371034})){
    assert.equal(await page.locator(`[data-orbit=${id}]`).count(),4);
    assert.ok(Math.abs(Number(await page.locator(`[data-orbit=${id}]`).first().getAttribute('r'))-160*r)<1e-8);
    assert.equal(await page.locator(`[data-orbit-label=${id}]`).count(),4);
  }
  assert.equal(await page.locator('#heading-toggle').count(),0);
  assert.equal(await page.locator('.top-status').count(),0);
  assert.equal(await page.locator('.solar-grid [data-solar]').count(),4);
  assert.equal(await page.locator('[data-video-model=enlil]').count(),2);
  const typography=await page.evaluate(()=>({brand:getComputedStyle(document.querySelector('.brand-name')).fontFamily,head:getComputedStyle(document.querySelector('h1')).fontFamily,weight:getComputedStyle(document.querySelector('.brand-name')).fontWeight}));
  assert.equal(typography.brand,typography.head);assert.equal(typography.weight,'900');
  await page.locator('#theme-toggle').click();
  await page.evaluate(()=>document.fonts.ready);await shot('orbits-light');
  results.push('four synchronized fields including CCMC; technical-report typography; no font toggle or notebook label');
  await open('nasa','#reference-metrics tbody tr');
  assert.equal(await page.locator('#reference-metrics tbody tr').count(),4);
  assert.equal(await page.locator('#reference-comet-means tbody tr').count(),4);
  assert.equal(await page.locator('[data-chart-export=reference-spacecraft] svg').count(),1,'NASA charts must use the shared download icon');
  for(const craft of ['wind','solar_orbiter','stereo_a']){
    await page.locator(`[data-reference-craft=${craft}]`).click();
    await page.waitForFunction(craft=>window.__HELIOS__.state.referenceCraft===craft,craft,{polling:100});
    await page.waitForSelector('#reference-quantity');
    assert.equal(await page.locator('p.footnote').filter({hasText:'not the exact Wind trajectory'}).count(),craft==='wind'?1:0,'Earth-proxy qualification belongs only to Wind');
  }
  await page.locator('#reference-quantity').selectOption('density');
  await page.waitForSelector('#reference-spacecraft svg');
  await shot('nasa-light');results.push('four-model NASA metrics, spacecraft and quantity controls');
  for(const agent of ['argon','codex','claude']){
    await open(`code?agent=${agent}`,'.source-line');
    await checkAgentSpacing();
    const methods=await page.locator('#source-method option').evaluateAll(nodes=>nodes.filter(n=>n.value).map(n=>n.value));
    if(methods.length){
      const line=methods.at(-1);await page.locator('#source-method').selectOption(line);
      assert.equal(await page.locator('.source-line.selected').getAttribute('data-source-line'),line);
      const visible=await page.locator('.source-line.selected').evaluate(row=>{const a=row.getBoundingClientRect(),b=row.closest('.source-code').getBoundingClientRect();return a.top>=b.top&&a.bottom<=b.bottom;});
      assert.ok(visible,'Method jump must scroll the selected line into the source viewport');
    }
    await page.locator('#source-search').fill('return');assert.ok(await page.locator('.source-line.matches').count()>0);
    const href=page.url();await page.reload({waitUntil:'domcontentloaded'});await page.waitForSelector('.source-line.selected');
    assert.equal(page.url(),href);
    const download=await page.locator('.source-actions a[download]').getAttribute('href');assert.equal((await page.request.get(download)).status(),200);
    await page.locator(`.heading-actions a[href="#methods?agent=${agent}"]`).click();
    await page.waitForSelector(`[data-method=${agent}].active`);
    assert.equal(await page.evaluate(()=>window.__HELIOS__.state.method),agent,'Source-to-physics links must preserve the model');
  }
  await shot('source-light');results.push('three source catalogues, method scrolling, search, line permalinks and raw downloads');
  for(const agent of ['argon','codex','claude']){
    await open(`writeups?agent=${agent}`,'.writeup-article');
    await checkAgentSpacing();
    assert.equal(await page.locator('.writeup-status').filter({hasText:'Submitted'}).count(),0,'Repeated submission labels should be omitted');
    await page.waitForFunction(()=>document.querySelector('.writeup-body .katex'),null,{polling:100});
    assert.ok(await page.locator('.writeup-body .katex').count()>0,`${agent} report equations must render`);
    assert.deepEqual(await page.locator('.writeup-body .katex-error').allTextContents(),[],`${agent} math errors`);
    await checkReportLayout(agent,1280);
    if(process.env.CAPTURE_SCREENSHOTS==='1')await page.locator('.writeup-equation').first().screenshot({path:`tests/screenshots/${agent}-equation-desktop.png`});
    for(const img of await page.locator('.writeup-body img').all()){
      await img.scrollIntoViewIfNeeded();
      await img.evaluate(node=>{node.loading='eager';});
      await page.waitForFunction(src=>[...document.images].some(node=>node.src===src&&node.complete&&node.naturalWidth>0),await img.getAttribute('src'),{polling:100,timeout:10000});
      assert.ok(await img.evaluate(node=>node.naturalWidth>0));
    }
    for(const link of await page.locator('.writeup-body a').all()){
      const url=await link.getAttribute('href');if(url.startsWith(base))assert.equal((await page.request.head(url)).status(),200);
    }
  }
  await page.locator('[data-nav=overview]').evaluate(node=>node.click());
  await page.waitForFunction(()=>window.__HELIOS__.state.route==='overview',null,{polling:100});
  await page.locator('[data-nav=writeups]').evaluate(node=>node.click());
  await page.waitForSelector('.model-tab.active[href="#writeups?agent=claude"]');
  await shot('writeup-light');results.push('three supplied reports, rendered math, original figures and working evidence links');
  for(const width of [1600,1024,768,390,320]){
    await page.setViewportSize({width,height:900});
    for(const route of ['nasa','code?agent=codex',...['argon','codex','claude'].map(agent=>`writeups?agent=${agent}`)]){
      await open(route,route==='nasa'?'#reference-metrics':route.startsWith('code')?'.source-code':'.writeup-body');
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${route} overflows at ${width}px`);
      if(route.startsWith('writeups')){
        const agent=route.split('agent=')[1];await checkReportLayout(agent,width);await checkAgentSpacing();
        if(process.env.CAPTURE_SCREENSHOTS==='1'&&width===320)await page.locator('.writeup-equation').first().screenshot({path:`tests/screenshots/${agent}-equation-mobile.png`});
      }
    }
  }
  await shot('writeup-mobile');await page.locator('#theme-toggle').click();await shot('writeup-dark-mobile');
  const rendered=await page.evaluate(async()=>{const {renderWriteupMarkdown}=await import([...performance.getEntriesByType('resource')].find(row=>row.name.includes('/research-pages.js?')).name);return renderWriteupMarkdown('<script>alert(1)</script>\n\n[x](javascript:alert)\n\n# Heading');});
  assert.ok(!rendered.includes('<script>')&&!rendered.includes('href="javascript:'));
  results.push('all reports use one centered column, no body headings, spaced paragraphs and centered multiline equations at 1600, 1280, 1024, 768, 390 and 320px; escaped report HTML');
  assert.deepEqual(errors,[]);
  writeFileSync('tests/research-results.json',JSON.stringify({passed:true,browser:engine.name(),results},null,2)+'\n');
  results.forEach(result=>console.log('PASS: '+result));
}finally{await browser.close();await new Promise(done=>server.close(done));}
