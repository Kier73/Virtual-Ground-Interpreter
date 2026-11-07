"""Small standard-library WAV reader for later measured room-IR ingestion.

This is an adapter only. Build 11 does not include empirical room-IR samples.
"""
from __future__ import annotations
import math
import wave
from pathlib import Path
from typing import List, Tuple


def read_pcm_wav(path: Path) -> Tuple[int, List[List[float]], dict]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.getnframes()
        comptype = wf.getcomptype()
        if comptype != "NONE":
            raise ValueError(f"Compressed WAV not supported: {comptype}")
        raw = wf.readframes(frames)
    if width not in (1, 2, 3, 4):
        raise ValueError(f"Unsupported PCM sample width: {width}")
    samples_per_channel = []
    frame_bytes = width * channels
    for offset in range(0, len(raw), frame_bytes):
        frame = []
        for c in range(channels):
            b = raw[offset + c * width: offset + (c + 1) * width]
            if width == 1:
                # 8-bit PCM WAV is unsigned.
                value = b[0] - 128
                scale = 128.0
            else:
                value = int.from_bytes(b, byteorder="little", signed=False)
                sign_bit = 1 << (8 * width - 1)
                if value & sign_bit:
                    value -= 1 << (8 * width)
                scale = float(1 << (8 * width - 1))
            frame.append(value / scale)
        samples_per_channel.append(frame)
    meta = {"sample_rate_hz": rate, "channels": channels, "sample_width_bytes": width, "frames": frames, "duration_s": frames / rate if rate else 0.0}
    return rate, samples_per_channel, meta


def estimate_rt60(samples: List[List[float]], sample_rate_hz: int) -> float | None:
    """Schroeder backward-integrated energy estimate, rough RT60 from -5 to -35 dB.

    Returns None for short/noisy signals that do not span the required decay range.
    This is a diagnostic estimate, not an ISO-compliant room-acoustic measurement.
    """
    if not samples or sample_rate_hz <= 0:
        return None
    mono = [sum(frame) / len(frame) for frame in samples]
    energy = [x * x for x in mono]
    if max(energy, default=0.0) <= 0:
        return None
    decay = [0.0] * len(energy)
    running = 0.0
    for i in range(len(energy) - 1, -1, -1):
        running += energy[i]
        decay[i] = running
    if decay[0] <= 0:
        return None
    db = [10.0 * math.log10(max(x / decay[0], 1e-15)) for x in decay]
    chosen = [(i / sample_rate_hz, v) for i, v in enumerate(db) if -35.0 <= v <= -5.0]
    if len(chosen) < 10:
        return None
    xs = [x for x, _ in chosen]
    ys = [y for _, y in chosen]
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in chosen) / den
    return -60.0 / slope if slope < 0 else None
