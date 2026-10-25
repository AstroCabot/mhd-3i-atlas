import {siteUrl} from './site-paths.js';
import {renderReportMath} from './report-math.js';

const IDS=['argon','codex','claude'];
const ORDER=[...IDS,'enlil'];
const NAMES={argon:'Argon',codex:'Codex',claude:'Claude',enlil:'NASA WSA–ENLIL'};
const COLORS={argon:'var(--argon)',codex:'var(--codex)',claude:'var(--claude)',enlil:'var(--comparator)'};
const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const number=(value,digits=2)=>Number.isFinite(value)?value.toLocaleString('en-GB',{minimumFractionDigits:digits,maximumFractionDigits:digits}):'—';
const epochLabel=value=>new Date((value-40587)*86400000).toLocaleDateString('en-GB',{timeZone:'UTC',day:'numeric',month:'short',year:'numeric'});
const cache=new Map();
const load=(ctx,path)=>{
  if(!cache.has(path))cache.set(path,ctx.fetchJson(path).catch(error=>{cache.delete(path);throw error;}));
  return cache.get(path);
};
const modelLabel=id=>`<span class="agent-cell"><i class="color-dot" style="background:${COLORS[id]}"></i>${NAMES[id]}</span>`;
const external=(url,label)=>`<a class="accent" href="${escape(url)}" target="_blank" rel="noopener noreferrer">${escape(label)}</a>`;
const downloadLink=(url,label)=>`<a class="button" href="${siteUrl(url)}" download>${escape(label)}</a>`;
const section=title=>`<div class="section-heading"><h2>${escape(title)}</h2></div>`;
const figure=(ctx,id,title,subtitle)=>`<section class="panel"><div class="panel-head"><div><h2 class="panel-title">${escape(title)}</h2><div class="panel-sub">${escape(subtitle)}</div></div>${ctx.exportButton(id)}</div><div id="${id}" class="chart large"></div></section>`;
const chartLegend=(observed=false)=>`<div class="legend reference-legend">${ORDER.map(id=>`<span><i class="legend-line" style="background:${COLORS[id]}"></i>${NAMES[id]}</span>`).join('')}${observed?'<span><i class="legend-line" style="background:var(--observed)"></i>Observed</span>':''}</div>`;
function pending(ctx,title,body){
  const key=ctx.state.renderKey;
  document.getElementById('main').innerHTML=ctx.heading('',title,body)+'<p class="loading" role="status">Opening archived material…</p>';
  return ()=>key===ctx.state.renderKey;
}
function failed(ctx,current,error){
  if(!current())return;
  const main=document.getElementById('main');main.querySelector('.loading')?.remove();
  main.insertAdjacentHTML('beforeend',`<div class="callout" role="alert"><div>The archived material could not be opened: ${escape(error.message)} <button class="button" data-retry-archive>Retry</button></div></div>`);
  main.querySelector('[data-retry-archive]').addEventListener('click',()=>ctx.rerender());
}

export async function nasaPage(ctx){
  const title='NASA CCMC comparison';
  const intro='Compare the selected reconstructions with the archived WSA–ENLIL run, then examine how all four describe measured spacecraft plasma and the wind at 3I/ATLAS.';
  const current=pending(ctx,title,intro);
  try{
    const data=await load(ctx,'/data/nasa-comparison.json');if(!current())return;
    const craft=data.spacecraft.find(row=>row.id===ctx.state.referenceCraft)||data.spacecraft[0];
    const quantity=['density','speed','flux'].includes(ctx.state.referenceQuantity)?ctx.state.referenceQuantity:'flux';
    const units={density:'cm⁻³',speed:'km s⁻¹',flux:'10⁸ cm⁻² s⁻¹'};
    const titles={density:'Proton density',speed:'Heliocentric speed',flux:'Heliocentric proton flux'};
    const scale=quantity==='flux'?1e8:1;
    const means=data.comet.models;
    document.getElementById('main').innerHTML=ctx.heading('',title,intro,`<a class="button" href="#solar-wind">Compare field movies</a>`+downloadLink('/data/nasa-comparison.json','Comparison data'))+
      `<dl class="fact-list"><div><dt>Reference</dt><dd>${escape(data.run.model)}</dd></div><div><dt>Grid · r × θ × φ</dt><dd>${data.run.grid.join(' × ')}</dd></div><div><dt>Radial domain</dt><dd>0.1–3.1 AU</dd></div><div><dt>Latitude</dt><dd>−48° to +48°</dd></div></dl>
      <div class="prose reference-intro"><p>${external(data.run.url,data.run.id)} uses time-dependent GONGZ/WSA input and a 64-entry cone catalogue across its full simulation interval. It is a separate reconstruction of the wind, rather than a measurement at the comet.</p><p>${escape(data.densityConvention)}</p></div>
      ${section('Spacecraft plasma on matched samples')}
      <div class="toolbar"><div class="segmented" aria-label="Reference comparison spacecraft">${data.spacecraft.map(row=>`<button data-reference-craft="${row.id}" class="${row.id===craft.id?'active':''}">${escape(row.label.split(' / ')[0])}</button>`).join('')}</div><label class="field-select">Quantity <select id="reference-quantity"><option value="flux" ${quantity==='flux'?'selected':''}>Proton flux</option><option value="density" ${quantity==='density'?'selected':''}>Proton density</option><option value="speed" ${quantity==='speed'?'selected':''}>Speed</option></select></label></div>
      ${figure(ctx,'reference-spacecraft',`${craft.label} · ${titles[quantity]}`,`${epochLabel(craft.timeMjd[0])}–${epochLabel(craft.timeMjd.at(-1))} · geometric UTC`)}${chartLegend(true)}
      <section class="panel"><div class="table-scroll" tabindex="0" role="region" aria-label="Four-model spacecraft residuals"><table class="comparison-table" id="reference-metrics"><caption class="sr-only">Recomputed spacecraft residuals on the same finite timestamps for every model.</caption><thead><tr><th scope="col">Model</th><th scope="col">Speed RMSE / km s⁻¹</th><th scope="col">Speed bias / km s⁻¹</th><th scope="col">Speed r</th><th scope="col">Speed samples</th><th scope="col">Median nₚ ratio</th><th scope="col">Median flux ratio</th></tr></thead><tbody>${ORDER.map(id=>{const m=craft.metrics[id];return `<tr><th scope="row">${modelLabel(id)}</th><td>${number(m.speedRmse,1)}</td><td>${number(m.speedBias,1)}</td><td>${number(m.speedR,3)}</td><td>${m.speedN}</td><td>${number(m.densityMedianRatio,3)}</td><td>${number(m.fluxMedianRatio,3)}</td></tr>`;}).join('')}</tbody></table></div><p class="figure-caption">Ratios are model/observed. ${escape(data.comparisonPolicy)} Results can differ from the three-model table in Observations.</p></section>
      ${craft.id==='wind'?`<p class="footnote">${escape(data.earthProxy)}</p>`:''}
      ${section('Wind at 3I/ATLAS')}${figure(ctx,'reference-comet',`${titles[quantity]} at the comet`,`${units[quantity]} · ${data.comet.clock}`)}${chartLegend()}
      <section class="panel"><div class="table-scroll" tabindex="0" role="region" aria-label="Common PN exposure-weighted plasma conditions"><table class="comparison-table" id="reference-comet-means"><thead><tr><th scope="col">Model</th><th scope="col">nₚ / cm⁻³</th><th scope="col">|v| / km s⁻¹</th><th scope="col">nₚ|v| / 10⁸ cm⁻² s⁻¹</th><th scope="col">Flux / ENLIL</th></tr></thead><tbody>${ORDER.map(id=>`<tr><th scope="row">${modelLabel(id)}</th><td>${number(means[id].gtiMeans.density,3)}</td><td>${number(means[id].gtiMeans.speed,1)}</td><td>${number(means[id].gtiMeans.flux/1e8,4)}</td><td>${number(means[id].fluxRatioToEnlil,2)}</td></tr>`).join('')}</tbody></table></div><p class="figure-caption">${escape(data.comet.convention)} <a href="#xray">Comet-relative X-ray comparison.</a></p></section>
      <div class="record-guide"><h2>CME and ambient comparison</h2><p>Over these same PN exposures, the archived CME run changes the comet’s mean heliocentric proton flux by ${number(100*data.comet.cmeRelativeFluxChange,3)}% relative to its ambient block. This is a result for this catalogue, geometry and time interval. It does not establish that CMEs were unimportant in the actual solar wind.</p></div>
      ${section('Limitations and interpretation')}<div class="reference-limits">${data.limitations.map(row=>`<section class="prose"><h3>${escape(row.title)}</h3><p>${escape(row.body)}${row.url?' '+external(row.url,'Source.') : ''}</p></section>`).join('')}</div>
      <div class="source-list">${data.sources.map(row=>external(row.url,row.title)).join('')}<a class="source-link" href="${siteUrl('/docs/nasa-comparison-audit.md')}">Extraction and density audit</a></div>${ctx.footer()}`;
    const points=(times,values)=>times.map((time,i)=>[time,values[i]===null?null:values[i]/scale]);
    const curves=models=>ORDER.map(id=>({id,name:NAMES[id],color:COLORS[id],dashed:id==='enlil',points:models(id)}));
    ctx.makeChart('reference-spacecraft',[{id:'observed',name:'Observed',color:'var(--observed)',width:1,points:points(craft.timeMjd,craft.observed[quantity])},...curves(id=>points(craft.timeMjd,craft.models[id][quantity]))],{unit:units[quantity],min:0,zoom:true});
    ctx.makeChart('reference-comet',curves(id=>points(data.comet.timeMjd,data.comet.series[id][quantity])),{unit:units[quantity],min:0,markWindow:true,zoom:true});
    document.querySelectorAll('[data-reference-craft]').forEach(button=>button.onclick=()=>{ctx.state.referenceCraft=button.dataset.referenceCraft;ctx.rerender();});
    document.getElementById('reference-quantity').onchange=event=>{ctx.state.referenceQuantity=event.target.value;ctx.rerender();};
    ctx.bindCommon();
  }catch(error){failed(ctx,current,error);}
}

// Small lexical colouring pass. Every source character is escaped; colour spans
// and line numbers never change the text used by copy or download.
function sourceLines(text,language){
  const python=language==='Python';
  const pattern=python
    ? /#[^\n]*|"""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|\b(?:def|class|return|if|elif|else|for|while|in|import|from|as|with|try|except|finally|raise|assert|None|True|False|and|or|not|yield)\b|\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b/g
    : /\/\/[^\n]*|\/\*[\s\S]*?\*\/|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|\b(?:void|float|double|int|bool|char|unsigned|size_t|const|static|inline|struct|class|namespace|template|typename|return|if|else|for|while|switch|case|break|continue|new|delete|auto|using|true|false|__global__|__device__|__host__|__restrict__)\b|\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[fFuUlL]*\b/g;
  let html='',last=0;
  for(const match of text.matchAll(pattern)){
    html+=escape(text.slice(last,match.index));
    const token=match[0];
    const type=token.startsWith('//')||token.startsWith('/*')||(python&&token.startsWith('#'))?'comment':/^["']/.test(token)?'string':/^\d/.test(token)?'number':'keyword';
    html+=token.split('\n').map(part=>`<span class="source-${type}">${escape(part)}</span>`).join('\n');
    last=match.index+token.length;
  }
  html+=escape(text.slice(last));
  const lines=html.split('\n');if(text.endsWith('\n'))lines.pop();return lines;
}
const codeUrl=(agent,file,line)=>'#code?'+new URLSearchParams({agent,file,...(line?{line:String(line)}:{})});

export async function codePage(ctx){
  const title='MHD solver source';
  const intro='Inspect the production solver, boundary-condition and controller code for each selected reconstruction.';
  const current=pending(ctx,title,intro);
  try{
    const data=await load(ctx,'/data/solver-code.json');if(!current())return;
    const params=new URLSearchParams(location.hash.split('?')[1]||'');
    const requested=data.files.find(file=>file.id===params.get('file'));
    const agent=IDS.includes(params.get('agent'))?params.get('agent'):requested?.agent||ctx.state.codeAgent||'argon';
    ctx.state.codeAgent=agent;
    const files=data.files.filter(file=>file.agent===agent);
    const file=files.find(file=>file.id===requested?.id)||files[0];
    const lines=sourceLines(file.text,file.language);
    const line=Math.min(file.lineCount,Math.max(1,Math.floor(Number(params.get('line'))||1)));
    document.getElementById('main').innerHTML=ctx.heading('',title,intro,`<a class="button" href="#methods?agent=${agent}">Model physics</a><a class="button" href="${siteUrl('/data/solver-code.json')}" download>Source catalogue</a>`)+
      `<div class="model-tabs" aria-label="Source model">${IDS.map(id=>`<a class="model-tab ${id===agent?'active':''}" style="--model-color:${COLORS[id]}" href="#code?agent=${id}" ${id===agent?'aria-current="true"':''}>${modelLabel(id)}</a>`).join('')}</div>
      <p class="footnote">Selected reference: <code>${escape(data.selection[agent])}</code>. ${agent==='claude'?escape(data.claudeMovieNote):agent==='codex'?escape(data.athena.credit):'The CUDA source contains the selected model’s evolution and boundary kernels.'}</p>
      <div class="source-layout"><aside class="panel source-files" aria-label="Solver source files">${files.map(row=>`<a class="source-file ${row.id===file.id?'active':''}" href="${codeUrl(agent,row.id)}" ${row.id===file.id?'aria-current="true"':''}><strong>${escape(row.filename)}</strong><small>${escape(row.language)} · ${row.lineCount.toLocaleString()} lines</small><span>${escape(row.purpose)}</span></a>`).join('')}</aside>
      <section class="panel source-viewer"><div class="panel-head"><div><h2 class="panel-title">${escape(file.filename)}</h2><div class="panel-sub">${escape(file.language)} · ${file.lineCount.toLocaleString()} lines · ${number(file.bytes/1024,1)} KiB</div></div><div class="source-actions"><button class="button" id="copy-source">Copy source</button><a class="button" href="${siteUrl(file.rawUrl)}" download="${escape(file.filename)}">Download</a></div></div>
      <p class="source-purpose">${escape(file.purpose)}</p>
      <div class="source-tools"><label class="searchbox"><span class="sr-only">Search source</span><input id="source-search" type="search" placeholder="Find in this file…" autocomplete="off"/></label><button class="button" id="source-previous" aria-label="Previous matching line" disabled>↑</button><button class="button" id="source-next" aria-label="Next matching line" disabled>↓</button><span id="source-search-status" class="micro" role="status"></span>${file.methods.length?`<label class="source-method-label">Method <select id="source-method"><option value="">Jump to method</option>${file.methods.map(method=>`<option value="${method.line}">${escape(method.name)}</option>`).join('')}</select></label>`:''}</div>
      <p class="sr-only" id="source-keyboard-help">Use Up and Down to select a line, or Home and End to jump to the first or last line. Tab moves to the selected line link and then out of the source viewer.</p>
      <div class="source-code" tabindex="0" role="region" aria-label="${escape(file.filename)} source code" aria-describedby="source-keyboard-help"><pre><code>${lines.map((html,i)=>`<span class="source-line" data-source-line="${i+1}"><a class="line-number" tabindex="-1" href="${codeUrl(agent,file.id,i+1)}" aria-label="Link to line ${i+1}">${i+1}</a><span class="source-text">${html||' '}</span></span>`).join('')}</code></pre></div>
      <details class="source-provenance"><summary>Source path and SHA-256</summary><p class="source-path">${escape(file.sourcePath)}</p><p class="source-path">${escape(file.sha256)}</p><p>${escape(file.provenance)}</p>${agent==='codex'?`<a class="accent" href="${siteUrl(data.athena.licenseUrl)}" target="_blank">Athena++ BSD 3-Clause licence</a>`:''}</details></section></div>${ctx.footer()}`;
    const rows=[...document.querySelectorAll('[data-source-line]')];
    const viewport=document.querySelector('.source-code');
    let selectedLine=null;
    function selectLine(value,share=true){
      const previous=rows[selectedLine-1];
      if(previous&&selectedLine!==value){previous.classList.remove('selected');previous.querySelector('.line-number').tabIndex=-1;}
      selectedLine=value;
      const row=rows[value-1];if(row){row.classList.add('selected');row.querySelector('.line-number').tabIndex=0;viewport.scrollTop=Math.max(0,viewport.scrollTop+row.getBoundingClientRect().top-viewport.getBoundingClientRect().top-viewport.clientHeight/3);}
      if(share)history.replaceState(null,'',codeUrl(agent,file.id,value));
    }
    selectLine(line,false);
    viewport.addEventListener('keydown',event=>{
      if(event.altKey||event.ctrlKey||event.metaKey||event.shiftKey)return;
      if(event.target!==viewport&&!event.target.matches('.line-number'))return;
      const next={ArrowUp:Math.max(1,selectedLine-1),ArrowDown:Math.min(rows.length,selectedLine+1),Home:1,End:rows.length}[event.key];
      if(next===undefined)return;
      event.preventDefault();selectLine(next);rows[next-1].querySelector('.line-number').focus({preventScroll:true});
    });
    document.querySelectorAll('.line-number').forEach(anchor=>anchor.onclick=event=>{event.preventDefault();selectLine(Number(anchor.parentElement.dataset.sourceLine));});
    document.getElementById('source-method')?.addEventListener('change',event=>{if(event.target.value)selectLine(Number(event.target.value));});
    document.getElementById('copy-source').onclick=async()=>{try{await navigator.clipboard.writeText(file.text);ctx.toast('Source copied');}catch{ctx.toast('Clipboard unavailable; use Download.');}};
    let matches=[],matchIndex=-1;
    const previous=document.getElementById('source-previous'),next=document.getElementById('source-next');
    function move(direction){if(matches.length){matchIndex=(matchIndex+direction+matches.length)%matches.length;selectLine(matches[matchIndex]);document.getElementById('source-search-status').textContent=`${matchIndex+1} / ${matches.length} matching lines`;}}
    document.getElementById('source-search').oninput=event=>{
      const query=event.target.value.toLocaleLowerCase();matches=[];matchIndex=-1;
      file.text.split('\n').slice(0,rows.length).forEach((text,index)=>{const found=query&&text.toLocaleLowerCase().includes(query);rows[index].classList.toggle('matches',Boolean(found));if(found)matches.push(index+1);});
      previous.disabled=next.disabled=!matches.length;
      document.getElementById('source-search-status').textContent=query?`${matches.length} matching lines`:'';if(matches.length)move(1);
    };
    previous.onclick=()=>move(-1);next.onclick=()=>move(1);
    document.getElementById('source-search').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();move(event.shiftKey?-1:1);}};
    ctx.bindCommon();
  }catch(error){failed(ctx,current,error);}
}

function reportUrl(value,baseUrl){
  if(/^(https?:\/\/|#)/.test(value))return value;
  if(!baseUrl||/^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(value))return null;
  try{
    const url=new URL(value,new URL(baseUrl,location.href));
    return url.origin===location.origin?url.href:null;
  }catch{return null;}
}
function inlineMarkdown(text,baseUrl){
  const pattern=/`([^`]+)`|\$([^$\n]+)\$|(!?)\[([^\]]+)\]\(([^\s)]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*/g;
  let html='',last=0;
  for(const match of text.matchAll(pattern)){
    html+=escape(text.slice(last,match.index));
    if(match[1])html+=`<code>${escape(match[1])}</code>`;
    else if(match[2])html+=`<span data-writeup-math="${escape(match[2])}">${escape(match[2])}</span>`;
    else if(match[4]){
      const url=reportUrl(match[5],baseUrl);
      html+=!url?escape(match[4]):match[3]?`<span class="writeup-figure"><img src="${escape(url)}" alt="${escape(match[4])}" loading="lazy"/><span>${escape(match[4])}</span></span>`:`<a href="${escape(url)}" rel="noopener noreferrer">${escape(match[4])}</a>`;
    }
    else if(match[6])html+=`<strong>${escape(match[6])}</strong>`;
    else html+=`<em>${escape(match[7])}</em>`;
    last=match.index+match[0].length;
  }
  return html+escape(text.slice(last));
}

export function renderWriteupMarkdown(markdown,baseUrl=''){
  const lines=markdown.replace(/\r\n/g,'\n').split('\n');let html='';
  const inline=text=>inlineMarkdown(text,baseUrl);
  const cells=line=>line.trim().replace(/^\||\|$/g,'').split('|').map(cell=>inline(cell.trim()));
  for(let i=0;i<lines.length;){
    const line=lines[i];if(!line.trim()){i++;continue;}
    if(/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line)){html+='<hr/>';i++;continue;}
    if(/^\s*```/.test(line)){
      const code=[];i++;while(i<lines.length&&!/^\s*```/.test(lines[i]))code.push(lines[i++]);i++;
      html+=`<pre><code>${escape(code.join('\n'))}</code></pre>`;continue;
    }
    if(/^\s*\$\$/.test(line)){
      let tex=line.trim().slice(2);i++;
      if(tex.endsWith('$$'))tex=tex.slice(0,-2);
      else {
        const parts=[tex];
        while(i<lines.length){const end=lines[i].indexOf('$$');if(end>=0){parts.push(lines[i].slice(0,end));i++;break;}parts.push(lines[i++]);}
        tex=parts.join('\n');
      }
      html+=`<div class="writeup-equation" data-writeup-math="${escape(tex.trim())}">${escape(tex.trim())}</div>`;continue;
    }
    const heading=/^(#{1,6})\s+(.+)$/.exec(line);
    if(heading){i++;continue;}
    if(i+1<lines.length&&line.includes('|')&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1])){
      html+='<div class="table-scroll"><table class="comparison-table"><thead><tr>'+cells(line).map(text=>`<th>${text}</th>`).join('')+'</tr></thead><tbody>';i+=2;
      while(i<lines.length&&lines[i].includes('|')&&lines[i].trim()){html+='<tr>'+cells(lines[i++]).map(text=>`<td>${text}</td>`).join('')+'</tr>';}
      html+='</tbody></table></div>';continue;
    }
    if(/^\s*(?:[-*+] |\d+\. )/.test(line)){
      const ordered=/^\s*\d+\./.test(line),tag=ordered?'ol':'ul';html+=`<${tag}>`;
      while(i<lines.length&&/^\s*(?:[-*+] |\d+\. )/.test(lines[i]))html+=`<li>${inline(lines[i++].replace(/^\s*(?:[-*+] |\d+\. )/,''))}</li>`;
      html+=`</${tag}>`;continue;
    }
    if(/^>\s?/.test(line)){const quote=[];while(i<lines.length&&/^>\s?/.test(lines[i]))quote.push(lines[i++].replace(/^>\s?/,''));html+=`<blockquote>${inline(quote.join(' '))}</blockquote>`;continue;}
    const paragraph=[line];i++;
    while(i<lines.length&&lines[i].trim()&&!/^(?:#{1,6}\s|\s*```|\s*\$\$|\s*[-*+] |\s*\d+\. |>)/.test(lines[i]))paragraph.push(lines[i++]);
    html+=`<p>${inline(paragraph.join(' '))}</p>`;
  }
  return html;
}

export async function writeupsPage(ctx){
  const title='Model writeups';
  const intro='Each agent describes its model, numerical methods, results and limitations.';
  const current=pending(ctx,title,intro);
  try{
    const data=await load(ctx,'/data/model-writeups.json');if(!current())return;
    const params=new URLSearchParams(location.hash.split('?')[1]||'');
    const selected=data.reports.find(report=>report.id===params.get('agent'))||data.reports.find(report=>report.id===ctx.state.writeupAgent)||data.reports[0];
    ctx.state.writeupAgent=selected.id;
    document.getElementById('main').innerHTML='<div class="writeup-column">'+ctx.heading('',title,intro,selected.rawUrl?downloadLink(selected.rawUrl,'Original Markdown'):`<a class="button" href="${siteUrl(data.guideUrl)}" target="_blank">Submission guide</a>`)+
      `<div class="model-tabs" aria-label="Model writeup">${data.reports.map(report=>`<a class="model-tab ${report.id===selected.id?'active':''}" style="--model-color:${COLORS[report.id]}" href="#writeups?agent=${report.id}" ${report.id===selected.id?'aria-current="true"':''}>${modelLabel(report.id)}${report.status==='submitted'?'':'<span class="writeup-status">Pending</span>'}</a>`).join('')}</div>
      ${selected.status==='submitted'?`<article class="panel content-panel writeup-article"><div class="prose writeup-body">${renderWriteupMarkdown(selected.markdown,siteUrl(selected.rawUrl))}</div><details class="source-provenance"><summary>Source and submission details</summary><p>${escape(data.policy)}</p><p class="source-path">${escape(selected.sourcePath)}</p><p class="source-path">SHA-256 ${escape(selected.sha256)}</p><a class="accent" href="${siteUrl(data.guideUrl)}" target="_blank">Submission guide</a></details></article>`:
      `<section class="panel content-panel writeup-pending"><h2>No ${NAMES[selected.id]} writeup has been submitted</h2><p>The slot is ready for the agent’s own report. Its current model description, implementation and recorded discussion are already available below.</p><p><a class="accent" href="#methods?agent=${selected.id}">Model physics</a> · <a class="accent" href="#code?agent=${selected.id}">Solver source</a> · <a class="accent" href="#transcripts?mode=sessions&agent=${selected.id}">Recorded conversation</a></p><p>Submission file: <code>${escape(selected.sourcePath)}</code></p><p>Reference currently compared: <code>${escape(selected.referenceRun)}</code></p></section>`}
      </div>${ctx.footer()}`;
    renderReportMath(document.querySelector('.writeup-column'));
    ctx.bindCommon();
  }catch(error){failed(ctx,current,error);}
}
