from __future__ import annotations
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from continuous_signal import (SignalChannel,SignalError,analyze_signals,event_tokens_for_build28,
                               read_wav_channels,write_wav_channels)
from run_build29 import build_corpus,make_amplitude_trace,make_weak_amplitude_trace,match_boundaries


class SignalValidationTests(unittest.TestCase):
    def test_reject_empty_name(self):
        with self.assertRaises(SignalError): SignalChannel("",8000,(0.0,1.0))

    def test_reject_nonfinite_samples(self):
        with self.assertRaises(SignalError): SignalChannel("x",8000,(0.0,float("nan")))

    def test_reject_bad_rate(self):
        with self.assertRaises(SignalError): SignalChannel("x",0,(0.0,1.0))

    def test_reject_original_nyquist_above_current(self):
        with self.assertRaises(SignalError): SignalChannel("x",8000,(0.0,1.0),5000)

    def test_reject_mismatched_channel_sample_rates(self):
        with self.assertRaises(SignalError):
            analyze_signals([SignalChannel("a",8000,tuple([0.0]*512)),SignalChannel("b",16000,tuple([0.0]*512))])

    def test_reject_mismatched_channel_lengths(self):
        with self.assertRaises(SignalError):
            analyze_signals([SignalChannel("a",8000,tuple([0.0]*512)),SignalChannel("b",8000,tuple([0.0]*511))])

    def test_reject_signal_shorter_than_frame(self):
        with self.assertRaises(SignalError):
            analyze_signals([SignalChannel("a",8000,tuple([0.0]*128))],frame_size=256)

    def test_reject_non_power_of_two_frame(self):
        with self.assertRaises(SignalError):
            analyze_signals([SignalChannel("a",8000,tuple([0.0]*512))],frame_size=250)


class WavIoTests(unittest.TestCase):
    def test_stereo_pcm16_roundtrip(self):
        fs=8000; a=[.2*math.sin(2*math.pi*400*i/fs) for i in range(1024)];b=[.3*math.sin(2*math.pi*700*i/fs) for i in range(1024)]
        with tempfile.TemporaryDirectory() as td:
            p=str(Path(td)/"stereo.wav");write_wav_channels(p,fs,[a,b],16)
            sr,ch=read_wav_channels(p)
        self.assertEqual(sr,fs);self.assertEqual(len(ch),2);self.assertEqual(len(ch[0].samples),1024)
        self.assertLess(max(abs(x-y) for x,y in zip(a,ch[0].samples)),4e-5)

    def test_stereo_pcm24_roundtrip(self):
        fs=8000;a=[.1*math.sin(2*math.pi*500*i/fs) for i in range(512)];b=[-.2*math.sin(2*math.pi*600*i/fs) for i in range(512)]
        with tempfile.TemporaryDirectory() as td:
            p=str(Path(td)/"stereo24.wav");write_wav_channels(p,fs,[a,b],24)
            sr,ch=read_wav_channels(p)
        self.assertEqual(sr,fs);self.assertEqual(len(ch),2)
        self.assertLess(max(abs(x-y) for x,y in zip(b,ch[1].samples)),2e-7)

    def test_raw_wav_analyzes(self):
        corpus,_=build_corpus();channels=corpus[0]["channels"]
        with tempfile.TemporaryDirectory() as td:
            p=str(Path(td)/"fixture.wav");write_wav_channels(p,8192,[c.samples for c in channels])
            fs,loaded=read_wav_channels(p);analysis=analyze_signals(loaded)
        self.assertEqual(fs,8192);self.assertEqual(len(loaded),2)
        self.assertIsNotNone(analysis.selected)
        self.assertEqual(len(analysis.selected.boundaries),9)


class BoundaryDetectionTests(unittest.TestCase):
    def test_frequency_boundaries_exact_within_tolerance(self):
        corpus,_=build_corpus();tp=fp=fn=0
        for item in corpus:
            a=analyze_signals(item["channels"],observer_view="combined")
            pred=list(a.selected.boundaries)
            m=match_boundaries(pred,[round(x/64) for x in item["truth_boundaries_samples"]],2)
            tp+=m["tp"];fp+=m["fp"];fn+=m["fn"]
        self.assertEqual((tp,fp,fn),(108,0,0))

    def test_harmonic_gain_invariance(self):
        item=build_corpus()[0][0];base=item["channels"]
        scaled=[SignalChannel(c.name,c.sample_rate,tuple(.35*x for x in c.samples)) for c in base]
        a=analyze_signals(base,observer_view="harmonic").selected.boundaries
        b=analyze_signals(scaled,observer_view="harmonic").selected.boundaries
        self.assertEqual(a,b)

    def test_stationary_tone_no_selected_boundary(self):
        fs=8192;x=tuple(.3*math.sin(2*math.pi*512*i/fs) for i in range(fs))
        a=analyze_signals([SignalChannel("tone",fs,x)],observer_view="harmonic")
        self.assertEqual(len(a.selected.boundaries),0)

    def test_stationary_noise_no_selected_boundary(self):
        fs=8192;rng=random.Random(440);x=tuple(.05*rng.gauss(0,1) for _ in range(fs))
        a=analyze_signals([SignalChannel("noise",fs,x)],observer_view="harmonic")
        self.assertEqual(len(a.selected.boundaries),0)

    def test_candidate_status_distinguishes_subthreshold(self):
        fs=8192;x=tuple(.05*math.sin(2*math.pi*500*i/fs) for i in range(fs))
        a=analyze_signals([SignalChannel("tone",fs,x)])
        self.assertTrue(all(c.status in ("subthreshold_candidate","supported_candidate") for c in a.candidates))

    def test_threshold_hypotheses_preserve_weak_alternatives(self):
        channels,bounds=make_weak_amplitude_trace()
        a=analyze_signals(channels,observer_view="temporal",token_view="temporal")
        by={h.threshold_name:h for h in a.hypotheses}
        self.assertNotEqual(by["conservative"].boundaries,by["nominal"].boundaries)
        self.assertEqual(len(by["sensitive"].boundaries),len(bounds))

    def test_amplitude_events_require_temporal_view(self):
        channels,bounds,_=make_amplitude_trace()
        h=analyze_signals(channels,observer_view="harmonic")
        t=analyze_signals(channels,observer_view="temporal")
        self.assertEqual(len(h.selected.boundaries),0)
        self.assertGreater(len(t.selected.boundaries),0)

    def test_token_view_changes_observable_equivalence(self):
        channels,_,_=make_amplitude_trace()
        h=analyze_signals(channels,observer_view="temporal",token_view="harmonic")
        t=analyze_signals(channels,observer_view="temporal",token_view="temporal")
        self.assertEqual(len(set(event_tokens_for_build28(h))),1)
        self.assertEqual(len(set(event_tokens_for_build28(t))),4)

    def test_phase_only_detection_is_partial_not_claimed_exact(self):
        fs=8192;hop=64;samples=[];bounds=[];offset=0
        for j in range(8):
            if j: bounds.append(offset)
            phase=0.0 if j%2==0 else math.pi/2
            for k in range(10*hop): samples.append(.4*math.sin(2*math.pi*640*(offset+k)/fs+phase))
            offset+=10*hop
        a=analyze_signals([SignalChannel("phase",fs,tuple(samples))],observer_view="harmonic")
        m=match_boundaries(list(a.selected.boundaries),[round(x/hop) for x in bounds],2)
        self.assertGreaterEqual(m["recall"],.5)
        self.assertLess(m["recall"],1.0)

    def test_token_labels_are_opaque(self):
        channels,_,_=make_amplitude_trace()
        a=analyze_signals(channels,observer_view="temporal",token_view="temporal")
        self.assertTrue(all(t.startswith("evt_") for t in event_tokens_for_build28(a)))

    def test_multiple_hypotheses_available(self):
        item=build_corpus()[0][0];a=analyze_signals(item["channels"])
        self.assertEqual({h.threshold_name for h in a.hypotheses},{"sensitive","nominal","conservative"})

    def test_all_reported_features_finite(self):
        item=build_corpus()[0][0];a=analyze_signals(item["channels"])
        for fs in a.channels.values():
            for fr in fs:
                self.assertTrue(all(math.isfinite(v) for v in fr.values.values()))

    def test_build28_motif_bridge_uses_signal_derived_tokens(self):
        sys.path.insert(0,str(ROOT/"notes"/"build28_workspace"))
        from stream_ground import ContinuousTrace,Checkpoint,mine_motifs,segment_stream
        corpus,_=build_corpus(); traces=[]
        for i,item in enumerate(corpus):
            analysis=analyze_signals(item["channels"])
            tokens=event_tokens_for_build28(analysis)
            traces.append(ContinuousTrace(f"t{i}",tuple(tokens),(Checkpoint(0,(0,)),Checkpoint(len(tokens),(0,)))))
        motifs,_=mine_motifs(traces[:10],min_len=2,max_len=4,min_occurrences=3,min_trace_support=2)
        self.assertGreater(len(motifs),0)
        heldout=segment_stream(traces[10],motifs,top_k=4)
        self.assertIn(heldout.status,("ambiguous","complete","partial"))


if __name__=="__main__": unittest.main()
