#!/usr/bin/env python3
"""Run Build 29 tests plus the preserved Build 28 -> Build 24–27 regression chain."""
from __future__ import annotations
import json, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
VER=ROOT/"verification"; VER.mkdir(exist_ok=True)
local=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=ROOT,
                     text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
(VER/"build29_tests.txt").write_text(local.stdout,encoding="utf-8")
match=re.search(r"Ran (\d+) tests?",local.stdout)
local_count=int(match.group(1)) if match else None
archive=ROOT/"notes"/"BUILD_28_ORIGINAL_ARCHIVE.zip"
if not archive.exists(): raise FileNotFoundError(archive)
with tempfile.TemporaryDirectory(prefix="build29_inherited_") as td:
    with zipfile.ZipFile(archive) as zf: zf.extractall(td)
    prior_root=Path(td)/"vl_response_geometry_build_28"
    run=subprocess.run([sys.executable,"run_all_regressions.py"],cwd=prior_root,
                       text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
    summary_path=prior_root/"verification"/"combined_regression_summary.json"
    if summary_path.exists():
        inherited=json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        inherited={"all_passed":False,"error":"Build 28 regression summary missing"}
    (VER/"build28_inherited_runner.txt").write_text(run.stdout,encoding="utf-8")
    for name in ("build28_tests.txt","build27_tests.txt","build26_tests.txt","build24_tests.txt","build25_tests.txt"):
        p=prior_root/"verification"/name
        if p.exists(): shutil.copy2(p,VER/name)

combined_count=(local_count or 0)+int(inherited.get("combined_test_count") or 0)
summary={"build29_return_code":local.returncode,"build29_tests":local_count,
         "inherited_build28_return_code":run.returncode,
         "inherited_summary":inherited,"combined_test_count":combined_count,
         "all_passed":local.returncode==0 and run.returncode==0 and bool(inherited.get("all_passed"))}
(VER/"combined_regression_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
(VER/"run_all_regressions.txt").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(summary,indent=2,sort_keys=True))
if not summary["all_passed"]:
    print(local.stdout); print(run.stdout); raise SystemExit(1)
