"""Validate NASA comparisons, verbatim solver sources and report packaging."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parents[1]
SRC = APP.parent/'mhd_llm'
DATA = APP/'public/data'
sys.path.insert(0, str(APP/'scripts'))
from build_writeups import build


class ResearchProducts(unittest.TestCase):
    def test_nasa_shared_masks_and_residuals(self):
        comparison = json.loads((DATA/'nasa-comparison.json').read_text())
        for craft in comparison['spacecraft']:
            for field in ('density', 'speed', 'flux'):
                obs = np.array(craft['observed'][field], float)
                models = {key: np.array(row[field], float) for key, row in craft['models'].items()}
                mask = np.isfinite(obs) & (obs > 0)
                for values in models.values():
                    mask &= np.isfinite(values) & (values > 0)
                self.assertGreater(mask.sum(), 350)
                for key, values in models.items():
                    metric = craft['metrics'][key]
                    self.assertEqual(metric[field+'N'], mask.sum())
                    if field == 'speed':
                        self.assertAlmostEqual(metric['speedRmse'], np.sqrt(np.mean((values[mask]-obs[mask])**2)), places=8)
                        self.assertAlmostEqual(metric['speedBias'], np.mean(values[mask]-obs[mask]), places=8)
                        self.assertAlmostEqual(metric['speedR'], np.corrcoef(values[mask], obs[mask])[0, 1], places=8)
                    else:
                        self.assertAlmostEqual(metric[field+'MedianRatio'], np.median(values[mask]/obs[mask]), places=8)

    def test_nasa_density_is_converted_once(self):
        from build_science import enlil_native
        csv = pd.read_csv(SRC/'claude/ref/ccmc/timeseries/enlil_3I-Atlas.csv')
        native = enlil_native()
        np.testing.assert_allclose(native['density'], csv.n_cm3/1.2, rtol=1e-12)
        speed = np.sqrt(csv.vr_kms**2+csv.vlon_kms**2+csv.vlat_kms**2)
        np.testing.assert_allclose(native['flux'], csv.n_cm3/1.2*speed*1e5, rtol=1e-12)
        # The older rounded export has ALREADY undergone this conversion.
        old = np.load(SRC/'argon/data/processed/ccmc_extracted.npz')
        for time in [61012.5, 61013, 61013.4]:
            density = np.interp(time, native['timeMjd'], native['density'])
            rounded = np.interp(time, old['3I-Atlas1_mjd'], old['3I-Atlas1_n_cm3'])
            self.assertLess(abs(density-rounded), .006)

    def test_source_files_match_selected_native_bytes(self):
        catalogue = json.loads((DATA/'solver-code.json').read_text())
        receipts = json.loads((SRC/'codex/results/ct156_w30_theta40_phi192/input_code_provenance.json').read_text())
        self.assertEqual(len(catalogue['files']), 13)
        for row in catalogue['files']:
            original = (SRC/row['sourcePath']).read_bytes()
            self.assertEqual(original, (APP/'public'/row['rawUrl'].lstrip('/')).read_bytes())
            self.assertEqual(original.decode(), row['text'])
            self.assertEqual(hashlib.sha256(original).hexdigest(), row['sha256'])
            if row['agent'] == 'codex':
                self.assertEqual(row['sha256'], receipts[row['sourcePath'].removeprefix('codex/')])
            for method in row['methods']:
                self.assertIn(method['name'], row['text'].splitlines()[method['line']-1])

    def test_supplied_reports_are_verbatim(self):
        reports = json.loads((DATA/'model-writeups.json').read_text())['reports']
        self.assertEqual(len(reports), 3)
        for row in reports:
            raw = (APP/row['sourcePath']).read_bytes()
            self.assertEqual(row['status'], 'submitted')
            self.assertEqual(row['markdown'], raw.decode())
            self.assertEqual(row['sha256'], hashlib.sha256(raw).hexdigest())

    def test_pending_submission_and_precedence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'public/data').mkdir(parents=True)
            (root/'public/data/models.json').write_bytes((DATA/'models.json').read_bytes())
            self.assertTrue(all(row['status'] == 'pending' for row in build(root)['reports']))
            (root/'public/assets/reports').mkdir(parents=True)
            (root/'public/assets/reports/argon_report.md').write_text('# Original\n')
            self.assertEqual(build(root)['reports'][0]['markdown'], '# Original\n')
            (root/'content/model-writeups').mkdir(parents=True)
            report = root/'content/model-writeups/argon.md'
            report.write_text('# Revised α\n')
            self.assertEqual(build(root)['reports'][0]['markdown'], '# Revised α\n')
            self.assertEqual((root/'public/data/writeups/argon.md').read_bytes(), report.read_bytes())
            report.write_text('  \n')
            self.assertEqual(build(root)['reports'][0]['status'], 'pending')
            self.assertFalse((root/'public/data/writeups/argon.md').exists())


if __name__ == '__main__':
    unittest.main()
