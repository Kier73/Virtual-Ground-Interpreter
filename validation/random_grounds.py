"""Deterministic random hidden-ground suites for Builds 22-23.

The frozen catalogues are fixed.  This module samples a larger space of
valid finite grounds and reports exactness, rejection and indistinguishability
instead of only the hand-picked examples.
"""
from __future__ import annotations

import random
from itertools import product

if __package__ in (None, ""):
    from common import gd22_module, gs23_module
else:
    from .common import gd22_module, gs23_module


def _gd22_extended_probes(gd, capacity: int):
    probes = list(gd.probe_catalog())
    for phase in range(4):
        for action in gd.ACTIONS:
            for sensor in gd.SENSORS:
                probes.append(gd.Probe(gd.State(capacity, 0, phase), action, sensor))
                probes.append(gd.Probe(gd.State(0, capacity, phase), action, sensor))
    return tuple(probes)


def _selected_mismatches(gd, true_ground, selected_id: str) -> int:
    selected = next((h for h in gd.candidate_grounds(true_ground.version) if h.identifier == selected_id), None)
    if selected is None:
        return -1
    mismatches = 0
    for probe in _gd22_extended_probes(gd, true_ground.capacity):
        if gd.predict(selected, probe) != gd.predict(true_ground, probe):
            mismatches += 1
    return mismatches


def random_build22_summary(seed: int = 20261106, cases: int = 48) -> dict:
    gd = gd22_module()
    rng = random.Random(seed)
    in_family = []
    out_of_family = []
    half = max(1, cases // 2)
    for _ in range(half):
        true = gd.GroundHypothesis(
            rng.choice((2, 3)),
            rng.choice(gd.CANDIDATE_INFLOW_NAMES),
            rng.choice(gd.CANDIDATE_DEMAND_NAMES),
            rng.choice((1, 2)),
            rng.choice((1, 2)),
        )
        in_family.append(true)
    for _ in range(cases - half):
        true = gd.GroundHypothesis(
            rng.choice((2, 3)),
            "inflow_C",
            rng.choice(gd.CANDIDATE_DEMAND_NAMES),
            rng.choice((1, 2)),
            rng.choice((1, 2)),
        )
        out_of_family.append(true)

    in_rows = [gd.run_active_identification(h) for h in in_family]
    oof_rows = []
    for true in out_of_family:
        result = gd.run_active_identification(true)
        selected = result["remaining_ids"][0] if result["identified"] else None
        mismatches = _selected_mismatches(gd, true, selected) if selected else None
        oof_rows.append(
            {
                "true": true.identifier,
                "status": result["status"],
                "identified": bool(result["identified"]),
                "remaining": int(result["remaining_hypotheses"]),
                "probe_count": int(result["probe_count"]),
                "selected": selected,
                "extended_probe_mismatches": mismatches,
            }
        )
    return {
        "seed": seed,
        "in_family_count": len(in_family),
        "in_family_identified": sum(bool(x["identified"]) for x in in_rows),
        "in_family_probe_count_mean": sum(int(x["probe_count"]) for x in in_rows) / len(in_rows),
        "in_family_probe_count_max": max(int(x["probe_count"]) for x in in_rows),
        "out_of_family_count": len(out_of_family),
        "out_of_family_rejected": sum(
            x["status"] == "candidate_family_rejected" for x in oof_rows
        ),
        "out_of_family_identified_with_extended_mismatch": sum(
            bool(x["identified"]) and int(x["extended_probe_mismatches"] or 0) > 0
            for x in oof_rows
        ),
        "out_of_family_identified_without_extended_mismatch": sum(
            bool(x["identified"]) and int(x["extended_probe_mismatches"] or 0) == 0
            for x in oof_rows
        ),
        "rows": oof_rows,
    }


def random_hidden_ground(rng: random.Random, index: int):
    gs = gs23_module()
    # Keep the random law in the learner's identifiable region: enough capacity
    # and headroom that strict uncensored A_TO_B probes can observe every
    # phase/residue transfer cell.  Unidentifiable high-quantum cells remain an
    # important failure mode, but they are not the intended first random suite.
    capacity = rng.choice((4, 5))
    period = rng.choice((3, 4))
    modulus = rng.choice((1, 2, 3))
    inflow = tuple(rng.randrange(2) for _ in range(period))
    demand = tuple(rng.randrange(2) for _ in range(period))
    phase = list(range(period))
    rng.shuffle(phase)
    phase_next = tuple(phase)
    rows = tuple(tuple(rng.randrange(1, 3) for _ in range(modulus)) for _ in range(period))
    return gs.HiddenGround(capacity, inflow, demand, phase_next, rows, modulus, f"random-{index:02d}")


def make_random_dataset(rng: random.Random, ground, transfer_train_prob: float = 0.85):
    """Build transition records with active uncensored A_TO_B probes.

    ``induce_ground`` infers the transfer matrix only from uncensored A_TO_B
    samples.  Randomly sampling all transitions can leave phase/residue cells
    unobserved.  This dataset therefore includes every HOLD record and every
    strictly uncensored A_TO_B record in training, then holds out censored
    transfers and most B_TO_A records.  It is a probe-rich generalization
    test, not a passive-observation test.
    """
    gs = gs23_module()
    all_records = []
    states = []
    for a, b, p in product(range(ground.capacity + 1), range(ground.capacity + 1), range(ground.period)):
        state = gs.State(a, b, p)
        states.append(state)
        for action in gs.ACTIONS:
            all_records.append(gs.TransitionRecord(state, action, ground.step(state, action)))
    withheld = set(rng.sample(states, k=max(1, len(states) // 8)))
    train, heldout = [], []
    for record in all_records:
        if record.action == "HOLD":
            train.append(record)
        elif record.action == "A_TO_B":
            ledger = ground.ledger(record.state, record.action)
            actual = int(ledger["transfer_ab"])
            uncensored = (
                actual > 0
                and record.state.a > actual
                and ground.capacity - record.state.b > actual
                and record.next_state.b > 0
            )
            if uncensored:
                train.append(record)
            else:
                heldout.append(record)
        else:  # B_TO_A: include a minority in train, hold out the rest.
            if record.state not in withheld and rng.random() < 0.35:
                train.append(record)
            else:
                heldout.append(record)
    return tuple(train), tuple(heldout)


def random_build23_summary(seed: int = 20261107, cases: int = 16) -> dict:
    gs = gs23_module()
    rng = random.Random(seed)
    rows = []
    successes = 0
    for i in range(cases):
        ground = random_hidden_ground(rng, i)
        train, heldout = make_random_dataset(rng, ground)
        try:
            program = gs.induce_ground(train, max_residue_modulus=ground.transfer_modulus)
            held = gs.evaluate_program(program, heldout)
            coverage = gs.full_domain_coverage(program, ground)
            successes += 1
            rows.append(
                {
                    "ground": ground.name,
                    "capacity": ground.capacity,
                    "period": ground.period,
                    "modulus": ground.transfer_modulus,
                    "status": "induced",
                    "heldout_correct": held["correct"],
                    "heldout_count": held["count"],
                    "transition_coverage": coverage["transition_coverage"],
                    "syntax_cost": program.as_dict()["syntax_cost"],
                }
            )
        except Exception as exc:  # keep law outside the grammar as reported data
            rows.append(
                {
                    "ground": ground.name,
                    "capacity": ground.capacity,
                    "period": ground.period,
                    "modulus": ground.transfer_modulus,
                    "status": "induction_failed",
                    "error": str(exc),
                }
            )
    induced = [r for r in rows if r["status"] == "induced"]
    return {
        "seed": seed,
        "cases": cases,
        "induced": successes,
        "induction_failed": cases - successes,
        "success_rate": successes / cases if cases else 0.0,
        "induced_heldout_correct": sum(int(r["heldout_correct"]) for r in induced),
        "induced_heldout_total": sum(int(r["heldout_count"]) for r in induced),
        "induced_full_coverage_min": min(
            (float(r["transition_coverage"]) for r in induced), default=0.0
        ),
        "rows": rows,
    }
