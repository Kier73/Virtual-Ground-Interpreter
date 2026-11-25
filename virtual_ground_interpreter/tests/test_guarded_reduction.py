"""VLD-002C: mutation, random, temporal, and live migration checks."""
from __future__ import annotations

from copy import deepcopy
from itertools import product
import random
import unittest

from vgi.symbolic_reduction import AffineAction, _digest
from vgi.guarded_reduction import (
    AdmittedGuardedGround, GuardedAction, GuardedGround, GuardError,
    discover_guarded_reduction, admit_guarded_reduction, run_guarded,
    verify_guarded_receipt, plan_migration, apply_migration,
    observe_migration_probes,
)


def identity(n):
    return tuple(tuple(int(i == j) for j in range(n)) for i in range(n))


def action(name, n, guard_index=1, guard_value=1, *, true_delta=1,
           false_delta=0, p=2):
    g = [0]*n
    g[guard_index] = 1
    bt = [0]*n
    bt[0] = true_delta % p
    bf = [0]*n
    bf[0] = false_delta % p
    return GuardedAction(name, tuple(g), guard_value % p,
        AffineAction(name, identity(n), tuple(bt)),
        AffineAction(name, identity(n), tuple(bf)))


def sealed(obj):
    obj['record_sha256'] = _digest({k: v for k,v in obj.items() if k!='record_sha256'})
    return obj


class GuardedReductionTests(unittest.TestCase):
    def test_guarded_influence_requires_new_coordinate(self):
        # 2^128 source states; 4-state exact guarded quotient.
        n = 128
        src = GuardedGround(2,n,(action('tick',n),),
                            (tuple([1]+[0]*(n-1)),),(0,))
        candidate = discover_guarded_reduction(src)
        q = admit_guarded_reduction(src,candidate)
        self.assertEqual(q.dimension,2)
        self.assertEqual(q.source_states,2**128)
        self.assertEqual(q.quotient_states,4)
        self.assertEqual(len(candidate['basis']),2)
        self.assertIsNotNone(q.actions[0].guard)
        for bit in (0,1):
            x = (0,bit)+(0,)*(n-2)
            z = q.project(x)
            self.assertEqual(q.project(src.step(x,'tick')),q.step(z,'tick'))
            self.assertEqual(q.observe(z),src.observe(x))
        r = run_guarded(q,q.project((0,1)+(0,)*(n-2)), ('tick',)*13)
        self.assertEqual(verify_guarded_receipt(q,r)['steps'],13)

    def test_hidden_guard_can_be_elided(self):
        n=80
        # Branches differ only in a hidden, never observed coordinate.
        t = [0]*n
        t[2] = 1
        a = GuardedAction('tick', tuple([0,1]+[0]*(n-2)),1,
            AffineAction('tick',identity(n),tuple(t)),
            AffineAction('tick',identity(n),(0,)*n))
        src=GuardedGround(2,n,(a,), (tuple([1]+[0]*(n-1)),),(0,))
        q=admit_guarded_reduction(src, discover_guarded_reduction(src))
        self.assertEqual(q.dimension,1)
        self.assertIsNone(q.actions[0].guard)
        for guard in (0,1):
            x=(1,guard)+(0,)*(n-2)
            self.assertEqual(q.step(q.project(x),'tick'),q.project(src.step(x,'tick')))

    def test_delayed_branch_dependency_is_recovered(self):
        # Branch changes hidden x1; next input reads x1 into observed x0.
        n=9
        A=[list(row) for row in identity(n)]
        A[0]=[0]*n; A[0][1]=1
        read=GuardedAction('read',(0,)*n,0,
            AffineAction('read',tuple(map(tuple,A)),(0,)*n),
            AffineAction('read',tuple(map(tuple,A)),(0,)*n))
        t = [0]*n
        t[1] = 1
        hide=GuardedAction('hide',tuple([0,0,1]+[0]*(n-3)),1,
            AffineAction('hide',identity(n),tuple(t)),
            AffineAction('hide',identity(n),(0,)*n))
        src=GuardedGround(2,n,(hide,read), (tuple([1]+[0]*(n-1)),),(0,))
        q=admit_guarded_reduction(src,discover_guarded_reduction(src))
        self.assertEqual(q.dimension,3)
        for x in [(0,0,0)+(0,)*(n-3),(0,0,1)+(0,)*(n-3)]:
            z=q.project(x)
            for inp in ('hide','read'):
                x=src.step(x,inp)
                z=q.step(z,inp)
                self.assertEqual(q.project(x),z)

    def test_no_observation_one_state(self):
        src=GuardedGround(2,2,(action('a',2),),(),())
        q=admit_guarded_reduction(src,discover_guarded_reduction(src))
        self.assertEqual((q.dimension,q.quotient_states),(0,1))
        self.assertEqual(q.step((),'a'),())
        self.assertIsNone(q.actions[0].guard)

    def test_exhaustive_small_source_states_and_words(self):
        rng=random.Random(20261125)
        total=0
        for p in (2,3,5):
            for _ in range(32):
                n=rng.randint(1,3)
                actions=[]
                for symbol in ('a','b'):
                    guard=tuple(rng.randrange(p) for _ in range(n))
                    threshold=rng.randrange(p)
                    branches=[]
                    for __ in range(2):
                        branches.append(AffineAction(symbol,
                            tuple(tuple(rng.randrange(p) for j in range(n)) for i in range(n)),
                            tuple(rng.randrange(p) for i in range(n))))
                    actions.append(GuardedAction(symbol,guard,threshold,*branches))
                obs=tuple(tuple(rng.randrange(p) for _ in range(n)) for _ in range(rng.randrange(3)))
                src=GuardedGround(p,n,tuple(actions),obs,(0,)*len(obs))
                q=admit_guarded_reduction(src,discover_guarded_reduction(src))
                for x0 in product(range(p),repeat=n):
                    z=q.project(x0)
                    self.assertEqual(q.observe(z),src.observe(x0))
                    for word in product(('a','b'),repeat=3):
                        x,z2=x0,z
                        for symbol in word:
                            x=src.step(x,symbol)
                            z2=q.step(z2,symbol)
                            self.assertEqual(q.project(x),z2)
                            self.assertEqual(src.observe(x),q.observe(z2))
                        total+=1
        self.assertGreater(total,2000)

    def test_rehashed_forgery_transition_is_rejected(self):
        src=GuardedGround(2,3,(action('a',3),),((1,0,0),),(0,))
        cert=discover_guarded_reduction(src)
        bad=deepcopy(cert)
        bad['actions'][0]['on_false']['offset'][0] ^= 1
        with self.assertRaisesRegex(GuardError,'digest'):
            admit_guarded_reduction(src,bad)
        with self.assertRaisesRegex(GuardError,'offset'):
            admit_guarded_reduction(src,sealed(bad))

    def test_rehashed_forgery_guard_is_rejected(self):
        src=GuardedGround(2,3,(action('a',3),),((1,0,0),),(0,))
        cert=discover_guarded_reduction(src)
        bad=deepcopy(cert)
        bad['actions'][0]['guard']=[0]*len(bad['basis'])
        with self.assertRaisesRegex(GuardError,'guard cannot'):
            admit_guarded_reduction(src,sealed(bad))

    def test_elision_attack_is_rejected(self):
        src=GuardedGround(2,3,(action('a',3),),((1,0,0),),(0,))
        cert=discover_guarded_reduction(src)
        cert['actions'][0]['guard']=None
        with self.assertRaisesRegex(GuardError,'elided'):
            admit_guarded_reduction(src,sealed(cert))

    def test_runtime_receipt_tampering_is_rejected(self):
        src=GuardedGround(2,3,(action('a',3),),((1,0,0),),(0,))
        q=admit_guarded_reduction(src,discover_guarded_reduction(src))
        record=run_guarded(q,q.project((0,1,0)),('a',)*7)
        verify_guarded_receipt(q,record)
        bad=deepcopy(record)
        bad['events'][0]['after'][0]^=1
        with self.assertRaises(GuardError):
            verify_guarded_receipt(q,bad)
        bad['receipt_sha256']=_digest({k:v for k,v in bad.items() if k!='receipt_sha256'})
        with self.assertRaisesRegex(GuardError,'event or chain'):
            verify_guarded_receipt(q,bad)

    def test_symbolic_live_migration_with_one_probe(self):
        n=96
        same=GuardedAction('tick',(0,)*n,0,
             AffineAction('tick',identity(n),(0,)*n),
             AffineAction('tick',identity(n),(0,)*n))
        old_source=GuardedGround(2,n,(same,),((1,)+(0,)*(n-1),),(0,))
        new_source=GuardedGround(2,n,(same,),((1,)+(0,)*(n-1),
             (0,0,1)+(0,)*(n-3)),(0,0))
        old=admit_guarded_reduction(old_source,discover_guarded_reduction(old_source))
        new=admit_guarded_reduction(new_source,discover_guarded_reduction(new_source))
        plan=plan_migration(old,new)
        self.assertEqual((old.dimension,new.dimension,plan.probe_count),(1,2,1))
        x=(1,0,1)+(0,)*(n-3)
        probes=observe_migration_probes(new_source,x,new,plan)
        self.assertEqual(apply_migration(old,new,old.project(x),probes,plan),new.project(x))
        with self.assertRaises(GuardError):
            apply_migration(old,new,old.project(x),probes,
                type(plan)(plan.probe_rows,((0,0),)*new.dimension))

    def test_live_migration_without_new_probes(self):
        n=4
        a=GuardedAction('tick',(0,)*n,0,
            AffineAction('tick',identity(n),(0,)*n),
            AffineAction('tick',identity(n),(0,)*n))
        big=GuardedGround(3,n,(a,),((1,0,0,0),(0,1,0,0)),(0,0))
        small=GuardedGround(3,n,(a,),((1,0,0,0),),(0,))
        qbig=admit_guarded_reduction(big,discover_guarded_reduction(big))
        qsmall=admit_guarded_reduction(small,discover_guarded_reduction(small))
        plan=plan_migration(qbig,qsmall)
        self.assertEqual(plan.probe_count,0)
        x=(1,2,0,0)
        self.assertEqual(apply_migration(qbig,qsmall,qbig.project(x),(),plan),qsmall.project(x))

    def test_invariant_guard_permits_huge_jump(self):
        # In branch x0==0, x0 remains 0 forever; on false, x0 increments mod 5.
        src=GuardedGround(5,1,(GuardedAction('tick',(1,),0,
            AffineAction('tick',((1,),),(0,)),
            AffineAction('tick',((1,),),(1,))),),((1,),),(0,))
        q=admit_guarded_reduction(src,discover_guarded_reduction(src))
        self.assertEqual(q.jump_invariant(q.project((0,)),'tick',10**100),(0,))
        self.assertEqual(q.step((2,),'tick'),(3,))
        with self.assertRaisesRegex(GuardError,'not invariant'):
            q.jump_invariant((2,),'tick',10**10)

    def test_elided_guard_fast_forward(self):
        src=GuardedGround(5,2,(GuardedAction('tick',(0,1),0,
            AffineAction('tick',identity(2),(1,0)),
            AffineAction('tick',identity(2),(1,4))),),((1,0),),(0,))
        q=admit_guarded_reduction(src,discover_guarded_reduction(src))
        self.assertEqual(q.dimension,1)
        self.assertIsNone(q.actions[0].guard)
        self.assertEqual(q.jump_invariant(q.project((2,1)),'tick',10**100),((2+10**100)%5,))

    def test_rejects_dynamics_change_during_migration(self):
        src1=GuardedGround(2,2,(action('a',2),),((1,0),),(0,))
        src2=GuardedGround(2,2,(action('a',2,true_delta=0,false_delta=1),),((1,0),),(0,))
        a=admit_guarded_reduction(src1,discover_guarded_reduction(src1))
        b=admit_guarded_reduction(src2,discover_guarded_reduction(src2))
        with self.assertRaisesRegex(GuardError,'dynamics'):
            plan_migration(a,b)


if __name__=='__main__':
    unittest.main()