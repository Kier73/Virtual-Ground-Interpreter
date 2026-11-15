"""Independent controls for structural extraction of navigable programs."""
import random
import unittest

from vgi.program_law import (
    ExtractedProgramLaw, ProgramNavigationCertificate, certify_program,
)
from vgi.polynomial_lift import PolynomialLiftError
from vgi.sparse_polynomial import (
    SparseTransitionObservations, propose_rank_probes, fit_sparse_hypothesis,
)
from vgi.affine import ModularAffineMap

SQUARE = """def advance(x, y):
    power = y * y
    next_y = y + 1
    next_x = x + power
    return (next_x % 101, next_y % 101)
"""
CUBE = """def advance(x, y):
    return (x + y**3, y + 1)
"""
PAIR = """def advance(x, y):
    x, y = y, x + y
    return x, y
"""
LINEAR = """def advance(x, y):
    return (2*x + 3*y + 5, x + y + 7)
"""


class ProgramLawTests(unittest.TestCase):
    def test_extracts_square_from_executable_structure_without_given_coefficients(self):
        law = ExtractedProgramLaw(SQUARE, 101)
        self.assertEqual(law.ground.x_next, (((0, 2), 1), ((1, 0), 1)))
        self.assertEqual(law.ground.y_next, (((0, 0), 1), ((0, 1), 1)))
        self.assertEqual(law.ground.degree, 2)
        self.assertEqual(law.to_dict()["status"], "derived_from_bounded_ast_subset")
        self.assertEqual(law.to_dict()["scope"], "formal_bounded_program_semantics_only")

    def test_certifies_square_without_enumerating_finite_ground(self):
        cert = certify_program(SQUARE, 101)
        self.assertEqual(cert.features, ((1, 0), (0, 1), (0, 2)))
        self.assertEqual(cert.to_dict()["observed_edges"], 0)
        self.assertEqual(cert.to_dict()["external_implementation_verified"], False)
        start = 39*101 + 47
        huge = 10**30 + 11
        ans = cert.state_at(start, huge)
        self.assertEqual(ans.coordinates, ((39 + huge*47*47 + 47*huge*(huge-1) + huge*(huge-1)*(2*huge-1)//6) % 101,
                                           (47+huge) % 101))
        self.assertEqual(ans.coordinates, (81, 57))
        self.assertEqual(ans.materialized_intermediate_states, 0)
        self.assertEqual(ans.exponent_bits, huge.bit_length())
        self.assertEqual(ans.trust_scope, "formal_bounded_program_semantics_only")

    def test_stepwise_agreement_with_independent_python_program_execution(self):
        # Only test-owned fixtures are executed. Production parser NEVER execs source.
        rng = random.Random(20261115)
        for src in (SQUARE, CUBE, PAIR, LINEAR):
            namespace = {}
            exec(src, {}, namespace)
            step = namespace["advance"]
            cert = certify_program(src, 101, max_feature_degree=3)
            for _ in range(40):
                x, y = rng.randrange(101), rng.randrange(101)
                t = rng.randrange(0, 80)
                expect = (x, y)
                for _ in range(t):
                    expect = tuple(c % 101 for c in step(*expect))
                result = cert.state_at(x*101+y, t)
                self.assertEqual(result.coordinates, expect)

    def test_parallel_assignment_is_semantically_simultaneous(self):
        law = ExtractedProgramLaw(PAIR, 101)
        self.assertEqual(law.state_after_one(3*101+8), 8*101+11)
        cert = certify_program(PAIR, 101)
        self.assertEqual(cert.state_at(3*101+8, 1).coordinates, (8, 11))
        self.assertEqual(cert.state_at(3*101+8, 0).coordinates, (3, 8))

    def test_cubic_lift_auto_discovers_y_squared_and_cubed(self):
        cert = certify_program(CUBE, 101)
        self.assertEqual(set(cert.features), {(1, 0), (0, 1), (0, 2), (0, 3)})
        with self.assertRaises(PolynomialLiftError):
            certify_program(CUBE, 101, max_feature_degree=2)

    def test_admits_observation_receipts_only_when_consistent(self):
        p = 101
        law = ExtractedProgramLaw(SQUARE, p)
        probes = propose_rank_probes(p, 2)
        edges = tuple((s, law.state_after_one(s)) for s in probes)
        obs = SparseTransitionObservations(p, "advance", edges, "local-fixture", "revision-a")
        cert = certify_program(SQUARE, p, observations=obs)
        hypothesis = fit_sparse_hypothesis(obs, 2)
        self.assertEqual(hypothesis.x_next, law.ground.x_next)
        self.assertEqual(hypothesis.y_next, law.ground.y_next)
        self.assertEqual(cert.to_dict()["observed_edges"], 6)
        self.assertEqual(cert.to_dict()["observation_fingerprint"], obs.fingerprint)
        self.assertNotEqual(cert.fingerprint, certify_program(SQUARE, p).fingerprint)
        s = probes[0]
        bad = SparseTransitionObservations(p, "advance", ((s, (law.state_after_one(s)+1)%(p*p)),))
        with self.assertRaisesRegex(PolynomialLiftError, "contradicts"):
            certify_program(SQUARE, p, observations=bad)
        mismatched = SparseTransitionObservations(p, "other", edges)
        with self.assertRaises(PolynomialLiftError):
            certify_program(SQUARE, p, observations=mismatched)

    def test_refuses_external_calls_control_flow_and_global_state(self):
        invalid = (
            "def advance(x,y):\n    return __import__('os').system('echo hi'), y\n",
            "def advance(x,y):\n    if x: return x,y\n    return y,x\n",
            "def advance(x,y):\n    for i in range(3): x=x+1\n    return x,y\n",
            "def advance(x,y):\n    return x/y,y\n",
            "def advance(x,y):\n    return x[0], y\n",
            "def advance(x,y):\n    return x, globals()\n",
            "def advance(x,y):\n    global x\n    return x,y\n",
            "def advance(x,y):\n    return (x, y)\nadvance(1,2)\n",
            "@property\ndef advance(x,y):\n    return x,y\n",
            "def advance(x,y):\n    return x+u,y\n",
            "def advance(x,y):\n    return x,y**100\n",
            "def advance(x,y):\n    return x%7, y\n",
            "def advance(x,y):\n    return x==y, y\n",
            "def advance(x,y):\n    return True, y\n",
        )
        for source in invalid:
            with self.subTest(source=source):
                with self.assertRaises(PolynomialLiftError):
                    certify_program(source, 101)

    def test_rejects_nonclosing_growth_and_degree_excess(self):
        with self.assertRaises(PolynomialLiftError):
            certify_program("def advance(x,y):\n    return x*x, y+1\n", 101)
        with self.assertRaises(PolynomialLiftError):
            certify_program("def advance(x,y):\n    return x+y**4, y+1\n", 101)
        with self.assertRaises(PolynomialLiftError):
            certify_program(SQUARE, 8)
        with self.assertRaises(PolynomialLiftError):
            certify_program(SQUARE, 101, max_feature_degree=1)

    def test_rejects_malicious_supplied_transform_and_features(self):
        cert = certify_program(SQUARE, 101)
        with self.assertRaises(PolynomialLiftError):
            ProgramNavigationCertificate(cert.law, 3, cert.features[:-1], cert.transform)
        with self.assertRaises(PolynomialLiftError):
            ProgramNavigationCertificate(
                cert.law, 3, cert.features,
                ModularAffineMap(101, ((1,0,0),(0,1,0),(0,0,1)), (0,0,0)),
            )

    def test_source_identity_and_model_identity_are_distinct(self):
        source2 = SQUARE.replace("power = y * y", "power = y ** 2")
        a = certify_program(SQUARE, 101)
        b = certify_program(source2, 101)
        self.assertNotEqual(a.law.source_digest, b.law.source_digest)
        self.assertNotEqual(a.law.ground.fingerprint, b.law.ground.fingerprint)
        self.assertEqual(a.features, b.features)
        self.assertEqual(a.transform.to_dict(), b.transform.to_dict())
        self.assertEqual(a.state_at(111, 101).coordinates, b.state_at(111, 101).coordinates)

    def test_cost_does_not_scale_with_number_of_logical_transitions(self):
        cert = certify_program(SQUARE, 101)
        source = 39*101+47
        for t in (1, 13, 10**6, 10**30+11, 10**100+123):
            found = cert.state_at(source, t)
            self.assertEqual(found.exponent_bits, t.bit_length())
            self.assertEqual(found.materialized_intermediate_states, 0)


if __name__ == "__main__":
    unittest.main()