#!/usr/bin/env python3
"""Command-line entry point for raw WAV -> candidate Virtual Ground events."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from continuous_signal import read_wav_channels, analyze_signals, analysis_to_dict


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_wav",type=Path)
    ap.add_argument("--output",type=Path,default=None)
    ap.add_argument("--view",choices=("harmonic","temporal","combined"),default="combined")
    ap.add_argument("--frame-size",type=int,default=256)
    ap.add_argument("--hop",type=int,default=64)
    ap.add_argument("--token-view",choices=("harmonic","temporal","combined"),default="harmonic")
    args=ap.parse_args()
    fs,channels=read_wav_channels(str(args.input_wav))
    analysis=analyze_signals(channels,frame_size=args.frame_size,hop=args.hop,
                             observer_view=args.view,token_view=args.token_view)
    result=analysis_to_dict(analysis)
    result["input"]={"filename":args.input_wav.name,"sample_rate_hz":fs,"channel_count":len(channels),
                      "samples_per_channel":len(channels[0].samples)}
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.output:
        args.output.write_text(text,encoding="utf-8")
    else:
        print(text,end="")

if __name__=="__main__": main()
