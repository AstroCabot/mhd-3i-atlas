#!/usr/bin/env python3
"""Render retained native solar-wind samples to continuous, provenance-bearing videos.

Read-only access to ../mhd_llm. Claude's optional app-owned 30-minute solver
replay is verified by refine_claude_movie.py against the original archive.
Output frames interpolate *physical flux*, not RGB or log flux, between
consecutive native epochs, then apply a fixed logarithmic colour map.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy.interpolate import RegularGridInterpolator

APP = Path(__file__).resolve().parents[1]
SOURCE = APP.parent / 'mhd_llm'
DEST = APP / 'public/assets/animation-v2'
MANIFEST = APP / 'public/data/animation-v2.json'
START, END = 61006.25, 61014.0
# Inferno, sampled from the perceptually uniform Matplotlib map at fixed stops.
PALETTE = [[0, 0, 4], [31, 12, 72], [85, 15, 109], [136, 34, 106],
           [186, 54, 85], [227, 89, 51], [249, 140, 10], [249, 201, 50], [252, 255, 164]]
BACKGROUND = [12, 16, 20]
LIMITS = {'flux': [1e7, 3e10], 'contrast': [1e7, 2e9]}
RECEIPTS = {}
REFINEMENT = APP / 'public/data/claude-temporal-refinement.json'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def source(rel):
    path = SOURCE / rel
    if rel not in RECEIPTS:
        RECEIPTS[rel] = {'path': rel, 'bytes': path.stat().st_size, 'sha256': digest(path)}
    return path


def periodic_sample(r, p, a, radius, longitude):
    extended = np.r_[p[-1] - 2 * np.pi, p, p[0] + 2 * np.pi]
    values = np.concatenate([a[:, -1:], a, a[:, :1]], axis=1)
    return RegularGridInterpolator((r, extended), values, bounds_error=False, fill_value=np.nan)(
        np.column_stack([radius.ravel(), longitude.ravel()])).reshape(radius.shape).astype(np.float32)


def load_native(model, xx, yy, *, retained=False):
    radius = np.hypot(xx, yy)
    longitude = np.arctan2(yy, xx) % (2 * np.pi)
    if model == 'argon':
        native = []
        times = []
        for path in sorted((SOURCE / 'argon/outputs/runs').glob('model3_assimilated_slice_*.bin')):
            with source(str(path.relative_to(SOURCE))).open('rb') as f:
                times.append(struct.unpack('d', f.read(8))[0])
                a = np.frombuffer(f.read(), np.float32).reshape(4, 160, 180)
                native.append(a[2])
        # Invert the producer's constant solar-latitude cone after its projection
        # into fixed-J2000 ecliptic xy; do not silently treat it as the ecliptic.
        coordinate = 'codex/observations/coordinate_system.json'
        rotation = np.array(json.loads(source(coordinate).read_text())['ecliptic_to_solar_equatorial_matrix'])
        latitude = np.deg2rad(-6.455)
        inv = np.linalg.inv(rotation.T[:2, :2])
        u = np.column_stack([xx.ravel(), yy.ravel()]) @ inv.T
        k = inv @ rotation.T[:2, 2] * np.tan(latitude)
        dot = u @ k
        den = 1 - k @ k
        projected_radius = (-dot + np.sqrt(dot * dot + den * np.sum(u * u, axis=1))) / den
        hxy = u - projected_radius[:, None] * k
        radius = (projected_radius / np.cos(latitude)).reshape(xx.shape)
        longitude = np.arctan2(hxy[:, 1], hxy[:, 0]).reshape(xx.shape) % (2 * np.pi)
        r = .1 + (np.arange(160) + .5) * 2.3 / 160
        p = (np.arange(180) + .5) * 2 * np.pi / 180
        sampler = lambda a: periodic_sample(r, p, a, radius, longitude)
        meta = {'name': 'Argon', 'reference': 'model3_assimilated', 'solverDimensions': [160, 32, 180],
                'nativeSliceDimensions': [160, 180], 'nativeSliceAxes': ['radius', 'longitude'],
                'nativePlane': 'Solar latitude −6.455° cone, projected into J2000 ecliptic x/y',
                'definition': 'nₚ |v|', 'nominalCadenceHours': 3,
                'qualification': 'Retained movie is the baseline run; the quantitative comet reference is the separate 224 × 48 × 240 run.',
                'supportRadiusAu': [float(r[0]), float(r[-1])]}
    elif model == 'claude':
        refinement = None
        original_path = source('claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/slices.bin')
        if REFINEMENT.exists() and not retained:
            refinement = json.loads(REFINEMENT.read_text())
            generated = refinement['generatedArchive']
            path = APP / generated['path']
            if not path.exists():
                raise FileNotFoundError('Regenerate the verified Claude native archive with '
                                        'python scripts/refine_claude_movie.py before rebuilding animations.')
            assert path.stat().st_size == generated['bytes'] and digest(path) == generated['sha256']
            assert refinement['originalInputsUnchanged']
            assert refinement['allCoincidentSlicesBitwiseEqual'], 'Refined movie must reproduce every coincident original slice bit for bit.'
            assert len(refinement['coincidentComparisons']) == 63
        else:
            path = original_path
        with path.open('rb') as f:
            nr, nphi, nf = struct.unpack('3i', f.read(12))
            ri, ro = struct.unpack('2f', f.read(8))
        record_bytes = 8 + 4 * nr * nphi * nf
        assert (path.stat().st_size - 20) % record_bytes == 0
        count = (path.stat().st_size - 20) // record_bytes
        times = []
        native = []
        # Only read flux samples bracketing the common interval; the complete
        # archive hash and binary dimensions are still retained in receipts.
        with path.open('rb') as f:
            f.seek(20)
            for i in range(count):
                t = round(struct.unpack('d', f.read(8))[0] / 86400 + 60949, 10)
                a = np.frombuffer(f.read(record_bytes - 8), np.float32).reshape(nf, nr, nphi)
                times.append(t)
                native.append((a[0] * a[1] * 1e5) if START - .126 <= t <= END + .126 else None)
        r = ri + (np.arange(nr) + .5) * (ro - ri) / nr
        p = (np.arange(nphi) + .5) * 2 * np.pi / nphi
        sampler = lambda a: periodic_sample(r, p, a, radius, longitude)
        meta = {'name': 'Claude', 'reference': 'prod_da3_ccmc_prod_t4_L1ref_L2', 'solverDimensions': [512, 120, 360],
                'nativeSliceDimensions': [nr, nphi], 'nativeSliceAxes': ['radius', 'longitude'],
                'nativePlane': 'J2000 ecliptic z = 0', 'definition': 'nₚ vᵣ, radial proton-flux proxy',
                'nominalCadenceHours': .5 if refinement else 3,
                'originalRetainedCadenceHours': 3,
                'temporalSource': ('Verified replay of the selected production solver with 30-minute slice output at existing 30-minute probe boundaries.'
                                   if refinement else 'Original retained production archive at three-hour cadence.'),
                'qualification': 'The saved slice contains radial speed rather than the complete velocity vector.',
                'supportRadiusAu': [float(r[0]), float(r[-1])]}
        if refinement:
            meta['temporalRefinement'] = {
                'receipt': '/data/claude-temporal-refinement.json',
                'nativeCadenceMinutes': refinement['nativeCadenceMinutes'],
                'coincidentOriginalSlices': len(refinement['coincidentComparisons']),
                'allCoincidentSlicesBitwiseEqual': refinement['allCoincidentSlicesBitwiseEqual'],
                'generatedArchiveSha256': refinement['generatedArchive']['sha256'],
                'integrationBoundaryPolicy': refinement['integrationBoundaryPolicy']}
    elif model == 'enlil':
        from prepare_ccmc_movie import load_native as load_ccmc
        return load_ccmc(xx, yy)
    else:
        base = 'codex/results/ct156_w30_theta40_phi192/'
        index = pd.read_csv(source(base + 'snapshots.csv'))
        times = index.day.to_numpy() + 60980
        x = np.load(source(base + 'ecliptic_x_au.npy'))
        y = np.load(source(base + 'ecliptic_y_au.npy'))
        native = [np.load(source(base + file)) for file in index.file]
        sampler = lambda a: RegularGridInterpolator((y, x), a, bounds_error=False, fill_value=np.nan)(
            np.column_stack([yy.ravel(), xx.ravel()])).reshape(xx.shape).astype(np.float32)
        meta = {'name': 'Codex', 'reference': 'ct156_w30_theta40_phi192', 'solverDimensions': [156, 40, 192],
                'nativeSliceDimensions': list(native[0].shape), 'nativeSliceAxes': ['Cartesian y', 'Cartesian x'],
                'nativePlane': 'J2000 ecliptic z = 0', 'definition': 'nₚ |v|', 'nominalCadenceHours': 6,
                'qualification': 'Retained 512² flux rasters interpolate the CT conserved state; they do not supply 512² independent solver cells. Missing outside the retained cell-centre support (outer radius about 2.293 AU).',
                'retainedExtentAu': [float(x[0]), float(x[-1]), float(y[0]), float(y[-1])]}
    times = np.asarray(times)
    assert np.all(np.diff(times) > 0) and times[0] <= START < END <= times[-1]
    selected = np.arange(max(0, np.searchsorted(times, START, side='right') - 1),
                         min(len(times), np.searchsorted(times, END, side='left') + 1))
    projected = [sampler(native[i]) for i in selected]
    meta['nativeTimeMjd'] = times.tolist()
    meta['usedNativeTimeMjd'] = times[selected].tolist()
    meta['actualCadenceHours'] = {'minimum': float(np.min(np.diff(times)) * 24),
                                 'median': float(np.median(np.diff(times)) * 24),
                                 'maximum': float(np.max(np.diff(times)) * 24)}
    assert all(a.shape == xx.shape for a in projected)
    return times[selected], projected, radius.astype(np.float32), meta


def lookup_table():
    # Index by log10 physical flux over a wide fixed domain. The 65k table adds
    # under 0.00022 dex of colour quantization; scalar fields are not quantized.
    log_values = np.linspace(2, 16, 65536)
    palette = np.asarray(PALETTE, float)
    result = {}
    for field, limits in LIMITS.items():
        position = np.clip((log_values - np.log10(limits[0])) / np.log10(limits[1] / limits[0]), 0, 1) * (len(palette) - 1)
        left = np.minimum(position.astype(int), len(palette) - 2)
        weight = (position - left)[:, None]
        result[field] = np.rint(palette[left] * (1 - weight) + palette[left + 1] * weight).astype(np.uint8)
    return result


def colorize(values, valid, table):
    safe = np.where(valid, values, 100).astype(np.float32)
    codes = np.clip(np.rint((np.log10(safe) - 2) / 14 * 65535), 0, 65535).astype(np.uint16)
    rgb = table[codes]
    rgb[~valid] = BACKGROUND
    return np.ascontiguousarray(rgb[::-1])  # North at the top, no inverted axes.


def encoder(path, size, fps):
    return subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', f'{size}x{size}', '-framerate', str(fps), '-i', '-', '-an', '-c:v', 'libx264',
        '-preset', 'fast', '-threads', '2', '-crf', '19', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
        '-g', str(fps), '-movflags', '+faststart', str(path)], stdin=subprocess.PIPE)


def render(model, size, fps, seconds):
    axis = np.linspace(-2.4, 2.4, size, dtype=np.float32)
    xx, yy = np.meshgrid(axis, axis)
    times, arrays, radius, meta = load_native(model, xx, yy)
    basename = f'{model}-native30m' if meta.get('temporalRefinement') else model
    tables = lookup_table()
    frame_count = round(fps * seconds)
    video_times = np.linspace(START, END, frame_count)
    writers = {field: encoder(DEST / f'{basename}-{field}.mp4', size, fps) for field in LIMITS}
    posters = {0, int(np.argmin(np.abs(video_times - 61012.75)))}
    valid_counts = []
    max_relative_error = 0.0
    try:
        for i, t in enumerate(video_times):
            high = min(np.searchsorted(times, t, side='right'), len(times) - 1)
            low = max(0, high - 1)
            w = (t - times[low]) / (times[high] - times[low]) if high != low else 0
            assert 0 <= w <= 1 and times[low] <= t <= times[high]
            valid = np.isfinite(arrays[low]) & np.isfinite(arrays[high]) & (arrays[low] > 0) & (arrays[high] > 0)
            flux = arrays[low] * np.float32(1 - w) + arrays[high] * np.float32(w)
            valid_counts.append(int(np.count_nonzero(valid)))
            # Direct arithmetic oracle at a stable, physically covered pixel.
            if i in (0, frame_count // 2, frame_count - 1):
                cells = np.flatnonzero(valid)
                assert len(cells)
                p = cells[len(cells) // 2]
                oracle = float(arrays[low].flat[p]) * (1 - w) + float(arrays[high].flat[p]) * w
                error = abs(float(flux.flat[p]) - oracle) / oracle
                max_relative_error = max(max_relative_error, error)
                assert error < 2e-7
            for field, writer in writers.items():
                values = flux if field == 'flux' else flux * radius * radius
                rgb = colorize(values, valid, tables[field])
                writer.stdin.write(rgb.tobytes())
                if i in posters:
                    label = 'first' if i == 0 else 'observation'
                    Image.fromarray(rgb).save(DEST / f'{basename}-{field}-{label}.jpg', quality=93)
            if i % (fps * 8) == 0:
                print(f'{model}: {i}/{frame_count} frames', flush=True)
    finally:
        for writer in writers.values():
            writer.stdin.close()
        for writer in writers.values():
            assert writer.wait() == 0, 'ffmpeg failed'
    meta['media'] = {}
    for field in LIMITS:
        path = DEST / f'{basename}-{field}.mp4'
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))
        stream = probe['streams'][0]
        assert int(stream['nb_frames']) == frame_count
        assert stream['width'] == stream['height'] == size
        assert stream['r_frame_rate'] == f'{fps}/1'
        assert abs(float(probe['format']['duration']) - seconds) < 1 / fps
        meta['media'][field] = {'url': f'/assets/animation-v2/{path.name}', 'bytes': path.stat().st_size,
                               'sha256': digest(path), 'poster': f'/assets/animation-v2/{basename}-{field}-observation.jpg',
                               'firstPoster': f'/assets/animation-v2/{basename}-{field}-first.jpg',
                               'codec': stream['codec_name'], 'frames': frame_count, 'fps': fps,
                               'width': size, 'height': size, 'durationSeconds': float(probe['format']['duration'])}
    meta['verification'] = {'physicalInterpolationMaxRelativeError': max_relative_error,
                            'minimumCoveredPixels': min(valid_counts), 'maximumCoveredPixels': max(valid_counts),
                            'noExtrapolation': True, 'no128PixelTileInputs': True, 'nativeCoverageMaskApplied': True,
                            'northAtTop': True, 'encodedFrameCountAndRateVerified': True}
    return meta


def render_image_sequence(model, size, seconds):
    """Portable display support, retaining exact physical interpolation at 30 min."""
    axis = np.linspace(-2.4, 2.4, size, dtype=np.float32)
    xx, yy = np.meshgrid(axis, axis)
    times, arrays, radius, meta = load_native(model, xx, yy)
    display_times = np.linspace(START, END, round((END - START) * 48) + 1)
    tables = lookup_table()
    basename = f'{model}-native30m' if meta.get('temporalRefinement') else model
    directory = DEST / 'frames' / basename
    directory.mkdir(parents=True, exist_ok=True)
    sequences = {field: [] for field in LIMITS}
    for i, t in enumerate(display_times):
        high = min(np.searchsorted(times, t, side='right'), len(times) - 1)
        low = max(0, high - 1)
        weight = (t - times[low]) / (times[high] - times[low]) if high != low else 0
        assert 0 <= weight <= 1 and times[low] <= t <= times[high]
        valid = np.isfinite(arrays[low]) & np.isfinite(arrays[high]) & (arrays[low] > 0) & (arrays[high] > 0)
        flux = arrays[low] * np.float32(1 - weight) + arrays[high] * np.float32(weight)
        for field in LIMITS:
            values = flux if field == 'flux' else flux * radius * radius
            rgb = colorize(values, valid, tables[field])
            path = directory / f'{field}-{i:03d}.webp'
            Image.fromarray(rgb).save(path, format='WEBP', quality=84, method=4)
            sequences[field].append({'url': f'/assets/animation-v2/frames/{basename}/{path.name}',
                'frame': i, 'timeMjd': float(t), 'bytes': path.stat().st_size, 'sha256': digest(path)})
        if i % 60 == 0:
            print(f'{model}: {i}/{len(display_times)} portable frames', flush=True)
    native_support = bool(meta.get('temporalRefinement'))
    return {'width': size, 'height': size, 'frameCount': len(display_times), 'durationSeconds': seconds,
        'displayCadenceMinutes': 30, 'timeMjd': display_times.tolist(), 'fields': sequences,
        'supportEpochsAreNativeSolverOutputs': native_support,
        'physicalInterpolation': ('Every 30-minute display-support epoch is a native solver output from the verified production replay; only continuous browser playback blends adjacent image colours.'
                                  if native_support else 'Bounded linear interpolation of physical flux between actual native epochs before logarithmic colour mapping.'),
        'browserInterpolation': 'Linear RGB opacity crossfade between adjacent 30 min display-support images at requestAnimationFrame cadence; a display interpolation, not a new physical sample.',
        'format': 'WebP', 'quality': 84}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size', type=int, default=768)
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--seconds', type=float, default=48)
    parser.add_argument('--model', choices=['argon', 'codex', 'claude', 'enlil'])
    parser.add_argument('--images-only', action='store_true', help='Add portable image sequences to the existing native-video manifest.')
    parser.add_argument('--with-images', action='store_true', help='Build videos and portable images before publishing one coherent manifest.')
    args = parser.parse_args()
    if args.images_only and args.with_images:
        parser.error('--images-only and --with-images are mutually exclusive')
    assert shutil.which('ffmpeg') and shutil.which('ffprobe')
    DEST.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if (args.model or args.images_only) and MANIFEST.exists() else {'models': {}}
    manifest.update({'schemaVersion': 2, 'builder': 'scripts/build_animation_v2.py', 'builderSha256': digest(__file__),
        'width': args.size, 'height': args.size, 'fps': args.fps, 'durationSeconds': args.seconds,
        'frameCount': round(args.fps * args.seconds), 'startMjd': START, 'endMjd': END,
        'startUtc': '2025-11-27T06:00:00Z', 'endUtc': '2025-12-05T00:00:00Z',
        'timeMjd': np.arange(START, END + 1e-8, .125).tolist(),
        'clock': 'Physical geometric UTC, not photon-arrival UTC.',
        'timeMapping': 'video frame i corresponds to startMjd + i/(frameCount−1) × (endMjd−startMjd). Displayed UTC clamps at the final encoded frame.',
        'temporalInterpolation': ('Claude uses verified native 30-minute solver re-outputs; Argon retains approximately 3-hour output, while Codex and CCMC retain approximately 6-hour output. Between native epochs, bounded linear physical-flux interpolation precedes logarithmic colour mapping. Display fps adds no independent simulation information.'
                                  if REFINEMENT.exists() else 'Bounded linear physical-flux interpolation between consecutive original native epochs precedes logarithmic colour mapping. Native support is approximately three hours for Argon and Claude, and six hours for Codex. Display fps adds no independent simulation information.'),
        'spatialInterpolation': 'Bilinear interpolation from native retained plane samples directly to the 768² display raster; no 128² tile input, no extrapolation. Spatial display pixels are not independent solver cells.',
        'extentAu': [-2.4, 2.4, -2.4, 2.4],
        'projection': 'Sun-centred fixed-J2000 ecliptic x/y, viewed from ecliptic north; vernal equinox to the right. Argon cone is projected, not replaced by an ecliptic sample.',
        'fluxLimits': LIMITS['flux'], 'contrastLimits': LIMITS['contrast'],
        'units': {'flux': 'cm⁻² s⁻¹', 'contrast': 'cm⁻² s⁻¹ AU²'},
        'contrastDefinition': 'Native flux multiplied by true native-plane heliocentric radius² (AU²).',
        'palette': PALETTE, 'background': BACKGROUND,
        'maskPolicy': 'A display pixel is missing if either bracketing native time sample has no finite positive source coverage; missing values retain the fixed background. No extrapolation across the radial support boundary.',
        'loopPolicy': 'End-to-start wrap restarts the finite physical observation interval; it is not a periodic simulation.',
        'rebuild': 'python scripts/build_animation_v2.py'})
    # Overlay tracks use the existing fixed-J2000 ephemeris product on its exact
    # timestamps. Re-sampling is bounded; video UTC never leaves that interval.
    science = json.loads((APP / 'public/data/science.json').read_text())['animation']
    manifest['tracks'] = {name: {axis: np.interp(manifest['timeMjd'], science['timeMjd'], row[axis]).tolist()
                                for axis in ('x', 'y')} for name, row in science['tracks'].items()}
    for model in ([args.model] if args.model else ['argon', 'codex', 'claude', 'enlil']):
        if args.images_only:
            if model == 'claude' and REFINEMENT.exists() and not manifest['models'][model].get('temporalRefinement'):
                raise SystemExit('Promote the refined Claude videos and metadata together: --model claude --with-images')
            manifest['models'][model]['frameSequence'] = render_image_sequence(model, args.size, args.seconds)
            manifest['defaultPlayback'] = 'Persistent paired 768px WebP layers, 30 min native or physically interpolated display support, continuous browser opacity crossfade. Native video downloads retained separately.'
            print(f'{model}: portable images encoded', flush=True)
        else:
            manifest['models'][model] = render(model, args.size, args.fps, args.seconds)
            print(f'{model}: videos encoded and checked', flush=True)
            if args.with_images:
                manifest['models'][model]['frameSequence'] = render_image_sequence(model, args.size, args.seconds)
                manifest['defaultPlayback'] = 'Persistent paired 768px WebP layers, 30 min native or physically interpolated display support, continuous browser opacity crossfade. Native video downloads retained separately.'
                print(f'{model}: portable images encoded', flush=True)
    prior = {item['path']: item for item in manifest.get('sourceReceipts', [])}
    prior.update(RECEIPTS)
    manifest['sourceReceipts'] = list(prior.values())
    for item in RECEIPTS.values():
        path = SOURCE / item['path']
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], 'Native input changed'
    manifest['verification'] = {'sourceHashesUnchanged': True, 'sharedLimitsAndProjection': True,
                               'nativeDimensionsReadFromArchive': True, 'sourceReadOnly': True}
    temporary = MANIFEST.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(MANIFEST)
    print(f'{MANIFEST.relative_to(APP)}; source receipts {len(manifest["sourceReceipts"])}', flush=True)


if __name__ == '__main__':
    main()
