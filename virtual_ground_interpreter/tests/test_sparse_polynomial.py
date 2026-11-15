"""Sparse observations are not universal proofs; symbolic model identity is."""
import random
import unittest
from vgi.geometry_first import FiniteGeometry
from vgi.polynomial_lift import PolynomialLiftError, TransitionSnapshot, discover_polynomial_lift
from vgi.sparse_polynomial import (
    SparseTransitionObservations, DeclaredPolynomialGround,
    ModelCertifiedSparseNavigation, certify_declared_model,
    fit_sparse_hypothesis, propose_rank_probes,
)

P = 101
EPSILON = DeclaredPolynomialGround(
    P, "epsilon", 2,
    (((0, 2), 1), ((1, 0), 1)),
    (((0, 0), 1), ((0, 1), 1)),
    "geometry-first-003-epsilon",
)


def observe(model, states):
    return SparseTransitionObservations(model.modulus, model.action,
                                        tuple((state, model.step(state)) for state in states),
                                        source="synthetic-polynomial-test",
                                        revision="rev-a")


class PartialAlgebraTests(unittest.TestCase):
    def test_minimal_active_basis_probes_discover_law_without_full_ground(self):
        probes = propose_rank_probes(P, 2)
        self.assertEqual(len(probes), 6)
        self.assertEqual(len(set(probes)), 6)
        observations = observe(EPSILON, (*probes, 40 * P + 41, 57 * P + 67))
        hypothesis = fit_sparse_hypothesis(observations)
        self.assertEqual(hypothesis.status, "observational_hypothesis_unverified_outside_samples")
        self.assertEqual(len(hypothesis.fit_states), 6)
        self.assertEqual(len(hypothesis.heldout_states), 2)
        self.assertEqual(hypothesis.x_next, EPSILON.x_next)
        self.assertEqual(hypothesis.y_next, EPSILON.y_next)
        self.assertEqual(len(propose_rank_probes(P, 2, hypothesis.fit_states)), 0)
        with self.assertRaises(PolynomialLiftError):
            hypothesis.state_at(1, 10**25)

    def test_symbolic_model_proof_discovers_lift_and_large_time(self):
        probes = propose_rank_probes(P, 2)
        h = fit_sparse_hypothesis(observe(EPSILON, probes))
        cert = certify_declared_model(h, EPSILON)
        self.assertEqual(cert.features, ((1, 0), (0, 1), (0, 2)))
        self.assertEqual(cert.status, "certified_for_declared_model_not_external_ground")
        self.assertEqual(cert.transform.matrix, ((1, 0, 1), (0, 1, 0), (0, 2, 1)))
        self.assertEqual(cert.transform.offset, (0, 1, 1))
        for initial in (0, 99, 4020, 8746):
            for ticks in (0, 1, 2, 5, 100, 300):
                expected = initial
                for _ in range(ticks):
                    expected = EPSILON.step(expected)
                self.assertEqual(cert.state_at(initial, ticks).state, expected)
        big = 10**30 + 11
        x, y = 39, 47
        squares = big * y*y + y*big*(big-1) + big*(big-1)*(2*big-1)//6
        result = cert.state_at(39 * P + 47, big)
        self.assertEqual(result.coordinates, ((39+squares)%P,(47+big)%P))
        self.assertEqual(result.observed_edges, 6)
        self.assertEqual(result.materialized_intermediate_states, 0)
        self.assertEqual(result.trust_scope, "formal_declared_ground_only")

    def test_sparse_untrusted_oracle_can_hide_an_unobserved_counterexample(self):
        probes = propose_rank_probes(P, 2)
        sample = observe(EPSILON, probes)
        h = fit_sparse_hypothesis(sample)
        self.assertEqual(len(sample.edges), 6)
        # The synthetic oracle below lies at a point that the probes never
        # inspected. Same hypothesis is compatible with both worlds.
        tampered_point = 50 * P + 50
        self.assertNotIn(tampered_point, probes)
        world_a = EPSILON.step(tampered_point)
        world_b = (world_a + P) % (P*P)
        self.assertNotEqual(world_a, world_b)
        self.assertEqual(fit_sparse_hypothesis(sample).fingerprint, h.fingerprint)
        with self.assertRaises(PolynomialLiftError):
            fit_sparse_hypothesis(SparseTransitionObservations(
                P, "epsilon", (*sample.edges, (tampered_point, world_b))))
        # A declared Ground certificate applies to the model, not world_b.
        self.assertEqual(certify_declared_model(h, EPSILON).status,
                         "certified_for_declared_model_not_external_ground")

    def test_partial_rank_and_counterexample_refusal(self):
        probes = propose_rank_probes(P, 2)
        with self.assertRaises(PolynomialLiftError):
            fit_sparse_hypothesis(observe(EPSILON, probes[:-1]))
        with self.assertRaises(PolynomialLiftError):
            SparseTransitionObservations(P, "epsilon", ((1, 2), (1, 2)))
        with self.assertRaises(PolynomialLiftError):
            propose_rank_probes(101, 3, (*probes, probes[0]))
        first = observe(EPSILON, probes)
        bad = DeclaredPolynomialGround(P,"epsilon",2,
                (((0,2),2),((1,0),1)), EPSILON.y_next, "conflicting-ground")
        with self.assertRaises(PolynomialLiftError):
            certify_declared_model(fit_sparse_hypothesis(first), bad)

    def test_cubic_law_auto_lifts_higher_basis_after_sparse_fitting(self):
        p = 13
        cubic = DeclaredPolynomialGround(p, "cubic", 3,
            (((0,3),1),((1,0),1)), (((0,0),1),((0,1),1)), "cubic-model")
        probes = propose_rank_probes(p, 3)
        self.assertEqual(len(probes), 10)
        hypothesis = fit_sparse_hypothesis(observe(cubic, probes), degree=3)
        with self.assertRaises(PolynomialLiftError):
            certify_declared_model(hypothesis, cubic, max_feature_degree=2)
        cert = certify_declared_model(hypothesis, cubic, max_feature_degree=3)
        self.assertEqual(cert.features, ((1,0),(0,1),(0,2),(0,3)))
        rng = random.Random(21)
        for _ in range(25):
            start = rng.randrange(p*p)
            t = rng.randrange(0,200)
            direct = start
            for _ in range(t):
                direct = cubic.step(direct)
            self.assertEqual(cert.state_at(start,t).state,direct)

    def test_existing_full_domain_certificate_remains_independent_stronger_evidence(self):
        geom = FiniteGeometry(11)
        full = discover_polynomial_lift(TransitionSnapshot.capture(geom,"epsilon"),2)
        sparse = fit_sparse_hypothesis(observe(DeclaredPolynomialGround(11,"epsilon",2,
                    EPSILON.x_next, EPSILON.y_next, "same-rule"),
                    propose_rank_probes(11,2)))
        declared = DeclaredPolynomialGround(11,"epsilon",2, EPSILON.x_next, EPSILON.y_next,"same-rule")
        cert = certify_declared_model(sparse,declared)
        for start in (0,11,83,120):
            for t in (0,2,35,1000):
                self.assertEqual(cert.state_at(start,t).state,full.state_at(start,t).state)
        self.assertEqual(len(full.snapshot.targets),121)
        self.assertEqual(cert.state_at(0,1).observed_edges,6)

    def test_random_affine_polynomial_models_have_independent_sample_reconstruction(self):
        rng = random.Random(20261115)
        p = 17
        for index in range(40):
            # Two independent degree-one polynomial updates with runtime inputs.
            values = [rng.randrange(p) for _ in range(6)]
            a,b,c,d,e,f = values
            model = DeclaredPolynomialGround(
                p, "random-affine", 1,
                tuple(sorted((m,k) for m,k in (((1,0),a),((0,1),b),((0,0),c)) if k)),
                tuple(sorted((m,k) for m,k in (((1,0),d),((0,1),e),((0,0),f)) if k)),
                f"sample-{index}",
            )
            probes = propose_rank_probes(p, 1)
            certificate = certify_declared_model(
                fit_sparse_hypothesis(observe(model, probes), 1), model, 1)
            self.assertEqual(certificate.features, ((1,0),(0,1)))
            for __ in range(3):
                start = rng.randrange(p*p)
                tick = rng.randrange(80)
                direct = start
                for _ in range(tick):
                    direct = model.step(direct)
                self.assertEqual(certificate.state_at(start,tick).state,direct)

    def test_symbolic_nonlinear_closure_can_refuse_explosive_feature_growth(self):
        p = 17
        nonlinear = DeclaredPolynomialGround(
            p,"expanding-features",2,(((1,0),1),),(((0,2),1),),"expanding-law")
        observations = observe(nonlinear, propose_rank_probes(p,2))
        hypothesis = fit_sparse_hypothesis(observations,2)
        with self.assertRaises(PolynomialLiftError):
            certify_declared_model(hypothesis,nonlinear,max_feature_degree=3)

    def test_evidence_identity_changes_without_reusing_certificate(self):
        queries=propose_rank_probes(P,2)
        original=observe(EPSILON,queries)
        changed=SparseTransitionObservations(
            P,"epsilon",original.edges,source="different-observer",revision="rev-b")
        self.assertNotEqual(original.fingerprint,changed.fingerprint)
        cert1=certify_declared_model(fit_sparse_hypothesis(original),EPSILON)
        cert2=certify_declared_model(fit_sparse_hypothesis(changed),EPSILON)
        self.assertNotEqual(cert1.fingerprint,cert2.fingerprint)
        self.assertEqual(cert1.state_at(39*P+47,100).state,
                         cert2.state_at(39*P+47,100).state)
        self.assertFalse(cert1.to_dict()["navigation_admitted_for_external_system"])
        self.assertEqual(cert1.to_dict()["model_fingerprint"],EPSILON.fingerprint)

    def test_invalid_symbolic_coefficients_or_contracts_are_refused(self):
        with self.assertRaises(PolynomialLiftError):
            DeclaredPolynomialGround(8,"bad",2,(((1,0),1),),(((0,1),1),))
        with self.assertRaises(PolynomialLiftError):
            DeclaredPolynomialGround(11,"bad",11,(((1,0),1),),(((0,1),1),))
        with self.assertRaises(PolynomialLiftError):
            DeclaredPolynomialGround(11,"bad",2,(((0,3),1),),(((0,1),1),))
        with self.assertRaises(PolynomialLiftError):
            DeclaredPolynomialGround(11,"bad",2,(((1,0),True),),(((0,1),1),))
        with self.assertRaises(PolynomialLiftError):
            DeclaredPolynomialGround(11,"bad",2,(((1,0),11),),(((0,1),1),))


if __name__ == "__main__":
    unittest.main()