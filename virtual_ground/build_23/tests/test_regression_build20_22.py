import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from virtual_ground import base_ground, all_states, bfs_policy
from partial_ground import PartialGround, initial_state, enumerate_reachable
from flow_ground import FlowGround, FlowState, verify_ground
from ground_discovery import candidate_grounds, probe_catalog, behavioral_equivalence_classes, run_active_identification

class PriorBuildRegressionTests(unittest.TestCase):
    def test_build20_reversible_state_count(self):
        self.assertEqual(len(all_states()),648)

    def test_build20_base_ground_bfs_covers_states(self):
        ground=base_ground(); distances,_=bfs_policy(ground)
        self.assertEqual(len(distances),648)

    def test_build20_partial_ground_reachability(self):
        ground=PartialGround(); distances,_,_=enumerate_reachable(ground,initial_state())
        self.assertEqual(len(distances),232)

    def test_build21_flow_ground_mass_balance(self):
        report=verify_ground(FlowGround())
        self.assertTrue(report["all_transitions_valid"])
        self.assertEqual(report["max_mass_balance_residual"],0)

    def test_build22_candidate_family_and_probe_catalog_remain(self):
        models=candidate_grounds(); probes=probe_catalog()
        self.assertEqual(len(models),32)
        self.assertEqual(len(probes),324)
        self.assertEqual(len(behavioral_equivalence_classes(models,probes)),32)

    def test_build22_active_probe_still_identifies_known_ground(self):
        model=candidate_grounds()[0]
        result=run_active_identification(model)
        self.assertTrue(result["identified"])

if __name__=="__main__": unittest.main(verbosity=2)
