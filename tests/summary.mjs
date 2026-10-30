// Reader-facing article checks: evidence, static figures, equations and recovery.
import {chromium,firefox} from 'playwright';
import assert from 'node:assert/strict';

const base=(process.env.TEST_URL||'http://127.0.0.1:8080').replace(/\/$/,'');
const engine=process.env.TEST_BROWSER==='firefox'?firefox:chromium;
const browser=await engine.launch({headless:true,...(engine===chromium?{args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']}:{})});
try{
  const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
  const requests=[],errors=[];
  page.on('request',request=>requests.push(request.url()));
  page.on('pageerror',error=>errors.push(error.message));
  page.on('response',response=>{if(response.status()>=400)errors.push(`${response.status()} ${response.url()}`);});
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>!!window.__HELIOS__,null,{polling:50});
  assert.ok(!requests.some(url=>url.includes('/data/summary.json')||url.includes('/assets/summary/')),'Overview must not load the article or its evidence');
  const before=requests.length;
  await page.locator('[data-nav=summary]').evaluate(node=>node.click());
  await page.locator('#summary-runtimes').waitFor();
  assert.equal(await page.locator('h1 .section-number').innerText(),'13');
  assert.equal(await page.locator('.summary-article table').count(),4);
  assert.equal(await page.locator('.summary-article .section-heading h2').count(),6);
  assert.equal(await page.locator('.summary-article img').count(),3);
  assert.equal(await page.locator('.summary-article figure').count(),3);
  assert.equal(await page.locator('.summary-article canvas,.summary-article video,.summary-article iframe').count(),0);
  assert.ok(!requests.slice(before).some(url=>url.includes('/assets/summary/evidence')||url.includes('/assets/summary/figure-inputs/')),'Raw research inputs must load only when readers follow a link');
  assert.equal(await page.locator('.summary-equation .katex-error').count(),0);
  assert.ok(await page.locator('.summary-equation .katex').count()>=4);
  for(const image of await page.locator('.summary-figure img').all()){
    assert.equal(await image.getAttribute('loading'),'lazy');
    assert.ok((await image.getAttribute('alt')).length>60);
    assert.ok(new URL(await image.getAttribute('src'),base).pathname.startsWith(new URL(base).pathname));
    await image.evaluate(node=>{node.loading='eager';node.scrollIntoView();});
    await page.waitForFunction(node=>node.complete&&node.naturalWidth>0,await image.elementHandle(),{polling:50});
  }
  const cells=await page.locator('#summary-confidence tbody tr').evaluateAll(rows=>rows.map(row=>[...row.cells].map(cell=>cell.textContent)));
  assert.deepEqual(cells.map(row=>row.slice(0,3)),[
    ['Argon','55.8','2.4'],['Codex','140.0','1.3'],['Claude','32.0','1.5'],['NASA/CCMC ENLIL','114.5','0.44']
  ]);
  assert.deepEqual(await page.locator('#summary-runtimes tbody tr td:last-child').allTextContents(),['2.7 min','63.7 min','56.3 min','Not recorded']);
  for(const geometry of await page.locator('.summary-table-scroll').evaluateAll(nodes=>nodes.map(node=>({viewport:node.clientWidth,table:node.querySelector('table').getBoundingClientRect().width}))))assert.ok(geometry.table<=geometry.viewport+1,'Tables should fit the desktop reading column');
  const article=await page.locator('.summary-article').textContent();
  assert.ok(!article.includes('{{'));
  for(const term of ['32 hours late','+0.12, +0.28, −0.71','not a completely blind test','no one-thread run'])assert.ok(article.includes(term),term);
  const citations=await page.locator('.summary-cite').evaluateAll(nodes=>nodes.map(node=>({href:node.href,description:node.getAttribute('aria-label')})));
  assert.ok(citations.length>=10);
  assert.ok(citations.every(row=>row.description&&row.href));
  await page.locator('.summary-sources > summary').evaluate(node=>node.click());
  const localLinks=await page.locator('.summary-article a').evaluateAll(nodes=>nodes.filter(node=>node.getAttribute('href').startsWith('/')).map(node=>node.href));
  for(const url of localLinks){
    assert.ok(new URL(url).pathname.startsWith(new URL(base).pathname));
    assert.equal((await page.request.head(url)).status(),200,url);
  }
  const evidence=await (await page.request.get(base+'/assets/summary/evidence.json')).json();
  assert.equal(evidence.derivations.stereoCommonSamples,385);
  assert.ok(evidence.figureDerivations.magnetogramAndWsa.velocityLawMaximumErrorKms<3.1e-5);
  assert.ok(Math.abs(evidence.figureDerivations.geometry.positions['3i_atlas'].radiusAu-1.87321288)<1e-8);
  for(const row of evidence.files)assert.equal((await page.request.head(base+row.url)).status(),200,row.url);
  for(const summary of await page.locator('.summary-explainer > summary').all())await summary.evaluate(node=>node.click());
  for(const width of [320,390,768,1280,1600]){
    await page.setViewportSize({width,height:900});
    for(const theme of ['light','dark']){
      if(await page.locator('html').getAttribute('data-theme')!==theme)await page.locator('#theme-toggle').evaluate(node=>node.click());
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,`Summary overflow at ${width}px in ${theme}`);
    }
  }
  await page.goto(base+'/#summary',{waitUntil:'domcontentloaded'});
  await page.locator('#summary-confidence').waitFor();
  assert.deepEqual(errors,[]);
  console.log('PASS: section 13, three static figures, MHD equations, verified tables and source links, lazy assets, deep links and responsive themes');

  const failure=await browser.newPage({reducedMotion:'reduce'});let count=0;
  await failure.route('**/data/summary.json*',route=>++count===1?route.fulfill({status:503,body:'Unavailable'}):route.continue());
  await failure.goto(base+'/#summary',{waitUntil:'domcontentloaded'});
  await failure.locator('[data-retry-summary]').waitFor();
  await failure.locator('[data-retry-summary]').evaluate(node=>node.click());
  await failure.locator('#summary-confidence').waitFor();assert.equal(count,2);
  console.log('PASS: Summary offers a working Retry after an article-data failure');
}finally{await browser.close();}
