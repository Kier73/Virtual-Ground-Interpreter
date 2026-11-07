from __future__ import annotations
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VER = ROOT / "verification"
VER.mkdir(exist_ok=True)

local = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                       cwd=ROOT, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False)
(VER / "build28_tests.txt").write_text(local.stdout, encoding="utf-8")

archive = ROOT / "notes" / "BUILD_27_ORIGINAL_ARCHIVE.zip"
with tempfile.TemporaryDirectory(prefix="build28_inherited_") as tmp:
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(tmp)
    prior_root = Path(tmp) / "vl_response_geometry_build_27"
    prior = subprocess.run([sys.executable, "run_all_regressions.py"], cwd=prior_root,
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           check=False)
    inherited_summary = prior.stdout
    inherited_counts = {}
    for name in ("build27", "build26", "build24", "build25"):
        log_path = prior_root / "verification" / f"{name}_tests.txt"
        content = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        match = re.search(r"Ran (\d+) tests?", content)
        inherited_counts[name] = int(match.group(1)) if match else None
        if log_path.exists():
            shutil.copy2(log_path, VER / f"{name}_tests.txt")

(VER / "inherited_regression_runner.txt").write_text(inherited_summary, encoding="utf-8")
local_match = re.search(r"Ran (\d+) tests?", local.stdout)
local_count = int(local_match.group(1)) if local_match else None
all_inherited_ok = prior.returncode == 0 and all(v is not None for v in inherited_counts.values())
summary = {
    "build28_return_code": local.returncode,
    "build28_tests": local_count,
    "inherited_return_code": prior.returncode,
    "inherited_test_counts": inherited_counts,
    "combined_test_count": (local_count or 0) + sum(v or 0 for v in inherited_counts.values()),
    "all_passed": local.returncode == 0 and all_inherited_ok,
}
import json
(VER / "combined_regression_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
print(json.dumps(summary, indent=2, sort_keys=True))
if not summary["all_passed"]:
    print(local.stdout)
    print(inherited_summary)
    raise SystemExit(1)
