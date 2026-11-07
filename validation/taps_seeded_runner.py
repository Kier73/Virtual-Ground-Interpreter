"""Seeded wrappers and group cross-validation for the frozen TAPS builds.

The frozen Builds 13-15 derive pair IDs from an ephemeral salt.  This wrapper
does not edit those builds.  It loads a frozen module, replaces its public
``_PAIR_SALT`` with an explicit seed-derived salt before calling the analysis,
and writes a small provenance file.  For cross-validation it extracts pair
features through the frozen code, then partitions the resulting rows by the
internal speaker and sentence groups in memory.
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from pathlib import Path

if __package__ in (None, ""):
    from common import ROOT, load_module
    from salt_cv import deterministic_pair_hash, explicit_pair_salt, pair_salt_provenance
else:
    from .common import ROOT, load_module
    from .salt_cv import deterministic_pair_hash, explicit_pair_salt, pair_salt_provenance


def load_taps_module(build: int):
    if build == 13:
        return load_module("build13", "theory_development/build_13/build_13.py", add_dir=True)
    if build == 14:
        return load_module("build14", "theory_development/build_14/build_14.py", add_dir=True)
    if build == 15:
        module = load_module("build15", "theory_development/build_15/build_15.py", add_dir=True)
        # Build 15 imports its sibling build_14 module; seed that module too.
        sibling = sys.modules.get("build_14")
        if sibling is not None and hasattr(sibling, "_PAIR_SALT"):
            return module, sibling
        return module, None
    raise ValueError("build must be 13, 14 or 15")


def seed_taps_module(build: int, seed: int):
    loaded = load_taps_module(build)
    if build == 15:
        module, sibling = loaded
        salt = explicit_pair_salt(seed)
        module._PAIR_SALT = salt
        if sibling is not None:
            sibling._PAIR_SALT = salt
        return module
    module = loaded
    module._PAIR_SALT = explicit_pair_salt(seed)
    return module


def run_seeded_taps(
    build: int,
    root: str | Path,
    output_dir: str | Path,
    *,
    split: str = "test",
    max_speakers: int | None = None,
    max_utterances_per_speaker: int | None = None,
    permutations: int = 99,
    seed: int = 13,
) -> dict:
    """Run a frozen TAPS analysis with an explicit logged pair-salt seed."""
    module = seed_taps_module(build, seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    common = dict(
        split=split,
        max_speakers=max_speakers,
        max_utterances_per_speaker=max_utterances_per_speaker,
        permutations=permutations,
        seed=seed,
        provenance="TAPS_file_release_local",
    )
    if build in (13, 14):
        report = module.run_analysis(root, output_dir, **common)
    else:
        report = module.run_taps_graph_analysis(
            root,
            output_dir,
            split=split,
            max_speakers=max_speakers,
            max_utterances_per_speaker=max_utterances_per_speaker,
        )
    provenance = {
        "build": build,
        "seed": seed,
        "salt": pair_salt_provenance(seed),
        "split": split,
        "root": str(root),
        "output_dir": str(output_dir),
        "pair_ordering": "explicit deterministic_pair_hash(seed, parts)",
        "note": (
            "The frozen build was not edited. Its _PAIR_SALT global was bound "
            "to explicit_pair_salt(seed) before the analysis ran."
        ),
    }
    (output_dir / "seeded_salt_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"report": report, "provenance": provenance}


def _fold_for(seed: int, group: str, folds: int) -> int:
    return int(deterministic_pair_hash(seed, (group,)), 16) % folds


def extract_pair_features(
    build: int,
    root: str | Path,
    *,
    split: str = "test",
    seed: int = 13,
    max_utterances_per_speaker: int | None = None,
):
    """Extract pair features through the frozen Build 14 code path.

    Build 14 is used because its feature rows are the Build 13 geometry rows
    plus the temporal-emission model used by Build 15.
    """
    module = seed_taps_module(14, seed)
    pairs = module.discover_pairs(root, split=split)
    by_speaker: dict[str, list[dict]] = {}
    for pair in pairs:
        by_speaker.setdefault(pair["speaker_internal"], []).append(pair)
    selected = []
    for speaker in sorted(by_speaker):
        rows = sorted(by_speaker[speaker], key=lambda p: p["utterance_internal"])
        if max_utterances_per_speaker is not None:
            rows = rows[:max_utterances_per_speaker]
        selected.extend(rows)
    features = []
    skipped = 0
    for pair in selected:
        try:
            features.append(module.analyze_pair(pair))
        except Exception:
            skipped += 1
    if not features:
        raise RuntimeError("no pair features extracted")
    return module, features, skipped


def summarize_features(module, features: list[dict], seed: int = 13, permutations: int = 99) -> dict:
    return module.summarize_rdm_relationships(features, n_perm=permutations, seed=seed)


def view_rhos(summary: dict) -> dict[str, float]:
    return {
        row["view"]: float(row["median_rdm_spearman"])
        for row in summary["views"]
    }


def speaker_cross_validation(
    root: str | Path,
    *,
    split: str = "test",
    seed: int = 13,
    folds: int = 5,
    permutations: int = 29,
    max_utterances_per_speaker: int | None = 30,
) -> dict:
    """Hold out whole speakers and summarize only held-out RDM geometry."""
    module, features, skipped = extract_pair_features(
        14,
        root,
        split=split,
        seed=seed,
        max_utterances_per_speaker=max_utterances_per_speaker,
    )
    speakers = sorted({row["speaker_internal"] for row in features})
    shuffled = sorted(speakers)
    random.Random(seed).shuffle(shuffled)
    fold_of_speaker = {speaker: i % folds for i, speaker in enumerate(shuffled)}
    fold_rows: list[dict] = []
    for fold in range(folds):
        heldout = [row for row in features if fold_of_speaker[row["speaker_internal"]] == fold]
        if len({row["speaker_internal"] for row in heldout}) < 2:
            continue
        summary = summarize_features(module, heldout, seed=seed + fold, permutations=permutations)
        fold_rows.append(
            {
                "fold": fold,
                "held_out_speakers": len({row["speaker_internal"] for row in heldout}),
                "held_out_pairs": len(heldout),
                "view_median_rho": view_rhos(summary),
            }
        )
    views = sorted({view for row in fold_rows for view in row["view_median_rho"]})
    view_summary = {}
    for view in views:
        values = [row["view_median_rho"][view] for row in fold_rows if view in row["view_median_rho"]]
        view_summary[view] = {
            "fold_count": len(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
        }
    return {
        "method": "speaker group cross-validation; speakers are held out as whole groups",
        "seed": seed,
        "folds": folds,
        "speakers": len(speakers),
        "pairs_extracted": len(features),
        "pairs_skipped": skipped,
        "max_utterances_per_speaker": max_utterances_per_speaker,
        "fold_rows": fold_rows,
        "view_summary": view_summary,
    }


def sentence_cross_validation(
    root: str | Path,
    *,
    split: str = "test",
    seed: int = 13,
    folds: int = 5,
    permutations: int = 29,
    max_utterances_per_speaker: int | None = None,
) -> dict:
    """Hold out sentence groups inside every speaker and summarize RDMs."""
    module, features, skipped = extract_pair_features(
        14,
        root,
        split=split,
        seed=seed,
        max_utterances_per_speaker=max_utterances_per_speaker,
    )
    # analyze_pair only returns speaker_internal; recover utterance group from
    # the pairing step by rebuilding the pair_key -> utterance map.
    pairs = module.discover_pairs(root, split=split)
    utterance_by_key = {p["pair_key"]: p["utterance_internal"] for p in pairs}
    for row in features:
        row["_sentence_group"] = utterance_by_key.get(row["pair_key"], row["pair_key"])
    fold_rows: list[dict] = []
    sentence_groups = sorted({row["_sentence_group"] for row in features})
    shuffled_sentences = sorted(sentence_groups)
    random.Random(seed + 1).shuffle(shuffled_sentences)
    fold_of_sentence = {group: i % folds for i, group in enumerate(shuffled_sentences)}
    for fold in range(folds):
        heldout = [
            row for row in features
            if fold_of_sentence[row["_sentence_group"]] == fold
        ]
        if len({row["speaker_internal"] for row in heldout}) < 2:
            continue
        summary = summarize_features(module, heldout, seed=seed + 100 + fold, permutations=permutations)
        fold_rows.append(
            {
                "fold": fold,
                "held_out_pairs": len(heldout),
                "held_out_speakers": len({row["speaker_internal"] for row in heldout}),
                "held_out_sentences": len({row["_sentence_group"] for row in heldout}),
                "view_median_rho": view_rhos(summary),
            }
        )
    views = sorted({view for row in fold_rows for view in row["view_median_rho"]})
    view_summary = {}
    for view in views:
        values = [row["view_median_rho"][view] for row in fold_rows if view in row["view_median_rho"]]
        view_summary[view] = {
            "fold_count": len(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
        }
    return {
        "method": "sentence group cross-validation inside speakers",
        "seed": seed,
        "folds": folds,
        "pairs_extracted": len(features),
        "pairs_skipped": skipped,
        "fold_rows": fold_rows,
        "view_summary": view_summary,
    }
