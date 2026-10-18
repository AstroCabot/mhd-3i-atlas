// Reflow report equations at TeX relation/operator boundaries. Source Markdown
// and the original TeX remain available unchanged in the report download.
function breakableTex(tex){
  let depth=0,result='';
  for(let index=0;index<tex.length;index++){
    const char=tex[index];
    if(char==='\\'){result+=char+(tex[++index]||'');continue;}
    if(char==='{')depth++;
    if(char==='}')depth--;
    result+=char;
    if(char===','&&depth===0)result+='\\allowbreak ';
  }
  // Fixed-size delimiters let the browser break a long flux expression at its
  // operators; automatic \left/\right pairs form an indivisible KaTeX box.
  return result.replace(/\\left\[/g,'\\bigl[').replace(/\\right\]/g,'\\bigr]');
}

export function displayMathRows(tex){
  const aligned=/^\s*\\begin\{aligned\}([\s\S]*?)\\end\{aligned\}\s*$/.exec(tex);
  return (aligned?aligned[1].split(/\\\\(?:\[[^\]]*\])?/):[tex])
    .flatMap(row=>row.split(/\\qquad\s*/))
    .map(row=>row.replace(/(^|[^\\])&/g,'$1').trim())
    .filter(Boolean).map(breakableTex);
}

export function renderReportMath(root){
  root.querySelectorAll('[data-writeup-math]').forEach(node=>{
    const tex=node.dataset.writeupMath;
    if(node.classList.contains('writeup-equation')){
      node.replaceChildren(...displayMathRows(tex).map(row=>{
        const line=document.createElement('div');line.className='writeup-equation-line';
        window.katex.render(row,line,{displayMode:true,output:'htmlAndMathml',throwOnError:false,trust:false});
        return line;
      }));
    }else window.katex.render(breakableTex(tex),node,{displayMode:false,output:'htmlAndMathml',throwOnError:false,trust:false});
  });
}
