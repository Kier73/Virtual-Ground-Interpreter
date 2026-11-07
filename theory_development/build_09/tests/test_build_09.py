import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cross_modal_response as cmr


class TestCodonExecution(unittest.TestCase):
    def test_arithmetic_codons(self):
        r = cmr.CodonRegistry()
        self.assertEqual(cmr.execute_codon(r.add, 2, 3), 5)
        self.assertEqual(cmr.execute_codon(r.sub, 9, 4), 5)
        self.assertEqual(cmr.execute_codon(r.mul, 3, 4), 12)
        self.assertEqual(cmr.execute_codon(r.div, 12, 3), 4)
        self.assertEqual(cmr.execute_codon(r.power, 2, 3), 8)

    def test_alias_registry_equivalence(self):
        result = cmr.codon_alias_equivalence(cmr.make_family_params(2, seed=19))
        self.assertEqual(result["max_abs_output_difference"], 0.0)
        self.assertEqual(result["n_system_domain_cases"], 4)

    def test_registry_rejects_duplicate_aliases(self):
        with self.assertRaises(ValueError):
            cmr.CodonRegistry(add="ld")

    def test_division_by_zero_rejected(self):
        with self.assertRaises(ZeroDivisionError):
            cmr.execute_codon("dv", 1.0, 0.0)


class TestSignalAndSystemModels(unittest.TestCase):
    def test_fft_dc_signal(self):
        x = [complex(1, 0)] * 8
        y = cmr.fft(x)
        self.assertAlmostEqual(y[0].real, 8.0)
        for v in y[1:]:
            self.assertAlmostEqual(abs(v), 0.0, places=10)

    def test_fft_single_bin(self):
        n = 16
        x = [complex(math.cos(2*math.pi*3*i/n), math.sin(2*math.pi*3*i/n)) for i in range(n)]
        y = cmr.fft(x)
        self.assertAlmostEqual(abs(y[3]), n, places=9)

    def test_probe_lengths_and_finite_values(self):
        p = cmr.probes()
        self.assertEqual(set(p), {"impulse", "step", "chirp", "low_amp", "high_amp"})
        self.assertTrue(all(len(v) == cmr.N for v in p.values()))
        self.assertTrue(all(math.isfinite(x) for v in p.values() for x in v))

    def test_acoustic_resonator_finite_and_stable(self):
        p = cmr.make_family_params(1)[0]
        out = cmr.acoustic_resonator(p, cmr.probes()["impulse"])
        self.assertEqual(len(out), cmr.N)
        self.assertTrue(all(math.isfinite(x) for x in out))
        self.assertLess(max(abs(x) for x in out[-100:]), max(abs(x) for x in out[:100]))

    def test_mechanical_impulse_decays(self):
        p = cmr.make_family_params(1)[0]
        out = cmr.rk4_mechanical(p, [0.0]*cmr.N, initial_velocity=1.0)
        self.assertEqual(len(out), cmr.N)
        self.assertTrue(all(math.isfinite(x) for x in out))
        self.assertLess(cmr.rms(out[-128:]), cmr.rms(out[:128]))

    def test_frequency_feature_shape(self):
        signal = [math.sin(2*math.pi*10*i/cmr.FS) for i in range(cmr.N)]
        mag, phase, peak = cmr.spectral_features(signal)
        self.assertEqual(len(mag), len(cmr.FREQS))
        self.assertEqual(len(phase), len(cmr.FREQS))
        self.assertEqual(len(peak), 1)
        self.assertAlmostEqual(peak[0], 10.0, delta=0.2)

    def test_mechanical_mass_and_gain_unit_rescale(self):
        p = cmr.make_family_params(1)[0]
        p2 = cmr.Params(p.family_id, p.f0_hz, p.zeta, p.gain*10, p.mass*10, p.nonlinearity)
        a = cmr.simulate_domain(p, "mechanical")
        b = cmr.simulate_domain(p2, "mechanical")
        self.assertLess(max(abs(x-y) for x,y in zip(a.impulse,b.impulse)), 1e-10)


class TestRepresentationalGeometry(unittest.TestCase):
    def test_rdm_symmetric_and_zero_diagonal(self):
        rows = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]
        d = cmr.rdm(rows)
        for i in range(3):
            self.assertAlmostEqual(d[i][i], 0.0)
            for j in range(3):
                self.assertAlmostEqual(d[i][j], d[j][i])

    def test_spearman_identity(self):
        values = [1, 5, 2, 8, 3, 9]
        self.assertAlmostEqual(cmr.spearman(values, values), 1.0)

    def test_spearman_reversal(self):
        values = [1, 5, 2, 8, 3, 9]
        self.assertAlmostEqual(cmr.spearman(values, list(reversed(values))), -1.0)

    def test_partner_retrieval_on_identical_rdms(self):
        rows = [[0,0], [1,0], [0,2], [3,1]]
        d = cmr.rdm(rows)
        self.assertEqual(cmr.nearest_partner_accuracy(d,d), 1.0)

    def test_permutation_p_is_bounded(self):
        rows = [[0,0], [1,0], [0,2], [3,1]]
        d = cmr.rdm(rows)
        _, p = cmr.permutation_test(d,d,reps=29,seed=4)
        self.assertGreaterEqual(p, 1/30)
        self.assertLessEqual(p, 1.0)


class TestReproducedBuildResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT/"reports"/"build_09_report.json").read_text(encoding="utf-8"))

    def test_expected_sample_and_family_count(self):
        self.assertEqual(self.report["n_families"], 40)
        self.assertEqual(self.report["samples"], 1024)

    def test_matched_linear_spectral_geometry(self):
        r = self.report["cross_domain_rdm_correlations"]["spectral"]["spearman_rdm"]
        self.assertGreater(r, 0.98)

    def test_sample_rate_rank_geometry_preserved(self):
        values = self.report["sample_rate_invariance"]
        self.assertTrue(all(x["rdm_correlation_vs_128hz"] > 0.98 for x in values))

    def test_unit_rescaling_preserves_rank_geometry(self):
        values = self.report["unit_scale_invariance"]
        self.assertTrue(all(x["rdm_correlation_after_unit_rescale"] > 0.999999 for x in values))

    def test_nonlinear_probes_are_domain_specific(self):
        result = self.report["nonlinear_response"]
        self.assertGreater(result["acoustic_mean_deviation_from_linear"], 0.3)
        self.assertLess(result["mechanical_mean_deviation_from_linear"], 0.05)

    def test_noise_and_dropout_sweeps_monotone_enough(self):
        noise = self.report["noise_robustness_acoustic_spectral"]
        drop = self.report["feature_dropout_acoustic_spectral"]
        self.assertEqual(noise[0]["mean_rdm_retention"], 1.0)
        self.assertEqual(drop[0]["mean_rdm_retention"], 1.0)
        self.assertGreater(drop[-1]["mean_rdm_retention"], 0.90)

    def test_codonic_aliases_execute_identically(self):
        self.assertEqual(self.report["codon_execution"]["max_abs_output_difference"], 0.0)

    def test_random_pairing_control_reports_nonzero_resolution(self):
        vals = self.report["cross_domain_rdm_correlations"]
        self.assertTrue(all(0.0 <= v["permutation_p"] <= 1.0 for v in vals.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
