"""Build 30: signal-coded instructions and phase-domain arithmetic.

Two layers are deliberately separated:
1. FSK carries operation/control symbols.
2. 8-PSK phasors carry operands; complex phasor multiplication/conjugation performs
   addition/subtraction in Z/8Z before the result is decoded.

This is a finite signal-domain arithmetic demonstrator, not a universal analog
computer and not a claim of lower energy/latency than ordinary digital logic.
"""
from __future__ import annotations
from dataclasses import dataclass
import cmath
import math
import random
from typing import Iterable, Sequence


class SignalCodeError(ValueError):
    pass


@dataclass(frozen=True)
class Instruction:
    opcode: str
    a: int
    b: int

    def __post_init__(self) -> None:
        if self.opcode not in ("ADD8", "SUB8"):
            raise SignalCodeError("supported opcodes are ADD8 and SUB8")
        if not (0 <= self.a < 8 and 0 <= self.b < 8):
            raise SignalCodeError("operands must be integers in Z/8Z")


@dataclass(frozen=True)
class PhaseOperand:
    signal: tuple[complex, ...]
    pilot: tuple[complex, ...]


@dataclass(frozen=True)
class EncodedProgram:
    control_samples: tuple[float, ...]
    operand_pairs: tuple[tuple[PhaseOperand, PhaseOperand], ...]
    output_pilots: tuple[tuple[complex, ...], ...]
    symbol_offset: int
    sample_rate: int
    frame_size: int


def _fft(values: Sequence[complex]) -> list[complex]:
    n = len(values)
    if n == 0 or n & (n - 1):
        raise SignalCodeError("FFT length must be a positive power of two")
    a = list(values)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        angle = -2 * math.pi / length
        wlen = complex(math.cos(angle), math.sin(angle))
        for start in range(0, n, length):
            w = 1 + 0j
            half = length // 2
            for k in range(start, start + half):
                u, v = a[k], a[k + half] * w
                a[k], a[k + half] = u + v, u - v
                w *= wlen
        length *= 2
    return a


def symbol_bin(symbol: int) -> int:
    if not 0 <= int(symbol) < 16:
        raise SignalCodeError("FSK symbol must be in [0,15]")
    return 8 + 2 * int(symbol)


def encode_fsk_symbols(symbols: Sequence[int], *, sample_rate: int = 8192,
                       frame_size: int = 512, amplitude: float = 0.5,
                       leading_offset: int = 0) -> tuple[float, ...]:
    if frame_size < 64 or frame_size & (frame_size - 1):
        raise SignalCodeError("frame_size must be a power of two >=64")
    if sample_rate <= 0 or amplitude <= 0 or leading_offset < 0:
        raise SignalCodeError("invalid FSK configuration")
    out = [0.0] * leading_offset
    for symbol in symbols:
        k = symbol_bin(int(symbol))
        for n in range(frame_size):
            out.append(amplitude * math.cos(2 * math.pi * k * n / frame_size))
    return tuple(out)


def _demod_one(frame: Sequence[float], sample_rate: int, frame_size: int) -> tuple[int, float]:
    if len(frame) != frame_size:
        raise SignalCodeError("incomplete FSK frame")
    mean = sum(frame) / len(frame)
    spec = _fft([complex(float(x) - mean, 0) for x in frame])
    bins = [symbol_bin(s) for s in range(16)]
    energies = [abs(spec[k]) ** 2 for k in bins]
    best = max(range(16), key=lambda i: energies[i])
    ordered = sorted(energies, reverse=True)
    margin = (ordered[0] - ordered[1]) / (ordered[0] + 1e-20)
    return best, margin


def decode_fsk_program(samples: Sequence[float], *, sample_rate: int = 8192,
                       frame_size: int = 512, max_offset: int | None = None) -> tuple[list[str], int, list[float]]:
    """Find the four-symbol preamble and decode [opcode, complement] pairs.

    Preamble = [15, 0, 15, 0]. ADD8=1, SUB8=2; complement=15-opcode.
    Offset search assumes the symbol-rate/frame size is known but not the start sample.
    """
    preamble = [15, 0, 15, 0]
    search = min(frame_size - 1, len(samples) - 4 * frame_size) if max_offset is None else min(max_offset, len(samples) - 4 * frame_size)
    if search < 0:
        raise SignalCodeError("signal too short for preamble")
    found = None
    # A no-tail framed stream gives an exact modular offset from its length.
    # Try that first; this avoids accepting a neighbouring one-sample-shifted
    # frame whose FFT still happens to be dominated by the same tone.
    length_offset = len(samples) % frame_size
    offsets = [length_offset] + [o for o in range(search + 1) if o != length_offset]
    valid = []
    for offset in offsets:
        if len(samples) - (offset + 4 * frame_size) < 0:
            continue
        remaining_here = len(samples) - (offset + 4 * frame_size)
        if remaining_here % (2 * frame_size):
            continue
        decisions = [_demod_one(samples[offset + i * frame_size:offset + (i + 1) * frame_size], sample_rate, frame_size)
                     for i in range(4)]
        decoded = [d[0] for d in decisions]
        if decoded == preamble:
            margin_score = sum(d[1] for d in decisions)
            # Prefer exact length-derived framing on a tie, otherwise strongest
            # coherent preamble margin.
            exact_bonus = 1e-9 if offset == length_offset else 0.0
            valid.append((margin_score + exact_bonus, offset))
    if valid:
        found = max(valid)[1]
    if found is None:
        raise SignalCodeError("preamble not found at a complete instruction-frame alignment")
    start = found + 4 * frame_size
    remaining = len(samples) - start
    if remaining % (2 * frame_size):
        raise SignalCodeError("trailing samples do not form complete instruction frames")
    opcodes: list[str] = []
    margins: list[float] = []
    for i in range(0, remaining, 2 * frame_size):
        op, m1 = _demod_one(samples[start + i:start + i + frame_size], sample_rate, frame_size)
        comp, m2 = _demod_one(samples[start + i + frame_size:start + i + 2 * frame_size], sample_rate, frame_size)
        if comp != 15 - op:
            raise SignalCodeError("opcode complement check failed")
        if op == 1:
            opcodes.append("ADD8")
        elif op == 2:
            opcodes.append("SUB8")
        else:
            raise SignalCodeError(f"unknown opcode symbol {op}")
        margins.extend([m1, m2])
    return opcodes, found, margins


def phase_symbol(value: int) -> complex:
    if not 0 <= int(value) < 8:
        raise SignalCodeError("8-PSK symbol must be in [0,7]")
    return cmath.exp(2j * math.pi * int(value) / 8)


def encode_phase_operand(value: int, *, sample_count: int = 256, sample_rate: int = 8192,
                         carrier_hz: float = 512.0, gain: float = 1.0,
                         phase_offset: float = 0.0, noise_sigma: float = 0.0,
                         seed: int = 0) -> PhaseOperand:
    if sample_count < 8 or sample_rate <= 0 or gain <= 0 or noise_sigma < 0:
        raise SignalCodeError("invalid phase operand configuration")
    rng = random.Random(seed)
    z = phase_symbol(value)
    pilot: list[complex] = []
    signal: list[complex] = []
    for n in range(sample_count):
        carrier = gain * cmath.exp(1j * (2 * math.pi * carrier_hz * n / sample_rate + phase_offset))
        pilot.append(carrier)
        noise = complex(rng.gauss(0, noise_sigma), rng.gauss(0, noise_sigma))
        signal.append(carrier * z + noise)
    return PhaseOperand(tuple(signal), tuple(pilot))


def recover_phase_symbol(operand: PhaseOperand) -> complex:
    if len(operand.signal) != len(operand.pilot) or not operand.signal:
        raise SignalCodeError("signal and pilot lengths must match")
    estimates = []
    for x, p in zip(operand.signal, operand.pilot):
        den = abs(p) ** 2
        if den <= 1e-20:
            continue
        estimates.append(x * p.conjugate() / den)
    if not estimates:
        raise SignalCodeError("pilot energy is zero")
    z = sum(estimates) / len(estimates)
    if abs(z) <= 1e-12:
        raise SignalCodeError("phase estimate has insufficient magnitude")
    return z / abs(z)


def phase_domain_execute(opcode: str, a: PhaseOperand, b: PhaseOperand) -> complex:
    """Execute Z/8Z addition/subtraction by phase-domain group operations.

    Operand symbols are not decoded to integers before this operation.
    The recovered unit phasors are multiplied or multiplied by a conjugate.
    """
    za = recover_phase_symbol(a)
    zb = recover_phase_symbol(b)
    if opcode == "ADD8":
        z = za * zb
    elif opcode == "SUB8":
        z = za * zb.conjugate()
    else:
        raise SignalCodeError(f"unsupported phase-domain opcode: {opcode}")
    return z / abs(z)


def decode_phase_symbol(z: complex) -> int:
    if not (math.isfinite(z.real) and math.isfinite(z.imag)) or abs(z) <= 1e-12:
        raise SignalCodeError("invalid output phasor")
    angle = math.atan2(z.imag, z.real) % (2 * math.pi)
    return int(round(angle * 8 / (2 * math.pi))) % 8


def encode_output_carrier(z: complex, *, pilot: Sequence[complex]) -> tuple[complex, ...]:
    if not pilot:
        raise SignalCodeError("output pilot cannot be empty")
    zn = z / abs(z)
    return tuple(p * zn for p in pilot)


def decode_output_carrier(signal: Sequence[complex], pilot: Sequence[complex]) -> int:
    return decode_phase_symbol(recover_phase_symbol(PhaseOperand(tuple(signal), tuple(pilot))))


def encode_program(instructions: Sequence[Instruction], *, sample_rate: int = 8192,
                   frame_size: int = 512, leading_offset: int = 37,
                   noise_sigma: float = 0.002, seed: int = 1) -> EncodedProgram:
    if not instructions:
        raise SignalCodeError("program must contain at least one instruction")
    control_symbols = [15, 0, 15, 0]
    for ins in instructions:
        op = 1 if ins.opcode == "ADD8" else 2
        control_symbols.extend([op, 15 - op])
    control = list(encode_fsk_symbols(control_symbols, sample_rate=sample_rate,
                                      frame_size=frame_size, leading_offset=leading_offset))
    rng = random.Random(seed + 900)
    control = [x + rng.gauss(0, noise_sigma) for x in control]
    pairs: list[tuple[PhaseOperand, PhaseOperand]] = []
    outputs: list[tuple[complex, ...]] = []
    for i, ins in enumerate(instructions):
        # Independent gains and carrier phase offsets model distinct sensor/transport paths.
        a = encode_phase_operand(ins.a, sample_count=frame_size, sample_rate=sample_rate,
                                 gain=0.5 + 0.7 * rng.random(), phase_offset=rng.uniform(-math.pi, math.pi),
                                 noise_sigma=noise_sigma, seed=seed + 2 * i + 1)
        b = encode_phase_operand(ins.b, sample_count=frame_size, sample_rate=sample_rate,
                                 gain=0.5 + 0.7 * rng.random(), phase_offset=rng.uniform(-math.pi, math.pi),
                                 noise_sigma=noise_sigma, seed=seed + 2 * i + 2)
        pairs.append((a, b))
        out_pilot = encode_phase_operand(0, sample_count=frame_size, sample_rate=sample_rate,
                                         gain=1.0, phase_offset=rng.uniform(-math.pi, math.pi),
                                         noise_sigma=0.0, seed=seed + 100 + i).pilot
        outputs.append(out_pilot)
    return EncodedProgram(tuple(control), tuple(pairs), tuple(outputs), leading_offset,
                          sample_rate, frame_size)


def execute_program(encoded: EncodedProgram) -> dict:
    opcodes, offset, margins = decode_fsk_program(encoded.control_samples,
        sample_rate=encoded.sample_rate, frame_size=encoded.frame_size)
    if len(opcodes) != len(encoded.operand_pairs):
        raise SignalCodeError("control and operand stream instruction counts differ")
    results = []
    for op, (a, b), pilot in zip(opcodes, encoded.operand_pairs, encoded.output_pilots):
        z = phase_domain_execute(op, a, b)
        out_signal = encode_output_carrier(z, pilot=pilot)
        value = decode_output_carrier(out_signal, pilot)
        results.append({"opcode": op, "output_symbol": value,
                        "output_phasor": [z.real, z.imag],
                        "signal_domain_operation": "phasor_multiply" if op == "ADD8" else "phasor_multiply_conjugate"})
    return {"decoded_opcodes": opcodes, "preamble_offset_samples": offset,
            "minimum_fsk_decision_margin": min(margins) if margins else 0.0,
            "results": results}
