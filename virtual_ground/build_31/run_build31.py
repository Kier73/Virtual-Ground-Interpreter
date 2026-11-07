#!/usr/bin/env python3
"""Build 31 reproducible experiments and reports (standard-library only)."""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRED = ROOT / "predecessor" / "vl_response_geometry_build_30"
sys.path.insert(0, str(PRED))
sys.path.insert(0, str(ROOT))

from build31_signal import (  # noqa: E402
    OBSERVER_UNITS,
    ChannelSpec,
    SignalState,
    apply_channel,
    binary_signal_operation,
    decode_state,
    encode_state,
    make_pilot,
    phase_residual,
    reframe_state,
    recover_phase_symbol,
    signal_chain,
    signal_state_summary,
    symbolic_chain,
)
from signal_code import phase_symbol  # noqa: E402


OPS = ("ADD8", "SUB8")
PATTERNS = (("ADD8", "ADD8"), ("ADD8", "SUB8"),
            ("SUB8", "ADD8"), ("SUB8", "SUB8"))


def phasor_distance(a: complex, b: complex) -> float:
    return abs(a / abs(a) - b / abs(b))


def experiment_observer_isomorphisms() -> dict:
    rows = []
    total = errors = 0
    for u in OBSERVER_UNITS:
        for value in range(8):
            state = encode_state(value, observer=u, sample_count=64,
                                 gain=0.73 + 0.11 * value,
                                 phase_offset=0.17 * value - 0.3,
                                 seed=1000 + 10 * u + value)
            recovered = decode_state(state)
            total += 1
            errors += recovered != value
        # Coordinate-transform round trips for every semantic state.
        roundtrip_errors = 0
        for value in range(8):
            original = encode_state(value, observer=u, sample_count=64, seed=2000 + value)
            for v in OBSERVER_UNITS:
                transformed = reframe_state(original, v)
                restored = reframe_state(transformed, u)
                roundtrip_errors += decode_state(restored) != value
        rows.append({"observer_unit": u, "symbol_roundtrip_errors": sum(
            decode_state(encode_state(v, observer=u, sample_count=32, seed=3000+v)) != v
            for v in range(8)), "cross_coordinate_roundtrip_errors": roundtrip_errors,
            "inverse_unit": next(v for v in OBSERVER_UNITS if (u*v) % 8 == 1)})
    return {"observer_units": list(OBSERVER_UNITS), "tested_values_per_observer": 8,
            "symbol_cases": total, "symbol_errors": errors,
            "coordinate_roundtrips": len(OBSERVER_UNITS) * 8 * len(OBSERVER_UNITS),
            "coordinate_roundtrip_errors": sum(r["cross_coordinate_roundtrip_errors"] for r in rows),
            "per_observer": rows,
            "law": "chi_u(k)=exp(2*pi*i*u*k/8), u in units(Z/8Z); reframing u->v applies z^(v*u^-1 mod 8)"}


def experiment_binary_closure() -> dict:
    total = errors = 0
    per_observer = {}
    for u in OBSERVER_UNITS:
        by_op = {}
        for op in OPS:
            count = op_errors = 0
            for a in range(8):
                for b in range(8):
                    sa = encode_state(a, observer=u, sample_count=64,
                                      gain=0.7 + 0.03 * a, phase_offset=0.19 * a,
                                      seed=4000 + u*100 + a)
                    sb = encode_state(b, observer=u, sample_count=64,
                                      gain=1.1 + 0.02 * b, phase_offset=-0.13 * b,
                                      seed=5000 + u*100 + b)
                    out = binary_signal_operation(op, sa, sb, output_observer=u,
                                                  output_pilot=make_pilot(64, gain=0.9,
                                                                          phase_offset=0.21))
                    got = decode_state(out)
                    want = (a+b) % 8 if op == "ADD8" else (a-b) % 8
                    count += 1
                    op_errors += got != want
            by_op[op] = {"cases": count, "errors": op_errors}
            total += count
            errors += op_errors
        per_observer[str(u)] = by_op
    return {"total_cases": total, "errors": errors, "per_observer": per_observer,
            "coverage": "4 observer coordinates x 2 operations x 8 x 8 operand pairs"}


def experiment_commuting_diagram() -> dict:
    total = errors = 0
    maximum_phasor_error = 0.0
    for u in OBSERVER_UNITS:
        for op in OPS:
            for a in range(8):
                for b in range(8):
                    a1 = encode_state(a, observer=1, sample_count=32, seed=6100+a)
                    b1 = encode_state(b, observer=1, sample_count=32, seed=6200+b)
                    left = binary_signal_operation(op, a1, b1, output_observer=1)
                    left_reframed = reframe_state(left, u)
                    au = reframe_state(a1, u)
                    bu = reframe_state(b1, u)
                    right = binary_signal_operation(op, au, bu, output_observer=u)
                    zl = recover_phase_symbol(left_reframed.operand)
                    zr = recover_phase_symbol(right.operand)
                    maximum_phasor_error = max(maximum_phasor_error, phasor_distance(zl, zr))
                    total += 1
                    errors += decode_state(left_reframed) != decode_state(right)
    return {"cases": total, "semantic_commutation_errors": errors,
            "maximum_unit_phasor_distance": maximum_phasor_error,
            "property": "R_u(F(x,y)) = F(R_u(x),R_u(y)) for R_u(z)=z^u"}


def experiment_composed_execution() -> dict:
    total = errors = 0
    per_pattern = {}
    for pattern_index, (op1, op2) in enumerate(PATTERNS):
        count = pattern_errors = 0
        for a in range(8):
            for b in range(8):
                for c in range(8):
                    # Inputs deliberately use different coordinate systems.
                    ua = OBSERVER_UNITS[(a + pattern_index) % 4]
                    ub = OBSERVER_UNITS[(b + 2*pattern_index + 1) % 4]
                    uc = OBSERVER_UNITS[(c + 3*pattern_index + 2) % 4]
                    mid = OBSERVER_UNITS[(a + b + pattern_index) % 4]
                    out_obs = OBSERVER_UNITS[(a + 2*b + c + pattern_index) % 4]
                    sa = encode_state(a, observer=ua, sample_count=32, seed=7000 + a)
                    sb = encode_state(b, observer=ub, sample_count=32, seed=7100 + b)
                    sc = encode_state(c, observer=uc, sample_count=32, seed=7200 + c)
                    result = signal_chain(
                        sa, sb, sc, op1, op2,
                        intermediate_observer=mid, output_observer=out_obs,
                        intermediate_pilot=make_pilot(32, gain=0.83, phase_offset=0.17),
                        output_pilot=make_pilot(32, gain=1.17, phase_offset=-0.31),
                        seed=8000 + a*64 + b*8 + c,
                    )
                    got = decode_state(result)
                    want = symbolic_chain(a, b, c, op1, op2)
                    count += 1
                    pattern_errors += got != want
        per_pattern[f"{op1}->{op2}"] = {"cases": count, "errors": pattern_errors}
        total += count
        errors += pattern_errors
    return {"total_chains": total, "errors": errors,
            "triple_domain": "all 8^3=512 triples for each of four two-opcode sequences",
            "observer_switching": "each input, intermediate, and final state may use a different odd-unit coordinate",
            "per_pattern": per_pattern}


def experiment_reversibility() -> dict:
    total = errors = 0
    # ADD(a,b) then SUB(result,b) recovers a; SUB(a,b) then ADD(result,b) recovers a.
    for u in OBSERVER_UNITS:
        for a in range(8):
            for b in range(8):
                sa = encode_state(a, observer=u, sample_count=48, seed=9000+a)
                sb = encode_state(b, observer=u, sample_count=48, seed=9100+b)
                for first, second in (("ADD8", "SUB8"), ("SUB8", "ADD8")):
                    intermediate = binary_signal_operation(first, sa, sb, output_observer=u)
                    restored = binary_signal_operation(second, intermediate, sb, output_observer=u)
                    total += 1
                    errors += decode_state(restored) != a
    return {"roundtrips": total, "errors": errors,
            "scope": "inverse group translation with the second operand retained as an input state"}


def experiment_channel_calibration() -> dict:
    # Common gain and phase applied equally to signal and pilot should cancel.
    common_cases = 0
    common_errors = 0
    for i in range(32):
        s = encode_state(i % 8, observer=1, sample_count=64, seed=10000+i)
        h = ChannelSpec(gain=0.2 + 0.13*i, phase=-2.8 + 0.17*i, seed=11000+i)
        got = decode_state(apply_channel(s, h))
        common_cases += 1
        common_errors += got != i % 8

    # Explicit calibration offsets propagate additively/subtractively through a chain.
    def run_drift(d_a: float, d_b: float, d_mid: float, d_c: float) -> dict:
        a = apply_channel(encode_state(3, sample_count=128, seed=12001),
                          ChannelSpec(calibration_error=d_a, seed=12101))
        b = apply_channel(encode_state(6, sample_count=128, seed=12002),
                          ChannelSpec(calibration_error=d_b, seed=12102))
        c = apply_channel(encode_state(2, sample_count=128, seed=12003),
                          ChannelSpec(calibration_error=d_c, seed=12103))
        middle = binary_signal_operation("ADD8", a, b, output_observer=1,
                                         output_pilot=make_pilot(128, phase_offset=0.4))
        middle = apply_channel(middle, ChannelSpec(calibration_error=d_mid, seed=12104))
        result = binary_signal_operation("SUB8", middle, c, output_observer=1,
                                         output_pilot=make_pilot(128, phase_offset=-0.2))
        observed_z = recover_phase_symbol(result.operand)
        exact_z = phase_symbol(7)
        predicted = d_a + d_b + d_mid - d_c
        measured = phase_residual(exact_z, observed_z)
        return {"input_a_error_rad": d_a, "input_b_error_rad": d_b,
                "intermediate_error_rad": d_mid, "input_c_error_rad": d_c,
                "predicted_output_phase_error_rad": predicted,
                "measured_output_phase_error_rad": measured,
                "absolute_model_residual_rad": abs(math.atan2(math.sin(measured-predicted), math.cos(measured-predicted))),
                "decoded_output": decode_state(result), "expected_output": 7,
                "correct": decode_state(result) == 7}

    drift_rows = [
        run_drift(0.0, 0.0, 0.0, 0.0),
        run_drift(0.05, 0.10, 0.04, 0.02),
        run_drift(0.12, 0.09, 0.08, 0.03),
        run_drift(0.25, 0.20, 0.15, 0.02),
        run_drift(0.45, 0.0, 0.0, 0.0),
    ]
    return {"common_gain_phase": {"cases": common_cases, "errors": common_errors,
                                  "invariance": "same scalar complex multiplier on signal and pilot cancels"},
            "calibration_drift_chain": drift_rows,
            "decision_half_width_rad": math.pi / 8,
            "propagation_law": "ADD residuals add; SUB residuals subtract; fresh stage calibration contributes its own residual"}


def experiment_noise_sweep() -> dict:
    levels = (0.0, 0.02, 0.10, 0.25, 0.50, 1.0, 1.5, 2.0)
    rows = []
    for level_index, sigma in enumerate(levels):
        total = errors = failures = 0
        for pattern_index, (op1, op2) in enumerate(PATTERNS):
            for a in range(8):
                for b in range(8):
                    for c in range(8):
                        base_seed = 130000 + level_index*100000 + pattern_index*10000 + a*512+b*8+c
                        try:
                            sa = encode_state(a, sample_count=64, noise_sigma=sigma,
                                              gain=0.8, phase_offset=0.23*a, seed=base_seed+1)
                            sb = encode_state(b, sample_count=64, noise_sigma=sigma,
                                              gain=1.1, phase_offset=-0.19*b, seed=base_seed+2)
                            sc = encode_state(c, sample_count=64, noise_sigma=sigma,
                                              gain=0.9, phase_offset=0.11*c, seed=base_seed+3)
                            out = signal_chain(
                                sa, sb, sc, op1, op2,
                                intermediate_pilot=make_pilot(64, gain=0.95, phase_offset=0.31),
                                output_pilot=make_pilot(64, gain=1.05, phase_offset=-0.27),
                                intermediate_noise_sigma=sigma,
                                output_noise_sigma=sigma,
                                seed=base_seed+4,
                            )
                            got = decode_state(out)
                            want = symbolic_chain(a, b, c, op1, op2)
                            errors += got != want
                        except Exception:  # Record erasures/failures as errors.
                            failures += 1
                            errors += 1
                        total += 1
        rows.append({"complex_noise_sigma_per_component": sigma,
                     "chains": total, "errors": errors, "erasures": failures,
                     "accuracy_including_erasures": 1 - errors/total})
    return {"sample_count_per_state": 64,
            "noise_model": "independent additive Gaussian I/Q noise on payload samples at input and both emitted stages; pilot is reference path",
            "results": rows,
            "warning": "Synthetic baseband channel only; sigma is in the same units as unit-amplitude complex samples."}


def experiment_performance() -> dict:
    # Timing is diagnostic only: signal-array software versus integer arithmetic.
    a = encode_state(3, sample_count=128, seed=14001)
    b = encode_state(6, sample_count=128, seed=14002)
    c = encode_state(2, sample_count=128, seed=14003)
    p1, p2 = make_pilot(128, phase_offset=0.13), make_pilot(128, phase_offset=-0.24)
    loops = 120
    signal_times = []
    integer_times = []
    for _ in range(5):
        t0 = time.perf_counter()
        for j in range(loops):
            signal_chain(a, b, c, "ADD8", "SUB8", intermediate_pilot=p1,
                         output_pilot=p2, seed=j)
        signal_times.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        for _j in range(loops):
            av, bv, cv = decode_state(a), decode_state(b), decode_state(c)
            (av + bv) % 8
            # Apply SUB8 to the first result; this is an integer baseline.
            # The expression is kept explicit to avoid timing a precomputed result.
            result = ((av + bv) % 8 - cv) % 8
            # Re-encode the final result so both paths return a signal state.
            encode_state(result, sample_count=128, seed=_j)
        integer_times.append(time.perf_counter() - t0)
    signal_med = statistics.median(signal_times) / loops
    integer_med = statistics.median(integer_times) / loops
    return {"loops_per_repeat": loops, "repeats": 5,
            "signal_chain_median_seconds_per_chain": signal_med,
            "decode_compute_reencode_median_seconds_per_chain": integer_med,
            "ratio_signal_to_decode_compute_reencode": signal_med / integer_med if integer_med else None,
            "scope": "Python complex-sample simulation only; not analog hardware, energy, throughput, or optimized implementation evidence"}


def write_example_chain_trace(path: Path) -> None:
    """Record one cross-observer execution without decoding its intermediate."""
    a = encode_state(3, observer=1, sample_count=128, seed=16001)
    b = encode_state(6, observer=3, sample_count=128, seed=16002)
    c = encode_state(2, observer=5, sample_count=128, seed=16003)
    middle = binary_signal_operation(
        "ADD8", a, b, output_observer=7,
        output_pilot=make_pilot(128, gain=0.91, phase_offset=0.22), seed=16101)
    middle_summary = signal_state_summary(middle)
    final = binary_signal_operation(
        "SUB8", middle, c, output_observer=3,
        output_pilot=make_pilot(128, gain=1.08, phase_offset=-0.19), seed=16102)
    final_z = recover_phase_symbol(final.operand)
    payload = {
        "example": "ADD8(3,6) then SUB8(intermediate,2) modulo 8",
        "input_states": [
            {"label": "a", "observer": a.observer, "sample_count": len(a.operand.signal)},
            {"label": "b", "observer": b.observer, "sample_count": len(b.operand.signal)},
            {"label": "c", "observer": c.observer, "sample_count": len(c.operand.signal)},
        ],
        "stage_1": {"opcode": "ADD8", "output_observer": middle.observer,
                    "signal_summary": middle_summary,
                    "integer_decode_performed": False},
        "stage_2": {"opcode": "SUB8", "output_observer": final.observer,
                    "signal_summary": signal_state_summary(final),
                    "terminal_phasor_real": final_z.real,
                    "terminal_phasor_imag": final_z.imag,
                    "terminal_decoded_value": decode_state(final),
                    "expected_value": 7,
                    "correct": decode_state(final) == 7},
        "observer_path": [1, 3, 7, 5, 3],
        "note": "Only the terminal result is decoded into an integer; the intermediate remains a calibrated signal state.",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_chain_fixture(path: Path) -> None:
    """Write inspectable CSV with input, intermediate, and output I/Q samples."""
    a = encode_state(3, sample_count=128, seed=15001)
    b = encode_state(6, sample_count=128, seed=15002)
    c = encode_state(2, sample_count=128, seed=15003)
    mid = binary_signal_operation("ADD8", a, b, output_pilot=make_pilot(128, phase_offset=0.2))
    out = binary_signal_operation("SUB8", mid, c, output_pilot=make_pilot(128, phase_offset=-0.3))
    columns = {}
    for name, state in (("a", a), ("b", b), ("c", c), ("intermediate", mid), ("output", out)):
        columns[f"{name}_signal_i"] = [x.real for x in state.operand.signal]
        columns[f"{name}_signal_q"] = [x.imag for x in state.operand.signal]
        columns[f"{name}_pilot_i"] = [x.real for x in state.operand.pilot]
        columns[f"{name}_pilot_q"] = [x.imag for x in state.operand.pilot]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sample_index", *columns.keys()])
        for i in range(128):
            writer.writerow([i, *(columns[k][i] for k in columns)])


def main() -> None:
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    result = {
        "build": 31,
        "title": "Compositional Signal Algebra and Observer-Coordinate Interchange",
        "scope": "finite signal-domain computation over Z/8Z using simulated complex-baseband arrays",
        "observer_isomorphisms": experiment_observer_isomorphisms(),
        "binary_operation_closure": experiment_binary_closure(),
        "observer_operation_commutation": experiment_commuting_diagram(),
        "composed_execution": experiment_composed_execution(),
        "reversibility": experiment_reversibility(),
        "channel_calibration": experiment_channel_calibration(),
        "noise_sweep": experiment_noise_sweep(),
        "software_performance_diagnostic": experiment_performance(),
        "verification_contracts": {
            "encoding": "chi_u(k) = exp(2*pi*i*u*k/8), u in {1,3,5,7}",
            "homomorphism": "chi_u(a+b) = chi_u(a)*chi_u(b)",
            "subtraction": "chi_u(a-b) = chi_u(a)*conjugate(chi_u(b))",
            "reframing": "R_(u->v)(z)=z^(v*u^-1 mod 8)",
            "operation_naturality": "R(F_u(x,y)) = F_v(R(x),R(y))",
            "composition": "if each transition preserves chi_u semantics, their composition preserves the composed Z/8Z expression",
            "terminal_decode": "semantic integer decoding occurs only at final observation / test oracle",
        },
        "limitations": [
            "Synthetic numerical complex-baseband simulation; no physical analog hardware was constructed or measured.",
            "The finite state group is Z/8Z; this does not establish universal or Turing-complete computation.",
            "The observer-coordinate family is the four automorphisms of this cyclic group, not arbitrary sensor or model representations.",
            "The scalar channel model does not include multipath, carrier-frequency offset, nonlinear distortion, or clock drift.",
            "Noise measurements are specific to the chosen sample count, pilot, and generated Gaussian distribution.",
            "The performance comparison is Python implementation timing, not a fair hardware comparison or evidence of speed/energy benefit.",
            "Reversibility applies to group translations when the second operand is retained; arbitrary branching and state erasure are not shown reversible.",
        ],
    }
    (reports / "build_31_results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (reports / "noise_sweep.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["complex_noise_sigma_per_component", "chains", "errors", "erasures", "accuracy"])
        for row in result["noise_sweep"]["results"]:
            w.writerow([row["complex_noise_sigma_per_component"], row["chains"], row["errors"],
                        row["erasures"], row["accuracy_including_erasures"]])
    with (reports / "calibration_drift.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["delta_a_rad", "delta_b_rad", "delta_intermediate_rad", "delta_c_rad",
                    "predicted_output_rad", "measured_output_rad", "decoded", "correct"])
        for row in result["channel_calibration"]["calibration_drift_chain"]:
            w.writerow([row["input_a_error_rad"], row["input_b_error_rad"],
                        row["intermediate_error_rad"], row["input_c_error_rad"],
                        row["predicted_output_phase_error_rad"], row["measured_output_phase_error_rad"],
                        row["decoded_output"], int(row["correct"])])
    with (reports / "observer_coordinates.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["observer_unit", "inverse_unit", "symbol_roundtrip_errors", "coordinate_roundtrip_errors"])
        for row in result["observer_isomorphisms"]["per_observer"]:
            w.writerow([row["observer_unit"], row["inverse_unit"], row["symbol_roundtrip_errors"],
                        row["cross_coordinate_roundtrip_errors"]])
    write_chain_fixture(ROOT / "fixtures" / "chain_3_6_2_iq.csv")
    write_example_chain_trace(reports / "example_chain_trace.json")
    print(json.dumps({
        "observer_symbol_errors": result["observer_isomorphisms"]["symbol_errors"],
        "observer_reframe_errors": result["observer_isomorphisms"]["coordinate_roundtrip_errors"],
        "binary_cases": result["binary_operation_closure"]["total_cases"],
        "binary_errors": result["binary_operation_closure"]["errors"],
        "commuting_cases": result["observer_operation_commutation"]["cases"],
        "commuting_errors": result["observer_operation_commutation"]["semantic_commutation_errors"],
        "composed_chains": result["composed_execution"]["total_chains"],
        "composition_errors": result["composed_execution"]["errors"],
        "reversible_roundtrips": result["reversibility"]["roundtrips"],
        "reversibility_errors": result["reversibility"]["errors"],
        "calibration_drift": result["channel_calibration"]["calibration_drift_chain"],
        "noise_sweep": result["noise_sweep"]["results"],
        "performance": result["software_performance_diagnostic"],
    }, indent=2))


if __name__ == "__main__":
    main()
