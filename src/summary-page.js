import {siteUrl} from './site-paths.js';
import {renderReportMath} from './report-math.js';

export async function summaryPage(ctx){
  const current=ctx.state.renderKey;
  const main=document.getElementById('main');
  const intro='The measurements, magnetic physics and modeling choices behind the reconstructions.';
  main.innerHTML=ctx.heading('','Summary',intro)+'<p class="loading" role="status">Opening the summary…</p>';
  try{
    const data=await ctx.fetchJson('/data/summary.json');
    if(current!==ctx.state.renderKey)return;
    const actions=`<a class="button" href="${siteUrl('/assets/summary/evidence.json')}" download>Research record</a><a class="button" href="#methods">Model physics</a>`;
    main.innerHTML=`<div class="summary-column">${ctx.heading('',data.title,data.intro,actions)}<article class="summary-article" aria-label="Summary of the solar-wind modeling study">${data.articleHtml}</article></div>${ctx.footer()}`;
    for(const link of main.querySelectorAll('.summary-article a')){
      const href=link.getAttribute('href');
      if(href.startsWith('/'))link.href=siteUrl(href);
      if(!href.startsWith('#')&&!link.hasAttribute('download')){
        link.target='_blank';
        link.rel='noopener noreferrer';
      }
    }
    for(const image of main.querySelectorAll('[data-summary-src]'))image.src=siteUrl(image.dataset.summarySrc);
    renderReportMath(main);
    ctx.bindCommon();
  }catch(error){
    if(current!==ctx.state.renderKey)return;
    main.innerHTML=ctx.heading('','Summary',intro)+'<div class="callout" role="alert"><div>The summary could not be loaded. <button class="button" data-retry-summary>Retry</button></div></div>';
    main.querySelector('[data-retry-summary]').onclick=()=>ctx.rerender();
  }
}
