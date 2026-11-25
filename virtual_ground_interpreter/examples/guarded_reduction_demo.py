"""Run from repository root: python -m examples.guarded_reduction_demo"""
from vgi.symbolic_reduction import AffineAction
from vgi.guarded_reduction import (
    GuardedAction, GuardedGround, admit_guarded_reduction,
    discover_guarded_reduction, run_guarded, verify_guarded_receipt,
    plan_migration, apply_migration, observe_migration_probes,
)


def identity(n):
    return tuple(tuple(int(i == j) for j in range(n)) for i in range(n))


def main():
    n=128
    x=(0,1,0)+(0,)*(n-3)
    guard=(0,1)+(0,)*(n-2)
    inc=(1,)+(0,)*(n-1)
    cond=GuardedAction('tick',guard,1,
        AffineAction('tick',identity(n),inc),
        AffineAction('tick',identity(n),(0,)*n))
    src=GuardedGround(2,n,(cond,), ((1,)+(0,)*(n-1),),(0,))
    admitted=admit_guarded_reduction(src, discover_guarded_reduction(src))
    start=admitted.project(x)
    receipt=run_guarded(admitted,start,('tick',)*16)
    verified=verify_guarded_receipt(admitted,receipt)
    print('Original states:',admitted.source_states)
    print('Exact observer states:',admitted.quotient_states)
    print('Required projected dimensions:',admitted.dimension)
    print('Process replay:',verified['status'],'steps:',verified['steps'])

    # Change observer need while preserving machine dynamics.
    extra=(0,0,1)+(0,)*(n-3)
    widened=GuardedGround(2,n,(cond,), (src.observations[0],extra),(0,0))
    new=admit_guarded_reduction(widened,discover_guarded_reduction(widened))
    plan=plan_migration(admitted,new)
    # Only the missing linear observation must be fetched from source.
    x_now=x
    for _ in range(16):
        x_now=src.step(x_now,'tick')
    probes=observe_migration_probes(widened,x_now,new,plan)
    lifted=apply_migration(admitted,new,tuple(receipt['final']),probes,plan)
    assert lifted==new.project(x_now)
    print('New observer dimensions:',new.dimension)
    print('Additional source probes needed:',plan.probe_count)
    print('Live migrated state:',lifted)

    # A provably invariant branch permits logarithmic time navigation.
    stable=GuardedAction('tick',(1,),0,
        AffineAction('tick',((1,),),(0,)),
        AffineAction('tick',((1,),),(1,)))
    loop=GuardedGround(5,1,(stable,),((1,),),(0,))
    q=admit_guarded_reduction(loop,discover_guarded_reduction(loop))
    print('Invariant jump (10^100 steps):',q.jump_invariant((0,),'tick',10**100))


if __name__=='__main__':
    main()