from __future__ import annotations
import json
from pathlib import Path
from latent_ground import (
    run_fixture_suite, run_delayed_horizon_experiment, compile_virtual_ground,
    verify_compiled_ground, LearnedMealyGround, sha256_json,
)

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

suite = run_fixture_suite()
delayed = run_delayed_horizon_experiment()
compiled = {}
for key, row in suite.items():
    machine = LearnedMealyGround.from_dict(row["learned_machine"])
    program = compile_virtual_ground(machine)
    verification = verify_compiled_ground(machine, program)
    spec = {
        "specification": machine.as_dict(),
        "compiled_program": program,
        "compiler_verification": verification,
        "metadata": {
            "ground_name": key.split(":")[0],
            "observer_profile": key.split(":")[1],
            "semantic_claim": "minimal predictive quotient supported by the observation table and bounded conformance suite",
            "physical_hidden_state_claim": "not inferred; only behaviorally distinguishable predictive contexts are represented",
        },
    }
    spec["fingerprint"] = sha256_json(spec["specification"])
    compiled[key] = spec
    safe_name = key.replace(":", "__")
    (REPORTS / f"ground_spec_{safe_name}.json").write_text(json.dumps(spec, indent=2) + "\n")

summary = {
    "build": 24,
    "purpose": "discover latent predictive context without exposing it to the learner",
    "all_experiments_synthetic": True,
    "suite": suite,
    "delayed_horizon_experiment": delayed,
    "compiled_specifications": compiled,
    "interpretation": {
        "coupled_six": "joint sensors reconstruct six predictive contexts; parity and modulo-three observers see quotients of two and three contexts",
        "aliased_six": "six physical fixture modes collapse to three behaviorally distinguishable contexts",
        "unobservable_eight": "eight hidden fixture modes collapse to one predictive context because the observer cannot distinguish them",
        "delayed_six": "a counterexample of length six refines a one-state candidate into a six-context cycle",
        "partial_four": "a non-bijective HOLD transition is learned as a finite automaton, not forced into a reversible group or clock model",
    },
    "query_accounting": {
        "membership_queries": "observation-table cells; explicit requests are counted separately from unique reset words",
        "probe_selection_queries": "candidate active diagnostic sequences evaluated against access histories",
        "conformance_queries": "bounded exhaustive equivalence checks against the synthetic teacher; these are a test oracle, not available for arbitrary live systems",
    },
    "limits": [
        "The teacher has a deterministic reproducible reset to a fixed initial context; real systems may not provide this.",
        "The action alphabet and available output channels are supplied by the interface.",
        "The learner discovers a minimal predictive quotient, not the system's ontological hidden variables.",
        "Conformance is exhaustive only up to the reported input-word depth.",
        "All tests are synthetic and noiseless; probabilistic, continuous, nonstationary and drifting systems remain open.",
    ],
}
(REPORTS / "build_24_results.json").write_text(json.dumps(summary, indent=2) + "\n")
(REPORTS / "delayed_horizon.csv").write_text(
    "depth,learned_predictive_contexts,counterexamples,learning_rounds,bounded_equivalent_within_depth,distinguishing_suffixes\n" +
    "".join(f"{r['conformance_depth']},{r['learned_contexts']},{r['counterexamples']},{r['rounds']},{int(r['bounded_equivalent'])},{r['distinguishing_suffixes']}\n" for r in delayed["results"])
)
with (REPORTS / "observer_quotients.csv").open("w") as f:
    f.write("fixture,observer,oracle_physical_modes_for_test_only,learned_predictive_contexts,clock_cycle,phase_period,conformance_depth,conformance_mismatches\n")
    for key, row in suite.items():
        clk = row["clock_coordinate"]
        f.write(f"{key.split(':')[0]},{key.split(':')[1]},{row['physical_hidden_modes_for_test_oracle_only']},{row['learned_predictive_contexts']},{int(clk.get('is_single_cycle', False))},{clk.get('period','')},{row['bounded_certificate']['depth']},{row['bounded_certificate']['mismatch_count']}\n")
with (REPORTS / "compiler_verification.csv").open("w") as f:
    f.write("fixture,observer,compiler_kind,cases_checked,exact,fingerprint\n")
    for key, spec in compiled.items():
        f.write(f"{key.split(':')[0]},{key.split(':')[1]},{spec['compiler_verification']['compiler_kind']},{spec['compiler_verification']['cases_checked']},{int(spec['compiler_verification']['exact'])},{spec['fingerprint']}\n")
with (REPORTS / "query_accounting.csv").open("w") as f:
    f.write("fixture,observer,purpose,requests,unique_words\n")
    for key, row in suite.items():
        stats = row["query_statistics"]
        purposes = sorted(set(stats["query_requests_by_purpose"]) | set(stats["unique_words_by_purpose"]))
        for purpose in purposes:
            f.write(f"{key.split(':')[0]},{key.split(':')[1]},{purpose},{stats['query_requests_by_purpose'].get(purpose,0)},{stats['unique_words_by_purpose'].get(purpose,0)}\n")
with (REPORTS / "latent_context_transitions.csv").open("w") as f:
    f.write("fixture,observer,context,action,output,next_context\n")
    for key, row in suite.items():
        machine = row["learned_machine"]
        for context, transitions in machine["transitions"].items():
            for action, next_context in transitions.items():
                output = machine["outputs"][context][action]
                f.write(f"{key.split(':')[0]},{key.split(':')[1]},{context},{action},\"{json.dumps(output)}\",{next_context}\n")
for key, row in suite.items():
    (REPORTS / f"adaptive_probe_policy_{key.replace(':', '__')}.json").write_text(
        json.dumps(row["adaptive_probe_policy"], indent=2) + "\n"
    )
print(json.dumps({
    "suite": {k: {
        "predictive_contexts": v["learned_predictive_contexts"],
        "counterexamples": v["counterexamples"],
        "bounded_equivalent": v["bounded_certificate"]["bounded_equivalence"],
        "query_statistics": v["query_statistics"],
        "clock": v["clock_coordinate"],
        "active_probe": v["post_learning_diagnostic_probe"],
    } for k,v in suite.items()},
    "delayed_horizon": delayed["results"],
}, indent=2))
