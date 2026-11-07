#!/usr/bin/env python3
"""Generate small synthetic paired channels and run the pipeline smoke test.

This script creates no human voice data and is not an empirical TAPS analysis.
"""
from __future__ import annotations
import json, math, random, struct, tempfile, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_13


def write_pcm16(path: Path, samples, fs=16000):
    vals = [max(-32768, min(32767, int(round(float(x) * 32767)))) for x in samples]
    payload = struct.pack("<" + "h" * len(vals), *vals)
    fmt = struct.pack("<HHIIHH", 1, 1, fs, fs * 2, 2, 16)
    def chunk(tag, data):
        return tag + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) & 1 else b"")
    body = b"WAVE" + chunk(b"fmt ", fmt) + chunk(b"data", payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def signal(fs, seconds, f0, delay=0.0, hf=0.0, seed=0):
    rng = random.Random(seed)
    n = int(fs * seconds)
    shift = int(round(delay * fs))
    out = []
    for i in range(n):
        t = i / fs
        env = 0.35 + 0.25 * (0.5 + 0.5 * math.sin(2 * math.pi * (1.0 + seed % 3) * t))
        v = (math.sin(2*math.pi*f0*t) + 0.35*math.sin(2*math.pi*2*f0*t)
             + 0.12*math.sin(2*math.pi*3*f0*t)) * env
        v += hf * math.sin(2*math.pi*4800*t) * env
        v += 0.0008 * (rng.random() - 0.5)
        out.append(0.18 * v)
    if shift:
        out = [0.0] * shift + out[:-shift]
    return out


def main():
    output = ROOT / "reports" / "synthetic_smoke_test.json"
    with tempfile.TemporaryDirectory(prefix="vl_build13_smoke_") as td:
        data = Path(td) / "test"
        for s in range(3):
            for u in range(10):
                d = data / f"speaker_{s:02d}" / f"utt_{u:03d}"
                fs = 16000; f0 = 110.0 + 8.0*u + 3*s
                throat = signal(fs, 0.9, f0, delay=0.0, hf=0.0, seed=s*100+u)
                acoustic = signal(fs, 0.9, f0, delay=0.001, hf=0.025, seed=s*100+u)
                write_pcm16(d / "throat_microphone.wav", throat, fs)
                write_pcm16(d / "acoustic_microphone.wav", acoustic, fs)
                (d / "features.json").write_text(json.dumps({
                    "speaker_id": f"speaker_{s:02d}", "sentence_id": f"utt_{u:03d}",
                    "text": "synthetic fixture only",
                    "throat_microphone": {"sampling_rate": fs, "num_samples": len(throat)},
                    "acoustic_microphone": {"sampling_rate": fs, "num_samples": len(acoustic)},
                }), encoding="utf-8")
        result = build_13.run_analysis(data, ROOT / "reports" / "synthetic_smoke_outputs",
                                       split="test", max_speakers=3,
                                       max_utterances_per_speaker=10, permutations=19,
                                       seed=13, provenance="synthetic_fixture")
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
