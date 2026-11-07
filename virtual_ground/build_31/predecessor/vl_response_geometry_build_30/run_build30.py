#!/usr/bin/env python3
"""Build 30 experiments: adaptive observer selection and signal-coded computation."""
from __future__ import annotations
import csv, json, math, random, sys, unittest, cmath
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"notes"/"build29_workspace"))
from continuous_signal import SignalChannel, analyze_signals, write_wav_channels
from adaptive_observer import LabeledTrace, candidate_profiles, select_observer, evaluate_on_heldout
from signal_code import (Instruction, PhaseOperand, encode_program, execute_program, phase_symbol,
                         phase_domain_execute, encode_phase_operand, decode_phase_symbol,
                         encode_output_carrier)


def make_signal_trace(task: str, seed: int, *, n_events: int = 10) -> LabeledTrace:
    rng=random.Random(seed); fs=8192; hop=64
    classes=tuple(rng.randrange(4) for _ in range(n_events))
    configs=[]
    if task in ("frequency", "mixed"):
        configs.append(("frequency", [512.0, 768.0, 1152.0, 1664.0]))
    if task in ("amplitude", "mixed"):
        configs.append(("amplitude", [768.0]*4))
    channels=[]
    for ci,(kind,freqs) in enumerate(configs):
        samples=[]; gain=rng.uniform(.65,1.35)
        phases=[rng.random()*2*math.pi for _ in range(4)]
        offset=0
        for event_idx,cls in enumerate(classes):
            n=10*hop
            if kind=="frequency":
                amp=gain*rng.uniform(.88,1.12)
            else:
                amp=gain*[.22,.45,.78,1.12][cls]
            f=freqs[cls]
            attack=12
            for j in range(n):
                env=min(1.0,(j+1)/attack,(n-j)/attack)
                v=amp*env*math.sin(2*math.pi*f*(offset+j)/fs+phases[cls])
                v += .0015*rng.gauss(0,1)
                samples.append(v)
            offset+=n
        channels.append(SignalChannel(f"{task}_sensor_{ci}",fs,tuple(samples)))
    boundaries=tuple(i*10 for i in range(1,n_events))
    return LabeledTrace(f"{task}_{seed}",tuple(channels),boundaries,classes)


@lru_cache(maxsize=1)
def build_adaptive_experiment() -> dict:
    tasks={}
    for task,seed0 in (("frequency",4100),("amplitude",5100),("mixed",6100)):
        calibration=[make_signal_trace(task,seed0+i) for i in range(4)]
        heldout=[make_signal_trace(task,seed0+100+i) for i in range(4)]
        selection=select_observer(calibration, boundary_weight=.7, token_weight=.3, ambiguity_epsilon=.015)
        profile=selection["selected_profile"]
        test=evaluate_on_heldout(profile,heldout, boundary_weight=.7, token_weight=.3)
        tasks[task]={
            "calibration_trace_count":len(calibration),"heldout_trace_count":len(heldout),
            "selected_profile":profile.profile_id,
            "selected_boundary_view":profile.boundary_view,
            "selected_token_view":profile.token_view,
            "calibration_utility":selection["selected_utility"],
            "ambiguous_selection":selection["ambiguous_selection"],
            "plausible_profiles":[p.profile_id for p in selection["plausible_profiles"]],
            "heldout_boundary_f1":test.boundary_f1,
            "heldout_token_pairwise_accuracy":test.token_pairwise_accuracy,
            "heldout_utility":test.utility,
            "candidate_scores":[{"profile":s.profile.profile_id,"boundary_f1":s.boundary_f1,
                                  "token_pairwise_accuracy":s.token_pairwise_accuracy,"utility":s.utility}
                                 for s in selection["scores"]]
        }
    return {"method":"calibration-selected observer profile, frozen before held-out evaluation",
            "task_utility":"0.7 * boundary F1 + 0.3 * pairwise event-class agreement",
            "task_results":tasks,
            "limitations":["Labels used only in calibration/evaluator fixture; not unsupervised observer discovery",
                            "Synthetic signal tasks only","Fixed frame size/hop; adaptive scale is deferred",
                            "Greedy event token clustering is order-dependent as in Build 29"]}


def _boundary_metrics(predicted, expected, tolerance=2):
    remaining=set(range(len(expected))); tp=0
    for p in sorted(predicted):
        possible=[i for i in remaining if abs(int(p)-int(expected[i]))<=tolerance]
        if possible:
            j=min(possible,key=lambda i:abs(int(p)-int(expected[i])))
            remaining.remove(j);tp+=1
    fp=len(predicted)-tp;fn=len(expected)-tp
    precision=tp/(tp+fp) if tp+fp else 1.0
    recall=tp/(tp+fn) if tp+fn else 1.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {"tp":tp,"fp":fp,"fn":fn,"precision":precision,"recall":recall,"f1":f1}


@lru_cache(maxsize=1)
def build_signal_program_experiment() -> dict:
    program=[Instruction("ADD8",3,6),Instruction("SUB8",1,4),
             Instruction("ADD8",7,7),Instruction("SUB8",0,3),
             Instruction("ADD8",5,5),Instruction("SUB8",7,2)]
    encoded=encode_program(program,leading_offset=37,noise_sigma=.0015,seed=781)
    executed=execute_program(encoded)
    expected=[(x.a+x.b)%8 if x.opcode=="ADD8" else (x.a-x.b)%8 for x in program]
    # Feed the continuous FSK control waveform back through Build 29's raw
    # signal observer to measure whether generic signal events expose symbols.
    control_channel=SignalChannel("fsk_control",encoded.sample_rate,encoded.control_samples)
    expected_symbol_boundaries=[round((encoded.symbol_offset+i*encoded.frame_size)/64)
                                for i in range(1,4+2*len(program))]
    fsk_event_audit={}
    for view in ("harmonic","temporal","combined"):
        analysis=analyze_signals([control_channel],frame_size=256,hop=64,observer_view=view)
        predicted=list(analysis.selected.boundaries if analysis.selected else [])
        fsk_event_audit[view]={"predicted_boundaries":predicted,
                               **_boundary_metrics(predicted,expected_symbol_boundaries)}
    actual=[x["output_symbol"] for x in executed["results"]]
    # Exhaustive algebraic coverage: 8x8 ADD and SUB pairs.
    exhaustive={"ADD8":0,"SUB8":0,"errors":0}
    for op in ("ADD8","SUB8"):
        for a in range(8):
            for b in range(8):
                pa=encode_phase_operand(a,sample_count=128,gain=.7,phase_offset=.31,noise_sigma=0.0,seed=100+a)
                pb=encode_phase_operand(b,sample_count=128,gain=1.2,phase_offset=-1.17,noise_sigma=0.0,seed=200+b)
                z=phase_domain_execute(op,pa,pb)
                got=decode_phase_symbol(z)
                want=(a+b)%8 if op=="ADD8" else (a-b)%8
                exhaustive[op]+=1; exhaustive["errors"]+=int(got!=want)
    # Noise robustness sweep with independent channel gain/phase and complex noise.
    sweep=[]
    for sigma in (0.0,.02,.1,.5,1.0,1.5,2.0):
        errors=total=0
        for a in range(8):
            for b in range(8):
                pa=encode_phase_operand(a,sample_count=256,gain=.55+(a%4)*.2,
                    phase_offset=.23*a,noise_sigma=sigma,seed=3000+int(sigma*1000)+a)
                pb=encode_phase_operand(b,sample_count=256,gain=.65+(b%3)*.25,
                    phase_offset=-.19*b,noise_sigma=sigma,seed=4000+int(sigma*1000)+b)
                for op in ("ADD8","SUB8"):
                    got=decode_phase_symbol(phase_domain_execute(op,pa,pb))
                    want=(a+b)%8 if op=="ADD8" else (a-b)%8
                    errors+=int(got!=want); total+=1
        sweep.append({"complex_noise_sigma":sigma,"total_operations":total,"errors":errors,
                      "accuracy":1-errors/total})
    # Explicitly show why independent pilot calibration matters.
    pa=encode_phase_operand(3,sample_count=128,seed=912)
    pb=encode_phase_operand(6,sample_count=128,seed=913)
    miscalibrated=PhaseOperand(pa.signal,tuple(p*cmath.exp(1j*math.pi/4) for p in pa.pilot))
    good=decode_phase_symbol(phase_domain_execute("ADD8",pa,pb))
    bad=decode_phase_symbol(phase_domain_execute("ADD8",miscalibrated,pb))
    return {
      "scope":"finite signal-domain arithmetic over Z/8Z; not universal computation",
      "control_encoding":"16-ary orthogonal FSK, with preamble and opcode complements",
      "operand_encoding":"8-PSK complex phasors with per-channel pilot references",
      "operation_law":"z(a+b mod 8) = z(a) z(b); z(a-b mod 8) = z(a) conjugate(z(b))",
      "program_instructions":[{"opcode":x.opcode,"a":x.a,"b":x.b} for x in program],
      "expected_outputs":expected,"actual_outputs":actual,"program_correct":expected==actual,
      "decoded_control_opcodes":executed["decoded_opcodes"],
      "fsk_event_boundary_audit_via_build29":fsk_event_audit,
      "expected_fsk_symbol_boundaries_frame_indices":expected_symbol_boundaries,
      "preamble_offset_samples_recovered":executed["preamble_offset_samples"],
      "minimum_fsk_decision_margin":executed["minimum_fsk_decision_margin"],
      "phase_domain_execution_records":executed["results"],
      "exhaustive_pair_coverage":exhaustive,
      "noise_robustness":sweep,
      "pilot_calibration_control":{"expected_add8_output":1,"correct_pilot_output":good,
                                    "one_symbol_phase_miscalibration_output":bad,
                                    "calibration_required":good==1 and bad!=1},
      "interpretation":{"signal_as_data":"yes: FSK control symbols and PSK operands carry the program",
                        "signal_as_instruction":"yes within the finite declared ISA: FSK opcodes select the operation",
                        "signal_domain_computation":"yes for modular phase addition/subtraction via complex phasor transformations",
                        "universal_computation":"not demonstrated; finite Z/8Z ISA only",
                        "physical_hardware":"not tested; complex-baseband computation is a numerical signal-domain model"}
    }


def main() -> None:
    reports=ROOT/"reports"; reports.mkdir(exist_ok=True)
    adaptive=build_adaptive_experiment()
    signal_program=build_signal_program_experiment()
    # Store inspectable synthetic signal artifacts: mono FSK control plus an
    # eight-channel I/Q capture (A signal/pilot, B signal/pilot) for instruction 0.
    demo=[Instruction("ADD8",3,6),Instruction("SUB8",1,4),Instruction("ADD8",7,7),
          Instruction("SUB8",0,3),Instruction("ADD8",5,5),Instruction("SUB8",7,2)]
    encoded=encode_program(demo,leading_offset=37,noise_sigma=.0015,seed=781)
    write_wav_channels(str(ROOT/"fixtures"/"signal_program_control_fsk.wav"),encoded.sample_rate,
                       [encoded.control_samples],16)
    (oa,ob)=encoded.operand_pairs[0]
    iq_channels=[[z.real for z in oa.signal],[z.imag for z in oa.signal],
                 [z.real for z in oa.pilot],[z.imag for z in oa.pilot],
                 [z.real for z in ob.signal],[z.imag for z in ob.signal],
                 [z.real for z in ob.pilot],[z.imag for z in ob.pilot]]
    write_wav_channels(str(ROOT/"fixtures"/"instruction_0_operands_iq.wav"),encoded.sample_rate,iq_channels,16)
    pilot=encoded.output_pilots[0]
    result_z=phase_domain_execute("ADD8",oa,ob)
    output_iq=encode_output_carrier(result_z,pilot=pilot)
    write_wav_channels(str(ROOT/"fixtures"/"instruction_0_output_iq.wav"),encoded.sample_rate,
                       [[z.real for z in output_iq],[z.imag for z in output_iq]],16)
    (reports/"adaptive_observer_results.json").write_text(json.dumps(adaptive,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (reports/"signal_program_results.json").write_text(json.dumps(signal_program,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (reports/"fsk_event_boundary_audit.json").write_text(json.dumps({
        "provenance":"synthetic FSK control waveform, analyzed by Build 29 event detector",
        "views":signal_program["fsk_event_boundary_audit_via_build29"],
        "expected_symbol_boundaries_frame_indices":signal_program["expected_fsk_symbol_boundaries_frame_indices"]
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    with (reports/"adaptive_profile_scores.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["task","profile","boundary_f1","token_pairwise_accuracy","utility"])
        for task,data in adaptive["task_results"].items():
            for s in data["candidate_scores"]:
                w.writerow([task,s["profile"],s["boundary_f1"],s["token_pairwise_accuracy"],s["utility"]])
    with (reports/"signal_program_execution.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["instruction_index","opcode","a","b","expected","actual","correct"])
        for i,(ins,exp,act) in enumerate(zip(signal_program["program_instructions"],signal_program["expected_outputs"],signal_program["actual_outputs"])):
            w.writerow([i,ins["opcode"],ins["a"],ins["b"],exp,act,int(exp==act)])
    combined={"adaptive_observer":adaptive,"signal_coded_computation":signal_program,
              "provenance":"synthetic controlled fixtures only"}
    (reports/"build_30_results.json").write_text(json.dumps(combined,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"adaptive_selected":{k:v["selected_profile"] for k,v in adaptive["task_results"].items()},
                      "heldout":{k:{"boundary_f1":v["heldout_boundary_f1"],"token_accuracy":v["heldout_token_pairwise_accuracy"]} for k,v in adaptive["task_results"].items()},
                      "signal_program_correct":signal_program["program_correct"],
                      "exhaustive_errors":signal_program["exhaustive_pair_coverage"]["errors"],
                      "noise":signal_program["noise_robustness"]},indent=2))

if __name__=="__main__": main()
