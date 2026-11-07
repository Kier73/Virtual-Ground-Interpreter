import unittest

from partial_ground import (
    PartialGround, enumerate_reachable, initial_state, level_counts,
    profile_is_transition_congruent,
)


class TestPartialIrreversibleGround(unittest.TestCase):
    def test_initial_state_is_stable(self):
        ground = PartialGround()
        self.assertTrue(ground.stable(initial_state()))

    def test_every_stable_mask_is_reachable_from_initial_ground(self):
        ground = PartialGround()
        reachable, _, _ = enumerate_reachable(ground)
        all_stable = {mask for mask in range(512) if ground.stable(mask)}
        self.assertEqual(set(reachable), all_stable)

    def test_every_stable_mask_is_reachable_after_support_revision(self):
        ground = PartialGround().revise_support(6, (3,))
        reachable, _, _ = enumerate_reachable(ground)
        all_stable = {mask for mask in range(512) if ground.stable(mask)}
        self.assertEqual(set(reachable), all_stable)

    def test_every_reachable_transition_is_legal_and_stable(self):
        ground = PartialGround()
        distances, _, edges = enumerate_reachable(ground)
        for before, action, after in edges:
            self.assertIn(action, ground.legal_actions(before))
            self.assertTrue(ground.stable(after))
            self.assertEqual(after.bit_count(), before.bit_count() - 1)
        self.assertEqual(len(distances), 232)
        self.assertEqual(len(edges), 774)

    def test_removal_is_irreversible_and_graph_is_acyclic(self):
        ground = PartialGround()
        distances, _, edges = enumerate_reachable(ground)
        self.assertTrue(all(after < before for before, _, after in edges))
        self.assertEqual(len(distances), 232)

    def test_empty_state_is_reachable_terminal(self):
        ground = PartialGround()
        distances, _, _ = enumerate_reachable(ground)
        self.assertIn(0, distances)
        self.assertEqual(ground.legal_actions(0), ())

    def test_support_rule_changes_ground_version(self):
        base = PartialGround()
        revised = base.revise_support(6, (3,))
        self.assertEqual(revised.version, base.version + 1)
        self.assertNotEqual(revised.supports, base.supports)

    def test_support_revision_changes_reachable_region(self):
        base = PartialGround()
        revised = base.revise_support(6, (3,))
        before, _, _ = enumerate_reachable(base)
        after, _, _ = enumerate_reachable(revised)
        self.assertEqual(len(before), 232)
        self.assertEqual(len(after), 200)

    def test_level_count_observer_is_not_transition_congruent(self):
        ground = PartialGround()
        states, _, _ = enumerate_reachable(ground)
        self.assertFalse(profile_is_transition_congruent(ground, tuple(states)))

    def test_same_level_counts_can_have_different_legal_actions(self):
        ground = PartialGround()
        states, _, _ = enumerate_reachable(ground)
        buckets = {}
        for state in states:
            buckets.setdefault(level_counts(state), []).append(state)
        witness = None
        for profile, group in buckets.items():
            actions = {tuple(ground.legal_actions(s)) for s in group}
            if len(actions) > 1:
                witness = (profile, group)
                break
        self.assertIsNotNone(witness)


if __name__ == "__main__":
    unittest.main(verbosity=2)
