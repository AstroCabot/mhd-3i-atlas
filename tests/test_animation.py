"""Native-source, encoded-media and physical-clock regression checks."""
import hashlib
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('animation_builder', ROOT / 'scripts/build_animation_v2.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
MANIFEST = json.loads((ROOT / 'public/data/animation-v2.json').read_text())


class Animation(unittest.TestCase):
    def test_native_source_receipts(self):
        self.assertEqual(len(MANIFEST['sourceReceipts']), 119)
        for receipt in MANIFEST['sourceReceipts']:
            source = builder.SOURCE / receipt['path']
            self.assertEqual(source.stat().st_size, receipt['bytes'], receipt['path'])
            self.assertEqual(builder.digest(source), receipt['sha256'], receipt['path'])

    def test_actual_native_support_and_clock(self):
        self.assertEqual(MANIFEST['models']['argon']['nativeSliceDimensions'], [160, 180])
        self.assertEqual(MANIFEST['models']['codex']['nativeSliceDimensions'], [512, 512])
        self.assertEqual(MANIFEST['models']['claude']['nativeSliceDimensions'], [320, 360])
        self.assertEqual(MANIFEST['models']['codex']['nominalCadenceHours'], 6)
        self.assertTrue(np.allclose(np.diff(MANIFEST['timeMjd']), .125))
        for model in MANIFEST['models'].values():
            self.assertLessEqual(model['usedNativeTimeMjd'][0], MANIFEST['startMjd'])
            self.assertGreaterEqual(model['usedNativeTimeMjd'][-1], MANIFEST['endMjd'])
            self.assertTrue(model['verification']['noExtrapolation'])
            self.assertTrue(model['verification']['nativeCoverageMaskApplied'])

    def test_encoded_media(self):
        for model in MANIFEST['models'].values():
            for media in model['media'].values():
                path = ROOT / 'public' / media['url'].lstrip('/')
                self.assertEqual(path.stat().st_size, media['bytes'])
                self.assertEqual(builder.digest(path), media['sha256'])
                data = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(path)]))
                stream = data['streams'][0]
                self.assertEqual((stream['width'], stream['height']), (768, 768))
                self.assertEqual(int(stream['nb_frames']), 1440)
                self.assertEqual(stream['r_frame_rate'], '30/1')
                self.assertAlmostEqual(float(stream['duration']), 48)

    def test_portable_frame_sequence(self):
        for model in MANIFEST['models'].values():
            sequence = model['frameSequence']
            self.assertEqual(sequence['frameCount'], 373)
            self.assertEqual(sequence['displayCadenceMinutes'], 30)
            self.assertEqual(sequence['timeMjd'][0], MANIFEST['startMjd'])
            self.assertEqual(sequence['timeMjd'][-1], MANIFEST['endMjd'])
            self.assertTrue(np.allclose(np.diff(sequence['timeMjd']), 1/48))
            for rows in sequence['fields'].values():
                self.assertEqual(len(rows), 373)
                for row in rows:
                    path = ROOT / 'public' / row['url'].lstrip('/')
                    self.assertEqual(builder.digest(path), row['sha256'])
                    with Image.open(path) as image:
                        self.assertEqual(image.size, (768, 768))

    def test_portable_colours_against_native_fields(self):
        indices = np.array([149, 227, 305, 462, 540, 618])
        axis = np.linspace(-2.4, 2.4, 768, dtype=np.float32)
        xx, yy = np.meshgrid(axis[indices], axis[indices])
        t = MANIFEST['models']['argon']['frameSequence']['timeMjd'][186]
        tables = builder.lookup_table()
        for model in ('argon', 'codex', 'claude'):
            times, fields, radius, _ = builder.load_native(model, xx, yy)
            hi = np.searchsorted(times, t, side='right')
            lo = hi - 1
            weight = (t-times[lo])/(times[hi]-times[lo])
            values = fields[lo]*np.float32(1-weight)+fields[hi]*np.float32(weight)
            valid = np.isfinite(fields[lo]) & np.isfinite(fields[hi]) & (fields[lo] > 0) & (fields[hi] > 0)
            for field in ('flux', 'contrast'):
                physical = values if field == 'flux' else values*radius*radius
                expected = builder.colorize(physical, valid, tables[field])[::-1]
                row = MANIFEST['models'][model]['frameSequence']['fields'][field][186]
                with Image.open(ROOT / 'public' / row['url'].lstrip('/')) as image:
                    decoded = np.asarray(image)
                actual = decoded[(767-indices)[:,None],indices[None,:]]
                error = np.abs(actual.astype(float)-expected.astype(float))[valid]
                self.assertLess(np.median(error), 5, (model,field))
                self.assertLess(np.percentile(error,95), 18, (model,field))

    def test_encoded_colour_matches_native_physical_interpolation(self):
        # Decode a middle display epoch and compare scattered covered pixels to
        # values independently resampled from the actual native files. This
        # checks native geometry, frame clock, r² transform and north-up output
        # together. Lossy video introduces a small bounded RGB error.
        indices = np.array([149, 227, 305, 462, 540, 618])
        axis = np.linspace(-2.4, 2.4, 768, dtype=np.float32)
        xx, yy = np.meshgrid(axis[indices], axis[indices])
        t = MANIFEST['startMjd'] + 720 / 1439 * (MANIFEST['endMjd'] - MANIFEST['startMjd'])
        tables = builder.lookup_table()
        for model in ('argon', 'codex', 'claude'):
            times, fields, radius, meta = builder.load_native(model, xx, yy)
            hi = np.searchsorted(times, t, side='right')
            lo = hi - 1
            w = (t - times[lo]) / (times[hi] - times[lo])
            values = fields[lo] * np.float32(1 - w) + fields[hi] * np.float32(w)
            valid = np.isfinite(fields[lo]) & np.isfinite(fields[hi]) & (fields[lo] > 0) & (fields[hi] > 0)
            for field in ('flux', 'contrast'):
                physical = values if field == 'flux' else values * radius * radius
                expected = builder.colorize(physical, valid, tables[field])[::-1]
                path = ROOT / 'public' / MANIFEST['models'][model]['media'][field]['url'].lstrip('/')
                raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-vf', 'select=eq(n\\,720)', '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
                decoded = np.frombuffer(raw, np.uint8).reshape(768, 768, 3)
                actual = decoded[(767 - indices)[:, None], indices[None, :]]
                error = np.abs(actual.astype(float) - expected.astype(float))[valid]
                self.assertLess(np.median(error), 4, (model, field))
                self.assertLess(np.percentile(error, 95), 14, (model, field))
                self.assertTrue(np.all(np.abs(decoded[0, 0].astype(float) - builder.BACKGROUND) < 5))


if __name__ == '__main__':
    unittest.main(verbosity=2)
