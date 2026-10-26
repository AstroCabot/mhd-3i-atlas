// Run after building. Two strict static servers exercise a user site and a project site.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { createReadStream, writeFileSync } from 'node:fs';
import { stat } from 'node:fs/promises';
import { resolve, sep, extname } from 'node:path';

const directory = resolve(process.env.PAGES_TEST_DIR || 'dist');
const types = {'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.webp':'image/webp','.jpg':'image/jpeg','.ttf':'font/ttf','.otf':'font/otf','.woff2':'font/woff2','.woff':'font/woff','.mp4':'video/mp4','.md':'text/plain'};
const browser = await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
const results = [];
try {
  for (const prefix of ['/', '/example-repo/']) {
    const server = createServer(async (req,res) => {
      try {
        const path = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
        if (!path.startsWith(prefix)) {res.writeHead(404).end(); return;}
        const file = resolve(directory,path.slice(prefix.length)||'index.html');
        if (!file.startsWith(directory+sep)) {res.writeHead(404).end(); return;}
        const info = await stat(file);
        if (!info.isFile()) {res.writeHead(404).end();return;}
        res.writeHead(200,{'Content-Type':types[extname(file)]||'application/octet-stream','Content-Length':info.size});
        if(req.method==='HEAD')res.end();else createReadStream(file).pipe(res);
      } catch {res.writeHead(404).end();}
    });
    await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
    const origin = `http://127.0.0.1:${server.address().port}`;
    const page = await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
    const errors = [], requests = [], requestUrls = [];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('response',response=>{if(response.status()>=400)errors.push(`${response.status()} ${response.url()}`);});
    page.on('request',request=>{if(request.url().startsWith(origin)){const url=new URL(request.url());requests.push(url.pathname);requestUrls.push(url);}});
    try {
      await page.goto(origin+prefix+'#overview',{waitUntil:'domcontentloaded'});
      await page.waitForFunction(()=>window.__HELIOS__?.player?.getState().status==='paused',null,{polling:100,timeout:30000});
      assert.match(await page.locator('h1').innerText(),/Solar-wind reconstructions/);
      assert.equal(await page.locator('[data-solar-image]').count(),2);
      await page.evaluate(()=>document.fonts.ready);
      for (const route of ['solar-wind','verification','observations','nasa','xray','methods','code','writeups','resources','transcripts','cooperation','summary']) {
        await page.locator(`[data-nav="${route}"]`).evaluate(node=>node.click());
        await page.waitForFunction(route=>window.__HELIOS__.state.route===route,route,{polling:100});
        assert.equal(await page.locator('h1').count(),1);
        if(route==='nasa')await page.waitForSelector('#reference-metrics');
        if(route==='code')await page.waitForSelector('.source-line');
        if(route==='writeups')await page.waitForSelector('.writeup-article, .writeup-pending');
        if(route==='cooperation'){
          await page.waitForSelector('#cooperation-time');
          assert.equal(await page.locator('h1 .section-number').innerText(),'12');
          const downloads=await page.locator('.cooperation-column a[download]').evaluateAll(nodes=>nodes.map(node=>node.href));
          for(const url of downloads){assert.ok(new URL(url).pathname.startsWith(prefix));assert.equal((await page.request.head(url)).status(),200);}
        }
        if(route==='summary'){
          await page.waitForSelector('#summary-confidence');
          assert.equal(await page.locator('h1 .section-number').innerText(),'13');
          for(const url of await page.locator('.summary-article a').evaluateAll(nodes=>nodes.filter(node=>node.getAttribute('href').startsWith('/')).map(node=>node.href))){
            assert.ok(new URL(url).pathname.startsWith(prefix));assert.equal((await page.request.head(url)).status(),200);
          }
        }
        if (route==='solar-wind') {
          await page.waitForFunction(()=>document.querySelectorAll('[data-image-ready=true]').length===4&&window.__HELIOS__.player?.getState().status==='paused',null,{polling:100});
          await page.locator('[data-field=fluxR2]').evaluate(node=>node.click());
          await page.waitForFunction(()=>window.__HELIOS__.player.getState().field==='contrast'&&window.__HELIOS__.player.getState().status==='paused',null,{polling:100});
          const links = await page.locator('a[download][href$=".mp4"]').evaluateAll(nodes=>nodes.map(node=>node.href));
          assert.equal(links.length,8);
          for(const url of links){assert.ok(new URL(url).pathname.startsWith(prefix));assert.equal((await page.request.head(url)).status(),200);}
        }
        if (route==='methods') {
          assert.ok(await page.locator('.katex').count()>=8);
          assert.equal(await page.locator('[data-math-error]').count(),0);
        }
        if (route==='resources') {
          for (const url of await page.locator('.source-list a').evaluateAll(nodes=>nodes.map(node=>node.href))) {
            assert.ok(new URL(url).pathname.startsWith(prefix));
            assert.equal((await page.request.head(url)).status(),200);
          }
        }
        if (route==='transcripts') {
          await page.waitForSelector('.message');
          await page.locator('#record-search').fill('solar');
          await page.locator('#record-search-form button').evaluate(node=>node.click());
          await page.waitForSelector('[data-jump]');
          await page.locator('[data-jump]').first().evaluate(node=>node.click());
          await page.waitForSelector('.message');
          await page.locator('[data-record-mode=notes]').evaluate(node=>node.click());
          await page.waitForSelector('.note-card');
        }
      }
      // Deep links refresh the same index; no host-side SPA rewrite is required.
      await page.goto(origin+prefix+'#methods',{waitUntil:'domcontentloaded'});
      await page.waitForFunction(()=>window.__HELIOS__?.state.route==='methods',null,{polling:100});
      assert.ok(await page.locator('.katex').count()>=8);
      assert.ok(requests.some(path=>path.endsWith('texgyreschola-regular.otf')),'The scientific body font must load locally');
      assert.ok(requests.every(path=>path.startsWith(prefix)),'A request escaped the repository prefix');
      const entry = requestUrls.find(url=>url.pathname===prefix+'app.js');
      const version = entry?.searchParams.get('v');
      assert.match(version||'',/^[a-f0-9]{12}$/,'The deployed entry point must be content-versioned');
      for(const name of ['solar-player.js','solar-labels.js','frame-cache.js','site-paths.js','theme.js','research-pages.js','report-math.js','cooperation-page.js','summary-page.js']) {
        const module=requestUrls.find(url=>url.pathname===prefix+name);
        assert.equal(module?.searchParams.get('v'),version,`${name} must share the deployment version`);
      }
      const jsonRequests=requestUrls.filter(url=>url.pathname.startsWith(prefix+'data/')&&url.pathname.endsWith('.json'));
      assert.ok(jsonRequests.length>=7,'The routes must request packaged scientific and archive data');
      assert.ok(jsonRequests.every(url=>url.searchParams.get('v')===version),'Data requests must revalidate with the deployed modules');
      assert.deepEqual(errors,[],'JavaScript or HTTP failure');
      results.push({prefix,passed:true,requests:requests.length,checks:['thirteen views','768 px images and field switching','eight video downloads','equations and local fonts','NASA comparison, solver sources and submitted writeups','cooperation article and publication downloads','data and methods downloads','transcript chunks, search and notes','hash deep-link reload','no escaped-prefix requests','consistent module and JSON deployment versions']});
      console.log(`PASS: strict static host at ${prefix}; ${requests.length} repository-relative requests.`);
    } finally {
      await page.close();
      await new Promise(resolve=>server.close(resolve));
    }
  }
  writeFileSync('tests/pages-results.json',JSON.stringify({passed:true,date:new Date().toISOString(),results},null,2));
} finally {await browser.close();}
