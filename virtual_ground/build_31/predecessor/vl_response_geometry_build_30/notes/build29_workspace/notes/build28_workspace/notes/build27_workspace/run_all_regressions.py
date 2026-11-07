from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "verification"
LOGS.mkdir(exist_ok=True)
suites = [
    ("build27", ROOT, [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
    ("build26", ROOT / "legacy" / "build26", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
    ("build24", ROOT / "legacy" / "build26", [sys.executable, "-m", "unittest", "discover", "-s", "legacy/build24/tests", "-v"]),
    ("build25", ROOT / "legacy" / "build26", [sys.executable, "-m", "unittest", "discover", "-s", "legacy/build25/tests", "-v"]),
]
results = []
for name, cwd, cmd in suites:
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=False)
    (LOGS / f"{name}_tests.txt").write_text(proc.stdout, encoding="utf-8")
    results.append({"suite": name, "return_code": proc.returncode,
                    "passed": proc.returncode == 0,
                    "log": str((LOGS / f"{name}_tests.txt").relative_to(ROOT))})
    if proc.returncode:
        print(proc.stdout)
print("\n".join(f"{r['suite']}: {'PASS' if r['passed'] else 'FAIL'}" for r in results))
if any(not r["passed"] for r in results):
    raise SystemExit(1)
