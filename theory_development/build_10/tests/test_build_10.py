import math
import unittest
from dataclasses import replace
from random import Random

import build_10 as b


class Build10Tests(unittest.TestCase):
    def test_probe_set_is_complete(self):
        probes = b.probe_signals()
        self.assertEqual(set(probes), set(b.PROBE_NAMES))
        self.assertTrue(all(len(x) == b.N for x in probes.values()))

    def test_feature_vector_shape_and_finiteness(self):
        p = b.generate_acoustic(Random(1), 2)
        x = b.probe_signals()["chirp"]
        y = b.simulate_acoustic(p, x)
        features = b.extract_features(x, y)
        self.assertEqual(len(features), len(b.FEATURE_NAMES))
        self.assertTrue(all(math.isfinite(v) for v in features))

    def test_acoustic_mode_classes(self):
        self.assertEqual(len(b.generate_acoustic(Random(2), 0).modes), 2)
        self.assertEqual(len(b.generate_acoustic(Random(2), 1).modes), 3)
        self.assertIsNotNone(b.generate_acoustic(Random(2), 2).notch_hz)
        self.assertGreater(b.generate_acoustic(Random(2), 3).compression, 0.01)

    def test_acoustic_outputs_finite(self):
        x = b.probe_signals()["impulse"]
        for cls in range(4):
            y = b.simulate_acoustic(b.generate_acoustic(Random(10+cls), cls), x)
            self.assertEqual(len(y), len(x))
            self.assertTrue(all(math.isfinite(v) for v in y))

    def test_mechanical_mass_and_stiffness_positive_definite(self):
        for cls in range(4):
            p = b.generate_mechanical(Random(20+cls), cls)
            for mat in (p.mass, p.stiffness):
                self.assertGreater(mat[0][0], 0)
                self.assertGreater(mat[1][1], 0)
                self.assertGreater(mat[0][0]*mat[1][1]-mat[0][1]*mat[1][0], 0)

    def test_proportional_damping_control(self):
        p = b.generate_mechanical(Random(31), 0)
        self.assertLess(b.damping_nonproportionality(p), 1e-10)

    def test_nonproportional_damping_is_detected(self):
        p = b.generate_mechanical(Random(32), 1)
        self.assertGreater(b.damping_nonproportionality(p), 1e-4)

    def test_mechanical_modal_frequencies_positive(self):
        p = b.generate_mechanical(Random(33), 2)
        f1, f2 = b.mechanical_modal_frequencies(p)
        self.assertGreater(f1, 0)
        self.assertGreater(f2, f1)

    def test_mechanical_simulation_finite(self):
        x = b.probe_signals()["multisine"]
        for cls in range(4):
            y = b.simulate_mechanical(b.generate_mechanical(Random(40+cls), cls), x)
            self.assertEqual(len(y), len(x))
            self.assertTrue(all(math.isfinite(v) for v in y))

    def test_nonlinearity_changes_response_for_same_plant(self):
        p = b.generate_mechanical(Random(55), 3)
        x = b.probe_signals()["amplitude_staircase"]
        y_nl = b.simulate_mechanical(p, x)
        y_lin = b.simulate_mechanical(replace(p, cubic=(0.0, 0.0, 0.0)), x)
        rel = b.rms([a-c for a,c in zip(y_nl, y_lin)])/(b.rms(y_lin)+1e-12)
        self.assertGreater(rel, 0.05)

    def test_codon_alias_invariance(self):
        p = b.generate_mechanical(Random(61), 3)
        x = b.probe_signals()["multisine"]
        y0 = b.simulate_mechanical(p, x, registry=b.CodonRegistry())
        alias = b.CodonRegistry("load", "plus", "minus", "times", "divide", "pow", "write")
        y1 = b.simulate_mechanical(p, x, registry=alias)
        self.assertEqual(y0, y1)

    def test_codon_arithmetic(self):
        r = b.CodonRegistry()
        self.assertEqual(b.execute_codon(r.add, 2, 3), 5)
        self.assertEqual(b.execute_codon(r.mul, 2, 3), 6)
        self.assertEqual(b.execute_codon(r.power, 2, 3), 8)

    def test_posterior_normalizes(self):
        train = b.make_training("acoustic", 70, 3)
        models = b.fit_probe_models(train)
        model = models["impulse"]
        obs = model.means[1]
        post = b.posterior_update([0.25]*4, obs, model)
        self.assertAlmostEqual(sum(post), 1.0, places=10)
        self.assertTrue(all(p >= 0 for p in post))

    def test_information_gain_bounds(self):
        train = b.make_training("mechanical", 71, 3)
        models = b.fit_probe_models(train)
        prior = [0.25]*4
        ig = b.expected_information_gain(prior, models["chirp"])
        self.assertGreaterEqual(ig, 0.0)
        self.assertLessEqual(ig, b.entropy(prior)+1e-10)

    def test_active_feature_subset_matches_model(self):
        train = b.make_training("acoustic", 72, 3)
        models = b.fit_probe_models(train)
        self.assertEqual(len(models["step"].means[0]), len(b.ACTIVE_FEATURE_INDICES))

    def test_rdm_is_symmetric_and_zero_diagonal(self):
        rows = [[0.0,0.0],[1.0,0.0],[0.0,2.0]]
        d = b.rdm(rows)
        for i in range(3):
            self.assertEqual(d[i][i], 0.0)
            for j in range(3): self.assertAlmostEqual(d[i][j],d[j][i])

    def test_covariance_spectrum_normalizes(self):
        rows = [[float(i),float(i*i % 7),float((i*3)%5)] for i in range(12)]
        spec = b.covariance_spectrum(rows)
        self.assertAlmostEqual(sum(spec),1.0,places=8)
        self.assertTrue(all(x>=0 for x in spec))

    def test_jacobi_known_eigenvalues(self):
        vals = b.jacobi_eigenvalues([[2.0,1.0],[1.0,2.0]])
        self.assertAlmostEqual(vals[0],3.0,places=8)
        self.assertAlmostEqual(vals[1],1.0,places=8)

    def test_unpaired_geometry_does_not_claim_paired_rdm(self):
        a,_ = b.make_system_bank("acoustic",80,8)
        m,_ = b.make_system_bank("mechanical",81,8)
        g = b.cross_domain_unpaired_geometry(a,m,82,null_reps=9)
        self.assertIsNone(g["paired_rdm_correlation"])
        self.assertIn("unpaired",g["comparison_type"])
        self.assertEqual(g["null_replicates"],9)
        for k in ("null_empirical_p_cosine_upper","null_empirical_p_distance_lower","null_empirical_p_mst_lower"):
            self.assertGreaterEqual(g[k],0.0); self.assertLessEqual(g[k],1.0)

    def test_policies_share_same_heldout_cases(self):
        _, traces = b.evaluate_active_observer("acoustic", 90, episodes_per_class=1, rounds=2, measurement_noise=0.1)
        by_episode = {}
        for t in traces:
            key=(t["true_class"],t["episode"])
            by_episode.setdefault(key,set()).add(t["case_fingerprint"])
        self.assertEqual(len(by_episode),4)
        self.assertTrue(all(len(v)==1 for v in by_episode.values()))

    def test_policy_probe_sequence_has_no_repeats(self):
        _, traces = b.evaluate_active_observer("mechanical", 91, episodes_per_class=1, rounds=3, measurement_noise=0.1)
        sequences={}
        for t in traces:
            key=(t["policy"],t["true_class"],t["episode"])
            sequences.setdefault(key,[]).append(t["probe"])
        self.assertTrue(all(len(seq)==len(set(seq)) for seq in sequences.values()))

    def test_sensor_lowpass_and_gain_are_applied(self):
        y=[0.0,1.0,0.0,-1.0]*32
        transformed=b.apply_sensor_response(y,256.0,gain=2.0,cutoff_hz=24.0,delay_seconds=0.0)
        self.assertEqual(len(transformed),len(y))
        self.assertTrue(all(math.isfinite(v) for v in transformed))
        self.assertLess(max(abs(v) for v in transformed),2.0)
        self.assertGreater(b.rms(transformed),0.0)

    def test_fixed_duration_sample_rate_bank(self):
        rng=Random(101)
        models=[replace(b.generate_mechanical(rng,cls),sensor_delay=0) for cls in range(4)]
        rows=b.response_bank_for_rate("mechanical",models,128.0)
        self.assertEqual(len(rows),4)
        self.assertTrue(all(len(row)==len(b.PROBE_NAMES)*len(b.FEATURE_NAMES) for row in rows))
        self.assertTrue(all(math.isfinite(v) for row in rows for v in row))

    def test_nuisance_sweep_outputs_expected_conditions(self):
        result=b.nuisance_sweeps(102,4)
        self.assertEqual(len(result["sample_rate_sweep"]),4)
        self.assertEqual(len(result["sensor_transfer_sweep"]),6)
        self.assertEqual(result["physical_duration_s"],b.DURATION)

    def test_wilson_interval_contains_observed_rate(self):
        lo,hi=b.wilson_interval(5,10)
        self.assertLessEqual(lo,0.5)
        self.assertGreaterEqual(hi,0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
