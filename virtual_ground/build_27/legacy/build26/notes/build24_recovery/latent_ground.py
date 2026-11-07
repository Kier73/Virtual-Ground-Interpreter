"""Build 24: latent-context discovery and self-constructing predictive grounds.

The learner receives only action/output traces from a deterministic resettable
black-box teacher. Hidden context is never exposed. It constructs a minimal
bounded predictive Mealy machine using an observation table, counterexamples,
and distinguishing suffixes; then tests whether that machine admits a compact
phase-coordinate representation.

Standard library only. Synthetic deterministic fixtures; no external data.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from itertools import product
from math import log2
from typing import Callable, Iterable, Sequence
import hashlib
import json

ACTIONS = ("HOLD", "PROBE_A", "PROBE_B")
Word = tuple[str, ...]
Output = tuple[int, ...]


def words_upto(alphabet: Sequence[str], depth: int, *, include_empty: bool = False) -> list[Word]:
    out: list[Word] = [()] if include_empty else []
    for n in range(1, depth + 1):
        out.extend(tuple(x) for x in product(alphabet, repeat=n))
    return out


@dataclass(frozen=True)
class HiddenContextGround:
    """Test-only data generator. The learner never receives this object."""
    name: str
    mode_count: int
    action_stride: tuple[int, int, int]
    output_mode: str
    output_period: int = 0
    rare_mode: int = -1
    action_maps: tuple[tuple[int, ...], ...] | None = None

    def next_mode(self, mode: int, action: str) -> int:
        if self.action_maps is not None:
            return self.action_maps[ACTIONS.index(action)][mode]
        return (mode + self.action_stride[ACTIONS.index(action)]) % self.mode_count

    def emit(self, mode: int, action: str) -> Output:
        if self.output_mode == "crt_pair":
            return (mode % 2, mode % 3)
        if self.output_mode == "mod2":
            return (mode % 2,)
        if self.output_mode == "mod3":
            return (mode % 3,)
        if self.output_mode == "rare_probe":
            return (int(action == "PROBE_A" and mode == self.rare_mode),)
        if self.output_mode == "constant":
            return (0,)
        if self.output_mode == "periodic_alias":
            return (mode % self.output_period,)
        raise ValueError(f"unknown output mode {self.output_mode}")


class ResettableTeacher:
    """Black-box membership-query interface; query always starts at hidden mode 0."""
    def __init__(self, ground: HiddenContextGround, channels: Sequence[int] | None = None):
        self.__ground = ground
        self.channels = tuple(channels) if channels is not None else None
        self._cache: dict[Word, tuple[Output, ...]] = {}
        self.query_count = 0
        self.query_requests: dict[str, int] = defaultdict(int)
        self.words_by_purpose: dict[str, set[Word]] = defaultdict(set)

    def query(self, word: Word, purpose: str = "membership") -> tuple[Output, ...]:
        if any(a not in ACTIONS for a in word):
            raise ValueError("invalid action in query word")
        self.query_requests[purpose] += 1
        self.words_by_purpose[purpose].add(word)
        if word in self._cache:
            return self._cache[word]
        mode = 0
        outputs: list[Output] = []
        for action in word:
            raw = self.__ground.emit(mode, action)
            output = raw if self.channels is None else tuple(raw[i] for i in self.channels)
            outputs.append(output)
            mode = self.__ground.next_mode(mode, action)
        result = tuple(outputs)
        self._cache[word] = result
        self.query_count += 1
        return result

    def stats(self) -> dict:
        return {
            "query_requests_by_purpose": dict(self.query_requests),
            "unique_words_by_purpose": {k: len(v) for k, v in self.words_by_purpose.items()},
            "unique_query_words_total": len(self._cache),
            "cache_hits": sum(self.query_requests.values()) - len(self._cache),
        }

    def fingerprint(self) -> str:
        # This does not reveal the ground. It fingerprints the observable query
        # interface over a bounded characterization suite.
        suite = words_upto(ACTIONS, 5)
        payload = [(w, self.query(w)) for w in suite]
        return hashlib.sha256(repr(payload).encode()).hexdigest()


@dataclass
class ObservationTable:
    teacher: ResettableTeacher
    access: set[Word] = field(default_factory=lambda: {()})
    experiments: set[Word] = field(default_factory=lambda: {(a,) for a in ACTIONS})

    def suffix_output(self, prefix: Word, suffix: Word) -> tuple[Output, ...]:
        if not suffix:
            return ()
        return self.teacher.query(prefix + suffix, purpose="membership")[len(prefix):]

    def row(self, prefix: Word) -> tuple[tuple[Word, tuple[Output, ...]], ...]:
        return tuple((e, self.suffix_output(prefix, e)) for e in sorted(self.experiments, key=lambda w: (len(w), w)))

    def close(self) -> bool:
        rows = {self.row(s) for s in self.access}
        frontier = {s + (a,) for s in self.access for a in ACTIONS}
        new = [r for r in frontier if self.row(r) not in rows]
        if new:
            candidate = min(new, key=lambda w: (len(w), w))
            self.add_access(candidate)
            return True
        return False

    def add_access(self, word: Word) -> None:
        for i in range(len(word) + 1):
            self.access.add(word[:i])

    def make_consistent(self) -> bool:
        by_row: dict[tuple, list[Word]] = defaultdict(list)
        for s in sorted(self.access, key=lambda w: (len(w), w)):
            by_row[self.row(s)].append(s)
        for histories in by_row.values():
            if len(histories) < 2:
                continue
            for i, s in enumerate(histories):
                for t in histories[i + 1:]:
                    for a in ACTIONS:
                        rs, rt = self.row(s + (a,)), self.row(t + (a,))
                        if rs != rt:
                            suffix = next(e for e in sorted(self.experiments, key=lambda w: (len(w), w))
                                          if self.suffix_output(s + (a,), e) != self.suffix_output(t + (a,), e))
                            self.experiments.add((a,) + suffix)
                            return True
        return False

    def build_machine(self) -> "LearnedMealyGround":
        representatives: dict[tuple, Word] = {}
        for s in sorted(self.access, key=lambda w: (len(w), w)):
            representatives.setdefault(self.row(s), s)
        ordered_rows = sorted(representatives, key=lambda r: (len(representatives[r]), representatives[r]))
        ids = {row: f"q{i}" for i, row in enumerate(ordered_rows)}
        transitions: dict[str, dict[str, str]] = {}
        outputs: dict[str, dict[str, Output]] = {}
        for row in ordered_rows:
            sid = ids[row]
            rep = representatives[row]
            transitions[sid] = {}
            outputs[sid] = {}
            for a in ACTIONS:
                target_row = self.row(rep + (a,))
                if target_row not in ids:
                    raise RuntimeError("table is not closed")
                transitions[sid][a] = ids[target_row]
                outputs[sid][a] = self.suffix_output(rep, (a,))[0]
        initial = ids[self.row(())]
        return LearnedMealyGround(
            initial=initial,
            transitions=transitions,
            outputs=outputs,
            representatives={ids[r]: list(representatives[r]) for r in ordered_rows},
            experiment_count=len(self.experiments),
            access_count=len(self.access),
        )


@dataclass
class LearnedMealyGround:
    initial: str
    transitions: dict[str, dict[str, str]]
    outputs: dict[str, dict[str, Output]]
    representatives: dict[str, list[str]]
    experiment_count: int
    access_count: int

    @property
    def states(self) -> tuple[str, ...]:
        return tuple(self.transitions)

    def run(self, word: Word) -> tuple[Output, ...]:
        state = self.initial
        out: list[Output] = []
        for action in word:
            out.append(self.outputs[state][action])
            state = self.transitions[state][action]
        return tuple(out)

    def as_dict(self) -> dict:
        return {
            "format": "VG-PredictiveMealy-1",
            "initial": self.initial,
            "actions": list(ACTIONS),
            "state_count": len(self.states),
            "transitions": self.transitions,
            "outputs": {q: {a: list(y) for a, y in row.items()} for q, row in self.outputs.items()},
            "access_representatives": self.representatives,
            "experiment_count": self.experiment_count,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LearnedMealyGround":
        if data.get("format") != "VG-PredictiveMealy-1":
            raise ValueError("unsupported ground specification")
        if set(data.get("actions", [])) != set(ACTIONS):
            raise ValueError("action alphabet mismatch")
        trans = data["transitions"]
        outs = {q: {a: tuple(y) for a, y in row.items()} for q, row in data["outputs"].items()}
        if set(trans) != set(outs) or data["initial"] not in trans:
            raise ValueError("invalid state maps")
        for q in trans:
            if set(trans[q]) != set(ACTIONS) or set(outs[q]) != set(ACTIONS):
                raise ValueError("incomplete transition row")
            if any(t not in trans for t in trans[q].values()):
                raise ValueError("transition to unknown state")
        return cls(data["initial"], trans, outs, data.get("access_representatives", {}),
                   int(data.get("experiment_count", 0)), int(data.get("access_count", 0)))


def first_counterexample(machine: LearnedMealyGround, teacher: ResettableTeacher, depth: int) -> tuple[Word, int] | None:
    for word in words_upto(ACTIONS, depth):
        observed = teacher.query(word, purpose="conformance")
        predicted = machine.run(word)
        for i, (x, y) in enumerate(zip(observed, predicted)):
            if x != y:
                return word, i
    return None


@dataclass
class LearningResult:
    machine: LearnedMealyGround
    rounds: list[dict]
    conformance_depth: int
    counterexample_count: int
    query_count: int
    bounded_equivalent: bool
    active_probe: dict

    def as_dict(self) -> dict:
        return {
            "state_count": len(self.machine.states),
            "rounds": self.rounds,
            "conformance_depth": self.conformance_depth,
            "counterexample_count": self.counterexample_count,
            "query_count": self.query_count,
            "bounded_equivalent": self.bounded_equivalent,
            "active_probe": self.active_probe,
            "machine": self.machine.as_dict(),
        }


def entropy_partition(outputs: Sequence[tuple[Output, ...]]) -> float:
    if not outputs:
        return 0.0
    counts: dict[tuple, int] = defaultdict(int)
    for out in outputs:
        counts[out] += 1
    n = len(outputs)
    return -sum((c / n) * log2(c / n) for c in counts.values())


def choose_active_probe(teacher: ResettableTeacher, histories: Sequence[Word], max_depth: int = 5,
                        cost: Callable[[Word], float] | None = None) -> dict:
    """Choose a distinguishing suffix by response-partition entropy per cost."""
    if cost is None:
        cost = lambda w: float(len(w))
    candidates = words_upto(ACTIONS, max_depth)
    scored = []
    for probe in candidates:
        responses = [teacher.query(h + probe, purpose="probe_selection")[len(h):] for h in histories]
        info = entropy_partition(responses)
        c = max(float(cost(probe)), 1e-12)
        scored.append((info / c, info, probe, c, len(set(responses))))
    best = max(scored, key=lambda x: (x[0], x[1], -len(x[2]), tuple(reversed(x[2]))))
    return {
        "probe": list(best[2]), "information_bits_empirical": best[1],
        "cost": best[3], "bits_per_cost": best[0], "response_classes": best[4],
        "history_count": len(histories), "candidate_count": len(candidates),
    }


class ActiveMealyLearner:
    def __init__(self, teacher: ResettableTeacher, *, conformance_depth: int = 7,
                 max_rounds: int = 40, max_access_states: int = 100):
        self.teacher = teacher
        self.conformance_depth = conformance_depth
        self.max_rounds = max_rounds
        self.max_access_states = max_access_states
        self.table = ObservationTable(teacher)

    def learn(self) -> LearningResult:
        rounds: list[dict] = []
        counterexamples = 0
        initial_probe = choose_active_probe(self.teacher, [(), ("HOLD",), ("PROBE_A",), ("PROBE_B",)], max_depth=3)
        for it in range(self.max_rounds):
            # Close the observation table.
            close_steps = 0
            while self.table.close():
                close_steps += 1
                if len(self.table.access) > self.max_access_states:
                    raise RuntimeError("access-state budget exceeded")
            # Make rows transition-consistent.
            consistency_steps = 0
            while self.table.make_consistent():
                consistency_steps += 1
            # A newly added distinguishing suffix can create new rows; close again.
            while self.table.close():
                close_steps += 1
                if len(self.table.access) > self.max_access_states:
                    raise RuntimeError("access-state budget exceeded")
            machine = self.table.build_machine()
            cex = first_counterexample(machine, self.teacher, self.conformance_depth)
            rounds.append({
                "round": it + 1,
                "candidate_states": len(machine.states),
                "access_prefixes": len(self.table.access),
                "distinguishing_suffixes": len(self.table.experiments),
                "closure_additions": close_steps,
                "consistency_refinements": consistency_steps,
                "counterexample": list(cex[0]) if cex else None,
                "first_mismatch_index": cex[1] if cex else None,
            })
            if cex is None:
                return LearningResult(machine, rounds, self.conformance_depth, counterexamples,
                                      self.teacher.query_count, True, initial_probe)
            counterexamples += 1
            word, mismatch = cex
            # The suffix beginning at the first wrong output distinguishes the
            # hidden state reached after the preceding access prefix.
            distinguishing_suffix = word[mismatch:]
            if not distinguishing_suffix:
                raise RuntimeError("empty counterexample suffix")
            self.table.experiments.add(distinguishing_suffix)
            self.table.add_access(word[:mismatch])
        raise RuntimeError("learning round budget exceeded")


def infer_clock_coordinate(machine: LearnedMealyGround, action: str = "HOLD") -> dict:
    states = list(machine.states)
    nxt = {q: machine.transitions[q][action] for q in states}
    start = machine.initial
    if len(states) == 1:
        return {"is_single_cycle": False, "is_fixed_context": True, "clock_action": action,
                "period": 1, "covered_states": 1, "state_count": 1,
                "interpretation": "no observable latent progression under this observer"}
    order: list[str] = []
    seen: dict[str, int] = {}
    q = start
    while q not in seen:
        seen[q] = len(order)
        order.append(q)
        q = nxt[q]
    is_single_cycle = q == start and len(order) == len(states)
    if not is_single_cycle:
        return {"is_single_cycle": False, "clock_action": action, "covered_states": len(order), "state_count": len(states)}
    strides: dict[str, int | None] = {}
    for a in ACTIONS:
        deltas = {(order.index(machine.transitions[s][a]) - i) % len(order) for i, s in enumerate(order)}
        strides[a] = next(iter(deltas)) if len(deltas) == 1 else None
    return {
        "is_single_cycle": True,
        "clock_action": action,
        "period": len(order),
        "phase_order": order,
        "action_phase_strides": strides,
        "all_actions_are_constant_phase_strides": all(v is not None for v in strides.values()),
    }


def bounded_certificate(machine: LearnedMealyGround, teacher: ResettableTeacher, depth: int) -> dict:
    cases = 0
    mismatches = []
    for word in words_upto(ACTIONS, depth):
        cases += 1
        observed = teacher.query(word, purpose="certificate")
        predicted = machine.run(word)
        if observed != predicted:
            mismatches.append({"word": list(word), "observed": observed, "predicted": predicted})
            if len(mismatches) >= 20:
                break
    return {
        "method": "exhaustive reset-query conformance over all action words up to stated depth",
        "depth": depth,
        "cases_checked": cases,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "bounded_equivalence": not mismatches,
    }



def compile_virtual_ground(machine: LearnedMealyGround) -> dict:
    """Compile the inferred Mealy ground to a phase law when possible, else FSM."""
    clock = infer_clock_coordinate(machine)
    if clock.get("is_single_cycle") and clock.get("all_actions_are_constant_phase_strides"):
        order = clock["phase_order"]
        phase_of = {state: i for i, state in enumerate(order)}
        output_table = {
            str(phase_of[state]): {a: list(machine.outputs[state][a]) for a in ACTIONS}
            for state in order
        }
        return {
            "compiler_kind": "modular_phase_program",
            "phase_count": len(order),
            "phase_order": order,
            "initial_phase": phase_of[machine.initial],
            "action_phase_strides": clock["action_phase_strides"],
            "output_table_by_phase_and_action": output_table,
            "semantics": "phase_next=(phase+stride[action]) mod phase_count; output=table[phase][action]",
        }
    return {
        "compiler_kind": "finite_predictive_automaton",
        "initial_state": machine.initial,
        "transitions": machine.transitions,
        "outputs": {q: {a: list(y) for a, y in row.items()} for q, row in machine.outputs.items()},
        "semantics": "state_next=transitions[state][action]; output=outputs[state][action]",
    }


def run_compiled_ground(program: dict, state: int | str, action: str) -> tuple[int | str, Output]:
    if action not in ACTIONS:
        raise ValueError("unknown action")
    if program["compiler_kind"] == "modular_phase_program":
        phase = int(state)
        n = int(program["phase_count"])
        if not 0 <= phase < n:
            raise ValueError("phase outside compiled ground")
        out = tuple(program["output_table_by_phase_and_action"][str(phase)][action])
        nxt = (phase + int(program["action_phase_strides"][action])) % n
        return nxt, out
    if program["compiler_kind"] == "finite_predictive_automaton":
        q = str(state)
        out = tuple(program["outputs"][q][action])
        return program["transitions"][q][action], out
    raise ValueError("unknown compiled ground kind")


def verify_compiled_ground(machine: LearnedMealyGround, program: dict) -> dict:
    if program["compiler_kind"] == "modular_phase_program":
        q_to_phase = {q: i for i, q in enumerate(program["phase_order"])} if "phase_order" in program else None
        # Reconstruct phase order from the inferred clock action. The compiled
        # output table is indexed in that order, and the initial phase is 0.
        clock = infer_clock_coordinate(machine)
        order = clock["phase_order"]
        if program["initial_phase"] != 0:
            raise AssertionError("compiled phase origin must map initial state to zero")
        state_by_phase = {i: q for i, q in enumerate(order)}
        cases = 0
        for phase, q in state_by_phase.items():
            for action in ACTIONS:
                nxt, out = run_compiled_ground(program, phase, action)
                if nxt != q_to_phase[machine.transitions[q][action]] or out != machine.outputs[q][action]:
                    raise AssertionError("compiled phase program differs from learned machine")
                cases += 1
        return {"cases_checked": cases, "exact": True, "compiler_kind": program["compiler_kind"]}
    cases = 0
    for q in machine.states:
        for action in ACTIONS:
            nxt, out = run_compiled_ground(program, q, action)
            if nxt != machine.transitions[q][action] or out != machine.outputs[q][action]:
                raise AssertionError("compiled automaton differs from learned machine")
            cases += 1
    return {"cases_checked": cases, "exact": True, "compiler_kind": program["compiler_kind"]}

def fixture_grounds() -> dict[str, HiddenContextGround]:
    return {
        "coupled_six": HiddenContextGround("coupled_six", 6, (1, 2, 3), "crt_pair"),
        "delayed_six": HiddenContextGround("delayed_six", 6, (1, 1, 1), "rare_probe", rare_mode=5),
        "aliased_six": HiddenContextGround("aliased_six", 6, (1, 2, 3), "mod3"),
        "unobservable_eight": HiddenContextGround("unobservable_eight", 8, (1, 2, 3), "constant"),
        "partial_four": HiddenContextGround(
            "partial_four", 4, (1, 1, 1), "mod2",
            action_maps=((1, 2, 2, 3), (1, 2, 3, 0), (0, 1, 2, 3)),
        ),
    }


def run_fixture_suite() -> dict:
    results: dict[str, dict] = {}
    for name, ground in fixture_grounds().items():
        if name == "coupled_six":
            profiles = {"parity_only": (0,), "residue3_only": (1,), "joint": None}
        elif name == "aliased_six":
            profiles = {"residue3_only": None}
        else:
            profiles = {"available": None}
        for profile_name, channels in profiles.items():
            teacher = ResettableTeacher(ground, channels=channels)
            learner = ActiveMealyLearner(teacher, conformance_depth=8)
            learned = learner.learn()
            machine = learned.machine
            cert = bounded_certificate(machine, teacher, 8)
            clock = infer_clock_coordinate(machine)
            post_learning_probe = choose_active_probe(
                teacher, [tuple(v) for v in machine.representatives.values()], max_depth=6
            )
            adaptive_policy = build_adaptive_probe_tree(
                teacher, {q: tuple(v) for q, v in machine.representatives.items()}, max_probe_depth=6
            )
            key = f"{name}:{profile_name}"
            results[key] = {
                "physical_hidden_modes_for_test_oracle_only": ground.mode_count,
                "learner_observed_channels": list(range(2)) if channels is None and ground.output_mode == "crt_pair" else ([channels[0]] if channels else [0]),
                "learned_predictive_contexts": len(machine.states),
                "counterexamples": learned.counterexample_count,
                "learning_rounds": learned.rounds,
                "query_count": learned.query_count,
                "query_statistics": teacher.stats(),
                "bounded_certificate": cert,
                "clock_coordinate": clock,
                "active_probe": learned.active_probe,
                "post_learning_diagnostic_probe": post_learning_probe,
                "adaptive_probe_policy": adaptive_policy,
                "learned_machine": machine.as_dict(),
            }
    return results



def build_adaptive_probe_tree(teacher: ResettableTeacher, context_histories: dict[str, Word],
                              max_probe_depth: int = 6, max_nodes: int = 32) -> dict:
    """Build an adaptive diagnostic policy over already discovered contexts.

    Each probe is a finite action word. After it is executed, histories are
    extended before choosing the next probe, so branches track the evolved
    hidden context rather than pretending observation is non-invasive.
    """
    stats = {"nodes": 0, "probe_cost": 0, "identified": 0, "ambiguous": 0, "identification_cost_by_context": {}}

    def recurse(histories: dict[str, Word], depth: int, cumulative_cost: int) -> dict:
        if len(histories) <= 1:
            stats["identified"] += len(histories)
            for label in histories:
                stats["identification_cost_by_context"][label] = cumulative_cost
            return {"kind": "identified", "contexts": list(histories), "cumulative_cost": cumulative_cost}
        if stats["nodes"] >= max_nodes or depth >= max_nodes:
            stats["ambiguous"] += len(histories)
            return {"kind": "budget_limited", "contexts": list(histories)}
        labels = sorted(histories)
        probe_info = choose_active_probe(teacher, [histories[x] for x in labels], max_probe_depth)
        probe = tuple(probe_info["probe"])
        groups: dict[tuple[Output, ...], dict[str, Word]] = defaultdict(dict)
        for label in labels:
            out = teacher.query(histories[label] + probe, purpose="adaptive_policy")[len(histories[label]):]
            groups[out][label] = histories[label] + probe
        if len(groups) <= 1:
            stats["ambiguous"] += len(histories)
            return {"kind": "boundedly_indistinguishable", "contexts": labels, "best_probe": list(probe),
                    "information_bits": probe_info["information_bits_empirical"]}
        stats["nodes"] += 1
        stats["probe_cost"] += len(probe)
        branches = []
        for out, sub in sorted(groups.items(), key=lambda kv: repr(kv[0])):
            branches.append({"observed_output": [list(y) for y in out], "next": recurse(sub, depth + 1, cumulative_cost + len(probe))})
        return {"kind": "probe", "probe": list(probe), "cost": len(probe),
                "information_bits": probe_info["information_bits_empirical"], "branches": branches}

    tree = recurse(dict(context_histories), 0, 0)
    costs = list(stats["identification_cost_by_context"].values())
    stats["worst_case_probe_cost"] = max(costs, default=0)
    stats["mean_probe_cost"] = (sum(costs) / len(costs)) if costs else None
    return {"tree": tree, "statistics": stats, "initial_contexts": len(context_histories),
            "max_probe_depth": max_probe_depth, "max_nodes": max_nodes}

def run_delayed_horizon_experiment() -> dict:
    ground = fixture_grounds()["delayed_six"]
    rows = []
    for depth in (1, 2, 3, 4, 5, 6, 7, 8):
        teacher = ResettableTeacher(ground)
        learned = ActiveMealyLearner(teacher, conformance_depth=depth).learn()
        rows.append({
            "conformance_depth": depth,
            "learned_contexts": len(learned.machine.states),
            "counterexamples": learned.counterexample_count,
            "rounds": len(learned.rounds),
            "bounded_equivalent": bounded_certificate(learned.machine, teacher, depth)["bounded_equivalence"],
            "distinguishing_suffixes": learned.machine.experiment_count,
        })
    return {"ground": ground.name, "physical_modes_hidden_from_learner": ground.mode_count, "results": rows}


def make_executable_spec(machine: LearnedMealyGround, ground_name: str, observer: str) -> dict:
    return {
        "specification": machine.as_dict(),
        "compiled_program": compile_virtual_ground(machine),
        "metadata": {
            "ground_name": ground_name,
            "observer_profile": observer,
            "semantic_claim": "minimal predictive quotient under the supplied reset, action and observation interface, to bounded conformance depth",
            "hidden_physical_state_claim": "not inferred; only behaviorally distinguishable predictive contexts are represented",
        },
    }


def sha256_json(data: dict) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()
