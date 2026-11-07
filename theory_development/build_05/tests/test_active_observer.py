import math
import unittest
from random import Random

from active_observer import (
    DEFAULT_CODON_ALGEBRA, HYPOTHESES, INTENTS, OBSERVERS, PROBES, Observer,
    ScalarCodonAlgebra,
    adaptive_episode, bayesian_update, choose_probe, expected_information_gain,
    invariance_audit, score_probes,
)


class ProbeSelectionTests(unittest.TestCase):
    def test_intention_changes_selected_probe(self):
        prior = {h.name: 0.25 for h in HYPOTHESES}
        upper = choose_probe(OBSERVERS["full"], INTENTS["locate_upper_coupling"], prior)
        lower = choose_probe(OBSERVERS["full"], INTENTS["locate_lower_coupling"], prior)
        self.assertEqual(upper.probe, "probe_y")
        self.assertEqual(lower.probe, "probe_x")

    def test_observer_projection_changes_selected_probe(self):
        prior = {h.name: 0.25 for h in HYPOTHESES}
        x_obs = choose_probe(OBSERVERS["x_only"], INTENTS["locate_upper_coupling"], prior)
        y_obs = choose_probe(OBSERVERS["y_only"], INTENTS["locate_lower_coupling"], prior)
        self.assertEqual(x_obs.probe, "probe_y")
        self.assertEqual(y_obs.probe, "probe_x")

    def test_cost_adjustment_can_prefer_lower_raw_information_probe(self):
        prior = {h.name: 0.25 for h in HYPOTHESES}
        scores = {s.probe: s for s in score_probes(
            OBSERVERS["full"], INTENTS["identify_structure"], prior)}
        self.assertGreater(scores["probe_diagonal"].eig_bits,
                           scores["probe_x"].eig_bits)
        self.assertGreater(scores["probe_x"].utility,
                           scores["probe_diagonal"].utility)

    def test_unobservable_intent_is_rejected(self):
        # x-channel sees no change under probe_x, but probe_y can measure upper coupling.
        # A deliberately constant observer and task is uninformative.
        blind = Observer("blind", (0,), (0.12,), gains=(0.0, 1.0))
        prior = {h.name: 0.25 for h in HYPOTHESES}
        with self.assertRaises(ValueError):
            choose_probe(blind, INTENTS["locate_upper_coupling"], prior,
                         probes=(PROBES[0],))

    def test_expected_information_gain_is_nonnegative(self):
        prior = {h.name: 0.25 for h in HYPOTHESES}
        for p in PROBES:
            value = expected_information_gain(p, OBSERVERS["full"],
                                              INTENTS["identify_structure"], prior)
            self.assertGreaterEqual(value, 0.0)

    def test_information_gain_does_not_exceed_target_entropy(self):
        prior = {h.name: 0.25 for h in HYPOTHESES}
        for intent in INTENTS.values():
            for p in PROBES:
                eig = expected_information_gain(p, OBSERVERS["full"], intent, prior)
                # All defined targets have <= 2 bits of entropy.
                self.assertLessEqual(eig, 2.0001)

    def test_more_noise_does_not_improve_eig_in_this_model(self):
        prior = {h.name: 0.25 for h in HYPOTHESES}
        p = PROBES[0]
        eigs = [expected_information_gain(p, OBSERVERS["full"],
                                           INTENTS["identify_structure"], prior, scale)
                for scale in (1.0, 1.5, 2.0)]
        self.assertGreaterEqual(eigs[0] + 1e-9, eigs[1])
        self.assertGreaterEqual(eigs[1] + 1e-9, eigs[2])

    def test_robust_score_is_worst_case_over_noise_scales(self):
        prior = {h.name: 0.25 for h in HYPOTHESES}
        scores = score_probes(OBSERVERS["full"], INTENTS["identify_structure"], prior)
        for score in scores:
            self.assertAlmostEqual(score.robust_eig_bits,
                                   min(score.noise_scale_eigs), places=12)


class BayesianUpdateTests(unittest.TestCase):
    def test_posterior_normalizes(self):
        prior = {h.name: 0.25 for h in HYPOTHESES}
        y = OBSERVERS["full"].predict(HYPOTHESES[1], PROBES[0])
        post = bayesian_update(prior, PROBES[0], OBSERVERS["full"], y)
        self.assertAlmostEqual(sum(post.values()), 1.0, places=14)

    def test_observation_increases_probability_of_matching_hypothesis(self):
        prior = {h.name: 0.25 for h in HYPOTHESES}
        y = OBSERVERS["full"].predict(HYPOTHESES[1], PROBES[1])
        post = bayesian_update(prior, PROBES[1], OBSERVERS["full"], y)
        self.assertGreater(post["H1_upper_coupling"], prior["H1_upper_coupling"])

    def test_active_episode_keeps_structural_identity_unchanged(self):
        before = {h.name: h.matrix for h in HYPOTHESES}
        adaptive_episode(HYPOTHESES[0], OBSERVERS["full"],
                         INTENTS["identify_structure"], Random(44))
        after = {h.name: h.matrix for h in HYPOTHESES}
        self.assertEqual(before, after)

    def test_active_policy_uses_complementary_probes(self):
        result = adaptive_episode(HYPOTHESES[0], OBSERVERS["full"],
                                  INTENTS["identify_structure"], Random(121),
                                  max_steps=2)
        names = [s["probe"] for s in result["history"]]
        self.assertEqual(names, ["probe_y", "probe_x"])

    def test_custom_codon_aliases_preserve_response(self):
        custom = ScalarCodonAlgebra(add="plus", mul="times")
        for hypothesis in HYPOTHESES:
            for probe in PROBES:
                expected = hypothesis.apply(probe.input_vector, DEFAULT_CODON_ALGEBRA)
                actual = hypothesis.apply(probe.input_vector, custom)
                self.assertEqual(expected, actual)

    def test_probe_chains_use_declared_local_codon_operations(self):
        allowed = {"ld", "mx", "ad"}
        self.assertTrue(all(set(probe.codon_chain) <= allowed for probe in PROBES))
        self.assertTrue(all(probe.codon_chain == ("ld", "mx", "ad") for probe in PROBES))


class InvarianceTests(unittest.TestCase):
    def test_probe_selection_does_not_mutate_algebra(self):
        self.assertTrue(invariance_audit()["underlying_structure_unchanged"])

    def test_observer_output_is_projection_not_new_underlying_state(self):
        full = OBSERVERS["full"].predict(HYPOTHESES[2], PROBES[0])
        x_only = OBSERVERS["x_only"].predict(HYPOTHESES[2], PROBES[0])
        y_only = OBSERVERS["y_only"].predict(HYPOTHESES[2], PROBES[0])
        self.assertEqual(full[0], x_only[0])
        self.assertEqual(full[1], y_only[0])
        self.assertEqual(HYPOTHESES[2].matrix, ((1.0, 0.0), (1.1, 1.0)))

    def test_probe_energy_is_normalized(self):
        for probe in PROBES:
            norm = math.sqrt(sum(x*x for x in probe.input_vector))
            self.assertAlmostEqual(norm, 1.0, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
