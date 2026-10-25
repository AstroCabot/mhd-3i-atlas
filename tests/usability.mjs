// Keyboard navigation and adversarial archive-loading regressions.
import {chromium,firefox} from 'playwright';
import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';

const base=(process.env.TEST_URL||'http://127.0.0.1:8080').replace(/\/$/,'');
const engine=process.env.TEST_BROWSER==='firefox'?firefox:chromium;
const browser=await engine.launch({headless:true,...(engine===chromium?{args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']}:{})});
const checks=[],errors=[];
function record(message){checks.push(message);console.log('PASS',message);}
async function newPage(options={}){
  const page=await browser.newPage({reducedMotion:'reduce',...options});
  page.on('pageerror',error=>errors.push(error.message));return page;
}
async function open(page,route='overview'){
  await page.goto(base+'/#'+route,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>Boolean(window.__HELIOS__),null,{polling:50});
}
try {
  const mobile=await newPage({viewport:{width:390,height:844}});
  await open(mobile);
  assert.equal(await mobile.locator('#sidebar').evaluate(node=>node.inert),true);
  await mobile.keyboard.press('Tab');await mobile.keyboard.press('Tab');
  assert.equal(await mobile.evaluate(()=>document.activeElement.id),'menu','Closed navigation must not add invisible tab stops');
  await mobile.keyboard.press('Enter');
  assert.equal(await mobile.evaluate(()=>Boolean(document.activeElement.closest('#sidebar'))),true);
  assert.equal(await mobile.locator('.workspace').evaluate(node=>node.inert),true);
  await mobile.locator('#sidebar a').last().focus();await mobile.keyboard.press('Tab');
  assert.equal(await mobile.evaluate(()=>document.activeElement===document.querySelector('#sidebar a')),true);
  await mobile.keyboard.press('Shift+Tab');
  assert.equal(await mobile.evaluate(()=>document.activeElement===Array.from(document.querySelectorAll('#sidebar a')).at(-1)),true);
  await mobile.keyboard.press('Escape');
  assert.equal(await mobile.evaluate(()=>document.activeElement.id),'menu');
  assert.equal(await mobile.locator('.workspace').evaluate(node=>node.inert),false);
  await mobile.locator('#menu').focus();await mobile.keyboard.press('Enter');
  await mobile.locator('[data-nav=overview]').focus();await mobile.keyboard.press('Enter');
  assert.equal(await mobile.locator('#menu').getAttribute('aria-expanded'),'false','The current route must also close the drawer');
  assert.equal(await mobile.evaluate(()=>document.activeElement.id),'main');
  await mobile.locator('#menu').focus();await mobile.keyboard.press('Enter');
  await mobile.locator('[data-nav=methods]').focus();await mobile.keyboard.press('Enter');
  await mobile.waitForFunction(()=>window.__HELIOS__.state.route==='methods',null,{polling:50});
  assert.equal(await mobile.evaluate(()=>document.activeElement.id),'main');
  await mobile.setViewportSize({width:1280,height:900});
  // Headless Chromium may defer native resize delivery until a compositor frame.
  await mobile.evaluate(()=>window.dispatchEvent(new Event('resize')));
  await mobile.waitForFunction(()=>!document.getElementById('sidebar').inert,null,{polling:50});
  assert.equal(await mobile.locator('#sidebar').evaluate(node=>node.inert),false);
  await mobile.close();record('Mobile drawer hides closed links, contains keyboard focus, restores focus and survives breakpoint changes');

  const notes=await newPage();let noteRequests=0;
  await notes.route('**/data/shared-notes.json*',route=>++noteRequests===1?route.fulfill({status:503,body:'Unavailable'}):route.continue());
  await open(notes,'transcripts?mode=notes');
  await notes.locator('[data-retry-record]').waitFor();
  assert.equal(await notes.locator('#notes-output .loading').count(),0);
  await notes.locator('[data-retry-record]').evaluate(node=>node.click());await notes.locator('.note-card').first().waitFor();
  assert.equal(noteRequests,2);await notes.close();
  record('Failed shared-note downloads show an accessible retry and recover without unhandled errors');

  const noteFilters=await newPage();await open(noteFilters,'transcripts?mode=notes&role=assistant');
  await noteFilters.locator('.note-card').first().waitFor();
  assert.deepEqual(await noteFilters.locator('#record-role option').evaluateAll(options=>options.map(option=>option.value)),['all','directed']);
  assert.equal(await noteFilters.locator('#record-role').inputValue(),'all');
  await noteFilters.locator('[data-record-view=exchanges]').evaluate(node=>node.click());
  await noteFilters.locator('[data-note-ref]').first().waitFor();
  await noteFilters.locator('[data-note-ref]').first().evaluate(node=>node.click());
  await noteFilters.waitForFunction(()=>window.__HELIOS__.state.role==='all'&&window.__HELIOS__.state.search.length>0,null,{polling:50});
  assert.equal(await noteFilters.locator('#record-role').inputValue(),'all');
  assert.equal(await noteFilters.locator('[data-record-mode=notes]').getAttribute('class'),'active');
  await noteFilters.close();record('Notes expose only supported filters, normalize deep links and clear Directed when following references');

  for(const [route,path,selector] of [['nasa','nasa-comparison.json','#reference-metrics'],['code','solver-code.json','.source-line'],['writeups','model-writeups.json','.writeup-article']]){
    const page=await newPage();let requests=0;
    await page.route(`**/data/${path}*`,request=>++requests===1?request.fulfill({status:503,body:'Unavailable'}):request.continue());
    await open(page,route);await page.locator('[data-retry-archive]').waitFor();
    assert.equal(await page.locator('#main .loading').count(),0);
    await page.locator('[data-retry-archive]').evaluate(node=>node.click());await page.locator(selector).first().waitFor();
    assert.equal(requests,2);await page.close();
  }
  record('NASA, source and report views replace failed loaders with working retry controls');

  const transcripts=await newPage();
  const index=await (await transcripts.request.get(base+'/data/transcripts.json')).json();
  const session=index.sessions.find(row=>row.agent==='argon'&&!row.parent_id),chunk=session.chunks[0].url;
  let held;
  await transcripts.route('**'+chunk+'*',route=>{held=route;});
  const requested=transcripts.waitForRequest(request=>new URL(request.url()).pathname.endsWith(chunk));
  await open(transcripts,'transcripts');await requested;
  await transcripts.locator('#record-role').selectOption('user');
  await transcripts.locator('#transcript-output .session-meta').waitFor();
  const filtered=await transcripts.locator('.message-role').allTextContents();
  assert.ok(filtered.length>0&&filtered.every(role=>role==='user'));
  const response=transcripts.waitForResponse(response=>new URL(response.url()).pathname.endsWith(chunk));
  await held.continue();await response;await transcripts.waitForTimeout(100);
  assert.deepEqual(await transcripts.locator('.message-role').allTextContents(),filtered);
  assert.equal(await transcripts.locator('#record-role').inputValue(),'user');
  await transcripts.close();record('A delayed unfiltered transcript response cannot overwrite a newer entry filter');

  const stale=await newPage();let oldNotes;
  await stale.route('**/data/shared-notes.json*',route=>{oldNotes=route;});
  const oldRequested=stale.waitForRequest('**/data/shared-notes.json*');
  await open(stale,'transcripts?mode=notes');await oldRequested;
  await stale.locator('[data-nav=methods]').evaluate(node=>node.click());
  await oldNotes.fulfill({status:503,body:'Unavailable'});await stale.waitForTimeout(100);
  assert.equal(await stale.locator('[data-retry-record]').count(),0);
  assert.match(await stale.locator('h1').innerText(),/Model equations/);
  await stale.close();record('Late archive failures cannot alter a different section');

  const source=await newPage();await open(source,'code?agent=codex&line=17');
  await source.locator('.source-line').first().waitFor();
  assert.equal(await source.locator('.line-number[tabindex="0"]').count(),1);
  await source.locator('.source-code').focus();await source.keyboard.press('Tab');
  assert.equal(await source.evaluate(()=>document.activeElement.textContent),'17');
  await source.keyboard.press('ArrowDown');
  assert.equal(await source.evaluate(()=>document.activeElement.textContent),'18');
  await source.keyboard.press('End');
  assert.equal(await source.evaluate(()=>document.activeElement===document.querySelector('.source-line:last-child .line-number')),true);
  await source.keyboard.press('Home');
  assert.equal(await source.evaluate(()=>document.activeElement.textContent),'1');
  await source.keyboard.press('Tab');
  assert.equal(await source.evaluate(()=>Boolean(document.activeElement.closest('.source-code'))),false,'Tab must leave the source viewer');
  assert.equal(await source.locator('.line-number[tabindex="0"]').count(),1);
  await source.close();record('Source lines support arrow navigation and permalinks without hundreds of tab stops');

  const solar=await newPage();await open(solar,'solar-wind');
  await solar.waitForFunction(()=>window.__HELIOS__.player?.getState().status==='paused',null,{polling:50});
  await solar.evaluate(()=>window.__HELIOS__.state.charts.find(row=>row.id==='comet-incident').chart.dispatchAction({type:'dataZoom',start:20,end:70}));
  const zoom=()=>solar.evaluate(()=>window.__HELIOS__.state.charts.find(row=>row.id==='comet-incident').chart.getOption().dataZoom.map(({start,end,startValue,endValue})=>({start,end,startValue,endValue})));
  const windowBefore=await zoom();
  await solar.locator('[data-model-toggle=codex]').evaluate(node=>node.click());assert.deepEqual(await zoom(),windowBefore);
  await solar.locator('#design-band').evaluate(node=>node.click());assert.deepEqual(await zoom(),windowBefore);
  await solar.close();record('Model visibility and design-spread controls preserve the selected chart time window');

  assert.deepEqual(errors,[]);
  if(process.env.REVIEW_RESULTS)writeFileSync(process.env.REVIEW_RESULTS,JSON.stringify({checks,errors},null,2)+'\n');
}finally{await browser.close();}
