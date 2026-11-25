"""VLD-002B tests: exhaustive small models + enormous symbolic state spaces."""
from __future__ import annotations

from copy import deepcopy
from itertools import product
import json
import random
import unittest

from vgi.symbolic_reduction import (
    AdmittedSymbolicGround, AffineAction, AffineGround, SymbolicReductionError,
    _digest, admit_symbolic_reduction, discover_symbolic_reduction,
)


def identity(n: int) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(i == j) for j in range(n)) for i in range(n))


def head_machine(n: int = 80, p: int = 2) -> AffineGround:
    """An observed 3D subsystem and a potentially enormous hidden subsystem."""
    a = [list(row) for row in identity(n)]
    a[0], a[1], a[2] = [0]*n, [0]*n, [0]*n
    a[0][1], a[1][2] = 1, 1
    a[2][0], a[2][1] = 1, 1
    if n > 3:
        for i in range(3, n):
            a[i] = [0]*n
            a[i][i+1 if i+1 < n else 3] = 1
    b = [list(row) for row in identity(n)]
    b[0][2] = 1
    c = [0]*n
    c[0] = 1
    shift_a = [0]*n
    shift_a[:3] = [1 % p, 0, 1 % p]
    return AffineGround(p, n, (
        AffineAction('a', tuple(tuple(x % p for x in row) for row in a), tuple(shift_a)),
        AffineAction('b', tuple(tuple(x % p for x in row) for row in b), (0,)*n),
    ), (tuple(c),), (1 % p,))


def rotating_machine(n: int) -> AffineGround:
    a = []
    for i in range(n):
        row = [0] * n
        row[(i+1) % n] = 1
        a.append(tuple(row))
    return AffineGround(2, n, (AffineAction('next', tuple(a), (0,)*n),),
                        (tuple([1]+[0]*(n-1)),), (0,))


def seal(record: dict) -> dict:
    record['record_sha256'] = _digest({k: v for k,v in record.items() if k!='record_sha256'})
    return record


def observe_word(source: AffineGround, x: tuple[int,...], word: tuple[str,...], index: int) -> int:
    for a in word:
        x = source.step(x, a)
    return source.observe(x)[index]


class SymbolicReductionTests(unittest.TestCase):
    def test_huge_hidden_state_compresses(self):
        source = head_machine(80)
        certificate = discover_symbolic_reduction(source)
        quotient = admit_symbolic_reduction(source, certificate)
        self.assertEqual(quotient.dimension, 3)
        self.assertEqual(quotient.source_states, 2**80)
        self.assertEqual(quotient.quotient_states, 8)
        self.assertEqual(len(certificate['witnesses']), 3)
        self.assertEqual(len(certificate['basis']), 3)
        self.assertEqual(quotient.observe(quotient.project((0,)*80)), source.observe((0,)*80))
        self.assertEqual(admit_symbolic_reduction(source, json.dumps(certificate)).basis, quotient.basis)

    def test_periodic_macro_jump(self):
        source = head_machine(10, 3)
        q = admit_symbolic_reduction(source, discover_symbolic_reduction(source))
        start = q.project(tuple(i % 3 for i in range(10)))
        word = ('a','b','a','a','b')
        for repetitions in (0,1,2,3,7,41,127):
            expected = start
            for _ in range(repetitions):
                for symbol in word:
                    expected = q.step(expected, symbol)
            self.assertEqual(q.jump_word(start, word, repetitions), expected)
        self.assertEqual(q.jump_word(start, (), 10**100), start)
        # This checks composition order using an independent 3x3 finite model.
        expected = start
        for symbol in word:
            expected = q.step(expected, symbol)
        self.assertEqual(q.jump_word(start, word, 1), expected)

    def test_cross_checks_against_explicit_reduction(self):
        """For an all-reachable machine, symbolic and prior finite quotients agree."""
        from vgi.certified_reduction import Edge, FiniteGround, discover_reduction, verify_reduction
        n = 4
        source = AffineGround(2, n, tuple(
            AffineAction(f'flip{i}', identity(n), tuple(int(i==j) for j in range(n)))
            for i in range(n)), (tuple([1,0,0,0]),), (0,))
        states = tuple('s'+''.join(map(str,bits)) for bits in product(range(2), repeat=n))
        by_state = {name: tuple(int(d) for d in name[1:]) for name in states}
        edges = []
        for name in states:
            for action in source.actions:
                after = source.step(by_state[name], action.symbol)
                target = 's'+''.join(map(str,after))
                out = source.observe(after)
                edges.append(Edge(name, action.symbol, target, (('observer',str(out[0])),)))
        machine = FiniteGround(states, tuple(act.symbol for act in source.actions), states[0], tuple(edges))
        reduced, witness = discover_reduction(machine, ('observer',))
        admission = verify_reduction(machine,reduced,witness)
        symbolic = admit_symbolic_reduction(source,discover_symbolic_reduction(source))
        self.assertEqual(admission['reachable_states'],2**n)
        self.assertEqual(admission['reduced_states'], symbolic.quotient_states)
        self.assertEqual(symbolic.dimension,1)

    def test_huge_hidden_clock_ternary(self):
        source = head_machine(60, 3)
        quotient = admit_symbolic_reduction(source, discover_symbolic_reduction(source))
        self.assertEqual((quotient.source_states, quotient.quotient_states), (3**60, 27))
        self.assertEqual(quotient.dimension, 3)

    def test_delayed_observation_prevents_false_reduction(self):
        source = rotating_machine(64)
        quotient = admit_symbolic_reduction(source, discover_symbolic_reduction(source))
        self.assertEqual(quotient.dimension, 64)
        self.assertEqual(quotient.quotient_states, 2**64)
        self.assertGreaterEqual(max(len(w['word']) for w in discover_symbolic_reduction(source)['witnesses']), 63)

    def test_no_observations_is_singleton(self):
        source = AffineGround(5, 3, (AffineAction('tick', identity(3), (3,4,2)),), (), ())
        quotient = admit_symbolic_reduction(source, discover_symbolic_reduction(source))
        self.assertEqual(quotient.dimension, 0)
        self.assertEqual(quotient.quotient_states, 1)
        self.assertEqual(quotient.step((), 'tick'), ())
        self.assertEqual(quotient.jump((), 'tick', 10**200), ())
        self.assertEqual(quotient.observe(()), ())

    def test_zero_observation_rows_and_affine_offsets(self):
        source = AffineGround(3, 2, (AffineAction('tick', identity(2), (1,2)),),
                              ((0,0),), (2,))
        quotient = admit_symbolic_reduction(source, discover_symbolic_reduction(source))
        self.assertEqual(quotient.dimension, 0)
        self.assertEqual(quotient.observe(()), (2,))

    def test_huge_temporal_jump(self):
        source = AffineGround(5, 1, (AffineAction('tick', ((1,),), (2,)),), ((1,),), (0,))
        quotient = admit_symbolic_reduction(source, discover_symbolic_reduction(source))
        steps = 10**150
        self.assertEqual(quotient.jump((3,), 'tick', steps), ((3+2*steps) % 5,))
        self.assertEqual(quotient.jump((3,), 'tick', 0), (3,))
        self.assertEqual(quotient.jump((3,), 'tick', 7), ((3+14)%5,))
        for steps in (0,1,2,3,7,51,137):
            y = (3,)
            for _ in range(steps):
                y = quotient.step(y, 'tick')
            self.assertEqual(quotient.jump((3,), 'tick', steps), y)

    def test_competing_inputs_randomized(self):
        rng = random.Random(20261125)
        for p in (2,3,5):
            for _ in range(42):
                n = rng.randint(1,5)
                actions = []
                for label in ('a','b'):
                    A = tuple(tuple(rng.randrange(p) for j in range(n)) for i in range(n))
                    b = tuple(rng.randrange(p) for i in range(n))
                    actions.append(AffineAction(label,A,b))
                m = rng.randint(0,3)
                C = tuple(tuple(rng.randrange(p) for j in range(n)) for i in range(m))
                c = tuple(rng.randrange(p) for i in range(m))
                source = AffineGround(p,n,tuple(actions),C,c)
                cert = discover_symbolic_reduction(source)
                q = admit_symbolic_reduction(source,cert)
                self.assertLessEqual(q.dimension,n)
                for _ in range(6):
                    x = tuple(rng.randrange(p) for i in range(n))
                    y = q.project(x)
                    for t in range(8):
                        self.assertEqual(source.observe(x),q.observe(y))
                        label = rng.choice(('a','b'))
                        x = source.step(x,label)
                        y = q.step(y,label)
                        self.assertEqual(q.project(x),y)

    def test_all_small_quotient_states_minimal_by_word_witness(self):
        for n in (2,3,4):
            source = rotating_machine(n)
            cert = discover_symbolic_reduction(source)
            q = admit_symbolic_reduction(source,cert)
            states = list(product(range(2),repeat=n))
            for i,x in enumerate(states):
                for z in states[i+1:]:
                    if q.project(x) == q.project(z):
                        continue
                    self.assertTrue(any(
                        observe_word(source,x,tuple(w['word']),w['output']) !=
                        observe_word(source,z,tuple(w['word']),w['output'])
                        for w in cert['witnesses']))

    def test_certificate_identification_and_algebraic_attack(self):
        source = head_machine(7)
        cert = discover_symbolic_reduction(source)
        damaged = deepcopy(cert)
        damaged['actions'][0]['matrix'][0][0] ^= 1
        with self.assertRaisesRegex(SymbolicReductionError,'digest'):
            admit_symbolic_reduction(source,damaged)
        with self.assertRaisesRegex(SymbolicReductionError,'commutation'):
            admit_symbolic_reduction(source,seal(damaged))

    def test_forged_distinguishing_witness_rejected(self):
        source = head_machine(7)
        cert = discover_symbolic_reduction(source)
        damaged = deepcopy(cert)
        damaged['witnesses'][1]['word'] = []
        with self.assertRaisesRegex(SymbolicReductionError,'observation word'):
            admit_symbolic_reduction(source,seal(damaged))

    def test_forged_output_projection_rejected(self):
        source = head_machine(7)
        damaged = deepcopy(discover_symbolic_reduction(source))
        damaged['output_matrix'][0] = [0] * len(damaged['basis'])
        with self.assertRaisesRegex(SymbolicReductionError,'observer'):
            admit_symbolic_reduction(source,seal(damaged))

    def test_rejects_missing_basis_even_with_sealed_hash(self):
        source = head_machine(7)
        damaged = deepcopy(discover_symbolic_reduction(source))
        damaged['basis'] = damaged['basis'][:1]
        damaged['witnesses'] = damaged['witnesses'][:1]
        damaged['actions'] = [{'symbol': a.symbol,'matrix': [[0]],'offset':[0]} for a in source.actions]
        damaged['output_matrix'] = [[1]]
        with self.assertRaises(SymbolicReductionError):
            admit_symbolic_reduction(source,seal(damaged))

    def test_foreign_machine_digest_rejected(self):
        a = head_machine(7)
        b = head_machine(8)
        with self.assertRaisesRegex(SymbolicReductionError,'source'):
            admit_symbolic_reduction(b,discover_symbolic_reduction(a))

    def test_rejects_composite_modulus_bool_and_overflow(self):
        with self.assertRaisesRegex(SymbolicReductionError,'prime'):
            AffineGround(4,1,(AffineAction('a', ((1,),),(0,)),),((1,),),(0,))
        with self.assertRaises(SymbolicReductionError):
            AffineGround(True,1,(AffineAction('a',((1,),),(0,)),),((1,),),(0,))
        with self.assertRaises(SymbolicReductionError):
            AffineGround(2,1,(AffineAction('a',((2,),),(0,)),),((1,),),(0,))

    def test_rejects_duplicate_json_keys(self):
        source = head_machine(7)
        cert = discover_symbolic_reduction(source)
        wire = json.dumps(cert)
        wire = wire.replace('"schema":', '"schema": "forged", "schema":', 1)
        with self.assertRaisesRegex(SymbolicReductionError,'duplicate'):
            admit_symbolic_reduction(source,wire)

    def test_canonical_source_roundtrip(self):
        source = head_machine(9,3)
        self.assertEqual(AffineGround.from_dict(source.to_dict()),source)
        self.assertEqual(source.fingerprint,AffineGround.from_dict(source.to_dict()).fingerprint)

    def test_invalid_jump_bounds(self):
        source = head_machine(5)
        q = admit_symbolic_reduction(source,discover_symbolic_reduction(source))
        with self.assertRaises(SymbolicReductionError):
            q.jump((0,)*q.dimension,'a',-1)
        with self.assertRaises(SymbolicReductionError):
            q.jump((0,)*q.dimension,'a',2**4096)


if __name__ == '__main__':
    unittest.main()
