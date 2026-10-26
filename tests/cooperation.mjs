// Article navigation, source fidelity, lazy loading, recovery and narrow layouts.
import {chromium,firefox} from 'playwright';
import assert from 'node:assert/strict';
const base=(process.env.TEST_URL||'http://127.0.0.1:8080').replace(/\/$/,'');
const engine=process.env.TEST_BROWSER==='firefox'?firefox:chromium;
const browser=await engine.launch({headless:true,...(engine===chromium?{args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']}:{})});
try{
  const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
  const requests=[],errors=[];
  page.on('request',request=>requests.push(request.url()));page.on('pageerror',error=>errors.push(error.message));
  page.on('response',response=>{if(response.status()>=400)errors.push(`${response.status()} ${response.url()}`);});
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>!!window.__HELIOS__,null,{polling:50});
  assert.ok(!requests.some(url=>url.includes('/data/agent-comparison.json')||url.includes('/assets/agent-comparison/')),'The article must not download its data or figures on the overview');
  await page.locator('[data-nav=cooperation]').evaluate(node=>node.click());
  await page.locator('.cooperation-article').waitFor();
  assert.equal(await page.locator('h1 .section-number').innerText(),'12');
  assert.deepEqual(await page.locator('#cooperation-time tbody tr:last-child td').allTextContents(),['4.66','6.50','28%']);
  assert.deepEqual(await page.locator('#cooperation-metrics tbody tr:first-child td').allTextContents(),['4.035','3.475','0.830','1.055']);
  const data=await page.evaluate(()=>window.__HELIOS__.state.route==='cooperation');assert.ok(data);
  const archive=await (await page.request.get(base+'/assets/agent-comparison/derived/quotes.json')).json();
  for(const card of await page.locator('.cooperation-quote').all()){
    const id=/Q\d+/.exec(await card.innerText())[0],record=archive.quotes.find(row=>row.id===id);
    assert.ok(record?.verified_verbatim);
    for(const text of record.excerpts)assert.ok((await card.locator('blockquote').innerText()).includes(text));
  }
  assert.equal(await page.locator('.cooperation-quote').count(),4);
  for(const summary of await page.locator('.cooperation-details > summary').all())await summary.evaluate(node=>node.click());
  for(const image of await page.locator('.cooperation-figure img').all()){
    assert.equal(await image.getAttribute('loading'),'lazy');
    // Decode explicitly after expansion: compositor-free Chromium can defer
    // intersection-driven lazy loads even after programmatic scrolling.
    await image.evaluate(node=>{node.loading='eager';node.scrollIntoView();});
    await page.waitForFunction(image=>image.complete&&image.naturalWidth>0,await image.elementHandle(),{polling:50});
  }
  assert.equal(await page.locator('.cooperation-figure img').count(),3);
  for(const url of await page.locator('.cooperation-column a').evaluateAll(links=>links.map(link=>link.href))){
    assert.ok(new URL(url).pathname.startsWith(new URL(base).pathname));
    assert.equal((await page.request.head(url)).status(),200,url);
  }
  for(const width of [320,390,768,1280,1600]){
    await page.setViewportSize({width,height:900});
    for(const theme of ['light','dark']){
      if(await page.locator('html').getAttribute('data-theme')!==theme)await page.locator('#theme-toggle').evaluate(node=>node.click());
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,`Article overflow at ${width}px in ${theme}`);
    }
  }
  await page.goto(base+'/#cooperation',{waitUntil:'domcontentloaded'});await page.locator('#cooperation-time').waitFor();
  assert.deepEqual(errors,[]);
  console.log('PASS: section12, matched figures and tables, exact quotes, downloads, deep link, lazy assets and both themes at five widths');

  const failure=await browser.newPage({reducedMotion:'reduce'});let count=0;
  await failure.route('**/data/agent-comparison.json*',route=>++count===1?route.fulfill({status:503,body:'Unavailable'}):route.continue());
  await failure.goto(base+'/#cooperation',{waitUntil:'domcontentloaded'});
  await failure.locator('[data-retry-comparison]').waitFor();await failure.locator('[data-retry-comparison]').evaluate(node=>node.click());
  await failure.locator('#cooperation-time').waitFor();assert.equal(count,2);
  console.log('PASS: article data failures offer a working Retry control');
}finally{await browser.close();}
