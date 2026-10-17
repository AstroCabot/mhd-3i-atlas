import { siteUrl } from './site-paths.js';
/** Continuous playback of retained scientific fields without a platform video codec.
 * await mountSolarPlayers({root,manifestUrl,models,field,playing,speed,progress,onTime,onState})
 * Returns {ready,manifest,play,pause,setSpeed,setProgress,setField,setModel,getState,destroy}.
 * Two persistent predecoded image layers crossfade at requestAnimationFrame cadence.
 * Physical samples are interpolated before colour mapping at 30 min display support;
 * intermediate opacity blending adds visual continuity, not native information.
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
function loadImageSource(image, url) {
  if(image.src===url&&image.complete&&image.naturalWidth>0)return Promise.resolve();
  return new Promise((resolve,reject)=>{
    const finish=error=>{clearTimeout(timer);image.removeEventListener('load',loaded);image.removeEventListener('error',failed);error?reject(error):resolve();};
    const loaded=()=>finish();
    const failed=()=>finish(new Error('Retained field image could not be loaded.'));
    const timer=setTimeout(()=>finish(new Error('Retained field image loading timed out.')),15000);
    image.addEventListener('load',loaded,{once:true});image.addEventListener('error',failed,{once:true});
    image.src=url;
    if(image.complete&&image.naturalWidth>0)queueMicrotask(loaded);
  });
}
function frameImage(url) {
  let entry = imageFrames.get(url);
  if (!entry) {
    entry = {used:++frameUse, ready:false, image:null, objectUrl:null};
    entry.promise = Promise.resolve().then(async () => {
      entry.objectUrl = siteUrl(url);
      entry.image = new Image();
      await loadImageSource(entry.image,entry.objectUrl);
      entry.ready = true;
      for (const [key, value] of [...imageFrames].sort((a,b)=>a[1].used-b[1].used)) {
        if (imageFrames.size <= MAX_DECODED_FRAMES) break;
        if (value.ready && key !== url) imageFrames.delete(key);
      }
      return entry;
    }).catch(error => {imageFrames.delete(url); throw error;});
    imageFrames.set(url, entry);
  }
  entry.used = ++frameUse;
  return entry.promise;
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
  const panels = [];
  const controls = [...root.querySelectorAll('[data-play]')];
  const ranges = [...root.querySelectorAll('[data-frame]')];
  const speeds = [...root.querySelectorAll('#play-speed')];
  const signalController = new AbortController();
  const signal = signalController.signal;
  const sequence = model => manifest.models[model].frameSequence;
  function getState() {return {playing,requestedPlaying,status,field,speed,progress,error:loadingError,engine:'persistent-images'};}
  function onState() {
    if (disposed) return;
    for (const button of controls) {
      button.innerHTML = icons[requestedPlaying ? 'pause' : 'play'];
      button.setAttribute('aria-label',requestedPlaying?'Pause solar-wind animation':'Play solar-wind animation');
      button.setAttribute('aria-pressed',String(requestedPlaying));
      button.dataset.playbackStatus = status;
    }
    for (const panel of panels) panel.wrap.dataset.playbackStatus = status;
    for (const node of root.querySelectorAll('[data-playback-status-label],span[data-playback-status]')) {
      node.textContent = ({playing:'Continuous display · native cadence 3–6 h',loading:'Loading retained fields…',seeking:'Seeking…',paused:'Paused',stalled:'Loading next field…',error:'Animation unavailable'})[status] || status;
      node.title = loadingError || '768 px · 30 min interpolated display support; native samples every 3–6 h.';
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
    if (force || now-lastUi>80) {
      lastUi=now;
      for (const range of ranges) range.value=String(Math.round(progress*1000));
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
    if (plane) plane.textContent = `${panel.model === 'argon' ? '−6.455° cone' : 'Ecliptic'} · ${model.nativeSliceDimensions.join(' × ')} retained samples · ${model.nominalCadenceHours} h`;
    const title = panel.wrap.querySelector('[data-bar-title]');
    if (title) title.textContent = field === 'contrast' ? 'nₚv × r² / cm⁻² s⁻¹ AU²' : `${panel.model === 'claude' ? 'nₚvᵣ' : 'nₚ|v|'} / cm⁻² s⁻¹`;
    const min = panel.wrap.querySelector('[data-bar-min]');
    const mid = panel.wrap.querySelector('[data-bar-mid]');
    const max = panel.wrap.querySelector('[data-bar-max]');
    if (min) min.textContent = '10⁷';
    if (mid) mid.textContent = field === 'contrast' ? '1.4×10⁸' : '5.5×10⁸';
    if (max) max.textContent = field === 'contrast' ? '2×10⁹' : '3×10¹⁰';
    const gradient = panel.wrap.querySelector('.gradient');
    if (gradient) gradient.style.background = `linear-gradient(90deg,${manifest.palette.map(color => `rgb(${color.join(',')})`).join(',')})`;
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
    for(const panel of panels) {
      const rows=sequence(panel.model).fields[field];
      for(const offset of [2,3,4,-1]) {
        const i=p.lower+offset;
        if(i>=0&&i<rows.length)frameImage(rows[i].url).catch(()=>{});
      }
    }
  }
  async function loadCurrent(nextStatus='stalled') {
    const token=++generation;
    requestActive=true;playing=false;status=nextStatus;loadingError=null;onState();
    cancelAnimationFrame(frameRequest);frameRequest=0;
    const p=position();
    try {
      const loaded=await Promise.all(panels.map(async panel=>{
        const [loUrl,hiUrl]=keys(panel,p);
        const [lo,hi]=await Promise.all([frameImage(loUrl),frameImage(hiUrl)]);
        return {panel,loUrl,hiUrl,lo,hi};
      }));
      if(disposed||token!==generation)return;
      // Every source has already decoded in the bounded image cache. Keep the
      // existing view until both persistent layers have accepted cached pixels.
      await Promise.all(loaded.map(async({panel,loUrl,hiUrl,lo,hi})=>{
        const matchingLower=panel.images.find(image=>image.dataset.frameUrl===loUrl);
        const lower=matchingLower||panel.images[0];
        const upper=panel.images.find(image=>image!==lower);
        if(matchingLower) {
          // At an interval boundary the previous upper image becomes the new
          // lower image. Keep it fully visible while recycling the other layer.
          lower.style.opacity='1';lower.style.zIndex='0';
          upper.style.opacity='0';upper.style.zIndex='1';
        } else if(panel.lower) {
          // During a field/model change one decoded old layer remains opaque
          // while the first incoming layer accepts its predecoded source.
          upper.style.opacity='1';upper.style.zIndex='1';
        }
        await loadImageSource(lower,lo.objectUrl);lower.dataset.frameUrl=loUrl;
        if(disposed||token!==generation)return;
        lower.style.visibility='visible';lower.style.opacity='1';lower.style.zIndex='0';
        upper.style.opacity='0';upper.style.zIndex='1';
        await loadImageSource(upper,hi.objectUrl);upper.dataset.frameUrl=hiUrl;
        if(disposed||token!==generation)return;
        lower.style.zIndex='0';upper.style.zIndex='1';
        lower.style.visibility=upper.style.visibility='visible';
        panel.lower=lower;panel.upper=upper;panel.pairKey=`${panel.model}:${field}:${p.lower}`;
        panel.wrap.style.backgroundImage='';panel.wrap.dataset.imageReady='true';
        updateLabels(panel);
      }));
      if(disposed||token!==generation)return;
      requestActive=false;status=requestedPlaying?'playing':'paused';playing=requestedPlaying;lastTick=performance.now();
      showBlend(p);updateUi(true);onState();prefetch(p);scheduleAnimation();
    }catch(error){
      if(disposed||token!==generation)return;
      requestActive=false;status='error';playing=false;loadingError=error.message;onState();
    }
  }
  function advance(now) {
    if(disposed)return;
    if(playing&&!requestActive&&!document.hidden) {
      const candidate=(progress+(now-lastTick)*speed/(manifest.durationSeconds*1000))%1;
      lastTick=now;
      const previous=progress;progress=candidate;
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
    play:async()=>{requestedPlaying=true;if(!requestActive&&status!=='error'){playing=true;status='playing';lastTick=performance.now();scheduleAnimation();}onState();},
    pause:()=>{requestedPlaying=false;playing=false;cancelAnimationFrame(frameRequest);frameRequest=0;if(status==='playing')status='paused';onState();},
    setSpeed:value=>{speed=clamp(Number(value)||1,.25,4);onState();},
    setProgress:async value=>{progress=clamp(value);updateUi(true);await loadCurrent('seeking');},
    setField:async value=>{const next=value==='fluxR2'?'contrast':value;if(!['flux','contrast'].includes(next))throw new Error(`Unknown field ${value}`);if(next!==field){field=next;await loadCurrent('loading');}},
    setModel:async(value,index=0)=>{if(!manifest.models[value])throw new Error(`Unknown model ${value}`);if(panels[index]&&panels[index].model!==value){panels[index].model=value;panels[index].svg.dataset.solar=value;await loadCurrent('loading');}},
    resize:()=>{for(const panel of panels)panel.resizeObserver?.unobserve(panel.wrap);for(const panel of panels)panel.resizeObserver?.observe(panel.wrap);},
    destroy:()=>{disposed=true;generation++;signalController.abort();options.signal?.removeEventListener('abort',onExternalAbort);cancelAnimationFrame(frameRequest);clearInterval(clockFallback);for(const panel of panels){panel.resizeObserver.disconnect();for(const image of panel.images)image.remove();}for(const button of controls)button.onclick=null;for(const range of ranges)range.oninput=null;for(const select of speeds)select.onchange=null;},
  };
  const onExternalAbort=()=>api.destroy();
  options.signal?.addEventListener('abort',onExternalAbort,{once:true});
  for(const button of controls)button.onclick=()=>requestedPlaying?api.pause():api.play();
  for(const range of ranges){range.min='0';range.max='1000';range.step='1';range.value=String(Math.round(progress*1000));range.oninput=event=>api.setProgress(Number(event.target.value)/1000);}
  for(const select of speeds){select.value=String(speed);select.onchange=event=>api.setSpeed(Number(event.target.value));}
  document.addEventListener('visibilitychange',()=>{lastTick=performance.now();if(document.hidden){cancelAnimationFrame(frameRequest);frameRequest=0;}else scheduleAnimation();},{signal});
  updateUi(true);
  api.ready=loadCurrent('loading').then(()=>{if(!disposed&&status==='error')throw new Error(loadingError||'Field images unavailable.');});
  return api;
}
