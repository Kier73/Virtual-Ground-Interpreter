import unittest
from fractions import Fraction

from vgi.exact import (
    ExactObservable, ExactObservableFrame, ExactPolynomial, ExactValueError,
    RationalValue, rational_mean, rational_sum, rational_variance,
    rational_weighted_sum,
)
from vgi.proof import (
    ProofGroundAdapter, ProofGroundError, VerifiedKernelReceipt,
)


ENV={
    "assistant":"Lean","assistant_version":"4.15.0",
    "environment_fingerprint":"env-sha256","imports_fingerprint":"imports-sha256",
    "options_fingerprint":"options-sha256",
}


def proof_trace():
    return {
        "format":"VGI-LeanProofTrace-1","environment":ENV,
        "obligations":[
            {"key":"root","goal":{"kind":"forall","type":"Nat","body":{"kind":"eq","lhs":"n","rhs":"n"}}},
            {"key":"left","goal":{"kind":"nat_induction_base","variable":"n"}},
            {"key":"right","goal":{"kind":"nat_induction_step","variable":"n"},
             "local_context":[{"name":"ih","type":"P(n)"}],"metavariables":{"?m":"Nat"}},
            {"key":"alternate","goal":{"kind":"alternate","target":"root"}},
        ],
        "transitions":[
            {"source":"root","tactic":"induction n","subgoals":["left","right"],"attempt_status":"elaborated"},
            {"source":"root","tactic":"custom_tactic","subgoals":["alternate"],"attempt_status":"candidate"},
            {"source":"right","tactic":"simp","subgoals":[],"attempt_status":"timeout"},
        ],
        "kernel_accepted":["root"],
    }


class ExactValueTests(unittest.TestCase):
    def test_exact_rational_aggregates(self):
        values=(Fraction(1,3),Fraction(1,2),Fraction(1,6))
        self.assertEqual(rational_sum(values),RationalValue(Fraction(1)))
        self.assertEqual(rational_mean(values),RationalValue(Fraction(1,3)))
        self.assertEqual(rational_variance((1,2,3)),RationalValue(Fraction(2,3)))
        self.assertEqual(
            rational_weighted_sum((2,4),(1,3),normalize=True),
            RationalValue(Fraction(7,2)),
        )

    def test_polynomial_arithmetic_and_exact_evaluation(self):
        x=ExactPolynomial.variable("x",("x","y"))
        y=ExactPolynomial.variable("y",("x","y"))
        expr=x*x+ExactPolynomial.constant(Fraction(1,2),("x","y"))*y
        self.assertEqual(expr.total_degree,2)
        self.assertEqual(expr.evaluate({"x":2,"y":4}),RationalValue(Fraction(6)))
        self.assertEqual(len(expr.terms),2)

    def test_exact_values_reject_float_approximations(self):
        with self.assertRaises(ExactValueError):
            RationalValue(0.1)
        with self.assertRaises(ExactValueError):
            ExactPolynomial.constant(0.1)

    def test_exact_observables_stay_outside_signal8(self):
        frame=ExactObservableFrame(
            "state-1","logical-clock",12,"ground-sha",
            (ExactObservable("influence",RationalValue(Fraction(1,3))),),
        )
        self.assertEqual(frame.to_dict()["observables"][0]["value"]["numerator"],1)
        with self.assertRaises(ExactValueError):
            RationalValue.of(1,0)


class ProofGroundTests(unittest.TestCase):
    def test_and_bundle_and_or_tactic_alternatives(self):
        ground=ProofGroundAdapter.from_lean_trace(proof_trace())
        root=ground.obligation_ids[0]
        induction=ground.alternatives(root,"induction n")
        alternative=ground.alternatives(root,"custom_tactic")
        self.assertEqual(len(induction),1)
        self.assertEqual(len(induction[0].subgoal_ids),2)
        self.assertEqual(len(alternative),1)
        self.assertEqual(ground.kernel_status(root),"unverified")
        self.assertEqual(ground.summary()["unverified_obligations"],4)
        self.assertEqual(ground.summary()["observed_untrusted_kernel_claims"],["root"])

    def test_goal_surface_match_does_not_merge_different_contexts(self):
        payload=proof_trace()
        payload["obligations"].append({
            "key":"different-context","goal":payload["obligations"][0]["goal"],
            "local_context":[{"name":"h","type":"P"}],
        })
        ground=ProofGroundAdapter.from_lean_trace(payload)
        self.assertEqual(len(ground.obligations),5)
        self.assertNotEqual(ground.obligations[0].fingerprint,ground.obligations[-1].fingerprint)

    def test_only_explicit_matched_receipt_admits_kernel_status(self):
        base=ProofGroundAdapter.from_lean_trace(proof_trace())
        root=base.obligation_ids[0]
        receipt=VerifiedKernelReceipt(
            root,"proof-term-sha",ENV["environment_fingerprint"],
            "Lean.kernel","4.15.0","accepted","kernel-run-17",
        )
        checked=ProofGroundAdapter.from_lean_trace(proof_trace(),verified_receipts=(receipt,))
        self.assertEqual(checked.kernel_status(root),"kernel_accepted")

    def test_receipt_from_another_environment_is_rejected(self):
        base=ProofGroundAdapter.from_lean_trace(proof_trace())
        receipt=VerifiedKernelReceipt(
            base.obligation_ids[0],"proof-term-sha","different-env",
            "Lean.kernel","4.15.0","accepted","kernel-run-17",
        )
        with self.assertRaises(ProofGroundError):
            ProofGroundAdapter.from_lean_trace(proof_trace(),verified_receipts=(receipt,))


if __name__=="__main__":
    unittest.main()
