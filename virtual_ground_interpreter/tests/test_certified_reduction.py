"""VLD-002: positive, negative, and finite exhaustive regression tests."""
import copy
from itertools import product
import random
import unittest

from vgi.certified_reduction import (
    Edge, FiniteGround, ReductionError, ReductionCertificate,
    discover_reduction, verify_reduction,
)


def clock_ground() -> FiniteGround:
    """Two independent clock registers. Every state is reachable from (0,0)."""
    states = tuple(f"{a}-{b}" for a in range(4) for b in range(3))
    edges = []
    for state in states:
        a, b = (int(x) for x in state.split("-"))
        for inp in ("A", "B"):
            x, y = ((a + 1) % 4, b) if inp == "A" else (a, (b + 1) % 3)
            edges.append(Edge(state, inp, f"{x}-{y}",
                              (("phaseA", str(x)), ("phaseB", str(y)))))
    return FiniteGround(states, ("A", "B"), "0-0", tuple(edges))


def run(machine, word):
    edges = machine.edges()
    state, observed = machine.initial, []
    for a in word:
        e = edges[(state, a)]
        observed.append(e.observations)
        state = e.next
    return observed


class CertifiedStateReductionTests(unittest.TestCase):
    def test_observer_scope_changes_minimal_machine(self):
        original = clock_ground()
        for channels, size in (((), 1), (("phaseA",), 4), (("phaseB",), 3),
                               (("phaseA", "phaseB"), 12)):
            target, cert = discover_reduction(original, channels)
            report = verify_reduction(original, target, cert)
            self.assertEqual(report["reduced_states"], size)
            self.assertEqual(report["checked_edges"], 24)
            self.assertTrue(report["minimal_reachable_quotient"])
            self.assertEqual(FiniteGround.from_dict(target.to_dict()), target)
            self.assertEqual(ReductionCertificate.from_dict(cert.to_dict()), cert)
            for length in range(6):
                for word in product(original.alphabet, repeat=length):
                    actual = run(target, word)
                    desired = [tuple((k, v) for k, v in step if k in channels)
                               for step in run(original, word)]
                    self.assertEqual(actual, desired)

    def test_unreachable_machine_state_is_pruned(self):
        original = clock_ground()
        edges = list(original.transitions)
        edges += [Edge("orphan", a, "orphan", (("phaseA", "0"), ("phaseB", "0")))
                  for a in original.alphabet]
        enriched = FiniteGround(tuple(sorted((*original.states, "orphan"))), original.alphabet,
                                original.initial, tuple(sorted(edges, key=lambda e: (e.state, e.input))))
        target, cert = discover_reduction(enriched, ("phaseA", "phaseB"))
        report = verify_reduction(enriched, target, cert)
        self.assertEqual((report["original_states"], report["reachable_states"], report["reduced_states"]), (13, 12, 12))

    def test_delayed_distinction_is_not_erased(self):
        # s0 and s1 initially emit the same result for input x; their next states differ.
        orig = FiniteGround(("s0", "s1", "s2"), ("x", "y"), "s0", (
            Edge("s0", "x", "s1", (("v", "0"),)),
            Edge("s0", "y", "s2", (("v", "0"),)),
            Edge("s1", "x", "s2", (("v", "0"),)),
            Edge("s1", "y", "s0", (("v", "0"),)),
            Edge("s2", "x", "s0", (("v", "1"),)),
            Edge("s2", "y", "s1", (("v", "1"),)),
        ))
        target, cert = discover_reduction(orig, ("v",))
        self.assertEqual(verify_reduction(orig, target, cert)["reduced_states"], 3)

    def test_tampered_output_transition_scope_and_digest_rejected(self):
        source = clock_ground()
        target, cert = discover_reduction(source, ("phaseA",))
        bad = copy.deepcopy(target.to_dict())
        bad["transitions"][0]["observations"]["phaseA"] = "tamper"
        with self.assertRaises(ReductionError):
            verify_reduction(source, FiniteGround.from_dict(bad), cert)
        bad = copy.deepcopy(target.to_dict())
        bad["transitions"][0]["next"] = target.initial
        with self.assertRaises(ReductionError):
            verify_reduction(source, FiniteGround.from_dict(bad), cert)
        bad_cert = copy.deepcopy(cert.to_dict())
        bad_cert["channels"] = ["phaseB"]
        with self.assertRaises(ReductionError):
            verify_reduction(source, target, ReductionCertificate.from_dict(bad_cert))
        bad_cert = copy.deepcopy(cert.to_dict())
        bad_cert["source_sha256"] = "0" * 64
        with self.assertRaises(ReductionError):
            verify_reduction(source, target, ReductionCertificate.from_dict(bad_cert))

    def test_forged_mapping_with_recomputed_checksums_rejected(self):
        source = clock_ground()
        target, cert = discover_reduction(source, ("phaseA",))
        bad = list(cert.mapping)
        bad[0] = (bad[0][0], bad[-1][1])
        forged = ReductionCertificate(source.fingerprint, target.fingerprint, cert.channels, tuple(bad))
        with self.assertRaises(ReductionError):
            verify_reduction(source, target, forged)

    def test_correct_but_nonminimal_target_rejected(self):
        source = clock_ground()
        # The identical full source is a valid simulation under phaseA, but nonminimal.
        target_record = source.to_dict()
        target_record["transitions"] = [dict(e, observations={"phaseA": e["observations"]["phaseA"]})
                                        for e in target_record["transitions"]]
        target = FiniteGround.from_dict(target_record)
        cert = ReductionCertificate(source.fingerprint, target.fingerprint, ("phaseA",),
                                    tuple((s, s) for s in source.states))
        with self.assertRaises(ReductionError):
            verify_reduction(source, target, cert)

    def test_random_total_machines_are_verified_without_sampling(self):
        rng = random.Random(913)
        for n in range(2, 16):
            for _ in range(8):
                states = tuple(f"s{i:02d}" for i in range(n))
                edges = tuple(Edge(s, a, rng.choice(states), (("hidden", str(rng.randrange(3))),
                                                              ("visible", str(rng.randrange(3)))))
                              for s in states for a in ("0", "1"))
                source = FiniteGround(states, ("0", "1"), states[0], edges)
                for scope in ((), ("visible",), ("hidden", "visible")):
                    target, cert = discover_reduction(source, scope)
                    self.assertEqual(verify_reduction(source, target, cert)["status"], "VERIFIED")

    def test_invalid_partial_or_noncanonical_machine_rejected(self):
        with self.assertRaises(ReductionError):
            FiniteGround(("a", "b"), ("x",), "a", (Edge("a", "x", "b", ()),))
        record = clock_ground().to_dict()
        record["transitions"][1]["input"] = "A"
        with self.assertRaises(ReductionError):
            FiniteGround.from_dict(record)


if __name__ == "__main__":
    unittest.main()
