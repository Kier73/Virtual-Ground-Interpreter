import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ground_synthesis import (
    State, TransitionRecord, ground_catalog, make_dataset, induce_ground,
    evaluate_program, full_domain_coverage, audit_projection,
    compare_programs, HiddenGround, infer_variable_roles, compile_program_spec,
)

class Build23SynthesisTests(unittest.TestCase):
    def test_all_five_grounds_induce_exact_finite_programs(self):
        for ground in ground_catalog():
            with self.subTest(ground=ground.name):
                train, heldout=make_dataset(ground)
                limit=3 if ground.name=="source-mod4-operation" else 4
                if ground.name=="source-mod4-operation":
                    with self.assertRaisesRegex(ValueError,"richer rule"):
                        induce_ground(train,max_residue_modulus=3)
                    program=induce_ground(train,max_residue_modulus=4)
                else:
                    program=induce_ground(train,max_residue_modulus=limit)
                self.assertEqual(evaluate_program(program,train)["correct"],len(train))
                self.assertEqual(evaluate_program(program,heldout)["correct"],len(heldout))
                # The deterministic split includes whole states absent from training.
                train_states={r.state for r in train}
                heldout_states={r.state for r in heldout}
                self.assertGreater(len(heldout_states-train_states),0)
                self.assertEqual(full_domain_coverage(program,ground)["transition_coverage"],1.0)
                self.assertTrue(all(r==0 for r in program.invariant_residuals))

    def test_modular_inflow_is_discovered_as_expression(self):
        ground=ground_catalog()[1]
        program=induce_ground(make_dataset(ground)[0])
        self.assertEqual(program.inflow.mode,"modular_ramp")
        self.assertEqual(tuple(program.inflow.evaluate(p) for p in range(ground.period)),ground.inflow)

    def test_irregular_phase_progression_falls_back_to_lookup(self):
        ground=ground_catalog()[2]
        program=induce_ground(make_dataset(ground)[0])
        self.assertEqual(program.phase_next.mode,"lookup")
        self.assertEqual(tuple(program.phase_next.evaluate(p) for p in range(ground.period)),ground.phase_next)

    def test_transfer_rule_refines_to_source_parity(self):
        ground=ground_catalog()[2]
        program=induce_ground(make_dataset(ground)[0])
        self.assertEqual(program.transfer.modulus,2)
        self.assertEqual(program.transfer.evaluate(0,2),1)
        self.assertEqual(program.transfer.evaluate(0,3),2)

    def test_transfer_rule_refines_to_source_mod4_after_grammar_expansion(self):
        ground=ground_catalog()[4]
        train,_=make_dataset(ground)
        with self.assertRaises(ValueError):
            induce_ground(train,max_residue_modulus=3)
        program=induce_ground(train,max_residue_modulus=4)
        self.assertEqual(program.transfer.modulus,4)
        self.assertEqual([program.transfer.evaluate(0,x) for x in range(4)],[1,2,3,1])

    def test_capacity_without_saturation_is_only_lower_bound(self):
        ground=ground_catalog()[0]
        train,_=make_dataset(ground)
        sparse=tuple(r for r in train if not (r.action=="HOLD" and r.state.a==ground.capacity))
        program=induce_ground(sparse)
        self.assertEqual(program.capacity_status,"lower_bound_only")

    def test_capacity_with_saturation_evidence_is_exact(self):
        ground=ground_catalog()[0]
        program=induce_ground(make_dataset(ground)[0])
        self.assertEqual(program.capacity_status,"exact_from_observed_saturation")

    def test_missing_action_intervention_fails_closed(self):
        ground=ground_catalog()[0]
        train,_=make_dataset(ground)
        without_ab=tuple(r for r in train if r.action!="A_TO_B")
        with self.assertRaisesRegex(ValueError,"uncensored transfer observations"):
            induce_ground(without_ab)

    def test_phase_coverage_is_required(self):
        ground=ground_catalog()[0]
        train,_=make_dataset(ground)
        partial=tuple(r for r in train if r.state.phase!=3)
        with self.assertRaises(ValueError):
            induce_ground(partial)

    def test_same_state_domain_can_have_new_transition_ground(self):
        old=ground_catalog()[0]
        new=HiddenGround(old.capacity,(0,1,0,1),old.demand,old.phase_next,old.transfer_by_phase_residue,old.transfer_modulus,"new-law")
        p_old=induce_ground(make_dataset(old)[0]); p_new=induce_ground(make_dataset(new)[0])
        report=compare_programs(p_old,p_new)
        self.assertTrue(report["revision_required"])
        self.assertTrue(report["state_encoding_compatible"])
        self.assertEqual([x["component"] for x in report["changed_components"]],["inflow_law"])

    def test_full_projection_is_transition_congruent(self):
        self.assertTrue(audit_projection(ground_catalog()[0],"FULL")["transition_congruent"])

    def test_total_projection_is_not_transition_congruent(self):
        self.assertFalse(audit_projection(ground_catalog()[0],"TOTAL")["transition_congruent"])


    def test_serialized_ground_spec_reloads_as_executable_program(self):
        ground=ground_catalog()[4]
        train,heldout=make_dataset(ground)
        program=induce_ground(train,max_residue_modulus=4)
        restored=compile_program_spec(program.as_dict())
        self.assertEqual(evaluate_program(restored,heldout)["correct"],len(heldout))
        self.assertEqual(restored.transfer,program.transfer)

    def test_program_fingerprint_is_stable_after_serialization(self):
        from ground_synthesis import program_fingerprint
        ground=ground_catalog()[1]
        program=induce_ground(make_dataset(ground)[0])
        restored=compile_program_spec(program.as_dict())
        self.assertEqual(program_fingerprint(restored),program_fingerprint(program))

    def test_roles_distinguish_controlled_endogenous_and_exogenous(self):
        ground=ground_catalog()[0]
        roles=infer_variable_roles(make_dataset(ground)[0])
        self.assertEqual(roles["action"],"controlled_input")
        self.assertEqual(roles["phase"],"exogenous_context")
        self.assertEqual(roles["a"],"endogenous_state")
        self.assertEqual(roles["b"],"endogenous_state")

if __name__=="__main__": unittest.main(verbosity=2)
