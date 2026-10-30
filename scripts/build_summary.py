"""Build the concluding article from committed observations and source receipts."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re
import shutil
import statistics

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'public/assets/summary'
SNAPSHOTS = {
    'argon-inputs.py': 'argon/scripts/prepare_inputs.py',
    'argon-reference.json': 'argon/outputs/runs/res_fine_224x48x240_run_meta.json',
    'claude-assimilation.py': 'claude/src/py/da.py',
    'claude-readme.txt': 'claude/README.md',
    'claude-reference.json': 'claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2.json',
    'claude-runtime.txt': 'claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/stdout.txt',
    'codex-inputs.json': 'codex/inputs/metadata.json',
    'codex-readme.txt': 'codex/README.txt',
    'codex-usage.json': 'codex/results/ct156_w30_theta40_phi192/runner_usage.json',
    'codex-runtime.txt': 'codex/results/ct156_w30_theta40_phi192/run.log',
    'enlil-control.txt': 'claude/ref/ccmc/Jan_Deca_120925_SH_1_control_file.txt',
}


def read(path):
    return json.loads(path.read_text())


def receipt(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def table(identifier, caption, headers, rows):
    heading = ''.join(f'<th scope="col">{html.escape(value)}</th>' for value in headers)
    body = ''.join('<tr><th scope="row">' + html.escape(row[0]) + '</th>' +
                   ''.join('<td>' + html.escape(value) + '</td>' for value in row[1:]) + '</tr>' for row in rows)
    return (f'<div class="table-scroll summary-table-scroll" tabindex="0" role="region" aria-label="{html.escape(caption)}">'
            f'<table class="comparison-table summary-table" id="{identifier}"><caption>{html.escape(caption)}</caption>'
            f'<thead><tr>{heading}</tr></thead><tbody>{body}</tbody></table></div>')


def build(source=None):
    ASSETS.mkdir(parents=True, exist_ok=True)
    manifest_path = ASSETS / 'source-manifest.json'
    if source:
        files = []
        for name, origin in SNAPSHOTS.items():
            target = ASSETS / 'evidence' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(source) / origin, target)
            files.append({'url': '/assets/summary/evidence/' + name, 'sourcePath': origin, **receipt(target)})
        manifest_path.write_text(json.dumps({'scope': 'Unmodified copies of selected research records; no solver reruns.',
                                            'files': files}, indent=2) + '\n')
    manifest = read(manifest_path)
    figure_manifest_path = ASSETS / 'figure-manifest.json'
    figure_manifest = read(figure_manifest_path)
    figure_builder = ROOT / figure_manifest['builder']['path']
    if receipt(figure_builder)['sha256'] != figure_manifest['builder']['sha256']:
        raise ValueError('The figure builder changed; run scripts/build_summary_figures.py before packaging')
    source_files = manifest['files'] + figure_manifest['files']
    for row in source_files:
        path = ROOT / 'public' / row['url'].lstrip('/')
        if receipt(path) != {key: row[key] for key in ['bytes', 'sha256']}:
            raise ValueError(f'Changed research source: {path}')

    model_path = ROOT / 'public/data/models.json'
    nasa_path = ROOT / 'public/data/nasa-comparison.json'
    science_path = ROOT / 'public/data/science.json'
    models = {row['id']: row for row in read(model_path)['models']}
    nasa, science = read(nasa_path), read(science_path)
    order = ['argon', 'codex', 'claude', 'enlil']
    names = ['Argon', 'Codex', 'Claude', 'NASA/CCMC ENLIL']
    stereo = next(row for row in nasa['spacecraft'] if row['id'] == 'stereo_a')
    valid = [index for index, observed in enumerate(stereo['observed']['speed'])
             if all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0
                    for value in [observed] + [stereo['models'][model]['speed'][index] for model in order])]
    if len(valid) != 385:
        raise ValueError('The summary comparison expects the archived 385 common STEREO-A samples')
    errors = {}
    for model in order:
        errors[model] = math.sqrt(statistics.mean((stereo['observed']['speed'][index] -
                                                  stereo['models'][model]['speed'][index]) ** 2 for index in valid))
        if not math.isclose(errors[model], stereo['metrics'][model]['speedRmse'], rel_tol=1e-12):
            raise ValueError(f'Spacecraft metric differs from its samples: {model}')

    def recorded(model, label):
        return next(row['value'] for row in models[model]['resources']['rows'] if row['label'] == label)

    evidence_dir = ASSETS / 'evidence'
    argon = read(evidence_dir / 'argon-reference.json')
    claude = read(evidence_dir / 'claude-reference.json')
    codex = read(evidence_dir / 'codex-usage.json')
    for model, value in [('argon', argon['wall_time_s']), ('claude', claude['wall_s']),
                         ('codex', codex['wall_seconds_including_inputs'])]:
        if not math.isclose(value, recorded(model, 'Reference solver wall time'), rel_tol=1e-12):
            raise ValueError(f'Runtime source differs: {model}')
    log = (evidence_dir / 'claude-runtime.txt').read_text()
    steps, native_wall = re.search(r'done (\d+) steps,.*?wall ([\d.]+) s', log).groups()
    claude_updates = 512 * 120 * 360 * int(steps) / float(native_wall) / 1e6
    codex_log = (evidence_dir / 'codex-runtime.txt').read_text()
    codex_updates = float(re.search(r'zone-cycles/omp_wsecond = ([\deE+.-]+)', codex_log)[1]) / 1e6
    busy_cores = (codex['user_seconds'] + codex['system_seconds']) / codex['wall_seconds_including_inputs']
    control = (evidence_dir / 'enlil-control.txt').read_text()
    if not re.search(r'^runpar=g53q5\b', control, re.M):
        raise ValueError('The archived ENLIL thermal setting changed')

    methods = table('summary-methods', 'What each reference model uses',
                    ['Model', 'Heat and numerical method', 'How spacecraft wind data are used', 'CMEs'], [
        ['Argon', 'γ = 1.5; HLL + GLM', 'Measured speed and density traced back and blended into one rotating WSA map', 'None in the reference run'],
        ['Codex', 'γ = 1.5; Athena++ HLLD + CT', 'Overall density, temperature and field scales fitted to two spacecraft; daily WSA maps otherwise unchanged', 'None in the reference run'],
        ['Claude', 'γ = 5/3, no heating; HLLD + GLM', 'Daily WSA maps corrected iteratively in longitude, latitude and time', 'Cones selected from DONKI'],
        ['NASA/CCMC ENLIL', 'γ = 5/3 with heating; ENLIL’s own solver', 'Not used; driven by GONG/WSA maps alone', 'Cones selected from DONKI'],
    ])
    confidence = table('summary-confidence', 'Spacecraft fit and estimated flux at the comet',
                       ['Model', 'STEREO-A speed RMSE / km s⁻¹', 'Proton flux at the comet / 10⁸ cm⁻² s⁻¹'],
                       [[name, f'{errors[model]:.1f}', f"{nasa['comet']['models'][model]['gtiMeans']['flux'] / 1e8:.2g}"]
                        for model, name in zip(order, names)])
    movies = table('summary-movies', 'What each movie shows',
                   ['Model', 'Run shown', 'Surface', 'Colored by', 'Time between saved frames'], [
        ['Argon', 'Coarser run (921,600 cells)', 'Constant solar latitude', 'nₚ|v|', 'About 3 hours'],
        ['Codex', 'Reference run', 'Ecliptic plane', 'nₚ|v|', 'About 6 hours'],
        ['Claude', 'Reference run', 'Ecliptic plane', 'nₚvᵣ', '30 minutes'],
        ['NASA/CCMC ENLIL', 'Archived run', 'Ecliptic plane', 'nₚ|v|', '6 hours'],
    ])
    runtime = table('summary-runtimes', 'Computing cost of each reference run',
                    ['Model', 'Cells', 'Hardware and precision', 'Elapsed time'], [
        ['Argon', '2.58 million', 'Shared RTX 4080 SUPER / single precision', f"{argon['wall_time_s'] / 60:.1f} min"],
        ['Codex', '1.20 million', 'Four CPU threads / double precision', f"{codex['wall_seconds_including_inputs'] / 60:.1f} min"],
        ['Claude', '22.12 million', 'Shared RTX 4080 SUPER / single precision', f"{claude['wall_s'] / 60:.1f} min"],
        ['NASA/CCMC ENLIL', '1.24 million', 'CPU job; 64 processes requested', 'Not recorded'],
    ])
    figures = {row['id']: row for row in figure_manifest['figures']}

    def figure(name, alt, caption):
        row = figures[name]
        return (f'<figure class="summary-figure" id="summary-figure-{name}">'
                f'<div class="summary-figure-scroll" tabindex="0" role="region" aria-label="{html.escape(alt)}">'
                f'<img data-summary-src="{row["url"]}?v={row["sha256"][:12]}" width="{math.ceil(row["width"])}" '
                f'height="{math.ceil(row["height"])}" loading="lazy" decoding="async" alt="{html.escape(alt)}"></div>'
                f'<figcaption>{caption} <a href="{row["url"]}?v={row["sha256"][:12]}">Enlarge</a> · '
                f'<a href="{row["url"].removesuffix(".svg")}.pdf" download>PDF</a>.</figcaption></figure>')

    geometry_figure = figure('geometry',
        'Projected positions of 3I/ATLAS, Earth, inner planets, STEREO-A and Solar Orbiter during the XMM observation; a side panel compares their solar latitudes.',
        'Figure 13.1. Positions at 23:00 UTC on 3 December 2025, close to the middle of the observation, seen from above the ecliptic plane. '
        'Solar Orbiter sits about 0.17 AU above that plane. Latitudes in the side list are measured from the Sun’s equator. '
        'The dotted lines mark the 25° in longitude between STEREO-A and the comet. '
        '<a href="/assets/summary/figure-inputs/positions.csv" download>Position data</a>.')
    gong_figure = figure('gong-wsa',
        'A real GONG synoptic radial magnetic map above the corresponding WSA 5.4 wind-speed estimate, both based on the 25 November 2025 GONG source.',
        'Figure 13.2. The top panel is a GONG map of the Sun’s surface field: red is positive radial field, blue is negative, and the color scale saturates at ±50 G. '
        'The bottom panel is the wind speed that WSA derives from the same GONG data at 21.5 solar radii, before any agent adjusted it. '
        'The two panels have different grids. Carrington longitude is fixed to the rotating Sun. '
        '<a href="/assets/summary/figure-inputs/gong-20251125.fits.gz" download>GONG FITS</a> · '
        '<a href="/assets/summary/figure-inputs/wsa-speed-20251125.fits" download>WSA FITS</a>.')
    schematic_figure = figure('field-and-cme',
        'Conceptual comparison of a spiral magnetic field with radial bulk flow, and a moving spherical CME cloud with an angular cone envelope crossing a model boundary.',
        'Figure 13.3. Left: an idealized Parker spiral near the Sun’s equator at one instant, for one magnetic polarity. '
        'Teal curves are field lines and grey arrows show the wind. Right: a cone model in cross-section. The dashed lines mark the cone’s half-width, w, '
        'and the thick arc marks the part of the boundary where the cloud’s values are imposed.')
    examples = figure_manifest['magnetogramAndWsa']['examplesKms']
    example_text = (f'With the formula used here, a bundle with fₛ = 3 starting 0.2° from the edge gets about {round(examples["f3_d0p2"], -1):.0f} km s⁻¹. '
                    f'Starting 4° inside the hole instead gives about {round(examples["f3_d4"], -1):.0f} km s⁻¹, '
                    f'and increasing the expansion to fₛ = 30 brings that down to about {round(examples["f30_d4"], -1):.0f} km s⁻¹')
    substitutions = {'METHOD_TABLE': methods, 'CONFIDENCE_TABLE': confidence, 'MOVIE_TABLE': movies, 'RUNTIME_TABLE': runtime,
                     'GEOMETRY_FIGURE': geometry_figure, 'GONG_FIGURE': gong_figure, 'SCHEMATIC_FIGURE': schematic_figure,
                     'WSA_EXAMPLES': example_text,
                     'NASA_CME_PERCENT': f"{nasa['comet']['cmeRelativeFluxChange'] * 100:.2f}",
                     'XRAY_CORRELATIONS': ', '.join(f"{science['xray']['models'][model]['pearsonR']:+.2f}".replace('-', '−') for model in order[:3]),
                     'CLAUDE_MUPDATES': f'{claude_updates:.0f}', 'CODEX_MUPDATES': f'{codex_updates:.1f}',
                     'CODEX_BUSY_CORES': f'{busy_cores:.2f}'}
    article_path = ROOT / 'content/summary.html'
    article = article_path.read_text()
    for key, value in substitutions.items():
        if article.count('{{' + key + '}}') != 1:
            raise ValueError(f'Missing or duplicate article field: {key}')
        article = article.replace('{{' + key + '}}', value)
    if '{{' in article or re.search(r'<(?:canvas|script|iframe|video)\b', article, re.I) or article.count('<figure ') != 3:
        raise ValueError('The summary must contain resolved prose and three static figures, without scripts or movies')
    inputs = [{'path': path.relative_to(ROOT).as_posix(), **receipt(path)}
              for path in [article_path, model_path, nasa_path, science_path, figure_manifest_path]]
    record = {'researchDate': '2026-10-26', 'scope': 'Selected cooperative references plus Jan_Deca_120925_SH_1; no solver reruns.',
              'files': source_files, 'applicationInputs': inputs,
              'figureDerivations': {'geometry': figure_manifest['geometry'], 'magnetogramAndWsa': figure_manifest['magnetogramAndWsa']},
              'derivations': {'stereoCommonSamples': len(valid), 'speedRmseKms': errors,
                              'claudeCellSteps': 512 * 120 * 360 * int(steps), 'claudeNativeWallSeconds': float(native_wall),
                              'claudeMillionCellStepsPerSecond': claude_updates, 'codexMillionZoneCyclesPerSecond': codex_updates,
                              'codexAverageBusyCores': busy_cores},
              'interpretation': [
                  'Confidence and publication judgments are editorial assessments, not model probabilities or peer-review decisions.',
                  'The common STEREO-A interval includes calibration data; it cannot rank blind forecast skill.',
                  'Argon holdout removes Wind/ACE samples from map updates but retains the same 6.80 density prior, described as STA/Wind-weighted in the input source.',
                  'Claude source tracers label mixed advected fluid; their source labels are approximate in a discretized mixed cell.',
                  'NASA gamma/heating identification uses the archived g53q5 control and the CCMC 2016 validation presentation; no unverified q5 heating exponent is asserted.',
                  'Published throughput comparisons differ in hardware, precision, grid geometry, numerical work and timing scope; no efficiency ranking is established.',
                  'No priority search can establish exhaustive absence of prior work; interesting extensions are identified without claiming invention.',
                  'Feynman references are to his discussions of fields and induction. Volume II section 40–2 explicitly excludes MHD; the modern plasma application is a separate synthesis.',
                  'The Parker and cone diagrams are conceptual. The GONG/WSA comparison and the solar-system geometry use archived native products with preserved inputs and checksums.',
              ]}
    (ASSETS / 'evidence.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
    files = source_files + [{'url': '/assets/summary/source-manifest.json', **receipt(manifest_path)},
                                 {'url': '/assets/summary/figure-manifest.json', **receipt(figure_manifest_path)},
                                 {'url': '/assets/summary/evidence.json', **receipt(ASSETS / 'evidence.json')}]
    output = {'schemaVersion': 1, 'title': 'Summary',
              'intro': 'How the solar-wind estimates at the comet were made.',
              'articleHtml': article, 'files': files, 'evidence': record['derivations']}
    (ROOT / 'public/data/summary.json').write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'Built section 13: {len(valid)} common samples checked, {len(manifest["files"])} research sources verified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Import unmodified evidence from the original research root; otherwise use committed copies.')
    build(parser.parse_args().source)
