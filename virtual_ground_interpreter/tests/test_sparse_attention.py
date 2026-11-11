import unittest
from fractions import Fraction

from vgi import GroundTransitionSystem, ObserverContext, TransitionObservation, TransitionOutcome
from vgi.relational import partial_contextual_comparison
from vgi.sparse import sparse_partial_refinement_series
from vgi.partial_attention import (
    PartialAttentionError, ProbeScenario, TransitionProbe,
    rank_partial_probes, score_partial_probe,
)


def partial_ground():
    return GroundTransitionSystem(
        states=("a","b","c"), actions=("X","Y"), initial_state="a", channels=("out",),
        observations=(
            TransitionObservation("a","X",(TransitionOutcome("a",(0,)),)),
            TransitionObservation("b","X",(TransitionOutcome("b",(0,)),)),
            TransitionObservation("c","X",(TransitionOutcome("c",(1,)),)),
            TransitionObservation("a","Y",(TransitionOutcome("a",(0,)),)),
            TransitionObservation("b","Y",(
                TransitionOutcome("a",(0,)),TransitionOutcome("c",(1,))
            ),support_count=2),
        ),
    )


class SparsePartialTests(unittest.TestCase):
    def test_sparse_partitions_and_queries_match_eager_reference(self):
        system=partial_ground();observer=ObserverContext.full(system)
        eager=[partial_contextual_comparison(system,observer,h) for h in range(4)]
        sparse=sparse_partial_refinement_series(system,observer,3)
        for old,new in zip(eager,sparse):
            self.assertEqual(new.stored_pair_records,0)
            for left in system.states:
                for right in system.states:
                    self.assertEqual(new.status(left,right),old.status(left,right))
                    self.assertEqual(new.witness(left,right),old.witness(left,right))
                    self.assertEqual(
                        tuple(x.reason for x in new.blockers(left,right)),
                        tuple(x.reason for x in old.blockers(left,right)),
                    )

    def test_lazy_partition_and_pair_explanations(self):
        system=partial_ground();observer=ObserverContext.full(system)
        comparison=sparse_partial_refinement_series(system,observer,2)[2]
        self.assertEqual(comparison.status("a","b"),"unresolved")
        self.assertEqual(comparison.status("a","c"),"distinguishable")
        self.assertEqual(comparison.witness("a","c"),("X",))
        self.assertEqual(comparison.stored_pair_records,0)
        self.assertGreater(comparison.unresolved_pair_count(),0)

    def test_scenarios_without_weights_report_bounds_not_expectation(self):
        system=partial_ground();observer=ObserverContext.full(system)
        probe=TransitionProbe("b","Y",(
            ProbeScenario(TransitionOutcome("a",(0,))),
            ProbeScenario(TransitionOutcome("c",(1,))),
        ),cost=Fraction(3,2))
        score=score_partial_probe(system,observer,probe,2)
        self.assertEqual(score.estimation_kind,"scenario_bounds_only")
        self.assertIsNone(score.expected_resolved_pairs)
        self.assertEqual(score.affected_pairs,2)
        self.assertLessEqual(score.minimum_resolved_pairs,score.maximum_resolved_pairs)

    def test_exact_expected_probe_value_requires_exact_weights(self):
        system=partial_ground();observer=ObserverContext.full(system)
        probe=TransitionProbe("b","Y",(
            ProbeScenario(TransitionOutcome("a",(0,)),Fraction(1,3)),
            ProbeScenario(TransitionOutcome("c",(1,)),Fraction(2,3)),
        ),cost=Fraction(2))
        score=score_partial_probe(system,observer,probe,2)
        expected=sum((x.resolved_pairs*x.weight for x in score.scenario_scores),Fraction(0))
        self.assertEqual(score.expected_resolved_pairs,expected)
        self.assertEqual(score.expected_gain_per_cost,expected/2)
        self.assertEqual(expected,Fraction(1))

    def test_probe_ranking_and_known_cell_rejection(self):
        system=partial_ground();observer=ObserverContext.full(system)
        unknown=TransitionProbe("c","Y",(ProbeScenario(TransitionOutcome("c",(0,))),))
        self.assertEqual(len(rank_partial_probes(system,observer,(unknown,),1)),1)
        known=TransitionProbe("a","X",(ProbeScenario(TransitionOutcome("b",(0,))),))
        with self.assertRaises(PartialAttentionError):
            score_partial_probe(system,observer,known,1)

    def test_probe_rejects_floating_point_probabilities_and_costs(self):
        with self.assertRaises(PartialAttentionError):
            ProbeScenario(TransitionOutcome("a",(0,)),0.5)
        with self.assertRaises(PartialAttentionError):
            TransitionProbe("c","Y",(ProbeScenario(TransitionOutcome("c",(0,))),),cost=0.1)


if __name__=="__main__":
    unittest.main()
