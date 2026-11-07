import math
import unittest
from random import Random

from s3_active_observer import (
    CodonRegistry, QuaternionAlgebra, DEFAULT_ALG, IDENTITY, PROBES, OBSERVERS,
    REGULAR_INTENTS, active_episode, antipodal_pair, build_antipodal_intent,
    cap_loop, choose_probe, fibre_phase, hopf_project, horizontal_lift,
    make_candidates, measurement, s3_distance, signed_solid_angle,
    so3_distance, so3_signed_k_angle, s3_phase_absolute,
    expected_information_gain, target_posterior, observable_equivalence_classes,
)


class CodonicQuaternionTests(unittest.TestCase):
    def test_compiled_quaternion_product_identity(self):
        q = DEFAULT_ALG.normalize((0.2, -0.3, 0.4, 0.5))
        self.assertLess(max(abs(a-b) for a, b in zip(DEFAULT_ALG.qmul(q, IDENTITY), q)), 1e-12)

    def test_quaternion_product_noncommutative(self):
        a = DEFAULT_ALG.normalize((0.7, 0.2, -0.1, 0.3))
        b = DEFAULT_ALG.normalize((0.4, -0.3, 0.6, 0.1))
        ab = DEFAULT_ALG.qmul(a, b)
        ba = DEFAULT_ALG.qmul(b, a)
        self.assertGreater(math.sqrt(sum((x-y)**2 for x, y in zip(ab, ba))), 1e-3)

    def test_alias_renaming_preserves_hamilton_product(self):
        alias = QuaternionAlgebra(CodonRegistry(add="plus", sub="minus", mul="times",
                                                div="over", sqrt="root"))
        a = (0.8, -0.1, 0.2, 0.4)
        b = (0.6, 0.3, -0.2, 0.5)
        x = DEFAULT_ALG.qmul(a, b)
        y = alias.qmul(a, b)
        self.assertLess(max(abs(i-j) for i, j in zip(x, y)), 1e-14)

    def test_alias_renaming_preserves_lifted_path(self):
        alias = QuaternionAlgebra(CodonRegistry(add="plus", sub="minus", mul="times",
                                                div="over", sqrt="root"))
        path = cap_loop(0.62, 1, 24, 240)
        a = horizontal_lift(path, alg=DEFAULT_ALG)[-1]
        b = horizontal_lift(path, alg=alias)[-1]
        self.assertLess(max(abs(x-y) for x, y in zip(a, b)), 1e-12)

    def test_registry_rejects_duplicate_aliases(self):
        with self.assertRaises(ValueError):
            CodonRegistry(add="x", sub="x")


class HopfGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = make_candidates(meridian_steps=40, latitude_steps=400)

    def test_hopf_projection_is_unit(self):
        for c in self.candidates:
            n = hopf_project(c.q_final)
            self.assertAlmostEqual(sum(x*x for x in n), 1.0, places=11)

    def test_all_regular_paths_close_in_base_space(self):
        for c in self.candidates:
            n = hopf_project(c.q_final)
            self.assertLess(math.sqrt(sum((x-y)**2 for x, y in zip(n, (0,0,1)))), 1e-8)

    def test_area_phase_half_area(self):
        for c in self.candidates:
            phase, residual = fibre_phase(IDENTITY, c.q_final)
            area = signed_solid_angle(c.base_path)
            self.assertLess(abs(phase - 0.5*area), 5e-5)
            self.assertLess(residual, 1e-8)

    def test_reverse_path_reverses_phase(self):
        forward = next(c for c in self.candidates if c.name == "small_forward")
        reverse = next(c for c in self.candidates if c.name == "small_reverse")
        self.assertAlmostEqual(s3_phase_absolute(forward.q_final),
                               -s3_phase_absolute(reverse.q_final), places=10)

    def test_size_changes_holonomy_magnitude(self):
        small = next(c for c in self.candidates if c.name == "small_forward")
        large = next(c for c in self.candidates if c.name == "large_forward")
        self.assertGreater(abs(s3_phase_absolute(large.q_final)),
                           abs(s3_phase_absolute(small.q_final)))

    def test_horizontal_lift_each_sample_matches_base(self):
        path = cap_loop(0.73, -1, 30, 200)
        lift = horizontal_lift(path)
        for n, q in zip(path, lift):
            p = hopf_project(q)
            self.assertLess(math.sqrt(sum((a-b)**2 for a,b in zip(n,p))), 1e-8)

    def test_fibre_gauge_shift_preserves_hopf_projection(self):
        q = self.candidates[0].q_final
        beta = 0.713
        fibre = (math.cos(beta), 0.0, 0.0, math.sin(beta))
        shifted = DEFAULT_ALG.qmul(q, fibre)
        a, b = hopf_project(q), hopf_project(shifted)
        self.assertLess(math.sqrt(sum((x-y)**2 for x,y in zip(a,b))), 1e-10)

    def test_s3_and_so3_antipodal_metrics_differ(self):
        q = self.candidates[0].q_final
        minus_q = tuple(-x for x in q)
        self.assertAlmostEqual(s3_distance(q, minus_q), math.pi, places=12)
        self.assertAlmostEqual(so3_distance(q, minus_q), 0.0, places=12)

    def test_so3_signed_angle_identifies_antipodes(self):
        q = self.candidates[0].q_final
        minus_q = tuple(-x for x in q)
        self.assertAlmostEqual(so3_signed_k_angle(q), so3_signed_k_angle(minus_q), places=12)


class ActiveObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = make_candidates(meridian_steps=32, latitude_steps=320)
        cls.prior = {c.name: 0.25 for c in cls.candidates}

    def test_endpoint_only_has_zero_information_about_full_path(self):
        probe = PROBES["base_endpoint"]
        eig = expected_information_gain(probe, OBSERVERS["endpoint_only"],
                                        REGULAR_INTENTS["full_path"], self.prior,
                                        self.candidates)
        self.assertLess(eig, 1e-9)

    def test_endpoint_only_reports_unresolved(self):
        candidate = self.candidates[0]
        result = active_episode(candidate, OBSERVERS["endpoint_only"],
                                REGULAR_INTENTS["full_path"], self.candidates,
                                Random(7), max_steps=3)
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["steps"], 0)
        self.assertIn("no available probe", result["reason"])

    def test_same_endpoint_intention_requires_no_probe(self):
        result = active_episode(self.candidates[0], OBSERVERS["endpoint_only"],
                                REGULAR_INTENTS["same_base_endpoint"], self.candidates,
                                Random(7))
        self.assertEqual(result["status"], "already_resolved")
        self.assertEqual(result["steps"], 0)

    def test_base_observer_chooses_apex_for_size_intent(self):
        score = choose_probe(OBSERVERS["base_path"], REGULAR_INTENTS["cap_size"],
                             self.prior, self.candidates)
        self.assertEqual(score["probe"], "base_apex")

    def test_base_observer_chooses_area_for_orientation_intent(self):
        score = choose_probe(OBSERVERS["base_path"], REGULAR_INTENTS["loop_orientation"],
                             self.prior, self.candidates)
        self.assertEqual(score["probe"], "base_area")

    def test_active_policy_selects_area_to_resolve_full_path(self):
        candidate = self.candidates[0]
        result = active_episode(candidate, OBSERVERS["base_path"],
                                REGULAR_INTENTS["full_path"], self.candidates,
                                Random(11), max_steps=2)
        self.assertEqual(result["status"], "resolved")
        self.assertEqual([x["probe"] for x in result["history"]], ["base_area"])
        self.assertTrue(result["correct"])

    def test_rotation_observer_can_discriminate_four_selected_paths(self):
        score = choose_probe(OBSERVERS["so3"], REGULAR_INTENTS["full_path"],
                             self.prior, self.candidates)
        self.assertEqual(score["probe"], "so3_angle")
        values = [measurement(c, PROBES["so3_angle"]) for c in self.candidates]
        self.assertEqual(len({round(v, 8) for v in values}), 4)

    def test_base_area_encodes_orientation_and_size(self):
        values = [measurement(c, PROBES["base_area"]) for c in self.candidates]
        self.assertEqual(len({round(v, 7) for v in values}), 4)

    def test_antipodal_pair_invisible_to_base_and_so3(self):
        pair = antipodal_pair(self.candidates[0])
        intent = build_antipodal_intent()
        prior = {pair[0].name: 0.5, pair[1].name: 0.5}
        for observer_name in ("endpoint_only", "base_path", "so3"):
            observer = OBSERVERS[observer_name]
            max_eig = max(expected_information_gain(PROBES[p], observer, intent,
                                                     prior, pair)
                          for p in observer.available_probes)
            self.assertLess(max_eig, 1e-8)

    def test_s3_observer_selects_phase_for_antipodal_pair(self):
        pair = antipodal_pair(self.candidates[0])
        intent = build_antipodal_intent()
        prior = {pair[0].name: 0.5, pair[1].name: 0.5}
        score = choose_probe(OBSERVERS["s3_lift"], intent, prior, pair)
        self.assertEqual(score["probe"], "s3_phase")
        self.assertGreater(score["robust_eig_bits"], 0.99)

    def test_antipodal_measurements(self):
        pair = antipodal_pair(self.candidates[0])
        self.assertAlmostEqual(measurement(pair[0], PROBES["base_endpoint"]),
                               measurement(pair[1], PROBES["base_endpoint"]), places=12)
        self.assertAlmostEqual(measurement(pair[0], PROBES["so3_angle"]),
                               measurement(pair[1], PROBES["so3_angle"]), places=12)
        self.assertAlmostEqual(abs(s3_distance(pair[0].q_final, pair[1].q_final)),
                               math.pi, places=12)
        self.assertAlmostEqual(so3_distance(pair[0].q_final, pair[1].q_final),
                               0.0, places=12)

    def test_s3_active_episode_resolves_antipodal_pair(self):
        pair = antipodal_pair(self.candidates[0])
        intent = build_antipodal_intent()
        result = active_episode(pair[1], OBSERVERS["s3_lift"], intent, pair,
                                 Random(19), max_steps=2)
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["history"][0]["probe"], "s3_phase")
        self.assertTrue(result["correct"])

    def test_alias_changes_do_not_change_observer_geometry(self):
        alias = QuaternionAlgebra(CodonRegistry(add="plus", sub="minus", mul="times",
                                                div="over", sqrt="root"))
        alias_candidates = make_candidates(meridian_steps=24, latitude_steps=240, alg=alias)
        default_candidates = make_candidates(meridian_steps=24, latitude_steps=240)
        self.assertEqual([c.name for c in alias_candidates], [c.name for c in default_candidates])
        for a, b in zip(alias_candidates, default_candidates):
            self.assertLess(max(abs(x-y) for x,y in zip(a.q_final,b.q_final)), 1e-12)

    def test_observable_quotient_endpoint_observer_collapses_all_four_paths(self):
        groups = observable_equivalence_classes(OBSERVERS["endpoint_only"], self.candidates)
        self.assertEqual(len(groups), 1)
        self.assertEqual(set(groups[0]), {c.name for c in self.candidates})

    def test_observable_quotient_base_path_observer_separates_four_paths(self):
        groups = observable_equivalence_classes(OBSERVERS["base_path"], self.candidates)
        self.assertEqual(len(groups), 4)

    def test_observable_quotient_so3_collapses_antipodes(self):
        pair = antipodal_pair(self.candidates[0])
        self.assertEqual(len(observable_equivalence_classes(OBSERVERS["so3"], pair)), 1)
        self.assertEqual(len(observable_equivalence_classes(OBSERVERS["s3_lift"], pair)), 2)

    def test_candidate_structures_are_immutable(self):
        c = self.candidates[0]
        before = c.q_final
        _ = [measurement(c, PROBES[p]) for p in PROBES]
        self.assertEqual(c.q_final, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
