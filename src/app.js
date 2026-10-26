import { mountSolarPlayers } from './solar-player.js';
import { siteUrl } from './site-paths.js';
import { nasaPage, codePage, writeupsPage } from './research-pages.js';
import { cooperationPage } from './cooperation-page.js';
import { summaryPage } from './summary-page.js';
import { chartColors, chartColor, readPalette } from './theme.js';
const COLORS = {argon:'var(--argon)',codex:'var(--codex)',claude:'var(--claude)',enlil:'var(--comparator)'};
const XRAY_EQUATION = String.raw`F_X \propto \int n_n\,n_p\,f_{q}\,v_{\mathrm{rel}}\,\sigma_{\mathrm{CX}}\,Y_X\,\mathrm{d}V`;
const NAMES = {argon:'Argon',codex:'Codex',claude:'Claude',enlil:'CCMC WSA–ENLIL'};
const IDS = ['argon','codex','claude'];
const MOVIE_IDS = [...IDS,'enlil'];
const icons = {
 orbit:'<circle cx="12" cy="12" r="3"/><ellipse cx="12" cy="12" rx="11" ry="6" transform="rotate(-35 12 12)"/><circle cx="20" cy="5" r="1.4" fill="currentColor"/>',
 grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
 wind:'<path d="M3 8h12a3 3 0 1 0-3-3M2 12h17a3 3 0 1 1-3 3M4 16h5a3 3 0 1 1-3 3"/>',
 check:'<path d="m8 12 3 3 5-6"/><path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6z"/>',
 signal:'<path d="M3 16a13 13 0 0 1 13-13M3 10a7 7 0 0 1 7-7"/><path d="m12 12 8-8M9 9l6 6-5 5a7 7 0 0 1-6-6z"/><circle cx="4" cy="4" r="1"/>',
 chart:'<path d="M3 3v18h18M6 14l4-5 4 3 6-7"/>',
 record:'<path d="M4 4h16v13H9l-5 4zM8 8h8M8 12h5"/>',
 atom:'<ellipse cx="12" cy="12" rx="11" ry="4"/><ellipse cx="12" cy="12" rx="11" ry="4" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="11" ry="4" transform="rotate(120 12 12)"/><circle cx="12" cy="12" r="1"/>',
 cpu:'<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
 arrow:'<path d="M4 12h15m-5-5 5 5-5 5"/>',
 down:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
 expand:'<path d="M8 3H3v5M16 3h5v5M21 16v5h-5M3 16v5h5"/>',
 menu:'<path d="M3 6h18M3 12h18M3 18h18"/>',
 search:'<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
 play:'<path d="m9 5 11 7-11 7z" fill="currentColor" stroke="none"/>',
 pause:'<path d="M8 5h3v14H8zM15 5h3v14h-3z" fill="currentColor" stroke="none"/>',
 moon:'<path d="M20.8 13.2A9 9 0 0 1 10.8 3.2a9 9 0 1 0 10 10z"/>',
 sun:'<circle cx="12" cy="12" r="4"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3M4 4l2 2M18 18l2 2M4 20l2-2M18 6l2-2"/>',
 link:'<path d="M14 3h7v7M21 3 11 13M10 3H3v18h18v-7"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
 layers:'<path d="m12 3 10 5-10 5L2 8zM2 12l10 5 10-5M2 16l10 5 10-5"/>',
 close:'<path d="m5 5 14 14M19 5 5 19"/>',
 copy:'<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>'
};
const ic = (name,size=16) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name]||icons.grid}</svg>`;
const esc = v => String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dot = id => `<i class="color-dot" style="background:${COLORS[id]||'#8a9aa5'}"></i>`;
const tag = (txt,cls='')=>`<span class="badge ${cls}">${txt}</span>`;
const mjdMs = v => (v-40587)*86400000;
const date = (v,full=false) => {
 const d = new Date(typeof v==='number'?mjdMs(v):v);
 return Number.isNaN(+d)?'—':d.toLocaleString('en-GB',{timeZone:'UTC',month:'short',day:'2-digit',...(full?{hour:'2-digit',minute:'2-digit'}:{})});
};
const num = (v,d=2) => typeof v==='number'&&isFinite(v)?v.toLocaleString('en-GB',{maximumFractionDigits:d,minimumFractionDigits:d}):'—';
const fmt = v => v===null||v===undefined?'—':typeof v==='object'?JSON.stringify(v):String(v);
const S = {route:'overview',active:new Set(IDS),charts:[],physics:null,models:null,science:null,transcripts:null,anim:null,frame:806,progress:25/31,playing:!matchMedia('(prefers-reduced-motion: reduce)').matches,animModel:'argon',field:'flux',speed:1,method:'argon',band:false,bench:'sod',craft:'STEREO-A',session:null,chunk:0,search:'',recordMode:'sessions',recordThread:'',role:'all',recordAgent:'all',sessionData:null,notes:null,searchIndexes:new Map(),renderKey:0};
const nav = [ ['overview','grid','Overview','01'], ['solar-wind','wind','Solar wind','02'], ['verification','check','Verification','03'], ['observations','signal','Observations','04'], ['nasa','signal','NASA comparison','05'], ['xray','chart','X-ray comparison','06'], ['transcripts','record','Agent conversations','07'], ['methods','atom','Model physics','08'], ['code','cpu','Solver code','09'], ['writeups','record','Model writeups','10'], ['resources','cpu','Resources & provenance','11'], ['cooperation','record','Cooperation & competition','12'], ['summary','record','Summary','13'] ];
const mobileNavigation=matchMedia('(max-width: 760px)');
function shell(){
 document.getElementById('app').innerHTML=`<aside class="sidebar" id="sidebar"><a class="brand" href="#overview" aria-label="3I/ATLAS model comparison"><div><div class="brand-name">3I/ATLAS</div><div class="brand-sub">SOLAR-WIND MODELS</div></div></a><div class="nav-label">CONTENTS</div><nav aria-label="Main navigation">${nav.map(([id,icon,label,index])=>`<a class="nav-link" href="#${id}" data-nav="${id}"><span class="nav-index">${Number(index)}</span><span>${label}</span></a>`).join('')}</nav><div class="sidebar-bottom"><div class="research-note"><span class="micro">XMM–NEWTON</span><p>0963720201<br>3–4 December 2025</p><span class="source-path">Argon · Codex · Claude</span></div><div class="sidebar-foot">Results: 17 October 2026</div></div></aside><div class="workspace"><header class="topbar"><button class="menu-button" id="menu" aria-label="Open navigation" aria-expanded="false">${ic('menu',19)}</button><div class="breadcrumbs"><strong>3I/ATLAS</strong> <span>/</span> <span id="crumb">Overview</span></div><div class="top-actions"><button id="theme-toggle" class="button theme-toggle" type="button" role="switch" aria-label="Light mode" aria-checked="false"></button></div></header><main class="main" id="main" tabindex="-1"></main></div>`;
 updateThemeToggle();
 document.getElementById('theme-toggle').onclick=()=>setTheme(document.documentElement.dataset.theme==='light'?'dark':'light');
 document.getElementById('menu').setAttribute('aria-controls','sidebar');
 document.getElementById('menu').onclick=()=>{
  const sidebar=document.getElementById('sidebar');
  if(sidebar.classList.contains('open')){closeNav();return;}
  sidebar.classList.add('open');syncNavigation();
  const backdrop=document.createElement('div');backdrop.className='sidebar-backdrop';backdrop.onclick=()=>closeNav();document.body.append(backdrop);
  (sidebar.querySelector('[aria-current=page]')||sidebar.querySelector('a')).focus();
 };
 document.getElementById('sidebar').addEventListener('click',event=>{
  const link=event.target.closest('a[href^="#"]');
  if(link&&mobileNavigation.matches&&location.hash===link.hash&&!event.metaKey&&!event.ctrlKey){
   closeNav(false);document.getElementById('main').focus({preventScroll:true});
  }
 });
 mobileNavigation.addEventListener('change',()=>{closeNav(false);syncNavigation();});
 syncNavigation();
}
function updateThemeToggle(){
 const light=document.documentElement.dataset.theme==='light';
 const button=document.getElementById('theme-toggle');
 button.setAttribute('aria-checked',String(light));
 button.title=`Switch to ${light?'dark':'light'} mode`;
 button.innerHTML=`${ic(light?'sun':'moon',15)}<span>${light?'Light':'Dark'}</span>`;
}
function setTheme(theme){
 const previous=readPalette();
 document.documentElement.dataset.theme=theme;
 try{localStorage.setItem('3i-atlas-theme',theme);}catch{}
 document.querySelector('meta[name="theme-color"]').content=getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();
 updateThemeToggle();
 for(const {chart} of S.charts)chart.setOption(chartColors(chart.getOption(),previous));
}
function syncNavigation(){
 const sidebar=document.getElementById('sidebar');
 const open=mobileNavigation.matches&&sidebar.classList.contains('open');
 const hidden=mobileNavigation.matches&&!open;
 document.querySelector('.workspace').inert=open;
 if(hidden&&sidebar.contains(document.activeElement))document.getElementById('menu').focus();
 sidebar.inert=hidden;
 if(hidden)sidebar.setAttribute('aria-hidden','true');else sidebar.removeAttribute('aria-hidden');
 document.body.classList.toggle('nav-open',open);
 document.getElementById('menu').setAttribute('aria-expanded',String(open));
}
function closeNav(restoreFocus=true){
 const sidebar=document.getElementById('sidebar'),wasOpen=sidebar.classList.contains('open');
 sidebar.classList.remove('open');document.querySelector('.sidebar-backdrop')?.remove();syncNavigation();
 if(wasOpen&&restoreFocus&&mobileNavigation.matches)document.getElementById('menu').focus();
}
function navigationKeys(event){
 const sidebar=document.getElementById('sidebar');
 if(event.key==='Escape'){closeNav();return;}
 if(event.key!=='Tab'||!mobileNavigation.matches||!sidebar.classList.contains('open'))return;
 const links=[...sidebar.querySelectorAll('a[href],button,[tabindex]')].filter(node=>node.tabIndex>=0&&!node.disabled);
 const first=links[0],last=links.at(-1);
 if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
 else if(!event.shiftKey&&(document.activeElement===last||!sidebar.contains(document.activeElement))){event.preventDefault();first.focus();}
}
function heading(kicker,title,body,buttons=''){
 const chapter=Number(nav.find(n=>n[0]===S.route)?.[3]||1);
 return `<div class="page-heading"><div><h1><span class="section-number">${chapter}</span>${title}</h1><p class="intro">${body}</p></div><div class="heading-actions">${buttons||`<button class="button" data-export="dataset">${ic('down',13)} Data</button><a class="button" href="#methods">Model physics</a>`}</div></div>`;
}
function sectionTitle(number,title,right=''){return `<div class="section-heading"><h2><span class="section-number">${number}</span>${title}</h2>${right}</div>`;}
function caption(number,text){return `<div class="figure-caption"><b>Fig. ${number}.</b> ${text}</div>`;}

function filters(){return `<div class="model-filter" aria-label="Models plotted in charts">${IDS.map(id=>`<button class="model-toggle" data-model-toggle="${id}" aria-pressed="${S.active.has(id)}">${dot(id)}${NAMES[id]}</button>`).join('')}</div>`;}
function panelHead(title,sub='',right=''){return `<div class="panel-head"><div><h2 class="panel-title">${title}</h2>${sub?`<div class="panel-sub">${sub}</div>`:''}</div>${right}</div>`;}
function footer(){return `<footer class="page-footer"><span>3I/ATLAS · Comparative solar-wind reconstruction</span><span>17 October 2026 · Times in UTC</span></footer>`;}
function callout(text,green=false){return `<div class="callout ${green?'green':''}">${ic('info',16)}<div>${text}</div></div>`;}
function exportButton(id){return `<button class="button icon ghost" data-chart-export="${id}" aria-label="Download chart as SVG">${ic('down',14)}</button>`;}
function modelData(id){return S.models.models.find(m=>m.id===id)||{};}
function getCometSeries(id,field='incidentFlux'){
 const c=S.science.comet;
 const values=c?.series?.[id]?.[field]||[];
 return (c?.timeMjd||[]).map((t,i)=>[t,values[i]??null]);
}
function fluxMean(id){return S.science.xray.models[id].gtiMeans.incidentFlux;}
function chartBase(opts={}){
 return {backgroundColor:'transparent',animation:false,color:IDS.map(id=>COLORS[id]),textStyle:{fontFamily:'IBM Plex Mono, monospace',fontSize:11,color:'#b5afa3'},grid:{left:65,right:23,top:32,bottom:opts.zoom?66:42},tooltip:{trigger:'axis',backgroundColor:'#24211c',borderColor:'#514a3e',borderWidth:1,textStyle:{color:'#eae5da',fontSize:12},extraCssText:'max-width:min(400px,90vw);box-shadow:0 5px 25px #0005;',confine:true},legend:{show:false},xAxis:{type:'time',boundaryGap:false,axisLine:{lineStyle:{color:'#514a3e'}},axisTick:{show:false},axisLabel:{fontSize:10,color:'#a39b8c',hideOverlap:true,formatter:v=>{const d=new Date(v);return d.toLocaleDateString('en-GB',{timeZone:'UTC',day:'2-digit',month:'short'})+'\n'+d.toISOString().slice(11,16);}},splitLine:{show:false}},yAxis:{type:'value',name:opts.unit||'',nameTextStyle:{fontSize:10,color:'#afa697',align:'left'},nameLocation:'end',nameGap:15,axisLabel:{fontSize:10,color:'#a39b8c'},axisLine:{show:false},axisTick:{show:false},splitLine:{lineStyle:{color:'#3b362e',type:'dashed',opacity:.65}},min:opts.min,max:opts.max},...(opts.zoom?{dataZoom:[{type:'inside'},{type:'slider',height:13,bottom:13,borderColor:'#25343f',backgroundColor:getComputedStyle(document.documentElement).getPropertyValue('--panel').trim(),fillerColor:'#c5a36918',handleStyle:{color:'#687d8d'},textStyle:{fontSize:10,color:'#a39b8c'},showDetail:false}]}:{})};
}
function makeChart(id,series,opts={}){
 const el=document.getElementById(id);if(!el)return;
 const c=window.echarts.init(el,null,{renderer:'svg'});S.charts.push({id,chart:c});
 const base=chartBase(opts);
 if(opts.numericX)base.xAxis={type:'value',name:opts.xUnit||'',nameLocation:'middle',nameGap:24,axisLabel:{fontSize:10,color:'#a39b8c'},axisLine:{lineStyle:{color:'#514a3e'}},axisTick:{show:false},splitLine:{show:false},min:opts.xMin,max:opts.xMax};
 if(opts.logX){base.xAxis.type='log';base.xAxis.logBase=2;}
 if(opts.logY){base.yAxis.type='log';base.yAxis.min=opts.min>0?opts.min:undefined;}
 if(opts.yFormatter)base.yAxis.axisLabel.formatter=opts.yFormatter;
 if(opts.xMin!==undefined&&!opts.numericX)base.xAxis.min=mjdMs(opts.xMin);
 if(opts.xMax!==undefined&&!opts.numericX)base.xAxis.max=mjdMs(opts.xMax);
 const data=series.map((s,i)=>({name:s.name||NAMES[s.id]||s.id,type:s.type||'line',data:s.points.map(p=>[opts.numericX?p[0]:mjdMs(p[0]),...p.slice(1)]),symbol:s.symbol||'none',symbolSize:5,showSymbol:s.type==='scatter',connectNulls:false,smooth:false,lineStyle:{width:s.width||1.7,type:s.lineType||(s.dashed?'dashed':'solid'),opacity:s.opacity??1},itemStyle:{color:s.color||COLORS[s.id]||'#8d9fab'},color:s.color||COLORS[s.id]||'#8d9fab',z:s.z||3,...(s.area?{areaStyle:{opacity:.08}}:{}),...(opts.markWindow&&i===0?{markArea:{silent:true,itemStyle:{color:'#c5a36912'},label:{show:true,color:'#a99b7d',fontSize:10,position:'insideTop',formatter:'XMM / PN WINDOW'},data:[[{xAxis:mjdMs(61012.503)},{xAxis:mjdMs(61013.425)}]]}}:{})}));
 if(opts.band){
  const band=S.science.comet.claudeDesignBand.incidentFlux,times=S.science.comet.timeMjd;
  data.unshift({name:'Claude design lower bound',type:'line',stack:'claude-design',silent:true,symbol:'none',lineStyle:{opacity:0},areaStyle:{opacity:0},data:times.map((t,i)=>[mjdMs(t),band.lower[i]===null?null:band.lower[i]/1e8]),tooltip:{show:false},z:0},{name:'Claude DA-design 16–84%',type:'line',stack:'claude-design',silent:true,symbol:'none',lineStyle:{opacity:0},areaStyle:{color:COLORS.claude,opacity:.12},data:times.map((t,i)=>[mjdMs(t),band.upper[i]===null||band.lower[i]===null?null:(band.upper[i]-band.lower[i])/1e8]),tooltip:{show:false},z:0});
 }
 c.setOption(chartColors({...base,series:data,...(opts.extra||{})}));
 return c;
}
function legend(ids=IDS,extra=''){return `<div class="legend">${ids.map(id=>`<span><i class="legend-line" style="background:${COLORS[id]}"></i>${NAMES[id]}</span>`).join('')}${extra}</div>`;}
function recordLink({mode='sessions',role='all',agent='all',thread='',q=''}={}){
 const params=new URLSearchParams({mode});
 if(role!=='all')params.set('role',role);if(agent!=='all')params.set('agent',agent);
 if(thread)params.set('thread',thread);if(q)params.set('q',q);
 return '#transcripts?'+params.toString();
}
const RECORD_THREADS={cme:{title:'CME input audit',body:'Follow the catalogue interpretation, the correction and the subsequent input checks. These contemporaneous notes include provisional claims; the model comparison identifies the configurations selected for this report.',files:['claude_20261016T2322Z_inputs_cme_sir.md','codex_external_model_20261016T2334Z_nov23_cme_correction.txt','20261016T235338Z_Codex-root_009.txt','20261017T030931Z_Codex-root_019.txt']}};
function recordEntrypoints(){return `<nav class="record-entrypoints" aria-label="Read the research record"><a class="record-entrypoint" href="${recordLink()}">Agent conversations</a><a class="record-entrypoint" href="${recordLink({mode:'notes'})}">Shared research notes</a><a class="record-entrypoint" href="${esc(recordLink({mode:'notes',role:'directed'}))}">Agent-to-agent exchanges</a></nav>`;}
function comparisonMatrix(rows,id,description){return `<div class="table-scroll"><table class="comparison-table comparison-matrix" id="${id}"><caption class="sr-only">${esc(description)}</caption><thead><tr><th scope="col">Quantity / convention</th>${IDS.map(id=>`<th scope="col">${dot(id)} ${NAMES[id]}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr><th scope="row">${esc(row.label)}</th>${IDS.map(id=>`<td class="wrap" data-comparison-model="${id}">${esc(row.values[id])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
function commonResultRows(){
 const quantities=[['Proton density / cm⁻³','density',1,3],['Heliocentric speed / km s⁻¹','speed',1,1],['Incident proton flux / 10⁸ cm⁻² s⁻¹','incidentFlux',1e8,4]];
 const rows=quantities.map(([label,key,scale,digits])=>({label,values:Object.fromEntries(IDS.map(id=>[id,num(S.science.xray.models[id].gtiMeans[key]/scale,digits)]))}));
 rows.push({label:'X-ray / proton-flux Pearson r · eight frames',values:Object.fromEntries(IDS.map(id=>[id,num(S.science.xray.models[id].pearsonR,3)]))});
 rows.push({label:'Explicit CME injection · selected model',values:Object.fromEntries(IDS.map(id=>[id,S.physics.models[id].explicitCmes?'DONKI cones':'Absent']))});
 return rows;
}
function forcingComparison(){const rows=[...S.physics.rows,{label:'Saved field cadence',values:Object.fromEntries(IDS.map(id=>{const m=S.anim.models[id];return [id,(m.nominalCadenceHours<1?`${m.nominalCadenceHours*60} min`:`${m.nominalCadenceHours} h`)+(m.temporalRefinement?' · regenerated solver output':' · original archive')];}))}];return `<section class="panel">${comparisonMatrix(rows,'model-conventions','Selected forcing, numerical grids and available movie surfaces.')}<p class="figure-caption">${esc(S.physics.scope)} <a href="${siteUrl('/docs/scientific-review.md')}">Source audit.</a></p></section>`;}
function overview(){
 document.getElementById('main').innerHTML=heading('','Solar-wind reconstructions at 3I/ATLAS','Argon, Codex and Claude reconstruct the solar wind incident on the comet during XMM–Newton observation 0963720201. The comparison uses the selected final runs, a common arrival-time axis and the same accepted EPIC-pn exposure intervals.')+
 recordEntrypoints()+
 `<dl class="fact-list"><div><dt>Observation</dt><dd>3–4 Dec 2025</dd></div><div><dt>Heliocentric distance</dt><dd>1.873 AU</dd></div><div><dt>Accepted exposure</dt><dd>21.36 ks · 45 GTIs</dd></div><div><dt>Incident flux</dt><dd>${num(Math.min(...IDS.map(fluxMean))/1e8,2)}–${num(Math.max(...IDS.map(fluxMean))/1e8,2)} × 10⁸ cm⁻² s⁻¹</dd></div></dl>
 ${sectionTitle('1–1','Solar-wind structure and incident flux',filters())}<div class="dashboard-grid"><section class="panel">${panelHead('Heliospheric proton flux','J2000 ecliptic projection · geometric UTC',`<select id="overview-model" aria-label="Animation model">${MOVIE_IDS.map(id=>`<option value="${id}" ${id===S.animModel?'selected':''}>${NAMES[id]}</option>`).join('')}</select>`)}${solarCanvas('overview-solar',S.animModel)}<div class="animation-control"><button class="play-button" data-play aria-label="Play solar-wind animation">${ic(S.playing?'pause':'play',14)}</button><input type="range" data-frame min="0" max="1000" value="${Math.round(S.progress*1000)}" aria-label="Solar-wind time"/><span class="time-label" data-frame-time></span></div>${caption('1',`Projected solar-wind field from the selected model. ${S.anim.models.claude.temporalRefinement?'Claude uses verified half-hour solver outputs; Argon, Codex and CCMC interpolate their original archives.':'Display frames interpolate between saved output times.'} The source surface and flux definition remain model-specific. <a href="#solar-wind">Compare all models.</a>`)}</section><section class="panel">${panelHead('Comet-frame incident proton flux','nₚ|vSW − vcomet| · photon-arrival UTC',exportButton('overview-flux'))}<div class="chart" id="overview-flux"></div><div class="figure-legend" data-model-legend>${legend(IDS.filter(id=>S.active.has(id)))}</div>${caption('2','Incident proton flux in units of 10⁸ cm⁻² s⁻¹. Shading marks the EPIC-pn frame window. Exact accepted exposure intervals determine the means in Table 1. <a href="#xray">X-ray comparison.</a>')}</section></div>
 ${sectionTitle('1–2','Common exposure-weighted comparison','<a class="link-button" href="#methods">Forcing, grids and equations →</a>')}<section class="panel">${comparisonMatrix(commonResultRows(),'common-results','Common PN exposure-weighted values for Argon, Codex and Claude.')}<div class="figure-caption"><b>Table 1.</b> Density, speed and incident proton flux are integrated over the same PN good-time intervals on the photon-arrival clock. Pearson r compares the same eight exposure-matched frames. The table retains all three models; curve controls select the plotted series. <a href="#xray">Native and common integration results.</a></div></section>
 ${sectionTitle('1–3','Interpretation and observational limits')}<div class="workspace-grid"><div class="prose"><p>The reconstructions differ in the timing and duration of the stream compression during the XMM observation. Argon’s flux falls through the observation, Claude produces a narrow mid-window flux peak, and Codex predicts a gradual increase. Their common exposure-weighted incident fluxes span ${num(Math.min(...IDS.map(fluxMean))/1e8,2)}–${num(Math.max(...IDS.map(fluxMean))/1e8,2)} × 10⁸ cm⁻² s⁻¹.</p><p>The spacecraft comparisons include measurements used to set the boundary conditions. Held-out tests and numerical verification are documented separately. Charge states, heavy-ion abundance and the neutral coma are additional inputs to an X-ray emission calculation; these runs constrain the upstream proton flow.</p></div><aside class="research-note"><b>Transient forcing</b><p>${esc(S.physics.cmeAnswer)}</p><b>Comparison conventions</b><p>Comet time series use photon-arrival UTC. Spatial fields and spacecraft data use geometric UTC. The saved movies sample different physical surfaces.</p><a href="#resources">Source files and comparison definitions →</a></aside></div>${footer()}`;
 drawOverviewChart();
 startSolar();
 document.getElementById('overview-model').onchange=async e=>{S.animModel=e.target.value;await solarPlayer?.setModel(S.animModel);};
}
function solarCanvas(id,model){return `<div class="canvas-wrap"><svg class="solar-canvas" id="${id}" data-solar="${model}" aria-label="Simulated solar-wind proton flux, ${NAMES[model]}, top-down projected view" role="img"></svg><div class="canvas-label"><strong style="color:${COLORS[model]}">${NAMES[model].toUpperCase()}</strong><small data-plane>Native sampling surface</small></div><div class="canvas-date" data-solar-date></div><div class="colorbar"><div class="bar-title" data-bar-title>PROTON FLUX / cm⁻² s⁻¹</div><div class="gradient"></div><div class="ticks"><span data-bar-min>10⁷</span><span data-bar-mid>10⁸</span><span data-bar-max>10⁹</span></div></div></div>`;}
function solarPage(){
 document.getElementById('main').innerHTML=heading('SIMULATION / SYNCHRONIZED PLAYBACK','Solar-wind evolution','Compare the three reconstructions with CCMC WSA–ENLIL using the same UTC timeline, projection, extent and colour scale. Native sampling and flux definitions are identified below each field.',`<button class="button" data-export="animation">${ic('down',13)} Animation metadata</button>`)+
 `<div class="toolbar"><div class="segmented" aria-label="Animation field"><button data-field="flux" class="${S.field==='flux'?'active':''}">Proton flux</button><button data-field="fluxR2" class="${S.field==='fluxR2'?'active':''}">Flux × r²</button></div><span class="micro">J2000 ECLIPTIC PROJECTION · ±2.4 AU</span></div><section class="solar-comparison" aria-label="Synchronized reconstructions and CCMC benchmark"><div class="shared-controls"><button class="play-button" data-play aria-label="Play synchronized animation">${ic(S.playing?'pause':'play',14)}</button><span class="micro" data-playback-status>Loading fields…</span><span class="time-label" data-frame-time>Loading fields…</span><input type="range" data-frame min="0" max="1000" value="${Math.round(S.progress*1000)}" aria-label="Synchronized solar-wind time"/><select id="play-speed" aria-label="Playback speed"><option value="1">1× playback</option><option value="2" ${S.speed===2?'selected':''}>2× playback</option><option value=".5" ${S.speed===.5?'selected':''}>0.5× playback</option></select></div><div class="solar-grid">${MOVIE_IDS.map(id=>`<section class="panel">${panelHead(`${dot(id)} ${NAMES[id]}`,'',`<div style="display:flex;gap:5px;align-items:center">${tag(id==='enlil'?'CCMC / MHD':id==='codex'?'CT / CPU':'GLM / GPU')}<button class="button icon ghost" data-solar-expand="${id}" aria-label="Expand ${NAMES[id]} field">${ic('expand',13)}</button></div>`)}${solarCanvas(`solar-${id}`,id)}<div class="panel-footer"><span>${id==='argon'?'Comet-latitude cone · projected':id==='claude'?'Ecliptic slice · radial-flux proxy':id==='enlil'?'External benchmark · ecliptic from 3-D output':'Ecliptic slice · total-speed flux'}</span><span class="forcing-label">${id==='enlil'?'Archived 64-cone input catalogue':esc(S.physics.models[id].cmeShortLabel)}</span></div></section>`).join('')}</div></section>
 <p class="orbit-guide">Circular guides mark Mercury (0.387 AU), Venus (0.723 AU), Earth (1.000 AU) and Mars (1.524 AU). They show mean orbital distances; the moving planet markers follow their ephemerides. <a href="https://ssd.jpl.nasa.gov/planets/approx_pos.html" target="_blank" rel="noopener noreferrer">JPL orbital elements.</a></p>
 <div class="record-guide"><h2>CMEs and stream compressions</h2><p>${esc(S.physics.cmeAnswer)} ${esc(S.physics.frontInterpretation)} <a href="${esc(recordLink({mode:'notes',thread:'cme'}))}">Read the agents’ CME input discussion.</a></p><p>${esc(S.physics.samplingNote)} Argon’s surface is a −6.455° cone. Claude and Codex use saved ecliptic slices; CCMC is sampled on the ecliptic from its native 3-D fields. Claude shows nₚvᵣ; the other fields show nₚ|v|. CCMC’s native output cadence is six hours; intermediate display epochs interpolate physical flux.</p><p>Dark regions within a model’s supported domain can contain finite flux below the shared colour floor. Unsupported inner and outer regions retain the separate grey background. Colour saturation is marked by the ≤ and ≥ limits.</p></div><div class="source-list" aria-label="Download field videos"><span class="micro">768 PX · 30 FPS MP4</span>${MOVIE_IDS.flatMap(id=>['flux','contrast'].map(field=>`<a class="source-link" data-video-model="${id}" data-video-field="${field}" href="${siteUrl(S.anim?.models?.[id]?.media?.[field]?.url||`/assets/animation-v2/${id}-${field}.mp4`)}" download>${NAMES[id]} · ${field==='flux'?'proton flux':'flux × r²'}</a>`)).join('')}</div>
 <div class="section-heading"><h2>Solar wind at the comet</h2><div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end">${filters()}<button id="design-band" class="button ${S.band?'active':''}" aria-pressed="${S.band}" style="font-size:9px;padding:6px 9px;min-height:28px">Claude design spread</button></div></div><section class="panel">${panelHead('Comet-frame incident proton flux','Photon-arrival UTC · accepted PN frame window shaded',exportButton('comet-incident'))}<div class="chart large" id="comet-incident"></div><div data-model-legend style="padding:0 22px 18px">${legend(IDS.filter(id=>S.active.has(id)))}</div></section><div class="two-column" style="margin-top:18px"><section class="panel">${panelHead('Proton density','Same time range across models',exportButton('comet-density'))}<div class="chart" id="comet-density"></div></section><section class="panel">${panelHead('Heliocentric bulk speed','Dashed grey: remote-driven ENLIL comparator',exportButton('comet-speed'))}<div class="chart" id="comet-speed"></div></section></div><p class="footnote" style="margin-top:12px">${esc(S.science.comet.bandQualification)} The design spread control affects Claude’s incident-flux chart only. <a class="accent" href="#nasa">Inspect the NASA CCMC comparison and its limitations.</a></p><div class="section-heading"><h2>Stream structure and source products</h2></div><div class="two-column"><section class="panel content-panel"><div class="prose"><h3>Formation of a compression region</h3><p>The rotating boundary launches streams at different speeds. Faster plasma overtakes slower plasma and forms a compressed interaction region. Bright ridges mark enhanced proton flux; structures farther from the Sun reflect earlier boundary conditions.</p><p><strong>Flux × r²</strong> compensates for the r⁻² dilution of a steady radial flow. This display transform makes departures from radial expansion easier to compare.</p></div></section><section class="panel content-panel"><span class="micro">ARCHIVED SIMULATION SLICES</span><ul class="detail-list"><li><strong>Argon · saved baseline movie</strong>160 × 32 × 180; the quantitative comet reference uses the separate 224 × 48 × 240 fine run.</li><li><strong>Codex · selected constrained-transport movie</strong>Uses the selected CT campaign’s native movie output; superseded GLM movies are excluded.</li><li><strong>Claude · 1° reference</strong>Native ecliptic density and radial velocity slices form the displayed flux proxy.</li><li><strong>CCMC · WSA–ENLIL reference</strong>Archived run Jan_Deca_120925_SH_1; 576 × 24 × 90 cells, approximately six-hour 3-D output, with the CME block selected. <a class="accent" href="#nasa">Reference comparison and limitations.</a></li></ul></section></div>${footer()}`;
 document.querySelectorAll('[data-field]').forEach(b=>b.onclick=async()=>{S.field=b.dataset.field;document.querySelectorAll('[data-field]').forEach(el=>el.classList.toggle('active',el===b));await solarPlayer?.setField(S.field==='fluxR2'?'contrast':'flux');});
 document.querySelectorAll('[data-solar-expand]').forEach(b=>b.onclick=()=>b.closest('.panel').requestFullscreen?.().catch(()=>toast('Full-screen view is unavailable')));
 document.getElementById('design-band').onclick=e=>{S.band=!S.band;e.currentTarget.classList.toggle('active',S.band);e.currentTarget.setAttribute('aria-pressed',String(S.band));redrawAnimationCharts();};
 drawSolarCharts();
 startSolar();
}
function drawOverviewChart(){
 makeChart('overview-flux',IDS.filter(id=>S.active.has(id)).map(id=>({id,points:getCometSeries(id).map(([t,v])=>[t,v===null?null:v/1e8])})),{unit:'10⁸ cm⁻² s⁻¹',min:0,max:6,markWindow:true,xMin:61012,xMax:61014.2});
}
function drawSolarCharts(){
 for(const [field,chartId,unit,div] of [['incidentFlux','comet-incident','cm⁻² s⁻¹ × 10⁸',1e8],['density','comet-density','cm⁻³',1],['speed','comet-speed','km s⁻¹',1]]){
  const series=IDS.filter(id=>S.active.has(id)).map(id=>({id,points:getCometSeries(id,field).map(([t,v])=>[t,v===null?null:v/div])}));
  if(field==='speed')series.push({id:'enlil',name:'CCMC ENLIL',color:'#81919e',dashed:true,points:getCometSeries('enlil',field)});
  const limits=S.science.comet.limits[field];
  makeChart(chartId,series,{unit,min:limits[0]/div,max:limits[1]/div,zoom:field==='incidentFlux',markWindow:true,band:field==='incidentFlux'&&S.band&&S.active.has('claude')});
 }
}
function redrawAnimationCharts(){
 const windows=new Map(S.charts.map(({id,chart})=>[id,(chart.getOption().dataZoom||[]).map(({start,end,startValue,endValue})=>({start,end,startValue,endValue}))]));
 S.charts.forEach(c=>c.chart.dispose());S.charts=[];
 if(S.route==='overview')drawOverviewChart();else drawSolarCharts();
 for(const {id,chart} of S.charts)if(windows.get(id)?.length)chart.setOption({dataZoom:windows.get(id)});
 document.querySelectorAll('[data-model-legend]').forEach(el=>el.innerHTML=legend(IDS.filter(id=>S.active.has(id))));
 document.querySelectorAll('[data-model-toggle]').forEach(el=>el.setAttribute('aria-pressed',String(S.active.has(el.dataset.modelToggle))));
}
let solarPlayer=null,solarMountKey=0,solarAbort=null;
async function startSolar(){
 const key=++solarMountKey;
 solarAbort?.abort();solarAbort=new AbortController();
 try{
  const player=await mountSolarPlayers({signal:solarAbort.signal,root:document.getElementById('main'),manifest:S.anim,models:S.route==='overview'?[S.animModel]:MOVIE_IDS,field:S.field==='fluxR2'?'contrast':'flux',playing:S.playing,speed:S.speed,progress:S.progress,onTime:state=>{
   const progress=typeof state==='number'?state:state.progress;
   if(Number.isFinite(progress)){S.progress=progress;S.frame=Math.round(progress*1000);}
  },onState:state=>{S.playing=state.requestedPlaying??state.playing;S.speed=state.speed;}});
  if(key!==solarMountKey){player.destroy();return;}
  solarPlayer=player;S.anim=player.manifest;window.__HELIOS__.player=player;
  document.querySelectorAll('[data-video-model]').forEach(link=>{link.href=siteUrl(S.anim.models[link.dataset.videoModel].media[link.dataset.videoField].url);});
  await player.ready;
 }catch(error){if(key!==solarMountKey)return;document.querySelectorAll('[data-frame-time]').forEach(el=>el.textContent='Field playback unavailable');console.error(error);}
}
function destroySolar(){solarMountKey++;solarAbort?.abort();solarAbort=null;if(solarPlayer){const state=solarPlayer.getState();S.progress=state.progress;S.playing=state.requestedPlaying??state.playing;solarPlayer.destroy();solarPlayer=null;}if(window.__HELIOS__)window.__HELIOS__.player=null;}

function cometPageCharts(){return IDS.filter(id=>S.active.has(id)).map(id=>({id,points:getCometSeries(id)}));}
function xrayPage(){
 const x=S.science.xray||{};
 document.getElementById('main').innerHTML=heading('OBSERVATION / XMM-NEWTON EPIC-pn','X-ray light-curve comparison','Compare the measured EPIC-pn light curve with the comet-incident proton flux integrated over the same exposures. Each curve is normalized by its exposure-weighted mean; the models calculate upstream wind conditions rather than X-ray emission.',`<button class="button" data-export="xray">${ic('down',13)} Export comparison</button>`)+
 `<div class="toolbar">${filters()}<span class="micro">ObsID 0963720201 · 0.2–1.0 keV</span></div><div class="stack"><section class="panel">${panelHead('Exposure-matched variability','Each series divided by its own exposure-weighted mean',exportButton('xray-shape'))}<div class="chart large" id="xray-shape"></div><div style="padding:0 22px 17px">${legend(IDS.filter(id=>S.active.has(id)),'<span><i class="legend-line" style="background:var(--observed)"></i>EPIC-pn ± 1σ</span>')}</div><div class="chart-note">Model means integrate the same accepted PN intervals within each X-ray frame. The time coordinate is photon-arrival UTC; this comparison applies the documented comet–Earth light-time correction.</div></section><section class="panel">${panelHead('Measured EPIC-pn light curve','Background-subtracted EPIC-pn rate; uncertainty retained',exportButton('xray-rate'))}<div class="chart short" id="xray-rate"></div></section></div>
 <div class="section-heading"><h2>Exposure-matched variability statistics</h2><span>PEARSON CORRELATION / EIGHT FRAMES</span></div><section class="panel"><div class="table-scroll"><table class="comparison-table"><thead><tr><th>Model</th><th>Pearson r</th><th>Exposure-matched frames</th><th>Interpretation</th></tr></thead><tbody>${IDS.filter(id=>S.active.has(id)).map(id=>{const m=x.models?.[id]||{};return `<tr><td><span class="agent-cell">${dot(id)}${NAMES[id]}</span></td><td class="strong">${num(m.pearsonR,3)}</td><td>${m.n??m.nFrames??x.observations?.length??'—'}</td><td class="wrap">${(m.pearsonR)<0?'Higher modeled proton flux coincides with lower observed count rate.':'Positive correlation; heavy-ion composition and neutral-coma emission remain unmodeled.'}</td></tr>`;}).join('')}</tbody></table></div></section><div class="section-heading"><h2>Native and common exposure-weighted means</h2></div><section class="panel"><div class="table-scroll"><table class="comparison-table"><thead><tr><th>Model</th><th>Reported native mean</th><th>Common arrival-GTI mean</th><th>Clock / quadrature effect</th></tr></thead><tbody>${IDS.map(id=>{const n=x.models[id].nativeMeanComparison;return `<tr><td><span class="agent-cell">${dot(id)}${NAMES[id]}</span></td><td>${num(n.reportedPnMean/1e8,4)} × 10⁸</td><td>${num(n.exactArrivalPnMean/1e8,4)} × 10⁸</td><td class="wrap">${esc(n.explanation)}</td></tr>`;}).join('')}</tbody></table></div><div class="panel-footer">Incident proton flux in cm⁻² s⁻¹. This application’s common values use native-sample interpolation and exact exposure endpoints.</div></section>${callout('<strong>Emission-model limits.</strong> Converting proton flux to an X-ray count rate requires heavy-ion abundances and charge states, charge-exchange cross sections, the neutral coma and the detector response. The wind was reconstructed without fitting the eight X-ray rates. Their correlation with proton flux is a variability diagnostic with limited statistical power.')}<section class="panel content-panel"><span class="micro">CHARGE-EXCHANGE EMISSION</span><div class="equation" data-tex="${esc(XRAY_EQUATION)}"></div><p class="equation-caption">Here nₙ is the neutral density, nₚ is the proton density, and f_q = n_q/nₚ is the emitting-ion abundance relative to protons, including elemental abundance and charge-state fraction. The emission also depends on relative speed, charge-exchange cross section σ_CX and photon yield Y_X.</p></section>${footer()}`;
 const obs=x.observations||[];
 const ot=obs.map(o=>o.timeMjd??o.mjd);
 const rates=obs.map(o=>o.rate);
 const mean=rates.reduce((a,b)=>a+(b??0),0)/Math.max(1,rates.filter(v=>v!==null).length);
 const observed={id:'observed',name:'EPIC-pn',color:'#d4dee5',symbol:'circle',points:obs.map((o,i)=>[ot[i],x.observedNormalized[i]]),width:1.5};
 const ss=[observed,...IDS.filter(id=>S.active.has(id)).map(id=>{const m=x.models?.[id]||{};return {id,symbol:'circle',points:ot.map((t,i)=>[t,m.normalizedFlux?.[i]??null])};})];
 const ch=makeChart('xray-shape',ss,{unit:'relative to mean',min:0});
 const errors=obs.map((o,i)=>[mjdMs(ot[i]),x.observedNormalized[i],x.observedNormalizedError[i]]);
 addErrorBars(ch,errors,'#d4dee5');
 const cr=makeChart('xray-rate',[{id:'observed',name:'EPIC-pn',color:'#d4dee5',symbol:'circle',points:obs.map((o,i)=>[ot[i],o.rate])}],{unit:'counts s⁻¹',min:0});
 addErrorBars(cr,obs.map((o,i)=>[mjdMs(ot[i]),o.rate,o.error??o.rateError??0]),'#d4dee5');
 renderMath();
}
function addErrorBars(chart,points,color){if(!chart)return;const option=chart.getOption();chart.setOption({series:[...option.series,{name:'1σ uncertainty',type:'custom',silent:true,renderItem:(p,api)=>{const x=api.value(0),y=api.value(1),e=api.value(2);const low=api.coord([x,y-e]),high=api.coord([x,y+e]);return {type:'group',children:[{type:'line',shape:{x1:low[0],y1:low[1],x2:high[0],y2:high[1]},style:{stroke:chartColor(color),lineWidth:1,opacity:.7}},...[-1,1].map(sign=>({type:'line',shape:{x1:low[0]-3,y1:sign===-1?low[1]:high[1],x2:low[0]+3,y2:sign===-1?low[1]:high[1]},style:{stroke:chartColor(color),lineWidth:1,opacity:.7}}))]};},data:points,z:10}]});}
function verificationPage(){
 const b=S.science.benchmarks;if(!b.charts.some(c=>c.id===S.bench))S.bench=b.charts[0].id;const sel=b.charts.find(c=>c.id===S.bench);
 document.getElementById('main').innerHTML=heading('NUMERICS / THEORY & VERIFICATION','Numerical verification','Benchmark profiles test the equations and numerical implementation. Refinement studies measure sensitivity to the recorded grid and timestep changes. Neither test directly measures the wind at the comet.',`<button class="button" data-export="benchmarks">${ic('down',13)} Benchmark data</button>`)+
 `<div class="toolbar"><div class="segmented">${b.charts.map(c=>`<button data-bench="${c.id}" class="${c.id===S.bench?'active':''}">${({'brio-wu':'Brio–Wu shock tube','shock-convergence':'Shock convergence',parker:'Steady radial wind','linear-waves':'Linear MHD waves'})[c.id]||esc(c.title)}</button>`).join('')}</div></div><section class="panel">${panelHead(esc(sel.title),`${esc(sel.yLabel)} · native benchmark configurations`,exportButton('benchmark-main'))}<div class="chart large" id="benchmark-main"></div><div style="padding:0 22px 18px"><div class="legend">${sel.series.map((s,i)=>`<span><i class="legend-line" style="background:${COLORS[s.model]}"></i>${esc(s.label)}</span>`).join('')}</div></div><div class="chart-note">${esc(sel.notes)}</div></section>
 <div class="section-heading"><h2>Benchmark results</h2><span>NATIVE TEST DEFINITIONS RETAINED</span></div><section class="panel"><div class="table-scroll"><table class="comparison-table"><thead><tr><th>Model</th><th>Test</th><th>Metric</th><th>Value</th><th>Qualification</th></tr></thead><tbody>${b.metrics.map(m=>`<tr><td><span class="agent-cell">${dot(m.model)}${NAMES[m.model]}</span></td><td>${esc(m.test)}</td><td>${esc(m.metric)}</td><td class="strong">${typeof m.value==='number'?num(m.value,4):esc(m.value)} <span class="dim">${esc(m.unit)}</span></td><td class="wrap">${esc(m.qualification)}</td></tr>`).join('')}</tbody></table></div></section>
 <div class="section-heading"><h2>Codex numerical controls</h2><span>REGISTERED CRITERIA · RECORDED MESH PAIRS</span></div><section class="panel"><div class="table-scroll"><table class="comparison-table"><thead><tr><th>Control</th><th>Reference → comparison</th><th>Max Δn</th><th>Max Δv</th><th>Max ΔΦ</th><th>Pointwise</th><th>PN exposure</th></tr></thead><tbody>${b.convergence.map(m=>`<tr><td>${esc(m.category)}</td><td style="font-size:8px">${esc(m.left)}<br><span class="dim">→ ${esc(m.right)}</span></td><td>${num(100*m.maximumRelativeDifferences?.n,2)}%</td><td>${num(100*m.maximumRelativeDifferences?.v,2)}%</td><td>${num(100*m.maximumRelativeDifferences?.f_incident,2)}%</td><td>${tag(m.passed?'PASS':'FAIL',m.passed?'green':'amber')}</td><td>${m.exposurePassed===undefined?'—':tag(m.exposurePassed?'PASS':'FAIL',m.exposurePassed?'green':'amber')}</td></tr>`).join('')}</tbody></table></div></section>
 ${callout('<strong>Control criteria.</strong> PASS/FAIL flags apply to the listed configuration pairs and their recorded criteria. Failed Codex controls remain in the table. Each benchmark chart identifies its numerical method and reference solution.')}
 <div class="two-column"><section class="panel content-panel"><span class="micro">ARGON / NATIVE SENSITIVITY</span><h3 style="font-size:14px;font-weight:500">Incident-flux sensitivity</h3><div class="chart short" id="argon-controls"></div><p class="footnote">Changes relative to Argon’s fine reference. Input/physics changes and numerical refinement have different meanings; this is not an uncertainty distribution.</p></section><section class="panel content-panel"><span class="micro">REFINEMENT AND MODEL ERROR</span><div class="prose"><h3>Scope of a refinement test</h3><p>Refinement measures how an observable changes with numerical resolution for a fixed model and input. Coronal-boundary errors, stream-arrival uncertainty and missing ion composition require separate tests.</p><p>The linear-wave test probes smooth-flow order. Shock-tube errors tend toward first order even for a higher-order method. Each plotted error retains its own reference solution.</p></div></section></div>${footer()}`;
 makeChart('benchmark-main',sel.series.map((s,i)=>({id:s.model,name:s.label,points:s.x.map((x,j)=>[x,s.y[j]]),dashed:i>0&&sel.series.slice(0,i).some(q=>q.model===s.model),symbol:sel.logX?'circle':'none'})),{numericX:true,xUnit:sel.xLabel,unit:sel.yLabel,logX:sel.logX,logY:sel.logY});
 const control=(b.nativeConvergence.argon||[]).filter(m=>m.run!=='res_fine_224x48x240');
 barChart('argon-controls',control.map(c=>({name:c.run.replace(/_/g,' '),value:100*c.fractionVsFine})),{horizontal:true,unit:'Δ incident flux (%)',height:300,color:COLORS.argon});
 document.querySelectorAll('[data-bench]').forEach(el=>el.onclick=()=>{S.bench=el.dataset.bench;rerender();});
}
function barChart(id,data,opts={}){
 const el=document.getElementById(id);if(!el)return;const c=echarts.init(el,null,{renderer:'svg'});S.charts.push({id,chart:c});
 const base=chartBase({});c.setOption(chartColors({...base,grid:{left:opts.horizontal?175:55,right:30,top:10,bottom:35},xAxis:opts.horizontal?{type:'value',axisLabel:{fontSize:10,color:'#7b8f9e'},splitLine:{lineStyle:{color:'#3b362e',type:'dashed'}},name:opts.unit||'',nameTextStyle:{fontSize:10,color:'#7b8f9e'},nameLocation:'middle',nameGap:25}:{type:'category',data:data.map(d=>d.name),axisLabel:{fontSize:11,color:'#91a1ae'},axisLine:{lineStyle:{color:'#514a3e'}}},yAxis:opts.horizontal?{type:'category',data:data.map(d=>d.name),axisLabel:{fontSize:10,color:'#91a1ae',width:155,overflow:'truncate'},axisLine:{show:false},axisTick:{show:false},inverse:true}:{type:'value',splitLine:{lineStyle:{color:'#3b362e',type:'dashed'}},axisLabel:{fontSize:10,color:'#7b8f9e'}},series:[{type:'bar',barMaxWidth:20,data:data.map(d=>({value:d.value,itemStyle:{color:d.color||opts.color||'#b4f57a',opacity:.8,borderRadius:2}}))}],tooltip:{trigger:'item',confine:true,backgroundColor:'#24211c',borderColor:'#514a3e',textStyle:{color:'#eae5da',fontSize:12}}}));return c;
}
function observationsPage(){
 const v=S.science.validation;const craft=v.spacecraft.find(c=>c.id===S.craft)||v.spacecraft[0];S.craft=craft.id;
 const remote=v.remote;const cor=remote.coronalReplication;
 document.getElementById('main').innerHTML=heading('OBSERVATIONS / CORONA TO SPACECRAFT','Spacecraft and coronal constraints','Magnetograms constrain the coronal boundary; spacecraft measure the propagating plasma. The plots compare reconstructed speed, density and proton flux with spacecraft measurements over a common interval.',`<button class="button" data-export="validation">${ic('down',13)} Observation data</button>`)+
 `<div class="toolbar"><div class="segmented">${v.spacecraft.map(c=>`<button data-craft="${c.id}" class="${craft.id===c.id?'active':''}">${esc(c.label.split(' / ')[0])}</button>`).join('')}</div>${filters()}</div><section class="panel">${panelHead(esc(craft.label),'Common hourly grid · geometric UTC',exportButton('craft-speed'))}<div class="chart large" id="craft-speed"></div><div style="padding:0 22px 18px">${legend(IDS.filter(id=>S.active.has(id)),'<span><i class="legend-line" style="background:var(--observed)"></i>Observed</span>')}</div></section>
 <div class="two-column" style="margin-top:18px"><section class="panel">${panelHead('Proton density','Matched valid hourly samples',exportButton('craft-density'))}<div class="chart short" id="craft-density"></div></section><section class="panel">${panelHead('Heliocentric proton flux','nₚ|v| · common units',exportButton('craft-flux'))}<div class="chart short" id="craft-flux"></div></section></div><div class="section-heading"><h2>Residuals against ${esc(craft.label.split(' / ')[0])}</h2><span>COMMON DATA & FINITE-PAIR MASKS</span></div><section class="panel"><div class="table-scroll"><table class="comparison-table"><thead><tr><th>Model</th><th>Speed RMSE</th><th>Speed bias</th><th>Speed r</th><th>Median nₚ ratio</th><th>Median flux ratio</th><th>Speed pairs</th></tr></thead><tbody>${IDS.filter(id=>S.active.has(id)).map(id=>{const m=craft.metrics[id]||{};return `<tr><td><span class="agent-cell">${dot(id)}${NAMES[id]}</span></td><td class="strong">${num(m.speedRmse,1)} <span class="dim">km s⁻¹</span></td><td>${num(m.speedBias,1)} <span class="dim">km s⁻¹</span></td><td>${num(m.speedR,3)}</td><td>${num(m.densityMedianRatio,3)}</td><td>${num(m.fluxMedianRatio,3)}</td><td>${m.speedN??'—'}</td></tr>`;}).join('')}</tbody></table></div></section>${callout(`<strong>Calibration assessment.</strong> ${esc(craft.qualification)}`)}
 <div class="section-heading"><h2>Coronal boundary from remote sensing</h2><span>GONG / WSA BOUNDARY INPUTS</span></div><div class="two-column"><section class="panel">${panelHead('WSA inner-boundary speed',`Carrington longitude / latitude · ${date(remote.boundaryMap.timeMjd)} 2025`,exportButton('boundary-map'))}<div class="chart" id="boundary-map"></div><div class="chart-note">${esc(remote.boundaryMap.qualification)}</div></section><section class="panel">${panelHead('Coronal-model comparison','Claude PFSS / SCS / WSA vs archived WSA map',exportButton('coronal-replication'))}<div class="chart" id="coronal-replication"></div><div class="chart-note">${esc(cor.qualification)}</div></section></div>
 <div class="section-heading"><h2>Input roles and limitations</h2></div><section class="panel"><div class="table-scroll"><table class="comparison-table"><thead><tr><th>Evidence</th><th>Role in reconstruction</th><th>Practical limit</th></tr></thead><tbody>${remote.evidence.map(e=>`<tr><td class="wrap strong">${esc(e.input)}</td><td class="wrap">${esc(e.role)}</td><td class="wrap">${esc(e.limit)}</td></tr>`).join('')}</tbody></table></div></section>
 <section class="panel content-panel" style="margin-top:18px"><span class="micro">SPACECRAFT HOLDOUT TESTS</span><div class="prose"><h3>Results from withheld spacecraft</h3><p>Argon’s machine-readable Wind/ACE holdout summary gives a Wind speed RMSE of 95.4 km s⁻¹; its report gives 67.3 km s⁻¹. This discrepancy is recorded under resources and provenance. Claude reports leave-one-out speed-RMSE reductions of about 15%, 24% and 15% for STEREO-A, L1 and Solar Orbiter; its unassimilated MAVEN check does not improve. Codex reports weak STEREO-A timing agreement.</p><p>The holdouts use different configurations and intervals from one another and from the common-window calibration table above. <a class="accent" href="#methods">Model-specific validation →</a></p></div></section>${footer()}`;
 for(const [field,id,unit] of [['speed','craft-speed','km s⁻¹'],['density','craft-density','cm⁻³'],['flux','craft-flux','cm⁻² s⁻¹ × 10⁸']]){
  const div=field==='flux'?1e8:1;
  const arr=[{id:'observed',name:'Observed',color:'#b4c3cf',width:1,opacity:.55,points:craft.timeMjd.map((t,i)=>[t,craft.observed[field][i]===null?null:craft.observed[field][i]/div])},...IDS.filter(id=>S.active.has(id)).map(id=>({id,points:craft.timeMjd.map((t,i)=>[t,craft.models[id]?.[field]?.[i]===null?null:craft.models[id]?.[field]?.[i]/div])}))];
  makeChart(id,arr,{unit,min:0,zoom:field==='speed'});
 }
 heatmap('boundary-map',remote.boundaryMap);
 makeChart('coronal-replication',[{id:'claude',name:'Speed-map correlation',points:cor.timeMjd.map((t,i)=>[t,cor.speedR[i]])}],{unit:'Pearson r',min:.7,max:1});
 document.querySelectorAll('[data-craft]').forEach(el=>el.onclick=()=>{S.craft=el.dataset.craft;rerender();});
}
function heatmap(id,map){
 const el=document.getElementById(id);const c=echarts.init(el,null,{renderer:'svg'});S.charts.push({id,chart:c});
 const data=[];map.latitudeDeg.forEach((lat,j)=>map.longitudeDeg.forEach((lon,i)=>data.push([i,j,map.speed[j]?.[i]??null])));
 c.setOption(chartColors({animation:false,grid:{left:48,right:20,top:15,bottom:62},tooltip:{confine:true,formatter:p=>`Carrington ${map.longitudeDeg[p.value[0]]}°<br>Latitude ${map.latitudeDeg[p.value[1]]}°<br>${num(p.value[2],0)} km s⁻¹`,backgroundColor:'#24211c',borderColor:'#514a3e',textStyle:{color:'#eae5da',fontSize:12}},xAxis:{type:'category',data:map.longitudeDeg,axisLabel:{fontSize:10,color:'#a39b8c',interval:29},splitArea:{show:false},axisLine:{lineStyle:{color:'#514a3e'}},axisTick:{show:false}},yAxis:{type:'category',data:map.latitudeDeg,axisLabel:{fontSize:10,color:'#a39b8c',interval:14},axisLine:{show:false},axisTick:{show:false}},visualMap:{min:200,max:800,orient:'horizontal',left:'center',bottom:10,itemWidth:8,itemHeight:150,text:['800 km/s','200'],textStyle:{color:'#b5afa3',fontSize:10},inRange:{color:['#243e5c','#435184','#957087','#d49a7b','#eed697']},calculable:false},series:[{type:'heatmap',data,progressive:20000,itemStyle:{borderWidth:0},emphasis:{itemStyle:{borderColor:'#eee',borderWidth:1}}}]}));
}
function methodsPage(){
 const m=modelData(S.method);
 document.getElementById('main').innerHTML=heading('MODEL PHYSICS / IMPLEMENTATION NOTES','Model equations and implementation','The three implementations solve ideal magnetohydrodynamics with different coronal boundaries, assimilation methods, thermodynamic closures and magnetic-divergence treatments.',`<button class="button" data-export="models">${ic('down',13)} Model guide</button><a class="button" href="#code?agent=${m.id}">Inspect solver code</a>`)+
 sectionTitle('8–1','Selected forcing and output conventions')+forcingComparison()+
 `<section class="panel content-panel"><div class="prose"><h3>Ideal magnetohydrodynamics</h3>${S.models.sharedPhysics.map(p=>`<p><strong>${esc(p.title)}.</strong> ${esc(p.body)}</p>`).join('')}</div><div class="two-column">${S.models.commonEquations.slice(0,4).map(eq=>`<div><div class="equation" data-tex="${esc(eq.latex)}"></div><p class="equation-caption"><strong>${esc(eq.label)}.</strong> ${esc(eq.explanation)}</p></div>`).join('')}</div></section>
 <div class="model-tabs" aria-label="Model implementation">${IDS.map(id=>`<button class="model-tab ${S.method===id?'active':''}" style="--model-color:${COLORS[id]}" data-method="${id}">${dot(id)}${NAMES[id]}</button>`).join('')}</div><div class="detail-grid"><div class="stack"><section class="panel content-panel"><span class="micro" style="color:${COLORS[m.id]}">${esc(m.subtitle)}</span><div class="prose"><h3>${NAMES[m.id]} / selected implementation</h3><p>${esc(m.summary)}</p>${m.physics.map(p=>`<h3>${esc(p.title)}</h3><p>${esc(p.body)}</p>`).join('')}</div></section><section class="panel content-panel"><span class="micro">EQUATIONS & CLOSURES</span>${m.equations.map(eq=>`<div class="equation" data-tex="${esc(eq.latex)}"></div><p class="equation-caption"><strong>${esc(eq.label)}.</strong> ${esc(eq.explanation)}</p>`).join('')}</section><section class="panel content-panel"><span class="micro">CALIBRATION & VALIDATION</span><div class="prose"><p style="margin-top:14px">${esc(m.calibration.body)}</p>${renderStructured(m.calibration.validation)}${renderStructured(m.calibration.limitations)}</div></section></div><div class="stack"><section class="panel content-panel"><span class="micro">SELECTED RUN</span><p class="source-path" style="color:${COLORS[m.id]};margin-top:12px">${esc(m.selection.reference)}</p><p class="prose">${esc(m.selection.description)}</p><ul class="detail-list">${Object.entries(m.numerics).map(([k,v])=>`<li><strong>${esc(k[0].toUpperCase()+k.slice(1))}</strong>${esc(v)}</li>`).join('')}</ul></section><section class="panel content-panel"><span class="micro">RESULTS AND INTERPRETATION</span><ul class="detail-list">${m.findings.map(v=>`<li>${esc(v)}</li>`).join('')}</ul></section><section class="panel content-panel"><span class="micro" style="color:var(--argon)">REMAINING LIMITATIONS</span><ul class="detail-list">${m.caveats.map(v=>`<li>${esc(v)}</li>`).join('')}</ul></section></div></div>
 <div class="section-heading"><h2>Incident flux and exposure integration</h2></div><section class="panel content-panel">${S.models.commonEquations.slice(4).map(eq=>`<div class="equation" data-tex="${esc(eq.latex)}"></div><p class="equation-caption"><strong>${esc(eq.label)}.</strong> ${esc(eq.explanation)}</p>`).join('')}</section><div class="section-heading"><h2>Source files and methods</h2></div><section class="panel content-panel"><ul class="detail-list">${m.sources.map(s=>`<li><strong>${esc(s.label)}</strong>${s.url&&safeUrl(s.url)?`<a class="accent" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">Primary source ${ic('link',11)}</a>`:`<span class="source-path">${esc(s.path)}</span>`}</li>`).join('')}</ul></section>${footer()}`;
 renderMath();document.querySelectorAll('[data-method]').forEach(el=>el.onclick=()=>{S.method=el.dataset.method;history.replaceState(null,'','#methods?agent='+S.method);rerender();});
}
function renderStructured(v){return Array.isArray(v)?`<ul>${v.map(s=>`<li>${esc(typeof s==='object'?s.body||s.text||JSON.stringify(s):s)}</li>`).join('')}</ul>`:typeof v==='object'?Object.entries(v).map(([k,x])=>`<p><strong>${esc(k)}.</strong> ${esc(x)}</p>`).join(''):`<p>${esc(v)}</p>`;}
function renderMath(){document.querySelectorAll('[data-tex]').forEach(el=>{const raw=el.dataset.tex;const latex=raw.replace(/\\\\/g,'\\');try{if(S.equations?.equations?.[latex]){el.innerHTML=S.equations.equations[latex];return;}katex.render(latex,el,{throwOnError:true,displayMode:true,trust:false,strict:'warn'});}catch(e){el.textContent=latex;el.dataset.mathError=e.message;}});}
const safeUrl = u => /^https?:\/\//i.test(u);
function resourcesPage(){
 const rc=S.models.resourceComparison;const roots=S.transcripts.sessions.filter(s=>!s.parent_id);
 const sources=[...S.models.provenance,...S.science.provenance];const seen=new Set();const uniq=sources.filter(x=>{if(seen.has(x.path))return false;seen.add(x.path);return true;});
 document.getElementById('main').innerHTML=heading('RESOURCES / REPRODUCIBILITY','Resources and provenance','Recorded compute use, session settings and source-file checksums. Workloads, hardware and accounting coverage differ between projects; the table documents those differences for each quantity.',`<button class="button" data-export="provenance">${ic('down',13)} Source manifest</button>`)+
 `<div class="insight-grid">${roots.map(s=>`<section class="panel insight"><span class="micro" style="color:${COLORS[s.agent]}">${NAMES[s.agent]} / RESEARCH SESSION</span><h3>${esc(s.model)}</h3><p>Reasoning: <strong style="color:var(--text)">${esc(s.reasoning_level||'unrecorded')}</strong> · ${s.subagent_count} recorded descendants</p><p class="source-path" style="font-size:8px;margin-top:12px">${esc(s.session_hash)}</p></section>`).join('')}</div><div class="section-heading"><h2>Recorded resource consumption</h2><span>UNKNOWN VALUES ARE SHOWN AS —</span></div><section class="panel"><div class="table-scroll"><table class="comparison-table"><thead><tr><th>Recorded quantity</th>${IDS.map(id=>`<th>${dot(id)} ${NAMES[id]}</th>`).join('')}<th>Unit</th><th>Scope / interpretation</th></tr></thead><tbody>${rc.rows.map(r=>`<tr><td class="strong">${esc(r.metric)}</td>${IDS.map(id=>`<td>${typeof r[id]==='number'?num(r[id],Math.abs(r[id])>1e5?0:3):esc(fmt(r[id]))}</td>`).join('')}<td>${esc(r.unit)}</td><td class="wrap">${esc(r.scope)}</td></tr>`).join('')}</tbody></table></div></section>${callout(`<strong>Accounting scope.</strong> ${rc.notes.map(esc).join(' ')}`)}
 <div class="section-heading"><h2>Comparison conventions</h2></div><div class="two-column"><section class="panel content-panel"><span class="micro">COMPARISON POLICY</span><ul class="detail-list">${S.models.comparisonPolicy.map(v=>`<li>${esc(v)}</li>`).join('')}</ul></section><section class="panel content-panel"><span class="micro">DATA TRANSFORMS</span><ul class="detail-list">${Object.entries(S.science.homogenization).map(([k,v])=>`<li><strong>${esc(k.replace(/([A-Z])/g,' $1'))}</strong>${esc(typeof v==='object'?JSON.stringify(v):v)}</li>`).join('')}</ul></section></div>
 <div class="section-heading"><h2>Source discrepancies</h2><span>REPORT / DATA / IMPLEMENTATION</span></div><section class="panel content-panel"><ul class="detail-list">${S.models.sourceDiscrepancies.map(d=>`<li><strong style="color:${COLORS[d.model]}">${NAMES[d.model]}</strong>${esc(d.issue)}<p class="source-path">${esc(d.evidence)}</p></li>`).join('')}</ul></section>
 <div class="section-heading"><h2>Source-file checksums</h2><span>${uniq.length} ARCHIVED FILE REFERENCES</span></div><section class="panel source-manifest"><div class="table-scroll" tabindex="0" role="region" aria-label="Scrollable source-file checksums"><table class="comparison-table"><thead><tr><th>Original research path</th><th>Bytes</th><th>SHA-256</th></tr></thead><tbody>${uniq.map(p=>`<tr><td style="font-size:10px">${esc(p.path)}</td><td>${p.bytes?.toLocaleString()??'—'}</td><td style="font-size:9px">${esc(p.sha256||p.hash||'—')}</td></tr>`).join('')}</tbody></table></div></section><div class="source-list"><a class="source-link" href="${siteUrl('/docs/editorial-audit.md')}" target="_blank">Editorial audit</a><a class="source-link" href="${siteUrl('/docs/animation-audit.md')}" target="_blank">Animation methods</a><a class="source-link" href="${siteUrl('/docs/layout-audit.md')}" target="_blank">Layout reference</a><a class="source-link" href="${siteUrl('/docs/notebook-review.md')}" target="_blank">Interface integration review</a><a class="source-link" href="${siteUrl('/docs/scientific-review.md')}" target="_blank">Forcing and CME audit</a><a class="source-link" href="${siteUrl('/docs/shared-note-metadata-audit.md')}" target="_blank">Shared-note attribution audit</a><a class="source-link" href="${siteUrl('/data/science.json')}" download>science.json ${ic('down',10)}</a><a class="source-link" href="${siteUrl('/data/models.json')}" download>models.json ${ic('down',10)}</a><a class="source-link" href="${siteUrl('/data/transcripts.json')}" download>transcript index ${ic('down',10)}</a>${S.anim?.models?.claude?.temporalRefinement?.receipt?`<a class="source-link" href="${siteUrl(S.anim.models.claude.temporalRefinement.receipt)}" download>Claude movie verification ${ic('down',10)}</a>`:''}</div>${footer()}`;
}
function researchPage(){
 const t=S.transcripts;if(!S.session)S.session=t.sessions.find(s=>s.agent==='argon'&&!s.parent_id)?.id;
 const sessions=t.sessions.filter(s=>S.recordAgent==='all'||s.agent===S.recordAgent);
 const selected=t.sessions.find(s=>s.id===S.session)||sessions[0];
 document.getElementById('main').innerHTML=heading('RESEARCH RECORD / SESSION ARCHIVE','Agent conversations and shared notes','Read the recorded conversations, tool activity and reasoning entries where available. Shared notes preserve the files passed between the projects; directed exchanges identify explicitly addressed messages.',`<button class="button" data-export="record">${ic('down',13)} Download ${S.recordMode==='sessions'?'session page':'notes'}</button>`)+
 `<div class="toolbar"><div class="segmented" aria-label="Research record view"><button data-record-mode="sessions" class="${S.recordMode==='sessions'?'active':''}">Agent conversations</button><button data-record-mode="notes" class="${S.recordMode==='notes'&&S.role!=='directed'?'active':''}">Shared notes</button><button data-record-view="exchanges" class="${S.recordMode==='notes'&&S.role==='directed'?'active':''}">Agent-to-agent exchanges · ${t.notes.directed_count}</button></div><select id="record-agent" aria-label="Research agent"><option value="all">All agents</option>${IDS.map(id=>`<option value="${id}" ${S.recordAgent===id?'selected':''}>${NAMES[id]}</option>`).join('')}</select></div>
 <p class="record-summary"><span>${t.stats.main_sessions} main conversations</span><span>${t.stats.subagent_sessions} subagent sessions</span><span>${t.stats.messages.toLocaleString()} recorded entries</span><span>${t.stats.notes} shared notes</span></p>
 ${S.recordMode==='sessions'?`<nav class="reading-path" aria-label="Main agent conversations">${IDS.map(id=>`<a href="${esc(recordLink({agent:id}))}">${NAMES[id]} main conversation</a>`).join('')}<a href="${esc(recordLink({role:'recorded_reasoning',agent:S.recordAgent}))}">Recorded reasoning entries</a></nav>`:`<div class="record-guide"><a href="${esc(recordLink({mode:'notes',thread:'cme'}))}">Case study: CME input audit and correction</a><p>${S.recordThread?esc(RECORD_THREADS[S.recordThread].body):'Read all shared notes chronologically, or select agent-to-agent exchanges to show explicitly addressed messages.'}</p></div>`}
 <div class="toolbar"><form class="searchbox" id="record-search-form" role="search">${ic('search',15)}<input id="record-search" type="search" placeholder="${S.recordMode==='sessions'?'Search the complete selected session…':'Search all shared notes…'}" aria-label="Search research record" value="${esc(S.search)}"/><button class="button ghost" type="submit">Search</button></form><select id="record-role" aria-label="Entry type"><option value="all">All entries</option><option value="assistant" ${S.role==='assistant'?'selected':''}>Assistant dialogue</option><option value="user" ${S.role==='user'?'selected':''}>User messages</option><option value="recorded_reasoning" ${S.role==='recorded_reasoning'?'selected':''}>Recorded reasoning</option><option value="tool" ${S.role==='tool'?'selected':''}>Tool activity</option><option value="directed" ${S.role==='directed'?'selected':''}>Directed exchanges</option></select></div>
 ${S.recordMode==='sessions'?`<div class="transcript-layout"><aside class="panel session-list" aria-label="Research sessions">${sessions.map(s=>`<button class="session-item ${selected.id===s.id?'active':''}" data-session="${s.id}"><strong>${dot(s.agent)}${esc(s.parent_id?'↳ '+s.name:s.name+' / main')}</strong><small>${esc(s.model||'Model not recorded')}</small><small>${s.message_count.toLocaleString()} entries · ${s.reasoning_level||'effort unrecorded'}</small><small class="session-id">${esc(s.session_hash)}</small></button>`).join('')}</aside><section class="panel transcript-content"><div class="session-meta"><span>${esc(selected.model||'Model not recorded')}</span><span>EFFORT: ${esc(selected.reasoning_level||'unknown')}</span><span>${selected.subagent_count} descendants</span><button class="link-button" id="copy-session">${ic('copy',11)} Session ID</button></div><div class="session-meta" style="font-size:8px;display:block;line-height:1.9"><span class="accent">${esc(selected.session_hash)}</span><br>${esc(selected.identification||selected.source)}<br><span class="dim">${esc(selected.availability?.notes||'Text is reproduced as recorded.')}</span></div><div id="transcript-output" class="loading">Opening archived session…</div></section></div>`:`<div id="notes-output" class="stack"><div class="loading">Opening shared notes…</div></div>`}
 ${callout(`<strong>Archive disclosure.</strong> ${esc(t.disclosure)}`)}${footer()}`;
 document.querySelectorAll('[data-record-mode]').forEach(el=>el.onclick=()=>{location.hash=recordLink({mode:el.dataset.recordMode});});
 document.querySelector('[data-record-view=exchanges]').onclick=()=>{location.hash=recordLink({mode:'notes',role:'directed'});};
 if(S.recordMode==='notes')document.querySelectorAll('#record-role option').forEach(option=>{if(!['all','directed'].includes(option.value))option.remove();});
 document.getElementById('record-agent').onchange=e=>{S.recordAgent=e.target.value;S.chunk=0;if(S.recordAgent!=='all'&&selected.agent!==S.recordAgent)S.session=t.sessions.find(s=>s.agent===S.recordAgent&&!s.parent_id).id;rerender();};
 document.getElementById('record-role').onchange=e=>{S.role=e.target.value;S.chunk=0;document.querySelector('[data-record-view=exchanges]').classList.toggle('active',S.recordMode==='notes'&&S.role==='directed');document.querySelector('[data-record-mode=notes]').classList.toggle('active',S.recordMode==='notes'&&S.role!=='directed');loadRecord();};
 document.getElementById('record-search-form').onsubmit=e=>{e.preventDefault();S.search=document.getElementById('record-search').value.trim();S.chunk=0;loadRecord();};
 document.querySelectorAll('[data-session]').forEach(el=>el.onclick=()=>{S.session=el.dataset.session;S.chunk=0;S.search='';S.role='all';rerender();});
 const copy=document.getElementById('copy-session');if(copy)copy.onclick=async()=>{try{await navigator.clipboard.writeText(selected.session_hash);toast('Session ID copied');}catch{toast(selected.session_hash);}};
 loadRecord();
}
function highlight(text,query){if(!query)return esc(text);const q=query.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');return esc(text).replace(new RegExp(q.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),'gi'),m=>`<mark>${m}</mark>`);}
function roleMatch(m){if(S.role==='all')return true;if(S.role==='tool')return m.kind==='tool_call'||m.kind==='tool_result'||m.role==='tool';if(S.role==='recorded_reasoning')return m.kind==='recorded_reasoning';if(S.role==='directed')return m.directed_to?.length>0;return m.role===S.role&&m.kind!== 'tool_call'&&m.kind!=='tool_result'&&m.kind!=='recorded_reasoning';}
function messageHtml(m,searchResult=false){
 const tool=m.role==='tool'||['tool_call','tool_result'].includes(m.kind);
 const text=`<pre>${highlight(m.text,S.search)}</pre>`;
 const body=tool?`<details class="tool-entry" ${S.search?'open':''}><summary>${m.kind==='tool_call'?'Tool input':'Tool output'} · ${m.text.split('\n').length.toLocaleString()} lines</summary>${text}</details>`:text;
 return `<article class="message ${tool?'tool':m.role==='user'?'user':''}" id="message-${esc(m.id)}"><div class="message-head"><span class="message-role">${esc(m.role)}</span><span class="message-type">${esc(m.kind.replace(/_/g,' '))}${m.tool_name?' / '+esc(m.tool_name):''}</span><span class="message-time">${m.timestamp?esc(new Date(m.timestamp).toISOString().replace('T',' ').slice(0,19))+' UTC':'Time unrecorded'}</span></div>${m.directed_to?.length?`<div class="directed">${ic('record',12)} Directed to ${m.directed_to.map(esc).join(', ')}</div>`:''}${body}${searchResult?`<button class="link-button" style="margin-top:10px" data-jump="${m.chunk}" data-jump-message="${esc(m.id)}">Open complete entry ${ic('arrow',12)}</button>`:''}</article>`;
}
let recordLoadKey=0;
function recordRequest(){
 const request=++recordLoadKey,renderKey=S.renderKey;
 return ()=>request===recordLoadKey&&renderKey===S.renderKey;
}
function recordFailure(output,current,retry){
 if(!current())return;
 output.classList.remove('loading');output.removeAttribute('aria-busy');
 output.innerHTML='<div class="empty" role="alert">This archive page could not be loaded. <button class="link-button" data-retry-record>Retry</button></div>';
 output.querySelector('[data-retry-record]').addEventListener('click',retry);
}
async function loadRecord(){
 if(S.recordMode==='notes')return loadNotes();
 const current=recordRequest(),id=S.session,s=S.transcripts.sessions.find(s=>s.id===id);
 const output=document.getElementById('transcript-output');if(!s||!output)return;
 output.setAttribute('aria-busy','true');output.innerHTML='<div class="loading" role="status">Loading archived entries…</div>';
 try{
  if(S.search||S.role!=='all'){
   if(!S.searchIndexes.has(id))S.searchIndexes.set(id,await fetchJson(s.search_url));
   if(!current())return;
   const index=S.searchIndexes.get(id).messages;
   const terms=S.search.toLowerCase().match(/[\p{L}\p{N}_./-]+/gu)||[];
   const matches=index.filter(m=>roleMatch(m)&&terms.every(t=>(m.terms||m.text.toLowerCase()).includes(t)));
   const page=matches.slice(S.chunk*20,(S.chunk+1)*20);S.sessionData={session_id:id,messages:page};
   output.innerHTML=`<div class="session-meta">${matches.length.toLocaleString()} matching entries · excerpts shown</div><div class="transcript-list">${page.length?page.map(m=>messageHtml(m,true)).join(''):'<div class="empty">No matching entries. Try a shorter term or change the entry filter.</div>'}</div>${pager(S.chunk,Math.ceil(matches.length/20),'search')}`;
  }else{
   S.chunk=Math.max(0,Math.min(S.chunk,s.chunks.length-1));
   const data=await fetchJson(s.chunks[S.chunk].url);if(!current())return;S.sessionData=data;
   output.innerHTML=`<div class="transcript-list">${data.messages.map(m=>messageHtml(m)).join('')}</div>${pager(S.chunk,s.chunks.length,'chunks')}`;
  }
  output.classList.remove('loading');output.removeAttribute('aria-busy');bindRecordPaging();
 }catch(error){recordFailure(output,current,loadRecord);}
}
function pager(page,pages,type){return `<div class="pager"><button class="button" data-record-page="${page-1}" ${page<=0?'disabled':''}>← Previous</button><span>Page ${page+1} / ${Math.max(1,pages)} ${type==='search'?'· search results':''}</span><button class="button" data-record-page="${page+1}" ${page>=pages-1?'disabled':''}>Next →</button></div>`;}
function bindRecordPaging(){document.querySelectorAll('[data-record-page]').forEach(el=>el.onclick=()=>{S.chunk=+el.dataset.recordPage;loadRecord();document.querySelector('.transcript-content')?.scrollIntoView({block:'start'});});document.querySelectorAll('[data-jump]').forEach(el=>el.onclick=async()=>{S.chunk=+el.dataset.jump;S.search='';S.role='all';document.getElementById('record-search').value='';document.getElementById('record-role').value='all';await loadRecord();const target=document.getElementById(`message-${el.dataset.jumpMessage}`);const details=target?.querySelector('details');if(details)details.open=true;target?.scrollIntoView({block:'center'});});}
async function loadNotes(){
 const current=recordRequest(),output=document.getElementById('notes-output');if(!output)return;
 output.setAttribute('aria-busy','true');output.innerHTML='<div class="loading" role="status">Opening shared notes…</div>';
 try{
 if(!S.notes)S.notes=await fetchJson(S.transcripts.notes.url);
 if(!current())return;
 const q=S.search.toLowerCase();const thread=RECORD_THREADS[S.recordThread];const all=S.notes.notes.filter(n=>(!thread||thread.files.includes(n.filename))&&(S.recordAgent==='all'||n.author.toLowerCase().includes(S.recordAgent))&&(!q||(n.text+' '+n.filename).toLowerCase().includes(q))&&(S.role!=='directed'||n.directed_to?.length));
 const notes=all.slice(S.chunk*15,(S.chunk+1)*15);
 output.innerHTML=`<div class="micro">${all.length} NOTES · CHRONOLOGICAL ORDER · ORIGINAL TEXT</div>${notes.map(n=>`<article class="panel note-card" id="note-${esc(n.id)}"><div class="note-meta">${dot(IDS.find(id=>n.author.toLowerCase().includes(id)))}<span>${esc(n.author.toUpperCase())}</span><span>${date(n.timestamp,true)} UTC</span>${n.directed_to.length?tag('→ '+n.directed_to.join(', '),'green'):''}</div><h3>${esc(n.filename)}</h3>${n.exchange_excerpt?`<div class="callout green" style="font-size:10px;margin:12px 0">${ic('record',14)}<div>${esc(n.exchange_excerpt)}</div></div>`:''}<pre>${highlight(n.text,S.search)}</pre>${n.references?.length?`<div class="source-list">${n.references.map(r=>`<button class="source-link" data-note-ref="${esc(typeof r==='string'?r:r.id||r.filename)}">${ic('link',10)} ${esc(typeof r==='string'?r:r.filename||r.id)}</button>`).join('')}</div>`:''}</article>`).join('')}${!notes.length?'<div class="empty">No notes match the selected filters.</div>':''}${pager(S.chunk,Math.ceil(all.length/15),'notes')}`;
 document.querySelectorAll('[data-record-page]').forEach(el=>el.onclick=()=>{S.chunk=+el.dataset.recordPage;loadNotes();document.getElementById('record-search-form').scrollIntoView({block:'start'});});
 document.querySelectorAll('[data-note-ref]').forEach(el=>el.onclick=()=>{location.hash=recordLink({mode:'notes',q:el.dataset.noteRef});}); output.removeAttribute('aria-busy');
 }catch(error){recordFailure(output,current,loadNotes);}
}
function toast(message){document.querySelector('.toast')?.remove();const el=document.createElement('div');el.className='toast';el.setAttribute('role','status');el.textContent=message;document.body.append(el);setTimeout(()=>el.remove(),3500);}
function download(data,name,type='application/json'){const blob=typeof data==='string'?new Blob([data],{type}):new Blob([JSON.stringify(data,null,2)],{type});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);toast('Download prepared');}
async function exportData(which){
 try {
 if(['dataset','benchmarks','validation','provenance'].includes(which))await loadFullScience();
 const payload=({dataset:S.science,models:S.models,benchmarks:S.science.benchmarks,validation:S.science.validation,xray:S.science.xray,animation:S.anim||S.science.animation,provenance:{science:S.science.provenance,models:S.models.provenance},record:S.recordMode==='sessions'?S.sessionData:S.notes})[which]||S.science;
 download(payload,`helios-${which}.json`);
 }catch(error){toast(`Could not prepare download: ${error.message}`);}
}
function bindCommon(){
 const chapter=Number(nav.find(n=>n[0]===S.route)?.[3]||1);document.querySelectorAll('.section-heading h2').forEach((h,i)=>{if(!h.querySelector('.section-number')){const span=document.createElement('span');span.className='section-number';span.textContent=`${chapter}–${i+1}`;h.prepend(span);}});
 document.querySelectorAll('[data-model-toggle]').forEach(el=>el.onclick=()=>{const id=el.dataset.modelToggle;if(S.active.has(id)){if(S.active.size===1){toast('Keep at least one model visible');return;}S.active.delete(id);}else S.active.add(id);if(['overview','solar-wind'].includes(S.route))redrawAnimationCharts();else rerender();});
 document.querySelectorAll('[data-export]').forEach(el=>el.onclick=()=>exportData(el.dataset.export));
 document.querySelectorAll('[data-chart-export]').forEach(el=>el.onclick=()=>{const entry=S.charts.find(c=>c.id===el.dataset.chartExport);if(!entry)return;const a=document.createElement('a');a.href=entry.chart.getDataURL({pixelRatio:3,backgroundColor:getComputedStyle(document.documentElement).getPropertyValue('--panel').trim()});a.download=`helios-${entry.id}.svg`;a.click();toast('Chart exported as SVG');});
}
function researchContext(){return {state:S,heading,footer,makeChart,exportButton,fetchJson,bindCommon,toast,rerender};}
async function rerender(){
 const key=++S.renderKey;
 S.charts.forEach(c=>c.chart.dispose());S.charts=[];destroySolar();
 const route=nav.find(x=>x[0]===S.route);
 document.querySelectorAll('[data-nav]').forEach(el=>{el.classList.toggle('active',el.dataset.nav===S.route);if(el.dataset.nav===S.route)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
 document.getElementById('crumb').textContent=route?.[2]||'Overview';document.title=`${route?.[2]||'Overview'} — 3I/ATLAS MHD`;
 if(['verification','observations','resources'].includes(S.route)&&!S.science.provenance){
  document.getElementById('main').innerHTML=heading('',route[2],'Opening comparison data…');
  try{await loadFullScience();}catch(error){if(key===S.renderKey)document.getElementById('main').innerHTML=heading('',route[2],'The comparison could not be loaded.')+`<button class="button" id="retry-page">Retry</button>`;document.getElementById('retry-page')?.addEventListener('click',rerender);return;}
  if(key!==S.renderKey)return;
 }
 ({overview, 'solar-wind':solarPage,verification:verificationPage,observations:observationsPage,xray:xrayPage,transcripts:researchPage,methods:methodsPage,nasa:()=>nasaPage(researchContext()),code:()=>codePage(researchContext()),writeups:()=>writeupsPage(researchContext()),resources:resourcesPage,cooperation:()=>cooperationPage(researchContext()),summary:()=>summaryPage(researchContext())}[S.route]||overview)();bindCommon();
}
function route(){
 const [hash,query='']=location.hash.slice(1).split('?');S.route=nav.some(n=>n[0]===hash)?hash:'overview';
 if(S.route==='methods'){
  const agent=new URLSearchParams(query).get('agent');if(IDS.includes(agent))S.method=agent;
 }
 if(S.route==='transcripts'){
  const params=new URLSearchParams(query);S.recordMode=params.get('mode')==='notes'?'notes':'sessions';
  const roles=S.recordMode==='notes'?['all','directed']:['all','assistant','user','recorded_reasoning','tool','directed'];S.role=roles.includes(params.get('role'))?params.get('role'):'all';
  S.recordAgent=IDS.includes(params.get('agent'))?params.get('agent'):'all';
  S.recordThread=S.recordMode==='notes'&&RECORD_THREADS[params.get('thread')]?params.get('thread'):'';
  S.search=params.get('q')||'';S.chunk=0;
  if(S.recordAgent!=='all')S.session=S.transcripts.sessions.find(session=>session.agent===S.recordAgent&&!session.parent_id)?.id;
 }
 const userNavigation=Boolean(window.__HELIOS__);
 closeNav(false);rerender();window.scrollTo(0,0);
 if(userNavigation)document.getElementById('main').focus({preventScroll:true});
}
const jsonRequests=new Map();
function fetchJson(url){
 if(!jsonRequests.has(url))jsonRequests.set(url,(async()=>{const response=await fetch(siteUrl(url));if(!response.ok)throw new Error(`${url}: ${response.status}`);return response.json();})().catch(error=>{jsonRequests.delete(url);throw error;}));
 return jsonRequests.get(url);
}
async function loadFullScience(){Object.assign(S.science,await fetchJson('/data/science.json'));}
async function init(){try{
 [S.science,S.models,S.transcripts,S.equations,S.physics,S.anim]=await Promise.all(['/data/science-overview.json','/data/models.json','/data/transcripts.json','/data/equations.json','/data/physics-comparison.json','/data/animation-playback.json'].map(fetchJson));
 S.frame=Math.round(S.progress*1000);
 shell();route();window.addEventListener('hashchange',route);window.addEventListener('resize',()=>{syncNavigation();S.charts.forEach(c=>c.chart.resize());solarPlayer?.resize?.();});
 // Fonts swap in without holding the data and fields behind another network round trip.
 document.fonts.ready.then(()=>{S.charts.forEach(c=>c.chart.resize());solarPlayer?.resize?.();});
 document.addEventListener('keydown',navigationKeys);
 window.__HELIOS__={state:S,player:solarPlayer};
 }catch(e){document.getElementById('app').innerHTML=`<div class="error-panel"><div class="eyebrow">Data unavailable</div><h1>The archive could not be opened.</h1><p>Serve the packaged application over HTTP and verify that its datasets are available.</p><pre>${esc(e.message)}</pre><button class="button" onclick="location.reload()">Reload application</button></div>`;console.error(e);}}
init();
