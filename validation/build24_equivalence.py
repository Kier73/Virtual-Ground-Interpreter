""" canonical minimization and distinguishing words for Build 24 machines."""
from __future__ import annotations

from collections import deque

if __package__ in (None, ""):
    from common import lg24_module
else:
    from .common import lg24_module


def minimize_mealy(machine) -> dict:
    lg = lg24_module()
    actions = lg.ACTIONS
    states = list(machine.states)
    output_signature = {q: tuple(machine.outputs[q][a] for a in actions) for q in states}
    signatures = {q: output_signature[q] for q in states}
    while True:
        signature_to_block = {sig: i for i, sig in enumerate(sorted(set(signatures.values())))}
        block_of_state = {q: signature_to_block[signatures[q]] for q in states}
        next_signatures = {}
        for q in states:
            next_signatures[q] = (
                output_signature[q],
                tuple(block_of_state[machine.transitions[q][a]] for a in actions),
            )
        if next_signatures == signatures:
            blocks = len(set(signatures.values()))
            break
        signatures = next_signatures
    initial_block = signatures[machine.initial]
    return {
        "state_count": len(states),
        "minimized_state_count": blocks,
        "is_minimal": blocks == len(states),
        "initial_block": initial_block,
    }


def distinguishing_word(machine, first: str, second: str, max_depth: int = 8) -> tuple[str, ...] | None:
    lg = lg24_module()
    if first == second:
        return None
    queue = deque([(first, second, ())])
    seen = {(first, second)}
    while queue:
        q1, q2, word = queue.popleft()
        if len(word) >= max_depth:
            continue
        for action in lg.ACTIONS:
            if machine.outputs[q1][action] != machine.outputs[q2][action]:
                return word + (action,)
            pair = (machine.transitions[q1][action], machine.transitions[q2][action])
            if pair not in seen:
                seen.add(pair)
                queue.append((pair[0], pair[1], word + (action,)))
    return None


def all_pairs_distinguishable(machine, max_depth: int = 8) -> dict:
    states = list(machine.states)
    missing = []
    longest = 0
    for i, q1 in enumerate(states):
        for q2 in states[i + 1 :]:
            word = distinguishing_word(machine, q1, q2, max_depth)
            if word is None:
                missing.append([q1, q2])
            else:
                longest = max(longest, len(word))
    return {
        "state_count": len(states),
        "pair_count": len(states) * (len(states) - 1) // 2,
        "distinguishable_pairs": len(states) * (len(states) - 1) // 2 - len(missing),
        "missing_distinguishing_pairs": missing,
        "longest_distinguishing_word": longest,
    }


def learn_machine(name: str, channels=None, depth: int = 8):
    lg = lg24_module()
    ground = lg.fixture_grounds()[name]
    teacher = lg.ResettableTeacher(ground, channels=channels)
    result = lg.ActiveMealyLearner(teacher, conformance_depth=depth).learn()
    return ground, teacher, result


def fixture_profiles():
    return [
        ("coupled_six", None),
        ("coupled_six", (0,)),
        ("coupled_six", (1,)),
        ("aliased_six", None),
        ("unobservable_eight", None),
        ("delayed_six", None),
        ("partial_four", None),
    ]


def equivalence_summary() -> dict:
    lg = lg24_module()
    rows = []
    for name, channels in fixture_profiles():
        _, teacher, result = learn_machine(name, channels, depth=8)
        machine = result.machine
        cert = lg.bounded_certificate(machine, teacher, 8)
        minimized = minimize_mealy(machine)
        pairs = all_pairs_distinguishable(machine, max_depth=8)
        rows.append(
            {
                "fixture": name,
                "channels": list(channels) if channels is not None else None,
                "state_count": len(machine.states),
                "minimized_state_count": minimized["minimized_state_count"],
                "is_minimal": minimized["is_minimal"],
                "bounded_equivalent": bool(cert["bounded_equivalence"]),
                "cases_checked": int(cert["cases_checked"]),
                "distinguishable_pairs": pairs["distinguishable_pairs"],
                "pair_count": pairs["pair_count"],
                "longest_distinguishing_word": pairs["longest_distinguishing_word"],
                "missing_distinguishing_pairs": pairs["missing_distinguishing_pairs"],
            }
        )
    return {"fixtures": rows}


def delayed_counterexample_summary() -> dict:
    lg = lg24_module()
    _, teacher, shallow_result = learn_machine("delayed_six", depth=5)
    _, _, deep_result = learn_machine("delayed_six", depth=6)
    counterexample = lg.first_counterexample(shallow_result.machine, teacher, 8)
    return {
        "shallow_state_count": len(shallow_result.machine.states),
        "deep_state_count": len(deep_result.machine.states),
        "counterexample_word_length": len(counterexample[0]) if counterexample else None,
        "counterexample": list(counterexample[0]) if counterexample else None,
        "first_mismatch_index": counterexample[1] if counterexample else None,
        "deep_round_counterexample_length": (
            len(deep_result.rounds[0]["counterexample"]) if deep_result.rounds else None
        ),
    }
