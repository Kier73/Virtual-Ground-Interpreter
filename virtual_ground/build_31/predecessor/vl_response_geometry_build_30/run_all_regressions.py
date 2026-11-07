#!/usr/bin/env python3
"""Run each preserved build test suite exactly once (Builds 24–30)."""
from __future__ import annotations
import json, re, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
VER=ROOT/"verification"; VER.mkdir(exist_ok=True)
BASE=ROOT/"notes"/"build29_workspace"
P={
 "build30":ROOT,
 "build29":BASE,
 "build28":BASE/"notes"/"build28_workspace",
 "build27":BASE/"notes"/"build28_workspace"/"notes"/"build27_workspace",
}
P["build26"]=P["build27"]/"legacy"/"build26"
P["build24"]=P["build26"]/"legacy"/"build24"
P["build25"]=P["build26"]/"legacy"/"build25"
counts={};details={}; all_ok=True
for name,path in P.items():
    proc=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=path,
                        text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
    (VER/f"{name}_tests.txt").write_text(proc.stdout,encoding="utf-8")
    m=re.search(r"Ran (\d+) tests?",proc.stdout)
    count=int(m.group(1)) if m else None
    ok=proc.returncode==0 and count is not None
    counts[name]=count
    details[name]={"path":str(path.relative_to(ROOT)),"return_code":proc.returncode,"test_count":count,"passed":ok}
    all_ok=all_ok and ok
    if not ok: print(proc.stdout)
combined=sum(v or 0 for v in counts.values())
result={"builds":details,"test_counts":counts,"combined_test_count":combined,"all_passed":all_ok,
        "method":"direct execution of each preserved suite once; avoids recursive duplicate regression runs"}
(VER/"combined_regression_summary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
(VER/"run_all_regressions.txt").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2,sort_keys=True))
if not all_ok: raise SystemExit(1)
