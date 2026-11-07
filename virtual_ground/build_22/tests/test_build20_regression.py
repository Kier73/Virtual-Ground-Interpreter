import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "legacy_build_21" / "legacy_build_20"
sys.path.insert(0, str(LEGACY))
import virtual_ground as vg
import partial_ground as pg


class Build20RegressionTests(unittest.TestCase):
    def test_reversible_ground_still_generates_648_states(self):
        ground = vg.base_ground()
        distances, paths = vg.bfs_policy(ground)
        self.assertEqual(len(vg.all_states()), 648)
        self.assertEqual(len(distances), 648)
        self.assertEqual(len(paths), 648)

    def test_reversible_state_encoding_roundtrips(self):
        for state in vg.all_states():
            self.assertEqual(vg.decode_state(vg.encode_state(state)), state)

    def test_partial_ground_still_has_232_reachable_states(self):
        ground = pg.PartialGround()
        distances, parents, edges = pg.enumerate_reachable(ground)
        self.assertEqual(len(distances), 232)
        self.assertEqual(len(edges), 774)

    def test_layer_counts_are_not_transition_congruent(self):
        ground = pg.PartialGround()
        distances, _, _ = pg.enumerate_reachable(ground)
        self.assertFalse(pg.profile_is_transition_congruent(ground, tuple(distances)))


if __name__ == "__main__":
    unittest.main()
