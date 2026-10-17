#!/usr/bin/env python3
"""Replay the retained Claude production configuration with 30-minute slices.

No source research file is changed. A copy of the retained CUDA source receives
an output-only hook after its existing 1,800 s probe callbacks. Both the probe
and original three-hour slice clocks remain unchanged, including their floating
point accumulation. The numerical kernels and all solver inputs are unchanged.
Only the common movie interval is retained in app-owned, ignored runtime data.
The script rejects a replay whose coincident native samples do not reproduce
the original archive to floating-point precision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

APP = Path(__file__).resolve().parents[1]
SOURCE = APP.parent / 'mhd_llm/claude'
ORIGINAL = SOURCE / 'runs/prod_da3_ccmc_prod_t4_L1ref_L2'
DEST = APP / 'runtime/claude-30min'
START_S, END_S = (61006.25 - 60949) * 86400, (61014 - 60949) * 86400
FLAGS = ['-O3', '-arch=sm_89', '-std=c++17', '--use_fast_math', '-lineinfo']


def add_output_only_hook(text):
    """Keep every numerical kernel and integration scheduling expression intact."""
    changes = [
        ('    std::vector<double> snaps = vget("snap_times_s");',
         '''    FILE* fmovie = nullptr;
    if (dget("movie_probe_slices", 0) && slice_dt > 0) {
        fmovie = fopen((out + "/movie-slices.bin").c_str(), "wb");
        int h[3] = {srs, sps, 5};
        float g[2] = {(float)rin, (float)srmax};
        fwrite(h, 4, 3, fmovie);
        fwrite(g, 4, 2, fmovie);
    }
    std::vector<double> snaps = vget("snap_times_s");'''),
        ('    auto do_slice = [&](double ta) {',
         '    auto do_slice = [&](double ta, FILE* sink = nullptr) {\n        if (!sink) sink = fslice;'),
        ('        fwrite(&ts, 8, 1, fslice);\n        fwrite(o.data(), 4, o.size(), fslice);\n        fflush(fslice);',
         '        fwrite(&ts, 8, 1, sink);\n        fwrite(o.data(), 4, o.size(), sink);\n        fflush(sink);'),
        ('if (tau >= next_probe - 1e-9) { do_probe(tau); next_probe += probe_dt / T0; }',
         'if (tau >= next_probe - 1e-9) { do_probe(tau); if (fmovie) do_slice(tau, fmovie); next_probe += probe_dt / T0; }'),
        ('    if (tau >= next_probe - 1e-9) do_probe(tau);',
         '    if (tau >= next_probe - 1e-9) { do_probe(tau); if (fmovie) do_slice(tau, fmovie); }'),
        ('    if (fslice) fclose(fslice);',
         '    if (fslice) fclose(fslice);\n    if (fmovie) fclose(fmovie);'),
    ]
    for old, new in changes:
        assert text.count(old) == 1, f'Output-hook anchor changed: {old}'
        text = text.replace(old, new)
    return text


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def records(path):
    with Path(path).open('rb') as stream:
        header = stream.read(20)
        nr, nphi, fields = struct.unpack('3i', header[:12])
        cells = nr * nphi * fields
        while stamp := stream.read(8):
            raw = stream.read(4 * cells)
            if len(raw) != 4 * cells:
                raise ValueError('Incomplete slice record')
            yield header, struct.unpack('d', stamp)[0], raw


def compare_and_retain(replay, destination):
    reference = {round(t, 3): (t, raw) for _, t, raw in records(ORIGINAL / 'slices.bin')
                 if START_S - 1e-4 <= t <= END_S + 1e-4}
    comparisons = []
    kept = 0
    with Path(destination).open('wb') as output:
        for header, stamp, raw in records(replay):
            if not START_S - 1e-4 <= stamp <= END_S + 1e-4:
                continue
            if kept == 0:
                output.write(header)
            output.write(struct.pack('d', stamp))
            output.write(raw)
            kept += 1
            key = round(stamp, 3)
            if key in reference:
                actual = np.frombuffer(raw, np.float32)
                original_stamp, original_raw = reference[key]
                expected = np.frombuffer(original_raw, np.float32)
                exact = raw == original_raw
                normalized = np.max(np.abs(actual - expected) / np.maximum(np.abs(expected), 1e-6))
                if not exact:
                    raise AssertionError(f'Replay is not bitwise identical to retained sample at {stamp}: {normalized}')
                comparisons.append({'timeMjd': stamp / 86400 + 60949,
                                    'bitwiseEqual': exact,
                                    'timestampDifferenceSeconds': float(stamp - original_stamp),
                                    'maximumRelativeDifference': float(normalized)})
    assert kept == 373, kept
    assert len(comparisons) == 63, len(comparisons)
    return kept, comparisons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-directory', type=Path,
                        help='An existing replay directory can be verified with --verify-only.')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    work = args.work_directory or Path(tempfile.mkdtemp(prefix='mhd-claude-30min-'))
    work.mkdir(parents=True, exist_ok=True)
    prior = json.loads((DEST / 'verification.json').read_text()) if args.verify_only and (DEST / 'verification.json').exists() else {}
    inputs = [SOURCE / 'src/mhd/helio', SOURCE / 'src/mhd/helio.cu', SOURCE / 'src/mhd/core.cuh',
              ORIGINAL / 'cfg.txt', ORIGINAL / 'bnd.bin', ORIGINAL / 'tracks.bin',
              ORIGINAL / 'cme.txt', ORIGINAL / 'slices.bin', ORIGINAL / 'probes.bin']
    receipts = [{'path': str(path.relative_to(APP.parent / 'mhd_llm')),
                 'bytes': path.stat().st_size, 'sha256': digest(path)} for path in inputs]
    started = time.time()
    print(f'Replay directory: {work}', flush=True)
    if not args.verify_only:
        for path in inputs:
            if path.name not in ('slices.bin', 'probes.bin', 'helio.cu'):
                shutil.copy2(path, work / path.name)
        patched = add_output_only_hook((SOURCE / 'src/mhd/helio.cu').read_text())
        (work / 'helio.cu').write_text(patched)
        subprocess.run(['nvcc', *FLAGS, '-o', str(work / 'helio-movie'), str(work / 'helio.cu')],
                       cwd=work, check=True)
        config = {}
        for line in (ORIGINAL / 'cfg.txt').read_text().splitlines():
            key, value = line.split('=', 1)
            config[key.strip()] = value.strip()
        assert config['probe_dt_s'] == '1800'
        changes = {'bnd_file': str(work / 'bnd.bin'), 'track_file': str(work / 'tracks.bin'),
                   'cme_file': str(work / 'cme.txt'), 'out_dir': str(work),
                   'stop_file': str(work / 'STOP'), 't_end_s': str(END_S),
                   'movie_probe_slices': '1'}
        config.update(changes)
        (work / 'cfg.txt').write_text(''.join(f'{key} = {value}\n' for key, value in config.items()))
        print('Unchanged 512 × 120 × 360 numerical kernels and integration clock; extra output at existing probe callbacks.', flush=True)
        with (work / 'stdout.txt').open('wb') as stream:
            subprocess.run([str(work / 'helio-movie'), str(work / 'cfg.txt')],
                           cwd=work, stdout=stream, stderr=subprocess.STDOUT, check=True)
    target = DEST / 'slices.bin'
    verification_started = time.time()
    count, comparisons = compare_and_retain(work / 'movie-slices.bin', target)
    produced_probes = (work / 'probes.bin').read_bytes()
    original_probes = (ORIGINAL / 'probes.bin').read_bytes()
    assert original_probes[:8] == produced_probes[:8]
    bodies, fields = struct.unpack('2i', produced_probes[:8])
    probe_type = np.dtype([('seconds', '<f8'), ('fields', '<f4', (bodies, fields))])
    actual_probes = np.frombuffer(produced_probes[8:], dtype=probe_type)
    expected_probes = np.frombuffer(original_probes[8:len(produced_probes)], dtype=probe_type)
    assert actual_probes['fields'].tobytes() == expected_probes['fields'].tobytes(), 'Moving-probe primitive values changed'
    timestamp_error = float(np.max(np.abs(actual_probes['seconds'] - expected_probes['seconds'])))
    assert timestamp_error < 1e-6
    for path, receipt in zip(inputs, receipts):
        assert digest(path) == receipt['sha256'], f'Original input changed: {path}'
    replay_wall = float(re.search(r'done steps=\d+ wall=([\d.]+)', (work / 'log.txt').read_text())[1])
    environment = {'gpu': subprocess.check_output(['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'], text=True).strip(),
                   'nvcc': subprocess.check_output(['nvcc', '--version'], text=True).strip(),
                   'effectiveConfigSha256': digest(work / 'cfg.txt')}
    report = {'schemaVersion': 1, 'method': 'Selected production solver and retained boundary inputs; output-only hook extracts slices after existing 1800 s probe callbacks. Original 10800 s slice clock and all numerical kernels remain unchanged.',
              'originalRun': 'prod_da3_ccmc_prod_t4_L1ref_L2',
              'solverDimensions': [512, 120, 360], 'sliceDimensions': [320, 360, 5],
              'startMjd': 61006.25, 'endMjd': 61014.0, 'nativeCadenceMinutes': 30,
              'slices': count, 'originalCadenceMinutes': 180,
              'probeCadenceUnchangedSeconds': 1800,
              'integrationBoundaryPolicy': 'The original probe and slice clocks and their floating-point accumulation are unchanged. Extra read-only extraction after probe callbacks introduces no new timestep boundary.',
              'originalInputsUnchanged': True, 'sourceReceipts': receipts,
              'coincidentComparisons': comparisons,
              'allCoincidentSlicesBitwiseEqual': all(row['bitwiseEqual'] for row in comparisons),
              'bitwiseEqualityScope': 'The five primitive-field arrays; timestamp bytes are checked separately.',
              'maximumTimestampDifferenceSeconds': max(abs(row['timestampDifferenceSeconds']) for row in comparisons),
              'generatedArchive': {'path': 'runtime/claude-30min/slices.bin',
                                   'bytes': target.stat().st_size, 'sha256': digest(target)},
              'compilerFlags': FLAGS, 'outputHookBuilderSha256': digest(__file__),
              'compiledExecutableSha256': digest(work / 'helio-movie'),
              'patchedSourceSha256': digest(work / 'helio.cu'),
              'runtimeEnvironment': environment,
              'probeVerification': {'allPrimitiveValuesBitwiseIdentical': True,
                                    'recordsCompared': len(actual_probes),
                                    'bodies': bodies, 'fieldsPerBody': fields,
                                    'maximumTimestampDifferenceSeconds': timestamp_error,
                                    'timestampQualification': 'Stopping exactly at the movie endpoint clamps the last timestamp; primitive values remain bitwise identical.',
                                    'bytesCompared': len(produced_probes),
                                    'originalSha256': digest(ORIGINAL / 'probes.bin'),
                                    'generatedSha256': digest(work / 'probes.bin'),
                                    'retainedPath': 'runtime/claude-30min/probes.bin'},
              'wallSeconds': prior.get('wallSeconds', time.time() - started),
              'solverWallSeconds': replay_wall,
              'receiptVerificationSeconds': time.time() - verification_started,
              'rebuild': 'python scripts/refine_claude_movie.py'}
    (DEST / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    shutil.copy2(DEST / 'verification.json', APP / 'public/data/claude-temporal-refinement.json')
    for name in ['cfg.txt', 'stdout.txt', 'log.txt', 'probes.bin']:
        if (work / name).exists():
            shutil.copy2(work / name, DEST / name)
    print(f'Verified {count} slices; {len(comparisons)} coincide with original archive.', flush=True)


if __name__ == '__main__':
    main()
