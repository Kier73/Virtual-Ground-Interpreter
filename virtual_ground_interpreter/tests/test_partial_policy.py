import unittest
from fractions import Fraction

from vgi import (
    GroundTransitionSystem,
    ObserverContext,
    TransitionObservation,
    TransitionOutcome,
)
from vgi.partial_attention import ProbeScenario, TransitionProbe, score_partial_probe
from vgi.partial_policy import (
    PartialProbePolicyError,
    plan_partial_probe_policy,
)


def complementary_unknown_ground(*, ambiguous=False):
    if ambiguous:
        observations = (
            TransitionObservation("a", "X", (TransitionOutcome("a", (0,)),)),
            TransitionObservation("b", "X", (TransitionOutcome("b", (0,)),)),
            TransitionObservation(
                "a",
                "Y",
                (
                    TransitionOutcome("a", (0,)),
                    TransitionOutcome("b", (1,)),
                ),
                support_count=2,
            ),
        )
    else:
        observations = (
            TransitionObservation("a", "X", (TransitionOutcome("a", (0,)),)),
            TransitionObservation("b", "X", (TransitionOutcome("b", (0,)),)),
        )
    return GroundTransitionSystem(
        states=("a", "b"),
        actions=("X", "Y"),
        initial_state="a",
        channels=("out",),
        observations=observations,
    )


def complement_probes(*, weighted=False, alternatives=False):
    a_scenarios = (
        ProbeScenario(
            TransitionOutcome("a", (0,)),
            Fraction(1, 100) if weighted else None,
        ),
        ProbeScenario(
            TransitionOutcome("b", (1,)),
            Fraction(99, 100) if weighted else None,
        ),
    )
    b_scenarios = (
        ProbeScenario(
            TransitionOutcome("b", (0,)),
            Fraction(3, 4) if weighted else None,
        ),
        ProbeScenario(
            TransitionOutcome("a", (1,)),
            Fraction(1, 4) if weighted else None,
        ),
    )
    probes = [
        TransitionProbe("a", "Y", a_scenarios, Fraction(1), "a-method"),
        TransitionProbe("b", "Y", b_scenarios, Fraction(1), "b-method"),
    ]
    if alternatives:
        probes.append(
            TransitionProbe("a", "Y", a_scenarios, Fraction(3), "a-slow-method")
        )
    return tuple(probes)


class PartialProbePolicyTests(unittest.TestCase):
    def setUp(self):
        self.system = complementary_unknown_ground()
        self.observer = ObserverContext.full(self.system)

    def test_zero_immediate_gain_cells_form_a_complete_two_step_policy(self):
        probes = complement_probes()
        local_scores = [
            score_partial_probe(self.system, self.observer, probe, 1)
            for probe in probes
        ]
        self.assertEqual(
            [score.minimum_resolved_pairs for score in local_scores],
            [0, 0],
        )

        plan = plan_partial_probe_policy(
            self.system, self.observer, probes, 1
        )
        self.assertEqual((plan.first_probe.state, plan.first_probe.action), ("a", "Y"))
        self.assertEqual(plan.worst_case_unresolved_pairs, 0)
        self.assertEqual(plan.worst_case_cost, Fraction(2))
        self.assertEqual(plan.maximum_probes_on_path, 2)
        self.assertEqual(len(plan.root.branches), 2)
        self.assertEqual(
            {(branch.child.probe.state, branch.child.probe.action)
             for branch in plan.root.branches},
            {("b", "Y")},
        )
        for branch in plan.root.branches:
            self.assertTrue(branch.child.branches)
            self.assertTrue(all(item.child.is_terminal for item in branch.child.branches))
            self.assertTrue(all(
                item.child.worst_case_unresolved_pairs == 0
                for item in branch.child.branches
            ))

    def test_exact_method_cost_selects_the_cheaper_measurement_for_a_cell(self):
        probes = complement_probes(alternatives=True)
        plan = plan_partial_probe_policy(self.system, self.observer, probes, 1)
        self.assertEqual(plan.first_probe.label, "a-method")
        first_branch = plan.root.branches[0]
        self.assertEqual(first_branch.child.probe.label, "b-method")
        self.assertNotEqual(first_branch.child.probe.state, plan.first_probe.state)

    def test_each_policy_path_measures_a_cell_at_most_once(self):
        plan = plan_partial_probe_policy(
            self.system, self.observer, complement_probes(alternatives=True), 1
        )

        def walk(node, used):
            if node.probe is None:
                return
            cell = (node.probe.state, node.probe.action)
            self.assertNotIn(cell, used)
            next_used = used | {cell}
            self.assertEqual(len(node.branches), len(node.probe.scenarios))
            for branch in node.branches:
                walk(branch.child, next_used)

        walk(plan.root, set())

    def test_worst_case_objective_ignores_scenario_weights(self):
        unweighted = plan_partial_probe_policy(
            self.system, self.observer, complement_probes(), 1
        )
        weighted = plan_partial_probe_policy(
            self.system, self.observer, complement_probes(weighted=True), 1
        )
        self.assertEqual(
            unweighted.worst_case_unresolved_pairs,
            weighted.worst_case_unresolved_pairs,
        )
        self.assertEqual(unweighted.worst_case_cost, weighted.worst_case_cost)
        self.assertEqual(plan_structure(unweighted.root), plan_structure(weighted.root))
        self.assertIsNotNone(weighted.root.branches[0].weight)

    def test_declared_scenarios_are_branches_not_an_exhaustiveness_claim(self):
        plan = plan_partial_probe_policy(
            self.system, self.observer, complement_probes(), 1
        )
        record = plan.to_dict()
        self.assertEqual(record["format"], "VGI-PartialProbePolicy-1")
        self.assertIn("not_probability_or_exhaustiveness_claim", record["scenario_semantics"])
        self.assertIn("finite_supplied_probe_candidates", record["optimality_scope"])
        self.assertEqual(record["root"]["branches"][0]["weight_role"],
                         "metadata_only_not_used_by_worst_case_objective")
        self.assertEqual(len(record["policy_digest"]), 64)

    def test_budget_and_probe_limits_remain_explicit(self):
        budget_limited = plan_partial_probe_policy(
            self.system,
            self.observer,
            complement_probes(),
            1,
            budget=Fraction(1, 2),
        )
        self.assertTrue(budget_limited.root.is_terminal)
        self.assertEqual(budget_limited.worst_case_unresolved_pairs, 1)
        self.assertEqual(budget_limited.worst_case_cost, Fraction(0))
        self.assertEqual(budget_limited.root.terminal_reason, "budget_exhausted")

        depth_limited = plan_partial_probe_policy(
            self.system,
            self.observer,
            complement_probes(),
            1,
            max_probes=0,
        )
        self.assertTrue(depth_limited.root.is_terminal)
        self.assertEqual(depth_limited.root.terminal_reason, "probe_limit_reached")

    def test_exact_search_bound_fails_closed_without_returning_a_partial_policy(self):
        with self.assertRaisesRegex(PartialProbePolicyError, "exceeded max_states"):
            plan_partial_probe_policy(
                self.system,
                self.observer,
                complement_probes(),
                1,
                max_states=1,
            )

    def test_ambiguous_cells_are_not_replaced_by_policy_scenarios(self):
        system = complementary_unknown_ground(ambiguous=True)
        observer = ObserverContext.full(system)
        ambiguous_probe = TransitionProbe(
            "a",
            "Y",
            (ProbeScenario(TransitionOutcome("a", (0,))),),
            label="forbidden-collapse",
        )
        with self.assertRaisesRegex(PartialProbePolicyError, "must not collapse existing ambiguity"):
            plan_partial_probe_policy(
                system, observer, (ambiguous_probe,), 1
            )

    def test_known_cells_and_invisible_actions_are_rejected(self):
        known_probe = TransitionProbe(
            "a",
            "X",
            (ProbeScenario(TransitionOutcome("a", (0,))),),
            label="already-known",
        )
        with self.assertRaisesRegex(PartialProbePolicyError, "targets a known cell"):
            plan_partial_probe_policy(
                self.system, self.observer, (known_probe,), 1
            )

        hidden_observer = ObserverContext("only-X", ("X",), ("out",))
        with self.assertRaisesRegex(PartialProbePolicyError, "not visible"):
            plan_partial_probe_policy(
                self.system, hidden_observer, complement_probes(), 1
            )

    def test_candidate_definition_duplicates_ignore_non_objective_weights(self):
        probe = complement_probes(weighted=True)[0]
        alternate_weights = TransitionProbe(
            probe.state,
            probe.action,
            (
                ProbeScenario(TransitionOutcome("a", (0,)), Fraction(1, 2)),
                ProbeScenario(TransitionOutcome("b", (1,)), Fraction(1, 2)),
            ),
            probe.cost,
            probe.label,
        )
        with self.assertRaisesRegex(PartialProbePolicyError, "exact duplicate"):
            plan_partial_probe_policy(
                self.system,
                self.observer,
                (probe, alternate_weights),
                1,
            )

    def test_empty_candidate_pool_returns_an_explicit_terminal_policy(self):
        plan = plan_partial_probe_policy(
            self.system, self.observer, (), 1
        )
        self.assertTrue(plan.root.is_terminal)
        self.assertEqual(plan.root.terminal_reason, "candidate_pool_exhausted")
        self.assertEqual(plan.worst_case_unresolved_pairs, 1)
        self.assertIsNone(plan.first_probe)


def plan_structure(node):
    if node.probe is None:
        return None
    return (
        node.probe.state,
        node.probe.action,
        node.probe.label,
        tuple(
            (branch.outcome.target, branch.outcome.output, plan_structure(branch.child))
            for branch in node.branches
        ),
    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
