import itertools
import unittest

from virtual_ground import (
    IDENTITY, SOLVED, State, all_states, apply_named_path, apply_transform,
    base_ground, bfs_policy, compose, decode_state, encode_state,
    factorized_plan, inverse, observer_view, primitive_moves, quotient_bfs,
    quotient_classes, quotient_plan, shortest_plan_between, stable_consensus,
    transform_of_state, validate_state, coordinate_transition, dijkstra_policy,
    GroundNavigator,
)


class TestVirtualGroundStateSpace(unittest.TestCase):
    def test_all_states_are_valid_and_count_is_648(self):
        states = all_states()
        self.assertEqual(len(states), 648)
        self.assertTrue(all(validate_state(s) for s in states))
        self.assertEqual(len(set(states)), 648)

    def test_ground_generators_reach_every_valid_state(self):
        ground = base_ground()
        distances, paths = bfs_policy(ground)
        self.assertEqual(len(distances), 648)
        self.assertEqual(set(distances), set(all_states()))

    def test_coordinate_encoding_is_bijective(self):
        states = all_states()
        codes = [encode_state(s) for s in states]
        self.assertEqual(len(set(codes)), 648)
        self.assertEqual(set(codes), set(range(648)))
        for s in states:
            self.assertEqual(decode_state(encode_state(s)), s)

    def test_rank_order_is_fixed_and_reversible(self):
        for code in range(648):
            self.assertEqual(encode_state(decode_state(code)), code)

    def test_coordinate_chart_intertwines_every_primitive_transition(self):
        ground = base_ground()
        for state in all_states():
            code = encode_state(state)
            for move in ground.moves:
                encoded_next = coordinate_transition(code, move.name, ground)
                direct_next = encode_state(apply_transform(state, move))
                self.assertEqual(encoded_next, direct_next)

    def test_every_primitive_move_preserves_validity(self):
        ground = base_ground()
        for s in all_states():
            for move in ground.moves:
                self.assertTrue(validate_state(apply_transform(s, move)))


class TestTransformationAlgebra(unittest.TestCase):
    def test_identity_is_identity(self):
        for s in all_states():
            self.assertEqual(apply_transform(s, IDENTITY), s)

    def test_each_primitive_has_inverse(self):
        for move in primitive_moves(True):
            self.assertEqual(apply_transform(apply_transform(SOLVED, move), inverse(move)), SOLVED)

    def test_inverse_works_from_arbitrary_states(self):
        states = all_states()
        for move in primitive_moves(True):
            for s in states[::17]:
                self.assertEqual(apply_transform(apply_transform(s, move), inverse(move)), s)

    def test_composition_matches_sequential_application(self):
        moves = primitive_moves(True)
        for a, b in itertools.product(moves, repeat=2):
            c = compose(a, b)
            for s in all_states()[::29]:
                self.assertEqual(apply_transform(s, c), apply_transform(apply_transform(s, a), b))

    def test_composition_is_associative_for_move_triples(self):
        moves = primitive_moves(True)
        for a, b, c in zip(moves, moves[1:] + moves[:1], moves[2:] + moves[:2]):
            left = compose(compose(a, b), c)
            right = compose(a, compose(b, c))
            self.assertEqual((left.dest, left.twist), (right.dest, right.twist))

    def test_state_has_unique_generating_transform(self):
        for s in all_states():
            self.assertEqual(apply_transform(SOLVED, transform_of_state(s)), s)


class TestNavigationAndMacros(unittest.TestCase):
    def test_exact_shortest_paths_reach_every_state(self):
        ground = base_ground()
        distances, paths = bfs_policy(ground)
        self.assertEqual(distances[SOLVED], 0)
        for target in all_states():
            path = paths[target]
            self.assertEqual(apply_named_path(SOLVED, path, ground), target)
            self.assertEqual(len(path), distances[target])

    def test_factorized_macro_plan_reaches_every_state_from_solved(self):
        ground = base_ground()
        for target in all_states():
            path, macros = factorized_plan(SOLVED, target)
            self.assertEqual(apply_named_path(SOLVED, path, ground), target)
            self.assertLessEqual(len([1 for _, exp in macros if exp]), 2)

    def test_factorized_macro_plan_reaches_sampled_arbitrary_targets(self):
        ground = base_ground()
        states = all_states()
        for i in range(0, len(states), 11):
            start = states[i]
            target = states[(i * 31 + 17) % len(states)]
            path, _ = factorized_plan(start, target)
            self.assertEqual(apply_named_path(start, path, ground), target)

    def test_macro_expansion_length_equals_primitive_path_length(self):
        for target in all_states()[::7]:
            path, macros = factorized_plan(SOLVED, target)
            self.assertEqual(len(path), sum(len(exp) for _, exp in macros))

    def test_resource_weighting_can_change_the_optimal_path(self):
        ground = base_ground()
        costs_unit = {m.name: 1.0 for m in ground.moves}
        costs_twist_expensive = {m.name: (4.0 if m.name.startswith("TWIST") else 1.0) for m in ground.moves}
        _, unit_paths = dijkstra_policy(ground, costs_unit)
        weighted_costs, weighted_paths = dijkstra_policy(ground, costs_twist_expensive)
        target = decode_state(5)
        self.assertEqual(unit_paths[target], ("TWIST1+", "TWIST2-"))
        self.assertEqual(weighted_paths[target], ("SWAP23", "TWIST1+", "SWAP23"))
        self.assertEqual(weighted_costs[target], 6.0)

    def test_shortest_metric_is_not_confused_with_macro_count(self):
        ground = base_ground()
        distances, _ = bfs_policy(ground)
        examples = 0
        for target in all_states():
            path, macros = factorized_plan(SOLVED, target)
            macro_count = sum(bool(exp) for _, exp in macros)
            if len(path) > distances[target] and macro_count < len(path):
                examples += 1
        self.assertGreater(examples, 0)

    def test_relative_group_plan_reaches_arbitrary_target(self):
        states = all_states()
        ground = base_ground()
        for i in range(0, 648, 23):
            start = states[i]
            target = states[(i * 17 + 41) % 648]
            path = shortest_plan_between(start, target, ground)
            self.assertIsNotNone(path)
            self.assertEqual(apply_named_path(start, path, ground), target)

    def test_precomputed_ground_navigator_uses_relative_transform(self):
        ground = base_ground()
        navigator = GroundNavigator(ground)
        states = all_states()
        for i in range(0, 648, 19):
            start = states[i]
            target = states[(i * 13 + 5) % 648]
            result = navigator.query(start, target)
            self.assertIsNotNone(result)
            path, cost = result
            self.assertEqual(apply_named_path(start, path, ground), target)
            self.assertEqual(cost, len(path))

    def test_relative_group_plan_is_shortest(self):
        ground = base_ground()
        states = all_states()
        for i in range(0, 648, 37):
            start = states[i]
            target = states[(i * 29 + 7) % 648]
            path = shortest_plan_between(start, target, ground)
            relative = compose(inverse(transform_of_state(start)), transform_of_state(target))
            relative_state = apply_transform(SOLVED, relative)
            distances, _ = bfs_policy(ground)
            self.assertEqual(len(path), distances[relative_state])


class TestObserverGrounds(unittest.TestCase):
    def test_observer_class_counts(self):
        states = all_states()
        self.assertEqual(len(quotient_classes(states, "full")), 648)
        self.assertEqual(len(quotient_classes(states, "layout")), 24)
        self.assertEqual(len(quotient_classes(states, "orientation")), 27)

    def test_layout_observer_collapses_orientation(self):
        a = State((0, 1, 2, 3), (0, 0, 0, 0))
        b = State((0, 1, 2, 3), (1, 2, 0, 0))
        self.assertEqual(observer_view(a, "layout"), observer_view(b, "layout"))
        self.assertNotEqual(observer_view(a, "full"), observer_view(b, "full"))

    def test_quotient_navigation_is_well_defined_for_each_observer(self):
        ground = base_ground()
        for observer in ("full", "layout", "orientation"):
            distances = quotient_bfs(ground, SOLVED, observer)
            self.assertEqual(len(distances), len(quotient_classes(all_states(), observer)))

    def test_layout_quotient_has_24_reachable_classes(self):
        self.assertEqual(len(quotient_bfs(base_ground(), SOLVED, "layout")), 24)

    def test_orientation_quotient_has_27_reachable_classes(self):
        self.assertEqual(len(quotient_bfs(base_ground(), SOLVED, "orientation")), 27)

    def test_layout_intention_can_be_satisfied_without_full_state_match(self):
        states = all_states()
        start = states[0]
        target = next(s for s in states if s.perm == start.perm and s.ori != start.ori)
        path = quotient_plan(start, target, base_ground(), "layout")
        self.assertEqual(path, ())
        self.assertEqual(observer_view(start, "layout"), observer_view(target, "layout"))
        self.assertNotEqual(start, target)

    def test_full_state_intention_requires_hidden_orientation(self):
        states = all_states()
        start = states[0]
        target = next(s for s in states if s.perm == start.perm and s.ori != start.ori)
        path = quotient_plan(start, target, base_ground(), "full")
        self.assertIsNotNone(path)
        self.assertEqual(apply_named_path(start, path, base_ground()), target)


class TestIntentionConsensusAndGroundShift(unittest.TestCase):
    def test_stable_consensus_requires_consecutive_dwell(self):
        self.assertEqual(stable_consensus([(1,), (1,), (1,), (2,)], 3), (True, (1,)))
        self.assertEqual(stable_consensus([(1,), (1,), (2,), (1,)], 3), (False, None))

    def test_consensus_rejects_zero_dwell(self):
        with self.assertRaises(ValueError):
            stable_consensus([(1,)], 0)

    def test_ground_revision_changes_version_and_operation_set(self):
        base = base_ground()
        locked = base.revise_without_twists()
        self.assertEqual(locked.version, base.version + 1)
        self.assertEqual(len(base.moves), 9)
        self.assertEqual(len(locked.moves), 3)

    def test_ground_shift_reduces_reachable_states(self):
        base = base_ground()
        locked = base.revise_without_twists()
        base_reach, _ = bfs_policy(base)
        locked_reach, _ = bfs_policy(locked)
        self.assertEqual(len(base_reach), 648)
        self.assertEqual(len(locked_reach), 24)

    def test_orientation_locked_ground_retains_layout_navigation(self):
        locked = base_ground().revise_without_twists()
        states = all_states()
        _, paths = bfs_policy(locked)
        for target in states:
            reachable = target.ori == SOLVED.ori
            self.assertEqual(target in paths, reachable)


if __name__ == "__main__":
    unittest.main(verbosity=2)
