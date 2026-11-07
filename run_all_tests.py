#!/usr/bin/env python3
"""Run the frozen test suite for every build and print a compact summary.

The builds are intentionally self-contained. This runner only orchestrates them;
it never edits a build or shares code between builds.

The top-level trees are split by purpose:
  theory_development/build_01 .. build_19   (Build 16 is embedded in build_17)
  virtual_ground/build_20 .. build_31       (Build 24 is embedded in build_25/26)

Builds 16 and 24 have no standalone directory. Run the embedded Build 24-30
regression chain with virtual_ground/build_30/run_all_regressions.py if needed.

Examples:
    python run_all_tests.py
    python run_all_tests.py --write-logs
    python run_all_tests.py --builds 12 13 14
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD_ROOTS = (ROOT / "theory_development", ROOT / "virtual_ground")
TEST_RESULTS = ROOT / "test_results"
TEST_RE = re.compile(r"Ran (\d+) tests? in ([\d.]+)s")
OK_RE = re.compile(r"^OK", re.MULTILINE)


def all_build_dirs() -> list[Path]:
    dirs = [
        path
        for root in BUILD_ROOTS
        if root.is_dir()
        for path in root.glob("build_*")
        if path.is_dir()
    ]
    return sorted(dirs, key=lambda path: int(path.name.split("_")[1]))


def find_build(number: int) -> Path | None:
    for root in BUILD_ROOTS:
        path = root / f"build_{number:02d}"
        if path.is_dir():
            return path
    return None


def discover_command(build_dir: Path) -> list[str]:
    tests_dir = build_dir / "tests"
    if tests_dir.is_dir() and any(tests_dir.glob("test*.py")):
        return [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py", "-v"]
    return [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test*.py", "-v"]


def run_build(build_dir: Path, write_log: bool) -> dict:
    command = discover_command(build_dir)
    env = dict(os.environ)
    # Keep the shipped manifests intact on Builds 27/30/31 and avoid cache clutter.
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    proc = subprocess.run(
        command,
        cwd=build_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    output = proc.stdout + proc.stderr
    match = TEST_RE.search(output)
    tests = int(match.group(1)) if match else None
    seconds = float(match.group(2)) if match else None
    ok = proc.returncode == 0 and OK_RE.search(output) is not None
    if write_log:
        TEST_RESULTS.mkdir(parents=True, exist_ok=True)
        (TEST_RESULTS / f"{build_dir.name}.txt").write_text(output, encoding="utf-8")
    return {
        "build": build_dir.name,
        "tests": tests,
        "seconds": seconds,
        "ok": ok,
        "returncode": proc.returncode,
        "output": output,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--builds", nargs="*", type=int, help="build numbers to run (default: all present)")
    ap.add_argument("--write-logs", action="store_true", help="overwrite test_results/build_NN.txt")
    ap.add_argument("--show-failures", action="store_true", help="print full output for failing builds")
    args = ap.parse_args()

    if args.builds:
        build_dirs = [p for n in args.builds if (p := find_build(n)) is not None]
        missing = [n for n in args.builds if find_build(n) is None]
        if missing:
            print(f"Build directories not found: {missing}", file=sys.stderr)
    else:
        build_dirs = all_build_dirs()
    if not build_dirs:
        print("No build directories found.", file=sys.stderr)
        return 2

    results = []
    for build_dir in build_dirs:
        print(f"running {build_dir.name} ...", flush=True)
        result = run_build(build_dir, args.write_logs)
        results.append(result)
        status = "ok" if result["ok"] else "FAILED"
        print(
            f"  {status:6s} {result['tests'] if result['tests'] is not None else '?':>3} tests"
            f"  {result['seconds'] if result['seconds'] is not None else '?'} s"
        )
        if args.show_failures and not result["ok"]:
            print(result["output"])
        if result["tests"] is None:
            print("  warning: could not parse a 'Ran N tests' line", file=sys.stderr)

    total_tests = sum(r["tests"] or 0 for r in results)
    total_seconds = sum(r["seconds"] or 0.0 for r in results)
    failed = [r["build"] for r in results if not r["ok"]]
    print()
    print(f"{len(results)} builds, {total_tests} tests, {total_seconds:.2f} s")
    if failed:
        print(f"failures: {', '.join(failed)}")
        return 1
    print("all suites passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
