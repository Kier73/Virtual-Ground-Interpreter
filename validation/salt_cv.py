"""Salt audit, explicit seeded pair hashing, and group cross-validation.

The frozen Builds 13-15 use an ephemeral ``_PAIR_SALT``.  This module audits
where that happens and provides an explicit seeded replacement for future
empirical runs.  It also provides group cross-validation helpers for any
paired-corpus run that supplies grouped rows.
"""
from __future__ import annotations

import csv
import hashlib
import random
import statistics
from pathlib import Path

if __package__ in (None, ""):
    from common import ROOT
else:
    from .common import ROOT


def explicit_pair_salt(seed: int) -> bytes:
    """Derive the 32-byte pair salt from an explicit, logged seed."""
    return hashlib.sha256(f"VL explicit pair salt seed={seed}".encode("utf-8")).digest()


def pair_salt_provenance(seed: int) -> dict:
    salt = explicit_pair_salt(seed)
    return {
        "seed": seed,
        "salt_source": "validation explicit_pair_salt(seed)",
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "salt_hex": salt.hex(),
    }


def deterministic_pair_hash(seed: int, parts: tuple[str, ...]) -> str:
    """Privacy-preserving pair identifier derived from an explicit seed.

    This mirrors the intent of Build 13-15's pair hashing while making the
    derivation reproducible: same seed and parts give the same ID; changing
    the seed changes the ordering without exposing raw IDs.
    """
    payload = f"{seed}\x1f" + "\x1f".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def seeded_pair_order(seed: int, pair_ids: list[str]) -> list[str]:
    return sorted(pair_ids, key=lambda pid: deterministic_pair_hash(seed, (pid,)))


def salt_audit() -> dict:
    files = [
        ROOT / "theory_development" / "build_13" / "build_13.py",
        ROOT / "theory_development" / "build_14" / "build_14.py",
        ROOT / "theory_development" / "build_15" / "build_14.py",
    ]
    rows = []
    patterns = ("_PAIR_SALT", "secrets.token_bytes", "def run_analysis", "seed")
    for path in files:
        text = path.read_text(encoding="utf-8")
        rows.append(
            {
                "file": str(path.relative_to(ROOT)),
                "salt_definition_count": text.count("_PAIR_SALT = secrets.token_bytes(32)"),
                "secrets_token_bytes_count": text.count("secrets.token_bytes"),
                "run_analysis_seed_parameter": "def run_analysis(" in text and "seed" in text,
                "hash_uses_salt": "_PAIR_SALT + " in text,
            }
        )
    return {
        "files": rows,
        "total_salt_definitions": sum(x["salt_definition_count"] for x in rows),
        "replacement": "deterministic_pair_hash(seed, parts)",
        "note": (
            "The frozen builds keep the ephemeral salt for privacy. New "
            "empirical runs should accept an explicit seed, log it, and use "
            "deterministic_pair_hash so null and bootstrap draws reproduce."
        ),
    }


def group_kfold(rows: list[dict], group_key: str, k: int = 5, seed: int = 13) -> list[dict]:
    """Return folds where every group appears in exactly one fold."""
    groups = sorted({row[group_key] for row in rows})
    rng = random.Random(seed)
    rng.shuffle(groups)
    fold_of = {group: i % k for i, group in enumerate(groups)}
    folds = []
    for fold in range(k):
        test = [row for row in rows if fold_of[row[group_key]] == fold]
        train = [row for row in rows if fold_of[row[group_key]] != fold]
        folds.append({"fold": fold, "train": train, "test": test})
    return folds


def cross_validated_mean(rows: list[dict], group_key: str, score_key: str, k: int = 5, seed: int = 13) -> dict:
    folds = group_kfold(rows, group_key, k=k, seed=seed)
    fold_means = []
    for fold in folds:
        test = fold["test"]
        if test:
            fold_means.append(statistics.fmean(float(row[score_key]) for row in test))
    all_scores = [float(row[score_key]) for row in rows]
    return {
        "group_key": group_key,
        "score_key": score_key,
        "fold_count": k,
        "seed": seed,
        "group_count": len({row[group_key] for row in rows}),
        "row_count": len(rows),
        "fold_means": fold_means,
        "overall_mean": statistics.fmean(all_scores) if all_scores else 0.0,
        "fold_mean_sd": statistics.pstdev(fold_means) if len(fold_means) > 1 else 0.0,
        "min_fold_mean": min(fold_means) if fold_means else 0.0,
        "max_fold_mean": max(fold_means) if fold_means else 0.0,
    }


def corpus_status(corpus_root: str | Path | None) -> dict:
    """Honest status for an external paired corpus.

    The repository does not redistribute Rochester or TAPS.  A second corpus
    can be used only when an external path is supplied.
    """
    if corpus_root is None:
        return {
            "status": "not_run",
            "reason": "external paired corpus not supplied",
            "second_paired_corpus": False,
        }
    path = Path(corpus_root)
    if not path.exists():
        return {
            "status": "not_run",
            "reason": f"corpus path does not exist: {path}",
            "second_paired_corpus": False,
        }
    return {
        "status": "available_for_adapter",
        "corpus_root": str(path),
        "second_paired_corpus": True,
        "note": "Run the empirical analysis with an explicit seed and group cross-validation.",
    }


def rochester_room_loro_summary() -> dict:
    """Leave-one-room-out summary for the corrected Build 12 room medians."""
    path = ROOT / "theory_development/empirical_results/build_12/corrected/room_features_corrected.csv"
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    metrics = {}
    for metric in ("edt_s", "t20_s", "c50_db", "d50"):
        values = [float(row[metric]) for row in rows]
        loo_means = []
        for i in range(len(values)):
            rest = values[:i] + values[i + 1 :]
            loo_means.append(statistics.fmean(rest) if rest else 0.0)
        metrics[metric] = {
            "min": min(values),
            "max": max(values),
            "mean": statistics.fmean(values),
            "loo_mean_min": min(loo_means),
            "loo_mean_max": max(loo_means),
            "loo_mean_range": max(loo_means) - min(loo_means),
        }
    return {
        "room_count": len(rows),
        "metrics": metrics,
        "rooms": [row["room_id"] for row in rows],
    }
