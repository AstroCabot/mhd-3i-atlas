#!/usr/bin/env python3
"""Publish allowlisted, verbatim solver source from the immutable research archive."""
import hashlib
import json
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
SOURCE = APP.parent / 'mhd_llm'
PIN = '3e5e08f2fd6564f1b1e11500fca784abb94564dc48410407bf59074c84978d9f'
BASE = f'codex/solver/athena_ct_pins/{PIN}/'
OWN = BASE+'own_source/solver/athena_ct_diagnostic/'
NATIVE = BASE+'external_source/tmp/x3i-codex-athena-ct-diagnostic/athena-e47fabb7dd5efb22e1e2c7ff193148d723e3e952/src/'
FILES = [
    ('argon-core','argon','argon/src/heliomhd3d.cu','CUDA','Spherical MHD evolution, boundary conditions and moving probes.',
     ['apply_boundary_conditions_kernel(', 'mhd_rk_stage_kernel(', 'sample_probe_trilinear(', 'run_3d_spherical_simulation(']),
    ('claude-core','claude','claude/src/mhd/helio.cu','CUDA','Production spherical solver, flux kernels, source terms, cone injection and output.',
     ['k_flux_r(', 'k_source(', 'cme_override(', 'k_bc_inner(', 'k_probe(', 'int main(']),
    ('claude-flux','claude','claude/src/mhd/core.cuh','CUDA','Primitive/conserved transformations and numerical MHD fluxes.', []),
    ('claude-inputs','claude','claude/src/py/run_helio.py','Python','Production input preparation and solver configuration.', []),
    ('codex-core','codex',OWN+'x3i_ct_diagnostic.cpp','C++','Selected production problem generator, physical boundaries and accepted-state probes.',
     ['hydro(', 'void Mesh::InitUserMeshData(', 'void MeshBlock::ProblemGenerator(', 'void Mesh::UserWorkInLoop(']),
    ('codex-hlld','codex',NATIVE+'hydro/rsolvers/mhd/hlld.cpp','C++','Athena++ HLLD Riemann solver used by the selected CT reconstruction.', ['Hydro::RiemannSolver(']),
    ('codex-plm','codex',NATIVE+'reconstruct/plm.cpp','C++','Piecewise-linear reconstruction of interface states.', ['Reconstruction::PiecewiseLinearX1(']),
    ('codex-ct','codex',NATIVE+'field/ct.cpp','C++','Constrained transport of the staggered magnetic field.', ['Field::CT(']),
    ('codex-integrator','codex',NATIVE+'task_list/time_integrator.cpp','C++','Native task schedule, integration stages and flux/field updates.', []),
    ('codex-eos','codex',NATIVE+'eos/adiabatic_mhd.cpp','C++','Adiabatic MHD equation of state and diagnostic floor-abort implementation.', []),
    ('codex-boundary','codex',OWN+'surface_driver.hpp','C++','Magnetic surface transport and compatible boundary electric fields.', []),
    ('codex-cones','codex',OWN+'cone_boundary.hpp','C++','Optional hydrodynamic cone boundary; disabled in the selected reference run.', []),
    ('codex-controller','codex',BASE+'run_ct_simulations_1863fd382c560189.py','Python','Pinned production controller and configuration translation.', []),
]


def build():
    selected = json.loads((SOURCE/'codex/results/ct156_w30_theta40_phi192/code_selection.json').read_text())
    assert selected['code_receipt_sha256'] == PIN
    receipts = json.loads((SOURCE/'codex/results/ct156_w30_theta40_phi192/input_code_provenance.json').read_text())
    target = APP/'public/data/solver-sources'
    target.mkdir(parents=True, exist_ok=True)
    entries = []
    for id, agent, path, language, purpose, anchors in FILES:
        raw = (SOURCE/path).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if agent == 'codex':
            assert receipts[path.removeprefix('codex/')] == digest, path
        text = raw.decode('utf-8')
        methods = []
        for anchor in anchors:
            assert anchor in text, (path, anchor)
            methods.append({'name': anchor.rstrip('('), 'line': text[:text.index(anchor)].count('\n')+1})
        (target/(id+'.txt')).write_bytes(raw)
        entries.append({'id': id, 'agent': agent, 'filename': Path(path).name, 'language': language,
                        'purpose': purpose, 'sourcePath': path, 'sha256': digest, 'bytes': len(raw),
                        'lineCount': len(text.splitlines()), 'text': text, 'methods': methods,
                        'rawUrl': '/data/solver-sources/'+id+'.txt',
                        'provenance': 'Selected production pin '+PIN if agent == 'codex' else 'Original archived research source; copied verbatim.'})
    (target/'ATHENA-LICENSE.txt').write_bytes((APP/'content/licenses/athena-bsd.txt').read_bytes())
    result = {'schemaVersion': 1, 'scope': 'Core numerical methods and their production boundary/controller code. These are verbatim research sources, not rewritten examples. The viewer is read-only.',
              'selection': {'argon': 'res_fine_224x48x240', 'codex': 'ct156_w30_theta40_phi192', 'claude': 'prod_da3_ccmc_prod_t4_L1ref_L2'},
              'claudeMovieNote': 'Claude’s finer movie uses an application-owned output-only hook. This catalogue shows the original production solver; numerical kernels are unchanged.',
              'athena': {'upstreamCommit': 'e47fabb7dd5efb22e1e2c7ff193148d723e3e952', 'licenseUrl': '/data/solver-sources/ATHENA-LICENSE.txt',
                         'credit': 'Athena++ core by James M. Stone and contributors; BSD 3-Clause. Codex supplies the problem setup, boundary coupling and production controller.'},
              'files': entries}
    (APP/'public/data/solver-code.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    print('Published',len(entries),'verbatim source files;',sum(row['bytes'] for row in entries),'bytes.')


if __name__ == '__main__':
    build()
