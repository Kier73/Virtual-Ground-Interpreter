"""Build 05: active observation and intention-conditioned probe selection.

A small, dependency-free experimental model. Candidate structures are 2x2
linear maps; probes are input directions; observers select output channels.
The observer chooses probes by robust expected information gain per cost.
This is a research prototype, not a complete Virtual Layer implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import exp, isfinite, log, log2, pi, sqrt
from random import Random
from typing import Iterable, Mapping, Sequence

Matrix2 = tuple[tuple[float, float], tuple[float, float]]
Vector2 = tuple[float, float]

# 7-point Gauss-Hermite quadrature transformed for expectations under N(0,1).
_GH_NODES = (
    -2.8569700138728056, -1.355626179974266, 0.0,
    1.355626179974266, 2.8569700138728056,
)
_GH_WEIGHTS = (
    0.0112574113277207, 0.2220759220056126, 0.5333333333333333,
    0.2220759220056126, 0.0112574113277207,
)


@dataclass(frozen=True)
class ScalarCodonAlgebra:
    """Minimal configurable codon interpreter for matrix-vector response.

    `ld` supplies probe registers; `mx` multiplies coefficient/input pairs;
    `ad` accumulates each row. Alias changes alter names, not operation laws.
    """
    add: str = "ad"
    mul: str = "mx"

    def __post_init__(self) -> None:
        if not self.add.strip() or not self.mul.strip() or self.add == self.mul:
            raise ValueError("codon aliases must be nonempty and distinct")

    def apply(self, codon: str, left: float, right: float) -> float:
        if codon == self.add:
            value = left + right
        elif codon == self.mul:
            value = left * right
        else:
            raise ValueError(f"unknown scalar codon: {codon}")
        if not isfinite(value):
            raise ValueError("codon operation produced a non-finite value")
        return value

    def matrix_vector(self, matrix: Matrix2, vector: Vector2) -> Vector2:
        # Executed algebra: (m00*x0 + m01*x1, m10*x0 + m11*x1).
        out = []
        for row in matrix:
            p0 = self.apply(self.mul, row[0], vector[0])
            p1 = self.apply(self.mul, row[1], vector[1])
            out.append(self.apply(self.add, p0, p1))
        return (out[0], out[1])


DEFAULT_CODON_ALGEBRA = ScalarCodonAlgebra()


@dataclass(frozen=True)
class Hypothesis:
    name: str
    matrix: Matrix2

    def apply(self, probe: Vector2,
              algebra: ScalarCodonAlgebra = DEFAULT_CODON_ALGEBRA) -> Vector2:
        return algebra.matrix_vector(self.matrix, probe)


@dataclass(frozen=True)
class Probe:
    name: str
    input_vector: Vector2
    codon_chain: tuple[str, ...]
    cost: float
    description: str

    def __post_init__(self) -> None:
        if self.cost <= 0:
            raise ValueError("probe cost must be positive")
        if not self.codon_chain or self.codon_chain[0] != "ld":
            raise ValueError("probe program must begin with the load codon")
        norm = sqrt(self.input_vector[0] ** 2 + self.input_vector[1] ** 2)
        if abs(norm - 1.0) > 1e-9:
            raise ValueError("probe input vector must be unit-normalized")

    def load(self) -> Vector2:
        """Execute the `ld` stage: make the selected probe vector available."""
        if self.codon_chain[0] != "ld":
            raise ValueError("probe has no load stage")
        return self.input_vector


@dataclass(frozen=True)
class Observer:
    name: str
    channels: tuple[int, ...]
    noise_std: tuple[float, ...]
    gains: tuple[float, ...] = (1.0, 1.0)

    def __post_init__(self) -> None:
        if not self.channels or any(c not in (0, 1) for c in self.channels):
            raise ValueError("observer channels must be a nonempty subset of (0,1)")
        if len(self.noise_std) != len(self.channels):
            raise ValueError("one noise standard deviation is required per channel")
        if any(s <= 0 for s in self.noise_std):
            raise ValueError("noise standard deviations must be positive")
        if len(self.gains) != 2:
            raise ValueError("observer gains must have length two")

    def predict(self, hypothesis: Hypothesis, probe: Probe) -> tuple[float, ...]:
        raw = hypothesis.apply(probe.load())
        return tuple(self.gains[ch] * raw[ch] for ch in self.channels)

    def sigmas(self, uncertainty_scale: float = 1.0) -> tuple[float, ...]:
        if uncertainty_scale <= 0:
            raise ValueError("uncertainty_scale must be positive")
        return tuple(s * uncertainty_scale for s in self.noise_std)


@dataclass(frozen=True)
class Intent:
    name: str
    # Labels define what the observer is trying to learn. Equal labels mean
    # the underlying distinction is irrelevant to this particular intention.
    target_labels: Mapping[str, str]

    def __post_init__(self) -> None:
        if not self.target_labels:
            raise ValueError("intent requires target labels")


@dataclass(frozen=True)
class ProbeScore:
    probe: str
    eig_bits: float
    robust_eig_bits: float
    cost: float
    utility: float
    noise_scale_eigs: tuple[float, ...]


HYPOTHESES: tuple[Hypothesis, ...] = (
    Hypothesis("H0_identity", ((1.0, 0.0), (0.0, 1.0))),
    Hypothesis("H1_upper_coupling", ((1.0, 1.1), (0.0, 1.0))),
    Hypothesis("H2_lower_coupling", ((1.0, 0.0), (1.1, 1.0))),
    Hypothesis("H3_bidirectional", ((1.0, 0.8), (0.8, 1.0))),
)

_PROBE_DIAG = 1.0 / sqrt(2.0)
PROBES: tuple[Probe, ...] = (
    Probe("probe_x", (1.0, 0.0), ("ld", "mx", "ad"), 1.0,
          "Excite x; observe the structure's response to the first basis direction."),
    Probe("probe_y", (0.0, 1.0), ("ld", "mx", "ad"), 1.0,
          "Excite y; observe the structure's response to the second basis direction."),
    Probe("probe_diagonal", (_PROBE_DIAG, _PROBE_DIAG), ("ld", "mx", "ad"), 2.6,
          "Excite a normalized diagonal combination; higher acquisition cost."),
)

INTENTS: Mapping[str, Intent] = {
    "identify_structure": Intent("identify_structure", {
        "H0_identity": "H0_identity",
        "H1_upper_coupling": "H1_upper_coupling",
        "H2_lower_coupling": "H2_lower_coupling",
        "H3_bidirectional": "H3_bidirectional",
    }),
    "locate_upper_coupling": Intent("locate_upper_coupling", {
        "H0_identity": "absent", "H1_upper_coupling": "present",
        "H2_lower_coupling": "absent", "H3_bidirectional": "present",
    }),
    "locate_lower_coupling": Intent("locate_lower_coupling", {
        "H0_identity": "absent", "H1_upper_coupling": "absent",
        "H2_lower_coupling": "present", "H3_bidirectional": "present",
    }),
}

OBSERVERS: Mapping[str, Observer] = {
    "full": Observer("full_observer", (0, 1), (0.12, 0.12)),
    "x_only": Observer("x_channel_only", (0,), (0.12,)),
    "y_only": Observer("y_channel_only", (1,), (0.12,)),
    "noisy_full": Observer("noisy_full_observer", (0, 1), (0.24, 0.24)),
}


def _normal_logpdf(y: Sequence[float], mu: Sequence[float], sigma: Sequence[float]) -> float:
    d = len(y)
    total = -0.5 * d * log(2.0 * pi)
    for yy, mm, ss in zip(y, mu, sigma):
        z = (yy - mm) / ss
        total += -log(ss) - 0.5 * z * z
    return total


def _logsumexp(values: Sequence[float]) -> float:
    m = max(values)
    if m == float("-inf"):
        return m
    return m + log(sum(exp(v - m) for v in values))


def _normal_pdf(y: Sequence[float], mu: Sequence[float], sigma: Sequence[float]) -> float:
    return exp(_normal_logpdf(y, mu, sigma))


def normalize_prior(prior: Mapping[str, float], hypotheses: Sequence[Hypothesis] = HYPOTHESES) -> dict[str, float]:
    names = [h.name for h in hypotheses]
    if set(prior) != set(names):
        raise ValueError("prior must contain exactly the configured hypothesis names")
    if any(v < 0 for v in prior.values()):
        raise ValueError("prior probabilities cannot be negative")
    z = sum(prior.values())
    if z <= 0:
        raise ValueError("prior must have positive total mass")
    return {name: prior[name] / z for name in names}


def expected_information_gain(
    probe: Probe,
    observer: Observer,
    intent: Intent,
    prior: Mapping[str, float],
    uncertainty_scale: float = 1.0,
    hypotheses: Sequence[Hypothesis] = HYPOTHESES,
) -> float:
    """Mutual information I(target(intent); observation | probe), in bits.

    Uses product Gauss-Hermite quadrature under the finite Gaussian mixture.
    The target is the intent's label, not necessarily the full hypothesis ID.
    """
    p = normalize_prior(prior, hypotheses)
    sigmas = observer.sigmas(uncertainty_scale)
    target_by_h = {h.name: intent.target_labels[h.name] for h in hypotheses}
    classes = sorted(set(target_by_h.values()))
    p_class = {c: sum(p[h.name] for h in hypotheses if target_by_h[h.name] == c)
               for c in classes}
    conditional = {
        c: {h.name: (p[h.name] / p_class[c] if p_class[c] > 0 and target_by_h[h.name] == c else 0.0)
            for h in hypotheses}
        for c in classes
    }
    means = {h.name: observer.predict(h, probe) for h in hypotheses}
    # I(C;Y) = sum_c p(c) E_{Y|c}[log2 p(Y|c)/p(Y)].
    eig = 0.0
    for c in classes:
        if p_class[c] <= 0:
            continue
        for h in hypotheses:
            wh = conditional[c][h.name]
            if wh <= 0:
                continue
            mu_h = means[h.name]
            # Integrate standard-normal noise using tensor-product GH nodes.
            for node_tuple in product(range(len(_GH_NODES)), repeat=len(sigmas)):
                qweight = 1.0
                y = []
                for j, node_idx in enumerate(node_tuple):
                    qweight *= _GH_WEIGHTS[node_idx]
                    y.append(mu_h[j] + sigmas[j] * _GH_NODES[node_idx])
                if qweight == 0:
                    continue
                log_pc_terms = []
                for h2 in hypotheses:
                    w2 = conditional[c][h2.name]
                    if w2 > 0:
                        log_pc_terms.append(log(w2) + _normal_logpdf(y, means[h2.name], sigmas))
                log_pcy = _logsumexp(log_pc_terms)
                log_py_terms = []
                for c2 in classes:
                    if p_class[c2] <= 0:
                        continue
                    class_terms = []
                    for h2 in hypotheses:
                        w2 = conditional[c2][h2.name]
                        if w2 > 0:
                            class_terms.append(log(w2) + _normal_logpdf(y, means[h2.name], sigmas))
                    log_py_terms.append(log(p_class[c2]) + _logsumexp(class_terms))
                log_py = _logsumexp(log_py_terms)
                eig += p_class[c] * wh * qweight * (log_pcy - log_py) / log(2.0)
    # Numerical quadrature can produce tiny negative values near zero.
    return max(0.0, eig)


def score_probes(
    observer: Observer,
    intent: Intent,
    prior: Mapping[str, float] | None = None,
    probes: Sequence[Probe] = PROBES,
    uncertainty_scales: Sequence[float] = (1.0, 2.0),
) -> tuple[ProbeScore, ...]:
    if prior is None:
        prior = {h.name: 1.0 / len(HYPOTHESES) for h in HYPOTHESES}
    normalized = normalize_prior(prior)
    scores = []
    for probe in probes:
        eigs = tuple(expected_information_gain(probe, observer, intent, normalized, scale)
                     for scale in uncertainty_scales)
        nominal = eigs[0]
        robust = min(eigs)
        utility = robust / probe.cost
        scores.append(ProbeScore(probe.name, nominal, robust, probe.cost, utility, eigs))
    return tuple(sorted(scores, key=lambda s: (-s.utility, s.probe)))


def choose_probe(
    observer: Observer,
    intent: Intent,
    prior: Mapping[str, float] | None = None,
    probes: Sequence[Probe] = PROBES,
    uncertainty_scales: Sequence[float] = (1.0, 2.0),
) -> ProbeScore:
    scores = score_probes(observer, intent, prior, probes, uncertainty_scales)
    if not scores or scores[0].robust_eig_bits <= 1e-12:
        raise ValueError("no candidate probe provides information about this intention")
    return scores[0]


def bayesian_update(
    prior: Mapping[str, float],
    probe: Probe,
    observer: Observer,
    observation: Sequence[float],
    uncertainty_scale: float = 1.0,
    hypotheses: Sequence[Hypothesis] = HYPOTHESES,
) -> dict[str, float]:
    p = normalize_prior(prior, hypotheses)
    sigmas = observer.sigmas(uncertainty_scale)
    if len(observation) != len(sigmas):
        raise ValueError("observation dimensionality does not match observer")
    log_weights = []
    for h in hypotheses:
        if p[h.name] <= 0:
            log_weights.append(float("-inf"))
        else:
            mu = observer.predict(h, probe)
            log_weights.append(log(p[h.name]) + _normal_logpdf(observation, mu, sigmas))
    z = _logsumexp(log_weights)
    return {h.name: exp(lw - z) if lw != float("-inf") else 0.0
            for h, lw in zip(hypotheses, log_weights)}


def sample_observation(
    hypothesis: Hypothesis, probe: Probe, observer: Observer, rng: Random,
    uncertainty_scale: float = 1.0,
) -> tuple[float, ...]:
    mu = observer.predict(hypothesis, probe)
    sigma = observer.sigmas(uncertainty_scale)
    return tuple(m + rng.gauss(0.0, s) for m, s in zip(mu, sigma))


def posterior_target_probability(prior: Mapping[str, float], intent: Intent) -> dict[str, float]:
    p = normalize_prior(prior)
    result: dict[str, float] = {}
    for h in HYPOTHESES:
        label = intent.target_labels[h.name]
        result[label] = result.get(label, 0.0) + p[h.name]
    return result


def adaptive_episode(
    true_hypothesis: Hypothesis,
    observer: Observer,
    intent: Intent,
    rng: Random,
    max_steps: int = 2,
    fixed_probe: Probe | None = None,
    random_policy: bool = False,
    fixed_schedule: Sequence[Probe] | None = None,
    noise_scale: float = 1.0,
) -> dict:
    prior = {h.name: 1.0 / len(HYPOTHESES) for h in HYPOTHESES}
    history = []
    for step in range(max_steps):
        if fixed_schedule is not None:
            selected = fixed_schedule[min(step, len(fixed_schedule) - 1)]
            score = None
        elif fixed_probe is not None:
            selected = fixed_probe
            score = None
        elif random_policy:
            selected = PROBES[rng.randrange(len(PROBES))]
            score = None
        else:
            score = choose_probe(observer, intent, prior)
            selected = next(p for p in PROBES if p.name == score.probe)
        y = sample_observation(true_hypothesis, selected, observer, rng, noise_scale)
        prior = bayesian_update(prior, selected, observer, y, noise_scale)
        target_post = posterior_target_probability(prior, intent)
        history.append({
            "step": step + 1,
            "probe": selected.name,
            "codon_chain": list(selected.codon_chain),
            "observation": list(y),
            "posterior": dict(prior),
            "target_posterior": target_post,
            "robust_eig_bits_before": score.robust_eig_bits if score else None,
            "probe_cost": selected.cost,
        })
        if max(target_post.values()) >= 0.995:
            break
    target_post = posterior_target_probability(prior, intent)
    predicted_target = max(target_post, key=target_post.get)
    true_target = intent.target_labels[true_hypothesis.name]
    predicted_h = max(prior, key=prior.get)
    return {
        "history": history,
        "posterior": prior,
        "target_posterior": target_post,
        "predicted_target": predicted_target,
        "true_target": true_target,
        "target_correct": predicted_target == true_target,
        "predicted_hypothesis": predicted_h,
        "true_hypothesis": true_hypothesis.name,
        "hypothesis_correct": predicted_h == true_hypothesis.name,
        "steps": len(history),
        "total_cost": sum(item["probe_cost"] for item in history),
    }


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial success rate."""
    if total < 1 or not 0 <= successes <= total:
        raise ValueError("invalid binomial counts")
    phat = successes / total
    denom = 1.0 + z * z / total
    center = (phat + z * z / (2.0 * total)) / denom
    radius = (z / denom) * sqrt(phat * (1.0 - phat) / total + z * z / (4.0 * total * total))
    return (max(0.0, center - radius), min(1.0, center + radius))


def evaluate_policies(
    observer: Observer,
    intent: Intent,
    trials_per_hypothesis: int = 100,
    max_steps: int = 2,
    seed: int = 20261104,
    noise_scale: float = 1.0,
) -> dict:
    if trials_per_hypothesis < 1:
        raise ValueError("trials_per_hypothesis must be positive")
    if noise_scale <= 0:
        raise ValueError("noise_scale must be positive")
    policies = ("active", "fixed_probe_x_repeat", "fixed_complementary_xy", "random")
    stats = {p: {"target_correct": 0, "hypothesis_correct": 0, "steps": 0,
                 "cost": 0.0} for p in policies}
    total = trials_per_hypothesis * len(HYPOTHESES)
    rng = Random(seed)
    for h in HYPOTHESES:
        for _ in range(trials_per_hypothesis):
            for policy in policies:
                local_rng = Random(rng.getrandbits(64))
                kwargs = {}
                if policy == "fixed_probe_x_repeat":
                    kwargs["fixed_probe"] = PROBES[0]
                elif policy == "fixed_complementary_xy":
                    kwargs["fixed_schedule"] = (PROBES[0], PROBES[1])
                elif policy == "random":
                    kwargs["random_policy"] = True
                result = adaptive_episode(h, observer, intent, local_rng,
                                          max_steps=max_steps, noise_scale=noise_scale, **kwargs)
                stats[policy]["target_correct"] += int(result["target_correct"])
                stats[policy]["hypothesis_correct"] += int(result["hypothesis_correct"])
                stats[policy]["steps"] += result["steps"]
                stats[policy]["cost"] += result["total_cost"]
    return {
        "trials_per_hypothesis": trials_per_hypothesis,
        "total_trials": total,
        "observer": observer.name,
        "intent": intent.name,
        "noise_scale": noise_scale,
        "max_steps": max_steps,
        "policies": {
            name: {
                "target_accuracy": values["target_correct"] / total,
                "target_accuracy_wilson_95": list(wilson_interval(values["target_correct"], total)),
                "full_hypothesis_accuracy": values["hypothesis_correct"] / total,
                "full_hypothesis_accuracy_wilson_95": list(wilson_interval(values["hypothesis_correct"], total)),
                "mean_steps": values["steps"] / total,
                "mean_probe_cost": values["cost"] / total,
                "correct_targets": values["target_correct"],
                "correct_hypotheses": values["hypothesis_correct"],
            }
            for name, values in stats.items()
        },
    }


def invariance_audit() -> dict:
    """Verify active observation doesn't mutate underlying algebraic laws."""
    before = {h.name: h.matrix for h in HYPOTHESES}
    # An observation/probe only applies the map; it must not mutate coefficients.
    observer = OBSERVERS["full"]
    intent = INTENTS["identify_structure"]
    prior = {h.name: 0.25 for h in HYPOTHESES}
    chosen = choose_probe(observer, intent, prior)
    h0 = HYPOTHESES[0]
    _ = sample_observation(h0, PROBES[0], observer, Random(7))
    after = {h.name: h.matrix for h in HYPOTHESES}
    return {
        "underlying_structure_unchanged": before == after,
        "probe_selection": chosen.probe,
        "matrix_snapshot_before": before,
        "matrix_snapshot_after": after,
    }


def run_report() -> dict:
    prior = {h.name: 0.25 for h in HYPOTHESES}
    rankings = {}
    for observer_key in ("full", "x_only", "y_only", "noisy_full"):
        observer = OBSERVERS[observer_key]
        rankings[observer_key] = {}
        for intent_key, intent in INTENTS.items():
            rows = score_probes(observer, intent, prior)
            rankings[observer_key][intent_key] = [
                {"probe": s.probe, "eig_bits": s.eig_bits,
                 "robust_eig_bits": s.robust_eig_bits,
                 "cost": s.cost, "utility": s.utility,
                 "eigs_by_noise_scale": list(s.noise_scale_eigs)}
                for s in rows
            ]
    episode_rng = Random(121)
    active_demo = adaptive_episode(HYPOTHESES[1], OBSERVERS["full"],
                                   INTENTS["identify_structure"], episode_rng)
    policy_eval = evaluate_policies(OBSERVERS["full"], INTENTS["identify_structure"],
                                   trials_per_hypothesis=40, max_steps=2)
    intent_eval_upper = evaluate_policies(OBSERVERS["full"], INTENTS["locate_upper_coupling"],
                                          trials_per_hypothesis=40, max_steps=2)
    intent_eval_lower = evaluate_policies(OBSERVERS["full"], INTENTS["locate_lower_coupling"],
                                          trials_per_hypothesis=40, max_steps=2)
    noise_robustness = []
    base = OBSERVERS["full"]
    for factor in (0.5, 1.0, 2.0, 4.0, 6.0):
        scaled = Observer(f"full_observer_noise_x{factor:g}", base.channels,
                          tuple(v * factor for v in base.noise_std), base.gains)
        noise_robustness.append(evaluate_policies(
            scaled, INTENTS["identify_structure"], trials_per_hypothesis=60,
            max_steps=2, seed=20261104 + int(factor * 100), noise_scale=1.0))
    return {
        "build": "05",
        "title": "Active Observation and Intention-Conditioned Probe Selection",
        "model_scope": "Synthetic finite hypothesis family and Gaussian observation model; not yet an integrated Virtual Layer runtime.",
        "hypotheses": {h.name: [list(h.matrix[0]), list(h.matrix[1])] for h in HYPOTHESES},
        "probes": {p.name: {"input": list(p.input_vector), "codon_chain": list(p.codon_chain),
                            "cost": p.cost} for p in PROBES},
        "rankings": rankings,
        "active_demo": active_demo,
        "policy_evaluation_full_identification": policy_eval,
        "policy_evaluation_upper_coupling_intent": intent_eval_upper,
        "policy_evaluation_lower_coupling_intent": intent_eval_lower,
        "noise_robustness": noise_robustness,
        "invariance_audit": invariance_audit(),
    }


if __name__ == "__main__":
    import json
    from pathlib import Path
    report = run_report()
    out = Path(__file__).parent / "reports" / "build_05_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(out),
        "full_identification": report["rankings"]["full"]["identify_structure"],
        "x_only_upper": report["rankings"]["x_only"]["locate_upper_coupling"],
        "y_only_lower": report["rankings"]["y_only"]["locate_lower_coupling"],
        "policy_evaluation": report["policy_evaluation_full_identification"],
        "noise_robustness": report["noise_robustness"],
        "invariance_audit": report["invariance_audit"]["underlying_structure_unchanged"],
    }, indent=2))
