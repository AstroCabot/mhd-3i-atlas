// Label placement is independent of the physical marker coordinates.
// Measure text and overlays only on resize; playback uses cached numeric boxes.
const NS='http://www.w3.org/2000/svg';
const priority=['comet','earth','solar_orbiter','stereo_a','mercury','venus','mars'];
const positions=[
  [10,-12,'start'],[-10,-12,'end'],[10,18,'start'],[-10,18,'end'],
  [0,-25,'middle'],[0,30,'middle'],[18,-35,'start'],[-18,-35,'end'],
  [18,38,'start'],[-18,38,'end'],[0,-48,'middle'],[0,53,'middle'],
  [36,-12,'start'],[-36,-12,'end'],[36,22,'start'],[-36,22,'end'],
];
const area=(a,b)=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));

export function createSolarLabelLayout(panel){
  let scale=1,margin=4,items=[],obstacles=[];
  const previous=new Map();
  function resize(){
    const rect=panel.svg.getBoundingClientRect();
    const side=Math.max(1,Math.min(rect.width,rect.height));
    scale=768/side;margin=4*scale;
    const left=rect.left+(rect.width-side)/2,top=rect.top+(rect.height-side)/2;
    // Distances remain in the orbital guide below the comparison and in each
    // circle's accessible title. Small maps keep tracked-body names legible.
    const narrow=side<360;
    for(const text of panel.svg.querySelectorAll('[data-orbit-label]'))text.style.display=narrow?'none':'';
    for(const text of panel.svg.querySelectorAll('text')){
      if(text.textContent==='J2000 ecliptic x/y · AU')text.style.display=narrow?'none':'';
    }
    obstacles=[];
    for(const node of panel.wrap.querySelectorAll('.canvas-label,.canvas-date,.colorbar')){
      const box=node.getBoundingClientRect();
      if(box.width&&box.height)obstacles.push({left:(box.left-left)*scale-2*scale,top:(box.top-top)*scale-2*scale,right:(box.right-left)*scale+2*scale,bottom:(box.bottom-top)*scale+2*scale});
    }
    for(const text of [...panel.svg.querySelectorAll('text')].filter(text=>text.hasAttribute('data-orbit-label')||text.textContent==='J2000 ecliptic x/y · AU')){
      if(text.style.display==='none')continue;
      const box=text.getBBox();
      obstacles.push({left:box.x-2*scale,top:box.y-2*scale,right:box.x+box.width+2*scale,bottom:box.y+box.height+2*scale});
    }
    items=priority.filter(name=>panel.markers.has(name)).map(name=>{
      const group=panel.markers.get(name),text=group.querySelector('text'),box=text.getBBox();
      let leader=group.querySelector('line');
      if(!leader){leader=document.createElementNS(NS,'line');group.insertBefore(leader,group.firstChild);}
      for(const [key,value]of Object.entries({stroke:'#c2c7bd','stroke-width':'.65','stroke-opacity':'.7','x1':'0','y1':'0'}))leader.setAttribute(key,value);
      return {name,group,text,leader,width:box.width,height:box.height,baseline:box.y-Number(text.getAttribute('y')||0)};
    });
    previous.clear();update();
  }
  function update(){
    const occupied=[...obstacles];
    // Keep the fixed solar marker visible even when Mercury projects close to it.
    const solarRadius=9*scale;
    occupied.push({left:384-solarRadius,top:384-solarRadius,right:384+solarRadius,bottom:384+solarRadius});
    for(const item of items){
      const match=/translate\(\s*([-+\d.eE]+)[ ,]+([-+\d.eE]+)/.exec(item.group.getAttribute('transform')||'');
      if(match){const x=Number(match[1]),y=Number(match[2]),radius=6*scale;occupied.push({left:x-radius,top:y-radius,right:x+radius,bottom:y+radius});}
    }
    for(const item of items){
      const match=/translate\(\s*([-+\d.eE]+)[ ,]+([-+\d.eE]+)/.exec(item.group.getAttribute('transform')||'');
      if(!match)continue;
      const x=Number(match[1]),y=Number(match[2]);
      const preferred=previous.get(item.name);
      const candidates=preferred?[preferred,...positions.filter(position=>position!==preferred)]:positions;
      let best;
      for(const position of candidates){
        const [dx,dy,anchor]=position;
        const start=x+dx*scale-(anchor==='middle'?.5:anchor==='end'?1:0)*item.width;
        const top=y+dy*scale+item.baseline;
        const box={left:start-2*scale,top:top-2*scale,right:start+item.width+2*scale,bottom:top+item.height+2*scale};
        const outside=Math.max(0,margin-box.left)+Math.max(0,margin-box.top)+Math.max(0,box.right-(768-margin))+Math.max(0,box.bottom-(768-margin));
        const collision=occupied.reduce((sum,obstacle)=>sum+area(box,obstacle),0);
        const score=outside*10000+collision;
        if(!best||score<best.score)best={position,box,score};
        if(score===0)break;
      }
      const [dx,dy,anchor]=best.position;
      if(previous.get(item.name)!==best.position){
        item.text.setAttribute('x',String(dx*scale));item.text.setAttribute('y',String(dy*scale));item.text.setAttribute('text-anchor',anchor);
        const endX=Math.max(best.box.left+2*scale,Math.min(x,best.box.right-2*scale));
        const endY=Math.max(best.box.top+2*scale,Math.min(y,best.box.bottom-2*scale));
        item.leader.setAttribute('x2',String(endX-x));item.leader.setAttribute('y2',String(endY-y));
      }
      previous.set(item.name,best.position);occupied.push(best.box);
    }
  }
  return {resize,update};
}
