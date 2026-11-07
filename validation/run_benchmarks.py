"""Run the post-freeze validation benchmarks and write a JSON report."""
from __future__ import annotations

import json
from pathlib import Path

if __package__ in (None, ""):
    from build12_preroll import summarize_preroll
    from build24_equivalence import delayed_counterexample_summary, equivalence_summary
    from productivity import productivity_summary
    from random_grounds import random_build22_summary, random_build23_summary
    from salt_cv import corpus_status, rochester_room_loro_summary, salt_audit
    from signal_stress import signal_stress_summary
else:
    from .build12_preroll import summarize_preroll
    from .build24_equivalence import delayed_counterexample_summary, equivalence_summary
    from .productivity import productivity_summary
    from .random_grounds import random_build22_summary, random_build23_summary
    from .salt_cv import corpus_status, rochester_room_loro_summary, salt_audit
    from .signal_stress import signal_stress_summary


def main() -> None:
    report = {
        "note": (
            "Post-freeze validation summaries. They exercise the published "
            "frozen code without modifying it."
        ),
        "build12_preroll": summarize_preroll(),
        "productivity": productivity_summary(),
        "random_build22": random_build22_summary(seed=20261106, cases=48),
        "random_build23": random_build23_summary(seed=20261107, cases=16),
        "build24_equivalence": equivalence_summary(),
        "build24_delayed_counterexample": delayed_counterexample_summary(),
        "signal_stress": signal_stress_summary(),
        "salt_audit": salt_audit(),
        "external_corpus_status": corpus_status(None),
        "rochester_room_loro": rochester_room_loro_summary(),
    }
    out = Path(__file__).resolve().parent / "benchmark_results.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
