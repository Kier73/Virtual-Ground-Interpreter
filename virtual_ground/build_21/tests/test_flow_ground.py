import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flow_ground import (
    ACTIONS, OBSERVERS, FLOW_PARTITION, FlowGround, FlowState,
    ResourceProfile, autonomous_invariant_kernel, belief_for_observation,
    choose_route, compile_navigation_task, controlled_invariant_kernel, migration_report, observe,
    pareto_routes, partition_refinement, reachable_edges, reachable_states,
    robust_belief_plan, task_observability, verify_ground, viability_policy,
)


class FlowGroundTests(unittest.TestCase):
    def setUp(self):
        self.g = FlowGround()

    def test_state_space_and_transition_counts(self):
        r = verify_ground(self.g)
        self.assertEqual(r["state_count"], 64)
        self.assertEqual(r["directed_transition_count"], 136)
        self.assertTrue(r["all_transitions_valid"])

    def test_canonical_reachable_component(self):
        states = reachable_states(self.g, FlowState(1, 1, 0))
        self.assertEqual(len(states), 40)
        self.assertEqual(reachable_edges(self.g, states), 93)

    def test_gate_moves_conserve_pre_environment_total(self):
        for s in self.g.all_states():
            for a in self.g.legal_actions(s):
                n, ledger = self.g.step_with_ledger(s, a)
                self.assertEqual(ledger.mass_balance_residual, 0)
                self.assertEqual(
                    ledger.after_total,
                    ledger.before_total + ledger.inflow - ledger.actual_demand - ledger.spill,
                )

    def test_gate_operation_is_partial(self):
        s = FlowState(0, 0, 0)
        self.assertEqual(self.g.legal_actions(s), ("HOLD",))
        with self.assertRaises(ValueError):
            self.g.transition(s, "A_TO_B")

    def test_phase_progress_does_not_change_ground_version(self):
        s2 = self.g.transition(FlowState(1, 1, 0), "HOLD")
        self.assertEqual(s2.phase, 1)
        self.assertEqual(self.g.version, 1)

    def test_ground_rules_are_versioned(self):
        changed = self.g.revise_environment(inflow=(0, 1, 0, 1))
        self.assertEqual(changed.version, self.g.version + 1)
        self.assertNotEqual(changed.structural_descriptor, self.g.structural_descriptor)

    def test_capacity_revision_and_migration(self):
        expanded = self.g.revise_capacity(4)
        reduced = self.g.revise_capacity(2)
        up = migration_report(self.g, expanded)
        down = migration_report(self.g, reduced)
        self.assertEqual(up["directly_migratable_states"], 64)
        self.assertEqual(up["unmappable_states"], 0)
        self.assertEqual(down["directly_migratable_states"], 36)
        self.assertEqual(down["unmappable_states"], 28)

    def test_environment_law_revision_preserves_state_encoding_but_changes_law(self):
        changed = self.g.revise_environment(demand=(1, 0, 0, 0))
        r = migration_report(self.g, changed)
        self.assertTrue(r["migration_is_total"])
        self.assertTrue(r["law_changed"])

    def test_variable_partition_names_all_four_roles(self):
        self.assertIn("gate_command", FLOW_PARTITION.controlled)
        self.assertIn("reservoir_a", FLOW_PARTITION.endogenous)
        self.assertIn("environment_phase", FLOW_PARTITION.exogenous)
        self.assertIn("capacity", FLOW_PARTITION.structural)

    def test_full_observer_is_predictive(self):
        p = partition_refinement(self.g, "FULL")
        self.assertEqual(p["initial_observation_classes"], 64)
        self.assertEqual(p["refined_predictive_classes"], 64)
        self.assertEqual(p["split_count"], 0)

    def test_partial_observers_need_predictive_refinement(self):
        for name in ("LEVELS", "TOTAL", "TOTAL_PHASE", "PHASE"):
            p = partition_refinement(self.g, name)
            self.assertEqual(p["refined_predictive_classes"], 64)
            self.assertGreater(p["split_count"], 0)

    def test_total_observes_inventory_goal_but_not_exact_distribution(self):
        inventory = task_observability(self.g, "TOTAL", lambda s: s.a + s.b == 3)
        exact = task_observability(self.g, "TOTAL", lambda s: s.a == 1 and s.b == 2)
        self.assertTrue(inventory["task_goal_is_observable"])
        self.assertFalse(exact["task_goal_is_observable"])

    def test_level_sensor_observes_goal_but_not_full_dynamics(self):
        r = task_observability(self.g, "LEVELS", lambda s: s.a == 1 and s.b == 2)
        self.assertTrue(r["task_goal_is_observable"])
        self.assertFalse(r["transition_congruent_without_refinement"])

    def test_total_only_belief_can_robustly_reach_inventory_goal(self):
        belief = belief_for_observation(self.g, "TOTAL", (2,))
        plan = robust_belief_plan(self.g, belief, "TOTAL", lambda s: s.a + s.b == 3, 12)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["worst_case_steps"], 4)

    def test_sensor_precision_changes_worst_case_navigation_time(self):
        goal = lambda s: s.a == 1 and s.b == 2
        cases = [
            ("TOTAL", (2,), 10),
            ("TOTAL_PHASE", (2, 0), 8),
            ("LEVELS", (1, 1), 4),
            ("FULL", (1, 1, 0), 1),
        ]
        for observer, value, expected in cases:
            belief = belief_for_observation(self.g, observer, value)
            plan = robust_belief_plan(self.g, belief, observer, goal, 16)
            self.assertIsNotNone(plan, observer)
            self.assertEqual(plan["worst_case_steps"], expected, observer)

    def test_belief_planner_uses_observation_branches(self):
        belief = belief_for_observation(self.g, "TOTAL", (2,))
        plan = robust_belief_plan(self.g, belief, "TOTAL", lambda s: s.a == 1 and s.b == 2, 16)
        self.assertIsNotNone(plan)
        self.assertTrue(plan["branches"])
        self.assertGreater(plan["belief_nodes_expanded"], 1)

    def test_ground_compiler_emits_verified_navigation_certificate(self):
        compiled = compile_navigation_task(
            self.g, "LEVELS", (1, 1), lambda s: s.a == 1 and s.b == 2, 16
        )
        self.assertTrue(compiled["compiled"])
        self.assertTrue(compiled["certificate"]["verified"])
        self.assertEqual(compiled["certificate"]["worst_case_steps"], 4)

    def test_resource_frontier_contains_time_energy_tradeoff(self):
        start, target = FlowState(0, 1, 0), FlowState(1, 2, 3)
        routes = pareto_routes(self.g, start, lambda s: s == target)
        self.assertEqual(len(routes), 2)
        costs = {r["cost"] for r in routes}
        self.assertIn((7.0, 10.0, 4.0), costs)
        self.assertIn((11.0, 9.0, 3.0), costs)

    def test_resource_profile_changes_route(self):
        start, target = FlowState(0, 1, 0), FlowState(1, 2, 3)
        routes = pareto_routes(self.g, start, lambda s: s == target)
        fast = choose_route(routes, ResourceProfile("fast", 1.0, 0.05))
        cheap = choose_route(routes, ResourceProfile("cheap", 0.2, 1.0))
        self.assertEqual(fast["cost"][0], 7.0)
        self.assertEqual(cheap["cost"][0], 11.0)
        self.assertLess(cheap["cost"][1], fast["cost"][1])

    def test_every_pareto_route_reaches_its_declared_target(self):
        start, target = FlowState(0, 1, 0), FlowState(1, 2, 3)
        routes = pareto_routes(self.g, start, lambda s: s == target)
        for route in routes:
            state = start
            for action in route["path"]:
                state = self.g.transition(state, action)
            self.assertEqual(state, target)

    def test_resource_budget_can_make_target_infeasible(self):
        start, target = FlowState(0, 1, 0), FlowState(1, 2, 3)
        routes = pareto_routes(self.g, start, lambda s: s == target)
        constrained = choose_route(
            routes, ResourceProfile("strict", 1.0, 0.0, max_time=8, max_energy=9)
        )
        self.assertIsNone(constrained)

    def test_controlled_viability_exceeds_passive_viability(self):
        safe = lambda s: s.a >= 1 and s.b >= 1
        controlled = controlled_invariant_kernel(self.g, safe)
        passive = autonomous_invariant_kernel(self.g, safe)
        self.assertEqual(len(controlled), 35)
        self.assertEqual(len(passive), 0)
        self.assertEqual(len(controlled - passive), 35)

    def test_viability_policy_keeps_all_states_safe(self):
        safe = lambda s: s.a >= 1 and s.b >= 1
        kernel = controlled_invariant_kernel(self.g, safe)
        policy = viability_policy(self.g, kernel)
        self.assertEqual(set(policy), set(kernel))
        for s, action in policy.items():
            nxt = self.g.transition(s, action)
            self.assertIn(nxt, kernel)
            self.assertTrue(safe(nxt))

    def test_external_phase_changes_endogenous_levels(self):
        states = [FlowState(1, 1, 0)]
        for _ in range(4):
            states.append(self.g.transition(states[-1], "HOLD"))
        self.assertEqual(states[1], FlowState(2, 1, 1))
        self.assertEqual(states[2], FlowState(2, 0, 2))
        self.assertEqual(states[4], FlowState(3, 0, 0))

    def test_exogenous_forcing_is_not_actuator_control(self):
        s = FlowState(1, 1, 0)
        hold, hold_ledger = self.g.step_with_ledger(s, "HOLD")
        move, move_ledger = self.g.step_with_ledger(s, "A_TO_B")
        self.assertEqual(hold_ledger.inflow, move_ledger.inflow)
        self.assertEqual(hold_ledger.requested_demand, move_ledger.requested_demand)
        self.assertNotEqual(hold, move)

    def test_ground_law_change_changes_transition_from_same_state(self):
        changed = self.g.revise_environment(inflow=(0, 1, 0, 1))
        state = FlowState(1, 1, 0)
        self.assertNotEqual(self.g.transition(state, "HOLD"), changed.transition(state, "HOLD"))

    def test_spill_and_unmet_demand_are_recorded_not_hidden(self):
        _, spill_ledger = self.g.step_with_ledger(FlowState(3, 0, 0), "HOLD")
        _, unmet_ledger = self.g.step_with_ledger(FlowState(0, 0, 1), "HOLD")
        self.assertEqual(spill_ledger.spill, 1)
        self.assertEqual(unmet_ledger.unmet_demand, 1)

    def test_ground_capacity_expansion_increases_state_space(self):
        self.assertEqual(len(self.g.all_states()), 64)
        self.assertEqual(len(self.g.revise_capacity(4).all_states()), 100)


if __name__ == "__main__":
    unittest.main()
