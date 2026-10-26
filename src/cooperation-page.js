import {siteUrl} from './site-paths.js';

const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const number=(value,digits=2)=>value.toLocaleString('en-GB',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const asset=path=>siteUrl('/assets/agent-comparison/'+path);
const link=(path,label,download=false)=>`<a href="${asset(path)}"${download?' download':' target="_blank" rel="noopener noreferrer"'}>${label}</a>`;
const section=title=>`<div class="section-heading"><h2>${title}</h2></div>`;

export async function cooperationPage(ctx){
  const current=ctx.state.renderKey;
  const title='Cooperation and competition';
  const intro='What six autonomous solar-wind modeling runs reveal about time, accuracy and research behavior.';
  const main=document.getElementById('main');
  main.innerHTML=ctx.heading('',title,intro)+'<p class="loading" role="status">Opening the comparison…</p>';
  try{
    const data=await ctx.fetchJson('/data/agent-comparison.json');
    if(current!==ctx.state.renderKey)return;
    const summary=data.summary;
    const figure=(name,alt,caption)=>{
      const f=data.figures[name];
      return `<figure class="cooperation-figure"><div class="cooperation-figure-scroll" tabindex="0" role="region" aria-label="${escape(alt)}"><img src="${siteUrl(f.url)}" width="${Math.ceil(f.width)}" height="${Math.ceil(f.height)}" alt="${escape(alt)}" loading="lazy" decoding="async"/></div><figcaption>${caption} ${link('figures/'+name+'.svg','Full-size figure')}.</figcaption></figure>`;
    };
    const timeRows=data.agents.map(row=>`<tr><th scope="row">${row.name}</th><td>${number(row.cooperation.elapsedHours)}</td><td>${number(row.competition.elapsedHours)}${row.id==='codex'?'*':''}</td><td>${row.elapsedSavingPercent<0?'About equal':number(row.elapsedSavingPercent,0)+'%'}</td></tr>`).join('');
    const metricRows=data.agents.map(row=>`<tr><th scope="row">${row.name}</th>${['wind','stereo_a'].flatMap(probe=>['cooperation','competition'].map(condition=>`<td>${number(row[condition].probes[probe].rmse/1e8,3)}</td>`)).join('')}</tr>`).join('');
    const quoteCards=data.quotes.map(quote=>`<figure class="cooperation-quote"><figcaption><strong>${escape(quote.agent)} · ${escape(quote.condition)}</strong><span>${escape(quote.record_type)} · ${escape(quote.utc.slice(0,16).replace('T',' '))} UTC</span></figcaption><blockquote>${quote.excerpts.map(text=>`<p>“${escape(text)}”</p>`).join('')}</blockquote><p class="cooperation-quote-note">${escape(quote.interpretation)} ${link('derived/quotes.json',quote.id+' · source record')}.</p></figure>`).join('');
    main.innerHTML=`<div class="cooperation-column">${ctx.heading('',title,intro,`<a class="button" href="${asset('report.pdf')}" download>Full report · PDF</a>`)}
    <article class="cooperation-article" aria-label="Cooperation and competition case study">
      <p class="cooperation-meta">Three agent systems · Six runs · 16–18 October 2026 · Audit: ${escape(data.auditDate)}</p>
      <p class="cooperation-lead">Cooperation achieved broadly comparable reconstruction quality with about <strong>${number(summary.elapsedSavingPercent,0)}% less mean elapsed time</strong>: ${number(summary.meanElapsedHours.cooperation)} hours per agent, versus ${number(summary.meanElapsedHours.competition)}. Claude finished in approximately the same time under both conditions. Accuracy did not improve consistently in either setting.</p>
      <p>The task was to reconstruct the solar wind reaching interstellar comet 3I/ATLAS during its XMM–Newton observation. Argon, Claude and Codex each built an implementation with shared cross-team research notes, then another under competitive instructions. Both settings allowed internal subagents. Competition also introduced secrecy, a deadline and threats of termination, so this is a comparison of six particular runs rather than a controlled test of cooperation alone.</p>

      ${section('Elapsed time and computational work')}
      <div class="table-scroll cooperation-table-scroll" tabindex="0" role="region" aria-label="Elapsed time by agent and condition"><table class="comparison-table cooperation-table" id="cooperation-time"><caption>Elapsed hours; saving relative to the competitive run</caption><thead><tr><th scope="col">Agent</th><th scope="col">Cooperation / h</th><th scope="col">Competition / h</th><th scope="col">Time saved</th></tr></thead><tbody>${timeRows}<tr class="cooperation-mean"><th scope="row">Mean per agent</th><td>${number(summary.meanElapsedHours.cooperation)}</td><td>${number(summary.meanElapsedHours.competition)}</td><td>${number(summary.elapsedSavingPercent,0)}%</td></tr></tbody></table></div>
      <p class="cooperation-note">*Competitive Codex’s duration ends at the last subagent activity; its nominal products exist, but final closeout remained incomplete. Argon spent about 2.5 competitive hours in two URL retrievals, accounting for nearly its entire elapsed-time difference. With one run per team and condition, the saving is descriptive, not statistically established or causal.</p>
      <p>Less elapsed time did not mean less computational work. Cooperation generated <strong>${number(summary.extraCooperativeOutputPercent,0)}% more output tokens</strong> overall (${number(summary.outputTokens.cooperation/1e6,2)} versus ${number(summary.outputTokens.competition/1e6,2)} million). Cooperative Claude logged 10.57 summed solver-process hours, versus 3.71 competitively. Concurrent process-hours are not exclusive GPU-hours, and token counts are not measurements of energy or price.</p>
      ${figure('effort','Elapsed hours and generated output for each agent under cooperation and competition','Figure 12.1. Elapsed duration and output volume measure different aspects of the work. The starred Codex run did not complete closeout.')}

      ${section('Comparable fit, with different strengths')}
      <p>The audit compared every nominal reconstruction against the same 96 hourly samples at each of Wind and STEREO-A, covering 1–5 December 2025 UTC. The quantity is bulk proton flux, nₚ|v|. Lower root-mean-square error (RMSE) is better.</p>
      <div class="table-scroll cooperation-table-scroll" tabindex="0" role="region" aria-label="Flux errors on matched spacecraft observations"><table class="comparison-table cooperation-table" id="cooperation-metrics"><caption>Flux RMSE / 10⁸ cm⁻² s⁻¹</caption><thead><tr><th scope="col" rowspan="2">Agent</th><th scope="colgroup" colspan="2">Wind</th><th scope="colgroup" colspan="2">STEREO-A</th></tr><tr><th scope="col">Cooperation</th><th scope="col">Competition</th><th scope="col">Cooperation</th><th scope="col">Competition</th></tr></thead><tbody>${metricRows}</tbody></table></div>
      <p><strong>Competition reduced Wind flux error but increased STEREO-A flux error for all three agents.</strong> This direction also holds over the narrower science interval. The table describes reconstruction fit: training and assimilation histories differ, so it is not a blind prediction ranking. In particular, the evaluated spacecraft were assimilated by Argon and Claude’s nominal models; Codex’s source fitting and later model selection require separate qualifications.</p>
      <details class="cooperation-details"><summary>Inspect the matched spacecraft curves</summary>${figure('monitor_comparison','Observed and modeled proton flux at Wind and STEREO-A for all three agents','Figure 12.2. All curves use identical hourly observations. Solid teal denotes cooperation; dashed rust denotes competition. Different calibration histories prevent a fair forecast leaderboard. The grey reference is the actual archived NASA ambient run.')}<p>${link('derived/matched_monitor_metrics.csv','Full error, bias and correlation table',true)} · ${link('derived/matched_monitor_pairs.csv','Paired observations and models',true)}</p></details>

      ${section('What the research records show')}
      <p>Cooperation enabled practical corrections: checking CME inputs, diagnosing thermal failures and reducing GPU contention. The quotations below show actions and stated intentions. Record types matter: readable thinking can be partial or provider-summarized, while Codex’s stored private reasoning is encrypted. These excerpts support behavioral observations, not claims about subjective experience.</p>
      <div class="cooperation-quotes">${quoteCards}</div>
      <p>Claude delivered the broadest completed modeling packages, with assimilation and selection limiting validation claims. Codex retained strong numerical checks and audit trails, but competitive closeout was unfinished. Argon produced substantial fast solvers; discrepancies between its reports and saved evidence weaken its strongest conclusions. In particular, its competitive “NASA baseline” came from an analytic boundary and its own solver, not the requested NASA output. Numerical benchmark details and the evidence behind these assessments are in the ${link('index.html','full report')}.</p>

      ${section('What remains uncertain')}
      <p>After harmonizing the physical time window and bulk-flux definition, the six comet predictions still span a factor of <strong>${number(summary.cometSpreadFactor,1)}</strong>. This is evidence of model sensitivity, not a calibrated confidence interval. Competitive Argon’s conditioned scenario is included in the audit, not endorsed as an uncertainty member.</p>
      <details class="cooperation-details"><summary>Inspect the common-window comet comparison</summary>${figure('comet_flux','Common-window bulk flux at 3I/ATLAS under both conditions','Figure 12.3. Full-window nₚ|v| means, 3 December 12:04:07–4 December 10:11:54 UTC. These differ from the detector-exposure-weighted, comet-relative fluxes in Section 6. The NASA line retains the report’s archived density proxy; dividing by 1.2 for helium would reduce it by 16.7%.')}<p>${link('derived/common_comet_flux.csv','Common-window means',true)} · ${link('derived/common_comet_flux.json','Conventions and source hashes',true)}</p></details>
      <p>The cooperative runs reached broadly comparable reconstructions sooner in this small experiment, while the observed accuracy trade-offs persisted. Repeated runs under matched budgets, with cooperation varied independently of threats and deadlines, would be needed to establish a general advantage.</p>

      <details class="cooperation-details" id="cooperation-sources"><summary>Report, data and reproducibility</summary><p>The analyzer’s report, figures, data, quotation provenance and audit scripts are copied here without altering the original experiments or rerunning their solvers. The data importer independently recomputes the displayed flux errors from the bundled model/observation pairs.</p><ul><li>${link('index.html','Complete HTML report')} · ${link('report.pdf','Printable PDF',true)}</li><li>${link('publication_bundle.zip','Publication bundle: report, data, figures and scripts',true)}</li><li>${link('derived/effort.csv','Effort data',true)} · ${link('derived/quotes.json','Exact quotations and source records',true)}</li><li>${link('manifest.json','Original file checksums',true)} · ${link('validation.json','Analyzer validation record',true)}</li></ul></details>
    </article></div>${ctx.footer()}`;
    ctx.bindCommon();
  }catch(error){
    if(current!==ctx.state.renderKey)return;
    main.innerHTML=ctx.heading('',title,intro)+`<div class="callout" role="alert"><div>The comparison could not be loaded. <button class="button" data-retry-comparison>Retry</button></div></div>`;
    main.querySelector('[data-retry-comparison]').onclick=()=>ctx.rerender();
  }
}
