"""Check that the finer Claude movie contains new solver states, not extra blends."""
import hashlib
import importlib.util
import json
import struct
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'public/data/claude-temporal-refinement.json'
spec = importlib.util.spec_from_file_location('claude_output', ROOT / 'scripts/refine_claude_movie.py')
output_hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(output_hook)


def archive(path):
    with path.open('rb') as stream:
        nr, nphi, fields = struct.unpack('3i', stream.read(12))
        stream.read(8)
    dtype = np.dtype([('seconds', '<f8'), ('fields', '<f4', (fields, nr, nphi))])
    assert (path.stat().st_size - 20) % dtype.itemsize == 0
    return np.memmap(path, dtype=dtype, mode='r', offset=20)


class OutputHook(unittest.TestCase):
    def test_extra_extraction_changes_no_numerical_kernel_or_timestep_expression(self):
        original = (ROOT.parent / 'mhd_llm/claude/src/mhd/helio.cu').read_text()
        patched = output_hook.add_output_only_hook(original)
        self.assertEqual(original.split('int main(')[0], patched.split('int main(')[0])
        start, end = '        CK(cudaMemset(d_red, 0, 12));', '        if (step % 500 == 0) {'
        self.assertEqual(original.split(start)[1].split(end)[0], patched.split(start)[1].split(end)[0])
        self.assertIn('next_slice += slice_dt / T0', patched)
        self.assertIn('if (fmovie) do_slice(tau, fmovie); next_probe += probe_dt / T0;', patched)


@unittest.skipUnless(RECEIPT.exists(), 'Verified finer-cadence solver replay has not been generated.')
class ClaudeNativeRefinement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.fine = archive(ROOT / cls.receipt['generatedArchive']['path'])
        cls.original = archive(ROOT.parent / 'mhd_llm/claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/slices.bin')

    def test_replay_preserves_selected_physics_and_original_states(self):
        self.assertEqual(self.receipt['solverDimensions'], [512, 120, 360])
        self.assertEqual(self.receipt['probeCadenceUnchangedSeconds'], 1800)
        self.assertTrue(self.receipt['originalInputsUnchanged'])
        self.assertEqual(len(self.receipt['coincidentComparisons']), 63)
        self.assertTrue(self.receipt['allCoincidentSlicesBitwiseEqual'])
        original_clock = self.original['seconds']
        for i in range(0, len(self.fine), 6):
            j = np.argmin(np.abs(original_clock - self.fine[i]['seconds']))
            self.assertLess(abs(original_clock[j] - self.fine[i]['seconds']), 1e-4)
            self.assertTrue(np.array_equal(self.original[j]['fields'], self.fine[i]['fields']))

    def test_thirty_minute_native_clock_and_generated_archive_receipt(self):
        self.assertEqual(len(self.fine), 373)
        self.assertTrue(np.allclose(np.diff(self.fine['seconds']), 1800, rtol=0, atol=1e-4))
        self.assertAlmostEqual(self.fine['seconds'][0] / 86400 + 60949, 61006.25)
        self.assertAlmostEqual(self.fine['seconds'][-1] / 86400 + 60949, 61014)
        path = ROOT / self.receipt['generatedArchive']['path']
        self.assertEqual(path.stat().st_size, self.receipt['generatedArchive']['bytes'])
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        self.assertEqual(digest.hexdigest(), self.receipt['generatedArchive']['sha256'])

    def test_three_dimensional_moving_probe_values_are_unchanged(self):
        proof = self.receipt['probeVerification']
        self.assertTrue(proof['allPrimitiveValuesBitwiseIdentical'])
        self.assertEqual(proof['recordsCompared'], 1105)
        self.assertEqual((proof['bodies'], proof['fieldsPerBody']), (12, 10))
        actual = (ROOT / proof['retainedPath']).read_bytes()
        original = (ROOT.parent / 'mhd_llm/claude/runs/prod_da3_ccmc_prod_t4_L1ref_L2/probes.bin').read_bytes()
        dtype = np.dtype([('seconds', '<f8'), ('fields', '<f4', (12, 10))])
        a = np.frombuffer(actual[8:], dtype=dtype)
        b = np.frombuffer(original[8:len(actual)], dtype=dtype)
        self.assertTrue(a['fields'].tobytes() == b['fields'].tobytes())
        self.assertLess(float(np.max(np.abs(a['seconds']-b['seconds']))), 1e-6)

    def test_intermediate_states_are_not_interpolated_three_hour_frames(self):
        # Every noncoincident half-hour state was computed by the same solver.
        # A cosmetic frame-rate increase would produce the Eulerian blend below
        # exactly; real intermediate evolution differs, especially near fronts.
        original_clock = self.original['seconds']
        relative_l1 = []
        for i in (1, 7, 55, 101, 181, 245, 311, 367):
            native = self.fine[i]
            hi = np.searchsorted(original_clock, native['seconds'])
            lo = hi - 1
            weight = (native['seconds'] - original_clock[lo]) / (original_clock[hi] - original_clock[lo])
            actual = native['fields'][0] * native['fields'][1]
            low = self.original[lo]['fields'][0] * self.original[lo]['fields'][1]
            high = self.original[hi]['fields'][0] * self.original[hi]['fields'][1]
            blend = low * (1 - weight) + high * weight
            relative_l1.append(float(np.sum(np.abs(actual - blend)) / np.sum(actual)))
        self.assertGreater(min(relative_l1), 1e-5)
        self.assertGreater(max(relative_l1), 1e-3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
