"""Import the analyzer's publication bundle without rerunning research models."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def build(source):
    source = Path(source).resolve()
    target = ROOT / 'public/assets/agent-comparison'
    target.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((source / 'manifest.json').read_text())
    names = []
    for entry in manifest['files']:
        name = entry['path']
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Unsafe publication path')
        raw = (source / name).read_bytes()
        if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError(f'Changed analyzer product: {name}')
        names.append(name)
    names += ['manifest.json', 'publication_bundle.zip']
    receipts = []
    for name in names:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, path)
        raw = path.read_bytes()
        receipts.append({'url': '/assets/agent-comparison/' + name,
                         'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})

    def read_csv(name):
        with (source / 'derived' / name).open(newline='') as stream:
            return list(csv.DictReader(stream))

    effort = {row['model']: row for row in read_csv('effort.csv')}
    metrics = {(row['model'], row['probe']): row for row in read_csv('matched_monitor_metrics.csv')
               if row['window'] == 'Dec1_to_Dec5_00UTC'}
    pairs = read_csv('matched_monitor_pairs.csv')
    agents = []
    for agent in ['argon', 'claude', 'codex']:
        row = {'id': agent, 'name': agent.title()}
        for condition, source_condition in [('cooperation', 'collaborative'), ('competition', 'competitive')]:
            key = source_condition + '_' + agent
            record = effort[key]
            result = {'elapsedHours': float(record['plot_elapsed_h']),
                      'outputTokens': int(record['output_tokens']), 'probes': {}}
            for probe in ['wind', 'stereo_a']:
                metric = metrics[key, probe]
                matched = [pair for pair in pairs if pair['model'] == key and pair['probe'] == probe]
                if len(matched) != 96 or int(metric['N']) != 96:
                    raise ValueError('The observational comparison must use 96 common samples')
                rmse = math.sqrt(statistics.mean((float(pair['model_bulk_flux_cm2_s']) -
                                                  float(pair['observed_bulk_flux_cm2_s'])) ** 2 for pair in matched))
                if not math.isclose(rmse, float(metric['bulk_flux_cm2_s_rmse']), rel_tol=1e-12):
                    raise ValueError(f'Metric differs from paired data: {key}, {probe}')
                result['probes'][probe] = {'rmse': rmse, 'r': float(metric['bulk_flux_cm2_s_pearson_r']),
                                           'samples': 96, 'validationStatus': metric['validation_status']}
            row[condition] = result
        row['elapsedSavingPercent'] = 100 * (1 - row['cooperation']['elapsedHours'] / row['competition']['elapsedHours'])
        agents.append(row)
    means = {condition: statistics.mean(row[condition]['elapsedHours'] for row in agents)
             for condition in ['cooperation', 'competition']}
    output = {condition: sum(row[condition]['outputTokens'] for row in agents)
              for condition in ['cooperation', 'competition']}
    quotes = json.loads((source / 'derived/quotes.json').read_text())['quotes']
    if not all(quote['verified_verbatim'] for quote in quotes):
        raise ValueError('Unverified quotation')
    figures = {}
    for name in ['effort', 'monitor_comparison', 'comet_flux']:
        view = ET.parse(target / 'figures' / (name + '.svg')).getroot().attrib['viewBox'].split()
        figures[name] = {'url': f'/assets/agent-comparison/figures/{name}.svg',
                         'width': float(view[2]), 'height': float(view[3])}
    comet = read_csv('common_comet_flux.csv')
    nominal = [float(row['mean_bulk_flux_cm2_s']) for row in comet if row['model'] != 'nasa_full_N_proxy']
    data = {'schemaVersion': 1, 'auditDate': '26 October 2026', 'agents': agents,
            'summary': {'meanElapsedHours': means,
                        'elapsedSavingPercent': 100 * (1 - means['cooperation'] / means['competition']),
                        'outputTokens': output,
                        'extraCooperativeOutputPercent': 100 * (output['cooperation'] / output['competition'] - 1),
                        'cometSpreadFactor': max(nominal) / min(nominal)},
            'quotes': [quote for quote in quotes if quote['id'] in ['Q1', 'Q2', 'Q7', 'Q9']],
            'figures': figures, 'files': receipts,
            'source': 'sw_analyzer / mhd_agent_report; imported publication products, 26 October 2026'}
    (ROOT / 'public/data/agent-comparison.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'Imported {len(receipts)} analyzer products; verified six runs and matched observation metrics.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT.parent / 'mhd_agent_report')
    build(parser.parse_args().source)
