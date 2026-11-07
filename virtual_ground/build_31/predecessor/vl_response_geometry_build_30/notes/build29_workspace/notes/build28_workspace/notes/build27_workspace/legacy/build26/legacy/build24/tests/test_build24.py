from __future__ import annotations
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from latent_ground import (
    ACTIONS, ActiveMealyLearner, HiddenContextGround, ResettableTeacher,
    bounded_certificate, build_adaptive_probe_tree, compile_virtual_ground, fixture_grounds,
    infer_clock_coordinate, run_compiled_ground, verify_compiled_ground,
    words_upto,
)


class Build24Tests(unittest.TestCase):
    def learn(self, name, channels=None, depth=8):
        ground = fixture_grounds()[name]
        teacher = ResettableTeacher(ground, channels=channels)
        result = ActiveMealyLearner(teacher, conformance_depth=depth).learn()
        return ground, teacher, result

    def test_joint_observation_recovers_six_predictive_contexts(self):
        _, teacher, result = self.learn("coupled_six")
        self.assertEqual(len(result.machine.states), 6)
        self.assertTrue(bounded_certificate(result.machine, teacher, 8)["bounded_equivalence"])

    def test_parity_sensor_observes_two_context_quotient(self):
        _, _, result = self.learn("coupled_six", channels=(0,))
        self.assertEqual(len(result.machine.states), 2)

    def test_mod3_sensor_observes_three_context_quotient(self):
        _, _, result = self.learn("coupled_six", channels=(1,))
        self.assertEqual(len(result.machine.states), 3)

    def test_combined_sensor_fuses_quotients_into_six(self):
        n2 = self.learn("coupled_six", channels=(0,))[2].machine
        n3 = self.learn("coupled_six", channels=(1,))[2].machine
        n6 = self.learn("coupled_six")[2].machine
        self.assertEqual(len(n6.states), 6)
        self.assertEqual(len(n2.states) * len(n3.states), len(n6.states))

    def test_six_physical_modes_can_collapse_to_three_predictive_contexts(self):
        ground, _, result = self.learn("aliased_six")
        self.assertEqual(ground.mode_count, 6)
        self.assertEqual(len(result.machine.states), 3)

    def test_unobservable_hidden_modes_are_not_invented(self):
        ground, _, result = self.learn("unobservable_eight")
        self.assertEqual(ground.mode_count, 8)
        self.assertEqual(len(result.machine.states), 1)

    def test_delayed_hidden_mode_requires_long_counterexample(self):
        _, _, shallow = self.learn("delayed_six", depth=5)
        _, _, deep = self.learn("delayed_six", depth=6)
        self.assertEqual(len(shallow.machine.states), 1)
        self.assertEqual(len(deep.machine.states), 6)
        self.assertEqual(deep.counterexample_count, 1)
        self.assertEqual(len(deep.rounds[0]["counterexample"]), 6)

    def test_action_dependent_phase_strides_are_recovered(self):
        _, _, result = self.learn("coupled_six")
        clock = infer_clock_coordinate(result.machine)
        self.assertTrue(clock["is_single_cycle"])
        self.assertEqual(clock["period"], 6)
        self.assertEqual(clock["action_phase_strides"], {"HOLD": 1, "PROBE_A": 2, "PROBE_B": 3})

    def test_nonbijective_context_is_not_forced_into_a_clock(self):
        _, _, result = self.learn("partial_four")
        self.assertEqual(len(result.machine.states), 4)
        self.assertFalse(infer_clock_coordinate(result.machine)["is_single_cycle"])

    def test_compiled_phase_program_matches_learned_machine(self):
        _, _, result = self.learn("coupled_six")
        program = compile_virtual_ground(result.machine)
        proof = verify_compiled_ground(result.machine, program)
        self.assertEqual(program["compiler_kind"], "modular_phase_program")
        self.assertTrue(proof["exact"])

    def test_compiled_general_automaton_matches_learned_machine(self):
        _, _, result = self.learn("partial_four")
        program = compile_virtual_ground(result.machine)
        proof = verify_compiled_ground(result.machine, program)
        self.assertEqual(program["compiler_kind"], "finite_predictive_automaton")
        self.assertTrue(proof["exact"])


    def test_adaptive_probe_tree_identifies_delayed_contexts(self):
        _, teacher, result = self.learn("delayed_six")
        histories = {q: tuple(v) for q, v in result.machine.representatives.items()}
        policy = build_adaptive_probe_tree(teacher, histories, max_probe_depth=6)
        stats = policy["statistics"]
        self.assertEqual(stats["identified"], 6)
        self.assertEqual(stats["ambiguous"], 0)
        self.assertEqual(stats["worst_case_probe_cost"], 5)
        self.assertAlmostEqual(stats["mean_probe_cost"], 20 / 6)

    def test_serialization_round_trip(self):
        _, teacher, result = self.learn("delayed_six")
        data = result.machine.as_dict()
        from latent_ground import LearnedMealyGround
        reloaded = LearnedMealyGround.from_dict(json.loads(json.dumps(data)))
        for word in words_upto(ACTIONS, 7):
            self.assertEqual(reloaded.run(word), teacher.query(word))

    def test_bounded_certificate_is_explicitly_horizon_limited(self):
        _, teacher, result = self.learn("delayed_six", depth=5)
        cert = bounded_certificate(result.machine, teacher, 5)
        self.assertTrue(cert["bounded_equivalence"])
        self.assertEqual(cert["depth"], 5)
        self.assertEqual(len(result.machine.states), 1)

    def test_query_purposes_are_separately_counted(self):
        _, teacher, result = self.learn("delayed_six")
        bounded_certificate(result.machine, teacher, 8)
        stats = teacher.stats()
        self.assertGreater(stats["query_requests_by_purpose"].get("membership", 0), 0)
        self.assertGreater(stats["query_requests_by_purpose"].get("conformance", 0), 0)
        self.assertGreater(stats["query_requests_by_purpose"].get("probe_selection", 0), 0)

    def test_repeated_query_is_deterministic_under_reset_contract(self):
        teacher = ResettableTeacher(fixture_grounds()["coupled_six"])
        word = ("HOLD", "PROBE_A", "PROBE_B", "HOLD")
        self.assertEqual(teacher.query(word), teacher.query(word))

    def test_build23_regression_inducer_still_works(self):
        legacy_path = ROOT / "legacy" / "build23_ground_synthesis.py"
        spec = importlib.util.spec_from_file_location("build23_legacy", legacy_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        ground = module.ground_catalog()[-1]
        train, holdout = module.make_dataset(ground)
        program = module.induce_ground(train, max_residue_modulus=4)
        metrics = module.evaluate_program(program, holdout)
        self.assertEqual(metrics["correct"], metrics["count"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
