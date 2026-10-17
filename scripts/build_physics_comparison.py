"""Record the forcing and comparison scope of the three archived references.

This extracts metadata only. It never runs a solver or changes the research tree.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'mhd_llm'
receipts = []


def read(rel):
    path = SOURCE / rel
    data = path.read_bytes()
    receipts.append({'path': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    return data.decode()


def config(text):
    return {k.strip(): v.strip() for k, v in (line.split('=', 1) for line in text.splitlines() if '=' in line)}


argon_movie = json.loads(read('argon/outputs/runs/model3_assimilated_run_meta.json'))
argon_fine = json.loads(read('argon/outputs/runs/res_fine_224x48x240_run_meta.json'))
codex_selection = json.loads(read('codex/results/reference_selection.json'))
codex_cfg = config(read('codex/results/ct156_w30_theta40_phi192/run.cfg'))
codex_runtime = json.loads(read('codex/results/ct156_w30_theta40_phi192/feature_runtime.json'))
claude_cfg = config(read('claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/cfg.txt'))
claude_da = json.loads(read('claude/runs/da3_ccmc_prod_t4_L1ref_config.json'))
claude_cmes = [[float(value) for value in line.split()] for line in read('claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/cme.txt').splitlines() if line.strip()]
claude_log = read('claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/stdout.txt')
start, end = float(claude_cfg['t_start_s']), float(claude_cfg['t_end_s'])
active_cones = sum(start - 10 * 86400 <= row[0] <= end for row in claude_cmes)

assert argon_movie['enable_cmes'] == argon_fine['enable_cmes'] == 0
assert codex_selection['reference_case'] == codex_selection['animation_case'] == 'ct156_w30_theta40_phi192'
assert not codex_cfg.get('cme_boundary_csv') and codex_runtime['cone_rows'] == 0
assert claude_da['cme'] == 'comet' and claude_cfg['cme_file'].endswith('/cme.txt')
assert active_cones == 74 and f'ncme {active_cones}' in claude_log.splitlines()[0]

for rel in (
    'argon/scripts/run_mhd_suite.sh',
    'argon/src/heliomhd3d.cu',
    'claude/src/py/inputs.py',
    'claude/src/py/production.py',
    'claude/src/py/run_helio.py',
    'claude/src/mhd/helio.cu',
    'codex/solver/athena_ct_features/cone_boundary.hpp',
):
    read(rel)

models = {
    'argon': {
        'name': 'Argon',
        'referenceRun': 'res_fine_224x48x240',
        'animationRun': 'model3_assimilated',
        'animationMatchesReference': False,
        'explicitCmes': False,
        'cmeLabel': 'Ambient wind; no explicit CME injection',
        'cmeShortLabel': 'No CME injection',
        'cmeDetail': 'Both the fine comet reference and the coarser movie run disable cone injection. A separate 16-cone sensitivity run exists; it does not supply the displayed reference or movie.',
        'boundary': 'One rotating WSA map, with spacecraft-based speed and density corrections',
        'temporalBoundary': 'Time-averaged coronal map; rotating structure',
        'thermalClosure': 'Effective gamma = 1.5',
        'referenceGrid': [224, 48, 240],
        'animationGrid': [160, 32, 180],
        'moviePlane': 'Solar-latitude −6.455° cone projected into ecliptic axes',
        'movieField': 'nₚ |v|',
        'originalRetainedCadenceHours': 3,
        'comparisonNote': 'The movie is a different, coarser run from the fine comet series.',
    },
    'codex': {
        'name': 'Codex',
        'referenceRun': 'ct156_w30_theta40_phi192',
        'animationRun': 'ct156_w30_theta40_phi192',
        'animationMatchesReference': True,
        'explicitCmes': False,
        'cmeLabel': 'Ambient wind; no explicit CME injection',
        'cmeShortLabel': 'No CME injection',
        'cmeDetail': 'The selected constrained-transport reference has zero cone rows. Separate 12-hour and 24-hour cone controls are sensitivity cases; they do not supply this reference or movie.',
        'boundary': 'Evolving WSA/GONG boundary with calibrated normalizations and compatible magnetic edge electric fields',
        'temporalBoundary': 'Evolving coronal maps',
        'thermalClosure': 'Effective gamma = 1.5',
        'referenceGrid': [156, 40, 192],
        'animationGrid': [156, 40, 192],
        'moviePlane': 'Ecliptic plane',
        'movieField': 'nₚ |v|',
        'originalRetainedCadenceHours': 6,
        'comparisonNote': 'The retained 512 × 512 movie raster interpolates the selected three-dimensional solver state.',
    },
    'claude': {
        'name': 'Claude',
        'referenceRun': 'prod_da3_ccmc_prod_t4_L1ref_L2',
        'animationRun': 'prod_da3_ccmc_prod_t4_L1ref_L2',
        'animationMatchesReference': True,
        'explicitCmes': True,
        'cmeLabel': 'Ambient wind with DONKI cone CMEs',
        'cmeShortLabel': 'DONKI cone CMEs included',
        'cmeDetail': 'The selected reference injects hydrodynamic cones from a filtered DONKI catalogue. The input file contains 121 catalogue rows; 74 pass the solver’s run-time loading interval. These are not 74 eruptions during the movie. The cones prescribe speed, density and temperature without a magnetic flux rope or ion charge-state model.',
        'catalogueRows': len(claude_cmes),
        'loadedCones': active_cones,
        'boundary': 'Daily WSA maps with time-dependent speed and density corrections inferred from spacecraft',
        'temporalBoundary': 'Evolving coronal maps and explicit cone transients',
        'thermalClosure': 'Gamma = 5/3; no explicit heating',
        'referenceGrid': [512, 120, 360],
        'animationGrid': [512, 120, 360],
        'moviePlane': 'Ecliptic plane',
        'movieField': 'nₚ vᵣ (radial flux proxy)',
        'originalRetainedCadenceHours': 3,
        'comparisonNote': 'The saved plane contains radial speed, so its colour represents radial proton flux rather than nₚ |v|.',
    },
}

rows = [
    ('Explicit CME injection', {'argon': 'Absent', 'codex': 'Absent', 'claude': 'DONKI hydrodynamic cones'}),
    ('Coronal forcing', {key: value['temporalBoundary'] for key, value in models.items()}),
    ('Thermodynamics', {key: value['thermalClosure'] for key, value in models.items()}),
    ('Reference grid (r × θ × φ)', {key: ' × '.join(map(str, value['referenceGrid'])) for key, value in models.items()}),
    ('Movie uses reference run', {'argon': 'No; 160 × 32 × 180 baseline', 'codex': 'Yes', 'claude': 'Yes'}),
    ('Movie surface', {key: value['moviePlane'] for key, value in models.items()}),
    ('Movie field', {key: value['movieField'] for key, value in models.items()}),
    ('Original archive cadence', {'argon': 'About 3 h', 'codex': 'About 6 h', 'claude': 'Exactly 3 h'}),
]

data = {
    'schemaVersion': 1,
    'sourcePolicy': 'Read-only metadata extraction from the archived selected configurations; no solver reruns or changed physical values.',
    'generatedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
    'builder': 'scripts/build_physics_comparison.py',
    'title': 'What differs between the reconstructions?',
    'cmeAnswer': 'Claude’s selected reconstruction includes explicit hydrodynamic cone CMEs. The selected Argon and Codex reconstructions use ambient wind without explicit CME injection. All three can also form compressions where fast streams catch slower wind.',
    'frontInterpretation': 'A bright arc is a region of high plotted proton flux. Its appearance alone does not identify a CME, a shock or a unique eruption. Stream interactions and injected cones can both produce moving compressions.',
    'scope': 'The views share clocks, units, exposure integration and plotting conventions. They retain different forcing, thermal closures, calibration histories, grids and saved surfaces. The comparison does not isolate the effect of any one modeling choice.',
    'clockNote': 'Movies use geometric physical UTC. Quantitative X-ray comparisons use photon-arrival UTC and the same accepted EPIC-pn good-time intervals.',
    'samplingNote': 'Comet curves use each model’s three-dimensional moving probe, including its out-of-plane position. Movie panels are selected two-dimensional surfaces and need not show the local value at the plotted comet marker.',
    'models': models,
    'rows': [{'label': label, 'values': values} for label, values in rows],
    'sourceReceipts': receipts,
}
target = ROOT / 'public/data/physics-comparison.json'
target.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'Wrote {target.relative_to(ROOT)}; {len(receipts)} archived inputs verified')
