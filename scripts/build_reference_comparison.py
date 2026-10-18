#!/usr/bin/env python3
"""Compare the archived CCMC run with the selected reconstructions; no MHD runs."""
import hashlib
import json
from pathlib import Path

import numpy as np
import build_science as science

APP = Path(__file__).resolve().parents[1]
OUTPUT = APP / 'public/data/nasa-comparison.json'
MODEL_IDS = ['argon', 'codex', 'claude', 'enlil']
RUN_URL = 'https://ccmc.gsfc.nasa.gov/ror/results/viewrun.php?runnumber=Jan_Deca_120925_SH_1'


def metrics(observed, models):
    """Use one common finite, positive mask per quantity for all four models."""
    masks = {}
    for field in ['density', 'speed', 'flux']:
        mask = np.isfinite(observed[field]) & (np.asarray(observed[field]) > 0)
        for model in models.values():
            mask &= np.isfinite(model[field]) & (np.asarray(model[field]) > 0)
        masks[field] = mask
    result = {}
    for name, model in models.items():
        speed = masks['speed']
        actual = np.asarray(observed['speed'])[speed]
        predicted = np.asarray(model['speed'])[speed]
        row = {'speedN': int(speed.sum()), 'speedRmse': float(np.sqrt(np.mean((predicted-actual)**2))),
               'speedBias': float(np.mean(predicted-actual)),
               'speedR': float(np.corrcoef(predicted, actual)[0, 1])}
        for field in ['density', 'flux']:
            mask = masks[field]
            row[field+'N'] = int(mask.sum())
            row[field+'MedianRatio'] = float(np.median(np.asarray(model[field])[mask]/np.asarray(observed[field])[mask]))
        result[name] = row
    return result


def build():
    packed_path = APP / 'public/data/science.json'
    packed = json.loads(packed_path.read_text())
    science.source('claude/ref/ccmc/Jan_Deca_120925_SH_1_control_file.txt')
    spacecraft = []
    for craft in packed['validation']['spacecraft']:
        body = {'stereo_a': 'stereoa', 'wind': 'earth', 'solar_orbiter': 'solo'}[craft['id']]
        native = science.enlil_native(body)
        enlil = {field: science.interp(native['timeMjd'], native[field], craft['timeMjd'])
                 for field in ['density', 'speed', 'flux']}
        models = {**craft['models'], 'enlil': enlil}
        spacecraft.append({key: craft[key] for key in ['id', 'label', 'timeMjd', 'observed', 'qualification']} |
                          {'models': models, 'metrics': metrics(craft['observed'], models)})

    science.native_models()
    tracks = science.ephemerides()
    intervals = np.asarray(packed['xray']['pnIntervals'])
    comet_models = {}
    for model in science.IDS:
        native = science.NATIVE[model]['comet']
        arrival = native.get('arrivalMjd', science.arrival_time(native['timeMjd'], tracks))
        comet_models[model] = {'gtiMeans': {field: science.exact_mean(arrival, native[field], intervals)
                                          for field in ['density', 'speed', 'flux']}}
    for key, ambient in [('enlil', False), ('ambient', True)]:
        native = science.enlil_native(ambient=ambient)
        arrival = science.arrival_time(native['timeMjd'], tracks)
        valid = np.isfinite(arrival)
        comet_models[key] = {'gtiMeans': {field: science.exact_mean(arrival[valid], value[valid], intervals)
                                         for field, value in native.items() if field != 'timeMjd'}}
        if key == 'enlil':
            packed['comet']['series']['enlil'] = {field: science.clean(science.interp(arrival, native[field], packed['comet']['timeMjd']))
                                                 for field in ['density', 'speed', 'flux']}
    packed['meta']['referenceOverlayRevision'] = '2026-10-18: higher-precision native ENLIL export; helium conversion applied once. Agent reconstructions and metrics unchanged.'
    existing = {row['path'] for row in packed['provenance']}
    for receipt in science.PROVENANCE.values():
        if receipt['path'] not in existing:
            packed['provenance'].append(receipt);existing.add(receipt['path'])
    packed_path.write_text(json.dumps(packed, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    reference_flux = comet_models['enlil']['gtiMeans']['flux']
    for model in MODEL_IDS:
        comet_models[model]['fluxRatioToEnlil'] = comet_models[model]['gtiMeans']['flux']/reference_flux
    cme_difference = reference_flux/comet_models['ambient']['gtiMeans']['flux']-1
    return science.clean({
        'schemaVersion': 1,
        'run': {'id': 'Jan_Deca_120925_SH_1', 'model': 'WSA 5.4 / ENLIL 2.8f', 'url': RUN_URL,
                'grid': [576, 24, 90], 'radialDomainAu': [0.1, 3.1], 'latitudeDomainDegrees': [-48, 48],
                'coneCatalogueEntries': 64, 'boundary': 'Time-dependent GONGZ / WSA',
                'window': '1 October–9 December 2025', 'threeDimensionalOutputHours': 6,
                'metadataChecked': '2026-10-18'},
        'modelOrder': MODEL_IDS,
        'comparisonPolicy': 'All four models use the same spacecraft timestamps and a shared positive finite mask for each quantity. The three reconstructions used spacecraft data in calibration; the archived CCMC run is a remote-driven comparator. These residuals alone do not measure independent forecasting skill.',
        'densityConvention': 'ENLIL archive N is mass density divided by proton mass. With nα/np = 0.05, np = N / 1.2. Density and proton flux use this correction; speed is the full heliocentric velocity magnitude.',
        'earthProxy': 'The archived Earth trajectory represents the near-Earth comparison to Wind. It is not the exact Wind trajectory.',
        'spacecraft': spacecraft,
        'comet': {'models': comet_models, 'timeMjd': packed['comet']['timeMjd'],
                  'series': {key: packed['comet']['series'][key] for key in MODEL_IDS},
                  'clock': packed['comet']['clock'], 'intervals': packed['xray']['pnIntervals'],
                  'cmeRelativeFluxChange': cme_difference,
                  'convention': 'This table and these curves compare heliocentric proton flux np|v| for every model. The X-ray section instead uses comet-relative incident flux np|v−vcomet|. Means use exact native piecewise-linear integration over the same accepted PN intervals on the photon-arrival clock.'},
        'limitations': [
            {'title': 'Input maps and prescribed transients', 'body': 'Coronal-map uncertainty and approximate cone directions, widths and speeds affect the propagated wind. A cone does not recover the full asymmetric structure of an eruption.', 'url': 'https://ccmc.gsfc.nasa.gov/models/WSA-Enlil-at-SWPC~3/'},
            {'title': 'Resolution and sampling', 'body': 'This archived run uses 90 longitude and 24 latitude cells. Narrow structures and their arrival times remain sensitive to numerical and boundary choices. A low residual in one sampled sector does not establish the wind at the comet.', 'url': RUN_URL},
            {'title': 'Agreement is not validation', 'body': 'ENLIL is another modeled reconstruction. Matching it tests consistency; spacecraft residuals test the sampled plasma. The calibrated agent runs and the remote-driven reference have different information available.', 'url': None},
            {'title': 'No absolute X-ray prediction', 'body': 'These plasma fields do not supply the neutral coma, emitting-ion charge states, charge-exchange yields or instrument response needed to predict the EPIC-pn count rate.', 'url': None}
        ],
        'sources': [{'title': 'CCMC run metadata and outputs', 'url': RUN_URL},
                    {'title': 'NASA ENLIL 2.8f model description', 'url': 'https://ccmc.gsfc.nasa.gov/models/ENLIL~2.8f/'},
                    {'title': 'NASA WSA–ENLIL caveats', 'url': 'https://ccmc.gsfc.nasa.gov/models/WSA-Enlil-at-SWPC~3/'}],
        'sourceReceipts': list(science.PROVENANCE.values()),
        'applicationInput': {'path': 'public/data/science.json', 'sha256': hashlib.sha256(packed_path.read_bytes()).hexdigest()},
        'builder': 'scripts/build_reference_comparison.py'
    })


if __name__ == '__main__':
    result = build()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n')
    print('Built NASA comparison:', len(result['spacecraft']), 'spacecraft; four models on shared masks.')
    print('PN heliocentric proton flux:', {key: round(value['gtiMeans']['flux']) for key, value in result['comet']['models'].items()})
