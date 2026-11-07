#!/usr/bin/env python3
"""Run Build 29 synthetic continuous-signal-to-event experiments."""
from __future__ import annotations
import csv, json, math, random, sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from continuous_signal import SignalChannel, analyze_signals, analysis_to_dict, event_tokens_for_build28, write_wav_channels, read_wav_channels


def make_trace(trace_id: str, classes: list[int], seed: int, *, gain: float=1.0, noise: float=.004,
               second_gain: float=.58, duration_jitter: bool=True) -> tuple[list[SignalChannel],list[int],list[int]]:
    rng=random.Random(seed); fs=8192; hop=64
    freqs_a=[512.0,768.0,1152.0,1664.0]
    freqs_b=[640.0,896.0,1280.0,1920.0]
    phases=[rng.random()*2*math.pi for _ in range(4)]
    samples_a=[]; samples_b=[]; truth=[]; starts=[0]; offset=0
    for idx, cls in enumerate(classes):
        frames=10 + (rng.choice([-1,0,1]) if duration_jitter else 0)
        n=frames*hop
        if idx>0: truth.append(offset)
        amp=gain*rng.uniform(.78,1.22)
        amp_b=second_gain*rng.uniform(.86,1.14)
        ph_a=phases[cls]; ph_b=phases[cls]+.37
        # Small attack/release envelope; boundaries are not directly encoded.
        attack=max(8,int(.06*n))
        for j in range(n):
            env=min(1.0,(j+1)/attack,(n-j)/attack)
            t=(offset+j)/fs
            va=amp*env*math.sin(2*math.pi*freqs_a[cls]*t+ph_a)
            vb=amp_b*env*math.sin(2*math.pi*freqs_b[cls]*t+ph_b)
            va += noise*rng.gauss(0,1); vb += noise*rng.gauss(0,1)
            samples_a.append(va); samples_b.append(vb)
        offset += n; starts.append(offset)
    channels=[SignalChannel(f"{trace_id}_sensor_a",fs,tuple(samples_a)),SignalChannel(f"{trace_id}_sensor_b",fs,tuple(samples_b))]
    return channels,truth,classes



def make_amplitude_trace(trace_id: str="amp_trace", seed: int=771) -> tuple[list[SignalChannel],list[int],list[int]]:
    rng=random.Random(seed); fs=8192; hop=64
    levels=[.22,.45,.78,1.12]
    classes=[0,1,2,3,0,2,1,3,0]
    samples=[]; bounds=[]; offset=0; freq=768.0
    for idx,cls in enumerate(classes):
        n=10*hop
        if idx>0: bounds.append(offset)
        amp=levels[cls]
        ph=.27*idx
        attack=12
        for j in range(n):
            env=min(1.0,(j+1)/attack,(n-j)/attack)
            t=(offset+j)/fs
            samples.append(amp*env*math.sin(2*math.pi*freq*t+ph)+.0015*rng.gauss(0,1))
        offset+=n
    return [SignalChannel(trace_id,fs,tuple(samples))],bounds,classes


def make_weak_amplitude_trace(seed: int=772) -> tuple[list[SignalChannel],list[int]]:
    rng=random.Random(seed); fs=8192; hop=64
    levels=[.30,.34,.38,.42,.46,.50,.54,.58]
    samples=[];bounds=[];offset=0
    for i,amp in enumerate(levels):
        if i: bounds.append(offset)
        for j in range(14*hop):
            env=min(1.0,(j+1)/12,(14*hop-j)/12)
            samples.append(amp*env*math.sin(2*math.pi*768*(offset+j)/fs)+.001*rng.gauss(0,1))
        offset+=14*hop
    return [SignalChannel("weak_amplitude",fs,tuple(samples))],bounds

def match_boundaries(pred: list[int], truth: list[int], tolerance: int=2) -> dict[str,float|int]:
    remaining=set(range(len(truth))); tp=0
    for p in sorted(pred):
        possible=[i for i in remaining if abs(p-truth[i])<=tolerance]
        if possible:
            j=min(possible,key=lambda i:abs(p-truth[i])); remaining.remove(j); tp+=1
    fp=len(pred)-tp; fn=len(truth)-tp
    precision=tp/(tp+fp) if tp+fp else (1.0 if not truth else 0.0)
    recall=tp/(tp+fn) if tp+fn else 1.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {"tp":tp,"fp":fp,"fn":fn,"precision":precision,"recall":recall,"f1":f1}


def pairwise_token_purity(tokens_by_trace: list[list[str]], classes_by_trace: list[list[int]]) -> dict[str,float]:
    same=tot=correct=0
    for toks,clss in zip(tokens_by_trace,classes_by_trace):
        for i in range(min(len(toks),len(clss))):
            for j in range(i+1,min(len(toks),len(clss))):
                if clss[i]==clss[j]:
                    same+=1; correct += int(toks[i]==toks[j])
                else:
                    tot+=1; correct += int(toks[i]!=toks[j])
    return {"pairwise_agreement":correct/max(1,same+tot),"same_class_pairs":same,"different_class_pairs":tot}


def build_corpus() -> tuple[list[dict[str,Any]],dict[str,Any]]:
    classes=[
      [0,1,2,3,0,2,1,3,0,1],
      [1,2,3,0,1,3,2,0,1,2],
      [2,3,0,1,2,0,3,1,2,3],
      [3,0,1,2,3,1,0,2,3,0],
      [0,2,0,3,1,2,1,3,0,2],
      [1,3,1,0,2,3,2,0,1,3],
      [2,0,2,1,3,0,3,1,2,0],
      [3,1,3,2,0,1,0,2,3,1],
      [0,1,0,2,3,1,3,2,0,1],
      [2,3,2,0,1,3,1,0,2,3],
      [1,0,1,3,2,0,2,3,1,0],
      [3,2,3,1,0,2,0,1,3,2],
    ]
    out=[]; truths=[]
    for i,seq in enumerate(classes):
        ch,bounds,cls=make_trace(f"trace_{i:02d}",seq,seed=9100+i,gain=[.7,1,1.3][i%3],noise=.003+(i%2)*.001)
        out.append({"trace_id":f"trace_{i:02d}","channels":ch,"truth_boundaries_samples":bounds,"truth_classes":cls})
        truths.append({"trace_id":f"trace_{i:02d}","boundaries_samples":bounds,"classes":cls})
    return out,{"description":"synthetic evaluator-only truth; never passed to learner", "traces":truths}


def main() -> None:
    outdir=ROOT/"reports"; outdir.mkdir(exist_ok=True)
    corpus,truth=build_corpus(); analyses=[]; predrows=[]; token_rows=[]; tokens_by=[]; classes_by=[]
    summary=[]
    for item in corpus:
        ana=analyze_signals(item["channels"],frame_size=256,hop=64,observer_view="combined",token_tolerance=.075)
        analyses.append(ana)
        selected=ana.selected
        pred=[b for b in (selected.boundaries if selected else [])]
        truth_frames=[round(x/64) for x in item["truth_boundaries_samples"]]
        metrics=match_boundaries(pred,truth_frames,tolerance=2)
        toks=event_tokens_for_build28(ana)
        tokens_by.append(toks); classes_by.append(item["truth_classes"])
        summary.append({"trace_id":item["trace_id"],"true_boundaries":len(truth_frames),"predicted_boundaries":len(pred),**metrics,"token_count":len(toks)})
        for p in pred: predrows.append({"trace_id":item["trace_id"],"predicted_boundary_frame":p})
        for i,tok in enumerate(toks): token_rows.append({"trace_id":item["trace_id"],"event_index":i,"opaque_token":tok})
    total_tp=sum(int(x["tp"]) for x in summary); total_fp=sum(int(x["fp"]) for x in summary); total_fn=sum(int(x["fn"]) for x in summary)
    p=total_tp/(total_tp+total_fp) if total_tp+total_fp else 0
    r=total_tp/(total_tp+total_fn) if total_tp+total_fn else 0
    f1=2*p*r/(p+r) if p+r else 0
    token_metrics=pairwise_token_purity(tokens_by,classes_by)
    # Gain and noise controls on a common source trace; gain-invariant harmonic observer should retain boundaries.
    base_channels=corpus[0]["channels"]
    scaled=[SignalChannel(c.name,c.sample_rate,tuple(.35*x for x in c.samples)) for c in base_channels]
    base_an=analyze_signals(base_channels,observer_view="harmonic")
    scaled_an=analyze_signals(scaled,observer_view="harmonic")
    base_bounds=list(base_an.selected.boundaries if base_an.selected else [])
    scaled_bounds=list(scaled_an.selected.boundaries if scaled_an.selected else [])
    gain_control={"base_boundaries":base_bounds,"scaled_boundaries":scaled_bounds,"boundary_sets_equal":base_bounds==scaled_bounds}
    # Noise-only and stationary tone controls.
    fs=8192;n=8192;rng=random.Random(440)
    noise=[.05*rng.gauss(0,1) for _ in range(n)]
    tone=[.3*math.sin(2*math.pi*512*i/fs) for i in range(n)]
    noise_ana=analyze_signals([SignalChannel("noise",fs,tuple(noise))],observer_view="harmonic")
    tone_ana=analyze_signals([SignalChannel("tone",fs,tuple(tone))],observer_view="harmonic")
    controls={"noise_candidate_count":len(noise_ana.candidates),"noise_selected_boundary_count":len(noise_ana.selected.boundaries if noise_ana.selected else []),"stationary_tone_candidate_count":len(tone_ana.candidates),"stationary_tone_selected_boundary_count":len(tone_ana.selected.boundaries if tone_ana.selected else [])}
    # Feed signal-derived opaque event tokens to the actual Build 28 motif miner.
    sys.path.insert(0,str(ROOT/"notes"/"build28_workspace"))
    from stream_ground import ContinuousTrace,Checkpoint,mine_motifs,segment_stream
    traces=[]
    for i,toks in enumerate(tokens_by):
        if not toks: continue
        traces.append(ContinuousTrace(f"signal_{i:02d}",tuple(toks),(Checkpoint(0,(0,)),Checkpoint(len(toks),(0,)))))
    train_traces=traces[:-2]
    heldout_trace=traces[-2:]
    motifs,nested=mine_motifs(train_traces,min_len=2,max_len=4,min_occurrences=3,min_trace_support=2)
    motif_report=[m.as_dict() for m in motifs]
    heldout_tokens=tokens_by[-2:]
    motif_predictions=[]
    for t in heldout_trace:
        seg=segment_stream(t,motifs,top_k=4)
        motif_predictions.append({"trace_id":t.trace_id,"status":seg.status,"alternatives":[a.as_dict() for a in seg.alternatives]})
    # Representation comparison on frequency-coded signals.
    view_metrics={}
    for view in ("harmonic","temporal","combined"):
        vtp=vfp=vfn=0
        for item in corpus:
            va=analyze_signals(item["channels"],observer_view=view)
            vb=list(va.selected.boundaries if va.selected else [])
            vm=match_boundaries(vb,[round(x/64) for x in item["truth_boundaries_samples"]],2)
            vtp+=vm["tp"];vfp+=vm["fp"];vfn+=vm["fn"]
        vp=vtp/(vtp+vfp) if vtp+vfp else 0;vr=vtp/(vtp+vfn) if vtp+vfn else 0
        view_metrics[view]={"tp":vtp,"fp":vfp,"fn":vfn,"precision":vp,"recall":vr,"f1":2*vp*vr/(vp+vr) if vp+vr else 0}
    amp_channels,amp_truth,amp_classes=make_amplitude_trace()
    amp_views={}
    for view in ("harmonic","temporal","combined"):
        aa=analyze_signals(amp_channels,observer_view=view,token_view="temporal")
        ab=list(aa.selected.boundaries if aa.selected else [])
        am=match_boundaries(ab,[round(x/64) for x in amp_truth],2)
        amp_views[view]={**am,"predicted_boundaries":ab,"candidate_count":len(aa.candidates)}
    # Phase-only boundary fixture: fixed carrier and fixed envelope, phase jumps.
    fs=8192;hop=64; n_events=8; phase_samples=[]; phase_truth=[]; offset=0
    for j in range(n_events):
        if j: phase_truth.append(offset)
        phase=0.0 if j%2==0 else math.pi/2
        for k in range(10*hop):
            phase_samples.append(.4*math.sin(2*math.pi*640*(offset+k)/fs+phase))
        offset+=10*hop
    phase_channels=[SignalChannel("phase_only",fs,tuple(phase_samples))]
    phase_views={}
    for view in ("harmonic","temporal","combined"):
        pa=analyze_signals(phase_channels,observer_view=view)
        pb=list(pa.selected.boundaries if pa.selected else [])
        pm=match_boundaries(pb,[round(x/hop) for x in phase_truth],2)
        phase_views[view]={**pm,"predicted_boundaries":pb}
    # Weak-signal threshold alternatives: retain multiple plausible segmentations.
    weak_channels,weak_truth=make_weak_amplitude_trace()
    weak_analysis=analyze_signals(weak_channels,observer_view="temporal",token_view="temporal")
    weak_hypotheses={}
    for h in weak_analysis.hypotheses:
        hm=match_boundaries(list(h.boundaries),[round(x/64) for x in weak_truth],2)
        weak_hypotheses[h.threshold_name]={"boundaries":list(h.boundaries),**hm}
    # Compare harmonic-invariant vs temporal marks on amplitude-coded events.
    amplitude_tokens={}
    for token_view in ("harmonic","temporal","combined"):
        at=analyze_signals(amp_channels,observer_view="temporal",token_view=token_view)
        amplitude_tokens[token_view]={"token_count":len(at.selected.segments) if at.selected else 0,
                                     "tokens":event_tokens_for_build28(at),
                                     "vocabulary_size":len(at.vocabulary)}
    # Exercise the raw multi-channel WAV path on a small synthetic trace.
    fixture_dir=ROOT/"fixtures";fixture_dir.mkdir(exist_ok=True)
    wav_path=fixture_dir/"synthetic_dual_sensor.wav"
    write_wav_channels(str(wav_path),8192,[corpus[0]["channels"][0].samples,corpus[0]["channels"][1].samples],bits=16)
    wav_fs,wav_channels=read_wav_channels(str(wav_path))
    wav_analysis=analyze_signals(wav_channels,observer_view="combined")
    wav_ingest={"sample_rate_hz":wav_fs,"channel_count":len(wav_channels),"sample_count_per_channel":len(wav_channels[0].samples),
                "selected_boundary_count":len(wav_analysis.selected.boundaries if wav_analysis.selected else []),"synthetic_fixture":True}
    # Detailed per-trace output: truth keys are isolated under evaluator_truth_only.
    result={"build":"29","provenance":"synthetic_fixture_only","trace_count":len(corpus),"sample_rate_hz":8192,"frame_size":256,"hop":64,
            "boundary_micro_metrics":{"tp":total_tp,"fp":total_fp,"fn":total_fn,"precision":p,"recall":r,"f1":f1},
            "observer_view_comparison":view_metrics,"amplitude_only_event_view_comparison":amp_views,"phase_only_event_view_comparison":phase_views,
            "weak_signal_segmentation_alternatives":weak_hypotheses,"amplitude_event_token_views":amplitude_tokens,"raw_wav_ingestion":wav_ingest,
            "per_trace_boundary_metrics":summary,"token_class_pairwise_metrics":token_metrics,
            "gain_invariance_control":gain_control,"negative_controls":controls,
            "build28_motif_training_traces":len(train_traces),"build28_motif_heldout_traces":len(heldout_trace),
            "build28_motif_count":len(motifs),"build28_motifs":motif_report,"heldout_build28_segmentations":motif_predictions,
            "limitations":["Synthetic data only","Threshold segmentation is an observer hypothesis, not a ground-truth event ontology","Boundary labels are evaluator-only","Exact token clustering is finite and view-dependent","Aligned sample rates/lengths required for fusion","Motif association is not causal validation"]}
    (outdir/"build_29_results.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    (outdir/"synthetic_truth_only.json").write_text(json.dumps(truth,indent=2),encoding="utf-8")
    all_analyses={item["trace_id"]:analysis_to_dict(a) for item,a in zip(corpus,analyses)}
    (outdir/"signal_analysis_hypotheses.json").write_text(json.dumps(all_analyses,indent=2),encoding="utf-8")
    for name,rows in (("event_tokens.csv",token_rows),("predicted_boundaries.csv",predrows),("per_trace_metrics.csv",summary),("build28_discovered_motifs.csv",[{"motif_id":m["motif_id"],"signature":" ".join(m["signature"]),"occurrences":m["occurrences"],"trace_support":m["trace_support"]} for m in motif_report])):
        if rows:
            with (outdir/name).open("w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({"boundary_metrics":result["boundary_micro_metrics"],"token_metrics":token_metrics,"gain_control":gain_control,"controls":controls,"build28_motifs":len(motifs)},indent=2))

if __name__=="__main__": main()
