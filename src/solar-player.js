import { siteUrl } from './site-paths.js';
/** Continuous playback of retained scientific fields without a platform video codec.
 * await mountSolarPlayers({root,manifestUrl,models,field,playing,speed,progress,onTime,onState})
 * Returns {ready,manifest,play,pause,setSpeed,setProgress,setField,setModel,getState,destroy}.
 * Two persistent predecoded image layers crossfade at requestAnimationFrame cadence.
 * Claude support uses verified native 30 min solver outputs; the other models
 * interpolate original native samples to that shared support before colour mapping.
 * Intermediate opacity blending adds visual continuity, not native information.
 */
const NS = 'http://www.w3.org/2000/svg';
const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));
const utc = mjd => new Date((mjd - 40587) * 86400000).toISOString().slice(0, 16).replace('T', ' ') + ' UTC';
const icons = {
  play: '<svg viewBox="0 0 20 20" width="14" height="14" aria-hidden="true"><path d="M6 3l11 7-11 7z" fill="currentColor"/></svg>',
  pause: '<svg viewBox="0 0 20 20" width="14" height="14" aria-hidden="true"><path d="M5 3h4v14H5zm7 0h4v14h-4z" fill="currentColor"/></svg>',
};
function el(tag, attrs = {}, text) {
  const node = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}

function placeTrackLabels(panel) {
  const box = panel.svg.getBoundingClientRect();
  const scale = 768 / Math.max(1, Math.min(box.width, box.height));
  const offsets = {earth:[10,-12,'start'],solar_orbiter:[6,-30,'start'],stereo_a:[-6,18,'end'],comet:[9,-9,'start'],mercury:[-8,-10,'end'],venus:[-8,18,'end'],mars:[8,-10,'start']};
  for (const [name,group] of panel.markers) {
    const [dx,dy,anchor] = offsets[name] || [8,-7,'start'];
    const text = group.querySelector('text');
    text.setAttribute('x',String(dx*scale)); text.setAttribute('y',String(dy*scale)); text.setAttribute('text-anchor',anchor);
    if (['earth','solar_orbiter','stereo_a'].includes(name)) {
      let leader=group.querySelector('line');
      if(!leader){leader=el('line',{stroke:'#c2c7bd','stroke-width':'.65','stroke-opacity':'.7'});group.insertBefore(leader,group.firstChild);}
      leader.setAttribute('x1','0');leader.setAttribute('y1','0');leader.setAttribute('x2',String(dx*scale*.8));leader.setAttribute('y2',String(dy*scale*.8));
    }
  }
}

// Portable default: image decoding needs no platform video codec, audio service,
// media process or GPU video acceleration. Native MP4 downloads remain available.
const imageFrames = new Map();
const MAX_DECODED_FRAMES = 48;
let frameUse = 0;
function loadImageSource(image, url, {signal, cancelSource = true} = {}) {
  if(signal?.aborted)return Promise.reject(signal.reason);
  if(image.src===url&&image.complete&&image.naturalWidth>0)return Promise.resolve();
  return new Promise((resolve,reject)=>{
    let settled=false;
    const finish=error=>{if(settled)return;settled=true;clearTimeout(timer);image.removeEventListener('load',loaded);image.removeEventListener('error',failed);signal?.removeEventListener('abort',aborted);error?reject(error):resolve();};
    const loaded=()=>finish();
    const failed=()=>finish(new Error('Retained field image could not be loaded.'));
    const aborted=()=>{finish(signal.reason);if(cancelSource&&image.src===url)image.removeAttribute('src');};
    const timer=setTimeout(()=>{finish(new Error('Retained field image loading timed out.'));if(cancelSource&&image.src===url)image.removeAttribute('src');},15000);
    image.addEventListener('load',loaded,{once:true});image.addEventListener('error',failed,{once:true});
    signal?.addEventListener('abort',aborted,{once:true});
    image.src=url;
    if(image.complete&&image.naturalWidth>0)queueMicrotask(loaded);
  });
}
export async function mountSolarPlayers(options = {}) {
  const root = options.root || document;
  const response = await fetch(siteUrl(options.manifestUrl || '/data/animation-v2.json'),{signal:options.signal});
  if (!response.ok) throw new Error(`Animation manifest ${response.status}`);
  const manifest = await response.json();
  options.signal?.throwIfAborted();
  if(!root.querySelector('[data-solar]')) {
    const state={playing:false,requestedPlaying:false,status:'disposed',field:options.field||'flux',speed:options.speed||1,progress:options.progress||0};
    const idle=()=>{};
    return {manifest,ready:Promise.resolve(),getState:()=>state,play:idle,pause:idle,setSpeed:idle,setProgress:idle,setField:idle,setModel:idle,resize:idle,destroy:idle};
  }
  const allowed = options.models || ['argon','codex','claude'];
  let field = options.field === 'fluxR2' ? 'contrast' : (options.field || 'flux');
  let speed = options.speed || 1;
  let progress = clamp(options.progress ?? 25/31);
  let requestedPlaying = (options.playing ?? true) && !matchMedia('(prefers-reduced-motion: reduce)').matches;
  let playing = false, status = 'loading', loadingError = null;
  let disposed = false, generation = 0, frameRequest = 0, lastTick = 0, lastUi = 0, lastAnimationTime = 0;
  let requestActive = false;
  let transition = null, seekTimer = 0, statusTimer = 0;
  const seekWaiters = [], pendingFrames = new Map();
  const panels = [];
  const controls = [...root.querySelectorAll('[data-play]')];
  const ranges = [...root.querySelectorAll('[data-frame]')];
  const speeds = [...root.querySelectorAll('#play-speed')];
  const signalController = new AbortController();
  const signal = signalController.signal;
  const sequence = model => manifest.models[model].frameSequence;
  // Share only completed images across mounts. Each player owns and can cancel
  // its pending HTTP work, so old seeks cannot occupy the browser's connections.
  function frameImage(url) {
    const cached=imageFrames.get(url);
    if(cached){cached.used=++frameUse;return Promise.resolve(cached);}
    if(pendingFrames.has(url))return pendingFrames.get(url).promise;
    const controller=new AbortController();
    const entry={used:++frameUse,image:new Image(),objectUrl:siteUrl(url),controller};
    entry.promise=loadImageSource(entry.image,entry.objectUrl,{signal:controller.signal}).then(()=>{
      imageFrames.set(url,entry);
      for(const [key] of [...imageFrames].sort((a,b)=>a[1].used-b[1].used)){
        if(imageFrames.size<=MAX_DECODED_FRAMES)break;
        imageFrames.delete(key);
      }
      return entry;
    }).finally(()=>{if(pendingFrames.get(url)===entry)pendingFrames.delete(url);});
    pendingFrames.set(url,entry);
    return entry.promise;
  }
  function cancelPendingFrames(keep = new Set()) {
    for(const [url,entry] of pendingFrames)if(!keep.has(url)){
      pendingFrames.delete(url);entry.controller.abort();
    }
  }
  const formatCadence = hours => hours < 1 ? `${hours * 60} min` : `${hours} h`;
  const cadence = model => formatCadence(manifest.models[model].nominalCadenceHours);
  const cadenceLabel = () => {
    const hours = panels.map(panel=>manifest.models[panel.model].nominalCadenceHours);
    const low = Math.min(...hours), high = Math.max(...hours);
    return low === high ? formatCadence(low) : `${formatCadence(low)}–${formatCadence(high)}`;
  };
  function getState() {return {playing,requestedPlaying,status,field,speed,progress,error:loadingError,engine:'persistent-images'};}
  function onState() {
    if (disposed) return;
    const showPause=requestedPlaying&&status!=='error';
    for (const button of controls) {
      button.innerHTML = icons[showPause ? 'pause' : 'play'];
      button.setAttribute('aria-label',showPause?'Pause solar-wind animation':'Play solar-wind animation');
      button.setAttribute('aria-pressed',String(showPause));
      button.dataset.playbackStatus = status;
    }
    for (const panel of panels) panel.wrap.dataset.playbackStatus = status;
    for (const node of root.querySelectorAll('[data-playback-status-label],span[data-playback-status]')) {
      node.textContent = ({playing:`Playing · native output ${cadenceLabel()}`,loading:'Loading fields…',seeking:'Seeking…',paused:'Paused',stalled:'Loading next field…',error:'Could not load this time. Press play to retry.'})[status] || status;
      node.title = loadingError || (manifest.models.claude.temporalRefinement
        ? '768 px · 30 min common display support. Claude uses verified native 30 min solver outputs; Argon and Codex interpolate their original approximately 3 h and 6 h samples.'
        : '768 px · 30 min interpolated display support; original native samples every approximately 3–6 h.');
    }
    options.onState?.(getState());
  }
  function updateUi(force = false) {
    const mjd = manifest.startMjd + progress*(manifest.endMjd-manifest.startMjd);
    const times = manifest.timeMjd;
    const t = clamp((mjd-times[0])/(times.at(-1)-times[0]))*(times.length-1);
    const lo = Math.min(Math.floor(t),times.length-2), weight=t-lo;
    for (const panel of panels) for (const [name,marker] of panel.markers) {
      const track=manifest.tracks[name];
      const x=track.x[lo]*(1-weight)+track.x[lo+1]*weight;
      const y=track.y[lo]*(1-weight)+track.y[lo+1]*weight;
      marker.setAttribute('transform',`translate(${384+x*160},${384-y*160})`);
    }
    const now=performance.now();
    for (const range of ranges) range.value=String(Math.round(progress*10000)/10);
    if (force || now-lastUi>80) {
      lastUi=now;
      for (const node of root.querySelectorAll('[data-frame-time],[data-solar-date]')) node.textContent=utc(mjd);
      options.onTime?.({mjd,progress,seconds:progress*manifest.durationSeconds});
    }
  }
  function buildOverlay(panel) {
    const svg = panel.svg;
    svg.replaceChildren(); // Once at mount. Subsequent frames update transforms only.
    svg.setAttribute('viewBox', '0 0 768 768');
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    Object.assign(svg.style, {position: 'absolute', inset: '0', width: '100%', height: '100%', zIndex: '2', pointerEvents: 'none'});
    const grid = el('g', {fill: 'none', stroke: '#d4d6cc', 'stroke-opacity': '.24', 'stroke-width': '.8'});
    for (const radius of [.5, 1, 1.5, 2]) grid.append(el('circle', {cx: 384, cy: 384, r: radius * 160, 'stroke-dasharray': '2 5'}));
    grid.append(el('path', {d: 'M0 384H768M384 0V768', 'stroke-opacity': '.13'}));
    svg.append(grid);
    const labels = el('g', {'font-family': 'IBM Plex Mono, monospace', 'font-size': '11', fill: '#c0c4bd', 'paint-order': 'stroke', stroke: '#0c1014', 'stroke-width': '2.5', 'stroke-linejoin': 'round'});
    for (const radius of [1, 2]) labels.append(el('text', {x: 379 + radius * 160, y: 399, 'text-anchor': 'end'}, `${radius} AU`));
    labels.append(el('text', {x: 12, y: 752, 'font-size': '10'}, 'J2000 ecliptic x/y · AU'));
    svg.append(labels, el('circle', {cx: 384, cy: 384, r: 4, fill: '#fff1ad'}));
    const names = {comet: '3I/ATLAS', earth: 'Earth / L1', stereo_a: 'STEREO-A', solar_orbiter: 'SolO', mercury: 'Mercury', venus: 'Venus', mars: 'Mars'};
    for (const [name, label] of Object.entries(names)) {
      if (!manifest.tracks[name]) continue;
      const marker = el('g');
      const comet = name === 'comet';
      const color = comet ? '#f9faf1' : '#c2c7bd';
      marker.append(el('circle', {r: comet ? 4 : 2.6, fill: color, stroke: '#0c1014', 'stroke-width': '1.1'}));
      marker.append(el('text', {x: 8, y: -7, fill: color, 'font-family': 'IBM Plex Mono, monospace', 'font-size': comet ? '12' : '10', 'paint-order': 'stroke', stroke: '#0c1014', 'stroke-width': '2.5', 'stroke-linejoin': 'round'}, label));
      svg.append(marker);
      panel.markers.set(name, marker);
    }
  }
  function updateLabels(panel) {
    const model = manifest.models[panel.model];
    const heading = panel.wrap.querySelector('.canvas-label strong');
    if (heading) {heading.textContent = model.name; heading.style.color = options.modelColors?.[panel.model] || 'var(--text, #e5e3da)';}
    const plane = panel.wrap.querySelector('[data-plane]');
    if (plane) plane.textContent = `${panel.model === 'argon' ? '−6.455° cone' : 'Ecliptic'} · ${model.nativeSliceDimensions.join(' × ')} samples · ${cadence(panel.model)}${model.temporalRefinement ? ' solver output' : ' retained'}`;
    const title = panel.wrap.querySelector('[data-bar-title]');
    if (title) title.textContent = field === 'contrast' ? 'nₚv × r² / cm⁻² s⁻¹ AU²' : `${panel.model === 'claude' ? 'nₚvᵣ' : 'nₚ|v|'} / cm⁻² s⁻¹`;
    const min = panel.wrap.querySelector('[data-bar-min]');
    const mid = panel.wrap.querySelector('[data-bar-mid]');
    const max = panel.wrap.querySelector('[data-bar-max]');
    if (min) min.textContent = '≤10⁷';
    if (mid) mid.textContent = field === 'contrast' ? '1.4×10⁸' : '5.5×10⁸';
    if (max) max.textContent = field === 'contrast' ? '≥2×10⁹' : '≥3×10¹⁰';
    const gradient = panel.wrap.querySelector('.gradient');
    if (gradient) {
      gradient.style.background = `linear-gradient(90deg,${manifest.palette.map(color => `rgb(${color.join(',')})`).join(',')})`;
      gradient.title = 'Colours saturate at both displayed limits. Values below the lower limit use the darkest colour; unsupported pixels use the separate dark-grey background.';
    }
    panel.svg.setAttribute('aria-label', `${model.name} solar-wind ${field === 'contrast' ? 'flux times radius squared' : 'proton flux'}; ${model.nativePlane}; retained ${model.nativeSliceDimensions.join(' by ')} samples`);
  }
  for (const svg of root.querySelectorAll('[data-solar]')) {
    const model=allowed.includes(svg.dataset.solar)?svg.dataset.solar:allowed[0];
    if (!sequence(model)) throw new Error(`Portable field frames missing for ${model}. Run python scripts/build_animation_v2.py --images-only`);
    const wrap=svg.closest('.canvas-wrap')||svg.parentElement;
    Object.assign(wrap.style,{position:'relative',backgroundColor:`rgb(${manifest.background.join(',')})`,backgroundImage:`url("${siteUrl(manifest.models[model].media[field].poster)}")`,backgroundSize:'contain',backgroundPosition:'center',backgroundRepeat:'no-repeat'});
    const panel={svg,wrap,model,markers:new Map(),images:[],lower:null,upper:null,pairKey:null};
    for(let i=0;i<2;i++) {
      const img=document.createElement('img');
      img.alt=''; img.setAttribute('aria-hidden','true'); img.dataset.solarImage=String(i);
      Object.assign(img.style,{position:'absolute',inset:'0',width:'100%',height:'100%',objectFit:'contain',visibility:'hidden',pointerEvents:'none',zIndex:String(i)});
      wrap.insertBefore(img,svg);panel.images.push(img);
    }
    panels.push(panel);buildOverlay(panel);updateLabels(panel);
    const resizeLabels=()=>{
      const box=svg.getBoundingClientRect(),factor=768/Math.max(1,Math.min(box.width,box.height));
      const base=wrap.closest('.solar-triptych')?10:11;
      for(const text of svg.querySelectorAll('text')) {
        if(!text.dataset.originalFontSize)text.dataset.originalFontSize=text.getAttribute('font-size')||text.parentElement.getAttribute('font-size')||'10';
        text.setAttribute('font-size',String(factor*(Number(text.dataset.originalFontSize)>=12?base+1:base)));
      }
    };
    panel.resizeObserver=new ResizeObserver(()=>{resizeLabels();placeTrackLabels(panel);});panel.resizeObserver.observe(wrap);resizeLabels();placeTrackLabels(panel);
    for(const label of wrap.querySelectorAll('.canvas-label,.canvas-date,.colorbar'))label.style.zIndex='3';
  }
  function position() {
    const count=sequence(panels[0].model).frameCount;
    const value=progress*(count-1), lower=Math.min(Math.floor(value),count-2);
    return {lower,upper:lower+1,weight:value-lower};
  }
  function keys(panel,p) {
    const rows=sequence(panel.model).fields[field];
    return [rows[p.lower].url,rows[p.upper].url];
  }
  function showBlend(p) {
    for(const panel of panels) {
      if(!panel.lower||!panel.upper)return;
      panel.lower.style.opacity='1';panel.upper.style.opacity=String(p.weight);
    }
  }
  function prefetch(p) {
    // Fetch the nearest epoch for every model before looking farther ahead.
    for(const offset of [2,3,4,-1]) {
      for(const panel of panels) {
        const rows=sequence(panel.model).fields[field];
        const i=p.lower+offset;
        if(i>=0&&i<rows.length)frameImage(rows[i].url).catch(()=>{});
      }
    }
  }
  function stopTransition() {
    generation++;transition?.abort();clearTimeout(statusTimer);
    cancelAnimationFrame(frameRequest);frameRequest=0;
  }
  async function loadCurrent(nextStatus='stalled') {
    if(disposed)return;
    stopTransition();
    const token=generation;
    transition=new AbortController();
    const currentSignal=transition.signal;
    requestActive=true;playing=false;loadingError=null;
    // Cached interval changes normally finish before the next paint. Show a
    // loading message only when the wait is long enough to be useful.
    if(nextStatus==='stalled'&&status==='playing'){
      statusTimer=setTimeout(()=>{if(!disposed&&token===generation&&requestActive&&requestedPlaying){status='stalled';onState();}},180);
    }else {status=nextStatus;onState();}
    const p=position();
    if(nextStatus!=='stalled')cancelPendingFrames(new Set(panels.flatMap(panel=>keys(panel,p))));
    try {
      const loaded=await Promise.all(panels.map(async panel=>{
        const [loUrl,hiUrl]=keys(panel,p);
        const [lo,hi]=await Promise.all([frameImage(loUrl),frameImage(hiUrl)]);
        return {panel,loUrl,hiUrl,lo,hi};
      }));
      if(disposed||token!==generation)return;
      // Stage one incoming layer behind an opaque decoded layer in every panel.
      // An interrupted transition never clears the last visible field.
      const targets=await Promise.all(loaded.map(async({panel,loUrl,hiUrl,lo,hi})=>{
        const matchingLower=panel.images.find(image=>image.dataset.frameUrl===loUrl&&image.complete&&image.naturalWidth>0);
        const visible=panel.upper&&Number(panel.upper.style.opacity)>=.5?panel.upper:panel.lower;
        const lower=matchingLower||panel.images.find(image=>image!==visible)||panel.images[0];
        const upper=panel.images.find(image=>image!==lower);
        if(visible){
          visible.style.opacity='1';
          if(lower!==visible)lower.style.opacity='0';
        }
        await loadImageSource(lower,lo.objectUrl,{signal:currentSignal,cancelSource:false});
        if(disposed||token!==generation)return;
        lower.dataset.frameUrl=loUrl;
        return {panel,lower,upper,hiUrl,hi};
      }));
      if(disposed||token!==generation)return;
      // Promote the same epoch across all panels before recycling their other
      // layers. Metadata is assigned only after a current-generation load.
      for(const {panel,lower,upper} of targets){
        lower.style.visibility='visible';lower.style.opacity='1';lower.style.zIndex='0';
        upper.style.opacity='0';upper.style.zIndex='1';
        panel.lower=lower;panel.upper=upper;panel.pairKey=null;
      }
      await Promise.all(targets.map(async({upper,hiUrl,hi})=>{
        await loadImageSource(upper,hi.objectUrl,{signal:currentSignal,cancelSource:false});
        if(disposed||token!==generation)return;
        upper.dataset.frameUrl=hiUrl;
      }));
      if(disposed||token!==generation)return;
      for(const {panel,lower,upper} of targets){
        lower.style.visibility=upper.style.visibility='visible';
        panel.pairKey=`${panel.model}:${field}:${p.lower}`;
        panel.wrap.style.backgroundImage='';panel.wrap.dataset.imageReady='true';
        updateLabels(panel);
      }
      clearTimeout(statusTimer);
      requestActive=false;status=requestedPlaying?'playing':'paused';playing=requestedPlaying;lastTick=performance.now();
      showBlend(p);updateUi(true);onState();prefetch(p);scheduleAnimation();
    }catch(error){
      if(disposed||token!==generation)return;
      transition.abort();clearTimeout(statusTimer);cancelPendingFrames();
      requestActive=false;status='error';playing=false;loadingError=error.message;onState();
    }
  }
  function restartCurrent(nextStatus) {
    clearTimeout(seekTimer);seekTimer=0;
    const waiting=seekWaiters.splice(0);
    return loadCurrent(nextStatus).finally(()=>waiting.forEach(resolve=>resolve()));
  }
  function seek(value) {
    if(disposed)return Promise.resolve();
    progress=clamp(value);updateUi(true);stopTransition();
    requestActive=true;playing=false;status='seeking';loadingError=null;onState();
    cancelPendingFrames(new Set(panels.flatMap(panel=>keys(panel,position()))));
    clearTimeout(seekTimer);
    // A drag produces many inputs. Update the control immediately, but combine
    // adjacent inputs before starting HTTP work for the chosen epoch.
    const done=new Promise(resolve=>seekWaiters.push(resolve));
    seekTimer=setTimeout(()=>restartCurrent('seeking'),40);
    return done;
  }
  function advance(now) {
    if(disposed)return;
    if(playing&&!requestActive&&!document.hidden) {
      const candidate=(progress+(now-lastTick)*speed/(manifest.durationSeconds*1000))%1;
      lastTick=now;
      progress=candidate;
      const p=position();
      const current=panels.every(panel=>panel.pairKey===`${panel.model}:${field}:${p.lower}`);
      if(current){showBlend(p);updateUi();}
      else {
        // Freeze the physical clock at this requested epoch until adjacent
        // decoded images are ready; the previous view remains on screen.
        loadCurrent('stalled');
      }
    }else lastTick=now;
  }
  function animate(now) {
    frameRequest=0;
    if(disposed||!playing||document.hidden)return;
    lastAnimationTime=now;advance(now);
    scheduleAnimation();
  }
  function scheduleAnimation(){if(!disposed&&playing&&!document.hidden&&!frameRequest)frameRequest=requestAnimationFrame(animate);}
  // Some remote/headless browsers suppress compositor animation callbacks
  // while the document remains visible. A bounded timer preserves the clock
  // in that case without running a second animation loop during normal RAF.
  const clockFallback=setInterval(()=>{const now=performance.now();if(playing&&!document.hidden&&now-lastAnimationTime>80)advance(now);},33);
  const api={
    manifest,getState,
    play:async()=>{if(disposed)return;requestedPlaying=true;if(status==='error'){await restartCurrent('loading');return;}if(!requestActive){playing=true;status='playing';lastTick=performance.now();scheduleAnimation();}onState();},
    pause:()=>{requestedPlaying=false;playing=false;cancelAnimationFrame(frameRequest);frameRequest=0;if(status==='playing')status='paused';onState();},
    setSpeed:value=>{speed=clamp(Number(value)||1,.25,4);onState();},
    setProgress:seek,
    setField:async value=>{const next=value==='fluxR2'?'contrast':value;if(!['flux','contrast'].includes(next))throw new Error(`Unknown field ${value}`);if(next!==field){field=next;await restartCurrent('loading');}},
    setModel:async(value,index=0)=>{if(!manifest.models[value])throw new Error(`Unknown model ${value}`);if(panels[index]&&panels[index].model!==value){panels[index].model=value;panels[index].svg.dataset.solar=value;await restartCurrent('loading');}},
    resize:()=>{for(const panel of panels)panel.resizeObserver?.unobserve(panel.wrap);for(const panel of panels)panel.resizeObserver?.observe(panel.wrap);},
    destroy:()=>{disposed=true;stopTransition();cancelPendingFrames();clearTimeout(seekTimer);seekWaiters.splice(0).forEach(resolve=>resolve());signalController.abort();options.signal?.removeEventListener('abort',onExternalAbort);clearInterval(clockFallback);for(const panel of panels){panel.resizeObserver.disconnect();for(const image of panel.images)image.remove();}for(const button of controls)button.onclick=null;for(const range of ranges)range.oninput=null;for(const select of speeds)select.onchange=null;},
  };
  const onExternalAbort=()=>api.destroy();
  options.signal?.addEventListener('abort',onExternalAbort,{once:true});
  for(const button of controls)button.onclick=()=>status==='error'?api.play():requestedPlaying?api.pause():api.play();
  for(const range of ranges){range.min='0';range.max='1000';range.step='.1';range.value=String(Math.round(progress*10000)/10);range.oninput=event=>api.setProgress(Number(event.target.value)/1000);}
  for(const select of speeds){select.value=String(speed);select.onchange=event=>api.setSpeed(Number(event.target.value));}
  document.addEventListener('visibilitychange',()=>{lastTick=performance.now();if(document.hidden){cancelAnimationFrame(frameRequest);frameRequest=0;}else scheduleAnimation();},{signal});
  updateUi(true);
  api.ready=loadCurrent('loading').then(()=>{if(!disposed&&status==='error')throw new Error(loadingError||'Field images unavailable.');});
  return api;
}
