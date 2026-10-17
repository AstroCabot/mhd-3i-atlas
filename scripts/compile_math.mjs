// Compile the equation catalogue with the vendored KaTeX distribution at build time.
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const mathSource=readFileSync(path.join(root,'public/data/models.json'),'utf8');
const models=JSON.parse(mathSource);
const sandbox={module:{exports:{}},console};sandbox.exports=sandbox.module.exports;
vm.runInNewContext(readFileSync(path.join(root,'public/assets/vendor/katex.min.js'),'utf8'),sandbox);
const katex=sandbox.module.exports;
const equations=[...models.commonEquations,...models.models.flatMap(m=>m.equations),{latex:String.raw`F_X \propto \int n_n\,n_p\,f_{q}\,v_{\mathrm{rel}}\,\sigma_{\mathrm{CX}}\,Y_X\,\mathrm{d}V`}];
const compiled={};
for(const eq of equations){const tex=eq.latex.replace(/\\\\/g,'\\');compiled[tex]=katex.renderToString(tex,{displayMode:true,throwOnError:true,trust:false,strict:'error',output:'htmlAndMathml'});}
writeFileSync(path.join(root,'public/data/equations.json'),JSON.stringify({compiler:`KaTeX ${katex.version}`,sourceHash:crypto.createHash('sha256').update(mathSource).digest('hex'),equations:compiled}));
console.log(`Compiled ${Object.keys(compiled).length} equations with KaTeX ${katex.version}.`);
