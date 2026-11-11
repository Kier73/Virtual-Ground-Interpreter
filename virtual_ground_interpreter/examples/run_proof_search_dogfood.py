"""Dogfood VGI's finite Ground and partial-relation layer on proof-shaped tasks.

Run from the virtual_ground_interpreter project root:
    python examples/run_proof_search_dogfood.py

These finite workloads test VGI's current abstraction; they are not proofs of
the asymptotic theorems that inspired them.
"""
from __future__ import annotations

from collections import Counter, deque
from itertools import combinations, product
import json

from vgi import (
    GroundTransitionSystem, ObserverContext, TransitionObservation,
    TransitionOutcome, partial_refinement_series,
)


def equivalence_classes(comparison):
    """Build classes from pair statuses, requiring a genuine partition."""
    remaining = list(comparison.states)
    groups = []
    while remaining:
        representative = remaining.pop(0)
        group, keep = [representative], []
        for candidate in remaining:
            if comparison.status(representative, candidate) == "equivalent":
                group.append(candidate)
            else:
                keep.append(candidate)
        remaining = keep
        groups.append(tuple(group))
    for left, right in combinations(comparison.states, 2):
        grouped = any(left in group and right in group for group in groups)
        if grouped != (comparison.status(left, right) == "equivalent"):
            raise AssertionError("equivalent pair statuses do not form a partition")
    return tuple(groups)


def status_counts(comparison):
    return dict(Counter(comparison.pair_statuses.values()))


def restrict_to_reachable(system):
    """Return the induced Ground on states reachable through known singleton edges."""
    reached = {system.initial_state}
    pending = deque([system.initial_state])
    while pending:
        source = pending.popleft()
        for action in system.actions:
            if system.status(source, action) != "known":
                continue
            target = system.step(source, action).target
            if target not in reached:
                reached.add(target)
                pending.append(target)
    states = tuple(state for state in system.states if state in reached)
    observations = tuple(item for item in system.observations if item.source in reached)
    return GroundTransitionSystem(
        states=states, actions=system.actions, initial_state=system.initial_state,
        channels=system.channels, observations=observations,
        metadata=dict(system.metadata),
    )


def fourier_degree_boolean(values, dimension):
    """Exact Walsh/Fourier degree for a Boolean truth table on the 3-cube."""
    degree = 0
    for subset in range(1 << dimension):
        coefficient_numerator = sum(
            -value if ((subset & point).bit_count() & 1) else value
            for point, value in enumerate(values)
        )
        if coefficient_numerator:
            degree = max(degree, subset.bit_count())
    return degree


def make_boolean_cube_ground(values, dimension):
    states = tuple(format(point, f"0{dimension}b") for point in range(1 << dimension))
    actions = tuple(f"FLIP_{coordinate}" for coordinate in range(dimension))
    observations = []
    for point, source in enumerate(states):
        for coordinate, action in enumerate(actions):
            target_point = point ^ (1 << coordinate)
            observations.append(TransitionObservation(
                source, action,
                (TransitionOutcome(
                    states[target_point],
                    (abs(values[point] - values[target_point]),),
                ),),
                evidence=(f"cube-edge:{point}:{coordinate}",),
            ))
    return GroundTransitionSystem(
        states, actions, states[0], ("absolute_discrete_derivative",),
        tuple(observations),
        metadata={"task": "boolean-cube-influence", "dimension": dimension},
    )


def run_aaronson_ambainis_finite():
    dimension = 3
    point_count = 1 << dimension
    truth_table_count = 1 << point_count
    tested = 0
    degree_counts = Counter()
    counterexamples = []
    minimum_max_influence = 1.0
    class_totals = [0, 0]
    total_unresolved = 0

    # Enumerate all nonconstant Boolean-valued functions on the 3-cube.
    for mask in range(1, truth_table_count - 1):
        values = tuple((mask >> point) & 1 for point in range(point_count))
        degree = fourier_degree_boolean(values, dimension)
        if degree not in (1, 2):
            continue
        ground = make_boolean_cube_ground(values, dimension)
        observer = ObserverContext(
            "all-coordinate-flips", ground.actions, ground.channels,
        )
        comparisons = partial_refinement_series(ground, observer, 2)
        influences = [
            sum(ground.step(state, action).output[0] for state in ground.states)
            / point_count
            for action in ground.actions
        ]
        max_influence = max(influences)
        tested += 1
        degree_counts[str(degree)] += 1
        minimum_max_influence = min(minimum_max_influence, max_influence)
        class_totals[0] += len(equivalence_classes(comparisons[1]))
        class_totals[1] += len(equivalence_classes(comparisons[2]))
        total_unresolved += status_counts(comparisons[2]).get("unresolved", 0)
        if max_influence == 0:
            counterexamples.append({"truth_table_mask": mask, "degree": degree})

    return {
        "dimension": dimension,
        "all_boolean_truth_tables": truth_table_count,
        "nonconstant_degree_le_2_functions_tested": tested,
        "degree_counts": dict(degree_counts),
        "minimum_max_coordinate_influence": minimum_max_influence,
        "zero_influence_counterexamples": counterexamples,
        "mean_quotient_classes_horizon_1": class_totals[0] / tested,
        "mean_quotient_classes_horizon_2": class_totals[1] / tested,
        "unresolved_pair_statuses_total": total_unresolved,
        "scope": (
            "Boolean-valued functions on the 3-cube with degree one or two; "
            "not a proof for arbitrary dimension, degree, or bounded real-valued polynomials"
        ),
    }


def clause_is_falsified(prefix, clause):
    for literal in clause:
        variable = abs(literal) - 1
        if variable >= len(prefix):
            return False
        bit = int(prefix[variable])
        literal_is_true = bit == 1 if literal > 0 else bit == 0
        if literal_is_true:
            return False
    return True


def assignment_satisfies(bits, clauses):
    return all(
        any(
            (bits[abs(literal) - 1] == "1")
            if literal > 0 else (bits[abs(literal) - 1] == "0")
            for literal in clause
        )
        for clause in clauses
    )


def build_sat_prefix_ground(variable_count, clauses, missing_cell=None):
    prefixes = [""]
    for depth in range(1, variable_count + 1):
        prefixes.extend("".join(bits) for bits in product("01", repeat=depth))
    states = tuple(prefixes + ["SAT", "UNSAT"])
    actions = ("SET0", "SET1")
    observations = []

    for prefix in prefixes:
        if len(prefix) == variable_count:
            terminal = "SAT" if assignment_satisfies(prefix, clauses) else "UNSAT"
            value = 1 if terminal == "SAT" else 0
            for action in actions:
                observations.append(TransitionObservation(
                    prefix, action, (TransitionOutcome(terminal, (value,)),),
                    evidence=("complete-assignment-check",),
                ))
            continue

        for action, bit in zip(actions, ("0", "1")):
            if (prefix, action) == missing_cell:
                continue
            successor = prefix + bit
            conflict = any(clause_is_falsified(successor, clause) for clause in clauses)
            target, output = ("UNSAT", (0,)) if conflict else (successor, (1,))
            observations.append(TransitionObservation(
                prefix, action, (TransitionOutcome(target, output),),
                evidence=(f"prefix-step:{prefix}:{action}",),
            ))

    for terminal, value in (("SAT", 1), ("UNSAT", 0)):
        for action in actions:
            observations.append(TransitionObservation(
                terminal, action, (TransitionOutcome(terminal, (value,)),),
                evidence=("terminal-stutter",),
            ))

    return GroundTransitionSystem(
        states, actions, "", ("prefix_remains_viable",), tuple(observations),
        metadata={
            "task": "bounded-cnf-prefix-search",
            "variables": variable_count,
            "clauses": [list(clause) for clause in clauses],
        },
    )


def brute_force_sat_solutions(variable_count, clauses):
    return [
        assignment
        for bits in product("01", repeat=variable_count)
        if assignment_satisfies(assignment := "".join(bits), clauses)
    ]


def run_sat_dogfood():
    clauses = (
        (1, 2, 3), (-1, 2, -4), (-2, 4, 5),
        (-3, -4, 5), (1, -5, -2), (-1, -3, 4),
    )
    full = build_sat_prefix_ground(5, clauses)
    reachable = restrict_to_reachable(full)
    observer = ObserverContext(
        "variable assignments", reachable.actions, reachable.channels,
    )
    comparisons = partial_refinement_series(reachable, observer, 5)
    groups = [equivalence_classes(item) for item in comparisons]
    solutions = brute_force_sat_solutions(5, clauses)

    incomplete = restrict_to_reachable(build_sat_prefix_ground(
        5, clauses, missing_cell=("", "SET1"),
    ))
    partial = partial_refinement_series(incomplete, observer, 2)
    pair = ("", "0")
    blockers = partial[1].unresolved_blockers.get(pair, ())

    return {
        "variables": 5,
        "clauses": [list(clause) for clause in clauses],
        "brute_force_solution_count": len(solutions),
        "solutions": solutions,
        "reachable_ground_states": len(reachable.states),
        "known_transition_records": len(reachable.observations),
        "ground_complete": reachable.complete,
        "quotient_classes_by_horizon": [len(group) for group in groups],
        "largest_class_by_horizon": [
            max(len(group) for group in grouping) for grouping in groups
        ],
        "pair_status_counts_at_horizon_5": status_counts(comparisons[-1]),
        "missing_edge_experiment": {
            "missing_cell": ["", "SET1"],
            "compared_states": list(pair),
            "pair_status_by_horizon": [item.status(*pair) for item in partial],
            "horizon_1_blockers": [
                {"action": item.action, "reason": item.reason} for item in blockers
            ],
        },
        "scope": (
            "finite five-variable CNF search model; brute-force checked, not an "
            "asymptotic SAT algorithm or an ETH result"
        ),
    }


def build_clique_ground(vertex_count, clique_size, edges):
    subsets = [
        subset
        for size in range(clique_size + 1)
        for subset in combinations(range(vertex_count), size)
    ]
    names = {
        subset: "{" + ",".join(str(vertex) for vertex in subset) + "}"
        for subset in subsets
    }
    states = tuple(names[subset] for subset in subsets) + ("FOUND", "DEAD")
    actions = tuple(f"ADD_{vertex}" for vertex in range(vertex_count))
    edge_set = set(edges)

    def adjacent(left, right):
        return (min(left, right), max(left, right)) in edge_set

    def is_clique(subset):
        return all(adjacent(left, right) for left, right in combinations(subset, 2))

    observations = []
    for subset in subsets:
        source = names[subset]
        for vertex, action in enumerate(actions):
            if len(subset) == clique_size:
                target = "FOUND" if is_clique(subset) else "DEAD"
                output = (1,) if target == "FOUND" else (0,)
            elif vertex in subset or (subset and vertex <= subset[-1]):
                target, output = source, (0,)
            else:
                successor = tuple(sorted(subset + (vertex,)))
                if all(adjacent(vertex, selected) for selected in subset):
                    target, output = names[successor], (1,)
                else:
                    target, output = "DEAD", (0,)
            observations.append(TransitionObservation(
                source, action, (TransitionOutcome(target, output),),
                evidence=("candidate-vertex-extension",),
            ))

    for terminal, value in (("FOUND", 1), ("DEAD", 0)):
        for action in actions:
            observations.append(TransitionObservation(
                terminal, action, (TransitionOutcome(terminal, (value,)),),
                evidence=("terminal-stutter",),
            ))

    return GroundTransitionSystem(
        states, actions, names[()], ("extension_remains_clique",),
        tuple(observations),
        metadata={
            "task": "finite-k-clique-extension-search",
            "vertices": vertex_count,
            "clique_size": clique_size,
            "edges": [list(edge) for edge in sorted(edge_set)],
        },
    )


def enumerate_cliques(vertex_count, clique_size, edges):
    edge_set = set(edges)
    return [
        subset
        for subset in combinations(range(vertex_count), clique_size)
        if all(
            (min(left, right), max(left, right)) in edge_set
            for left, right in combinations(subset, 2)
        )
    ]


def run_clique_dogfood():
    vertex_count, clique_size = 8, 4
    edges = (
        (0, 1), (0, 3), (0, 4), (0, 7),
        (1, 3), (1, 4), (1, 5), (1, 6), (1, 7),
        (2, 5), (2, 6), (2, 7), (3, 4), (3, 6),
        (4, 6), (5, 6), (6, 7),
    )
    reachable = restrict_to_reachable(
        build_clique_ground(vertex_count, clique_size, edges)
    )
    observer = ObserverContext(
        "candidate vertex probes", reachable.actions, reachable.channels,
    )
    comparisons = partial_refinement_series(reachable, observer, clique_size + 1)
    groups = [equivalence_classes(item) for item in comparisons]
    cliques = enumerate_cliques(vertex_count, clique_size, edges)

    return {
        "vertices": vertex_count,
        "clique_size": clique_size,
        "edges": len(edges),
        "brute_force_clique_count": len(cliques),
        "cliques": [list(clique) for clique in cliques],
        "reachable_ground_states": len(reachable.states),
        "known_transition_records": len(reachable.observations),
        "ground_complete": reachable.complete,
        "quotient_classes_by_horizon": [len(group) for group in groups],
        "largest_class_by_horizon": [
            max(len(group) for group in grouping) for grouping in groups
        ],
        "final_class_reduction_fraction": 1 - len(groups[-1]) / len(reachable.states),
        "scope": (
            "finite eight-vertex instance; subset states are explicitly constructed, "
            "so this is redundancy analysis, not an improved asymptotic k-Clique algorithm"
        ),
    }


def main():
    result = {
        "format": "VGI-ProofSearchDogfood-1",
        "aaronson_ambainis_finite_boolean_subfamily": run_aaronson_ambainis_finite(),
        "sat_prefix_search": run_sat_dogfood(),
        "k_clique_finite_search": run_clique_dogfood(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
