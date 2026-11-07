from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "predecessor" / "vl_response_geometry_build_30"
sys.path.insert(0, str(PRED))
sys.path.insert(0, str(ROOT))

import build31_signal as b31
from build31_signal import (
    OBSERVER_UNITS, Build31Error, ChannelSpec, apply_channel,
    binary_signal_operation, decode_state, encode_state, make_pilot,
    phase_residual, reframe_state, recover_phase_symbol, signal_chain,
    symbolic_chain,
)
from signal_code import phase_symbol


class ObserverCoordinateTests(unittest.TestCase):
    def test_all_four_characters_roundtrip_all_symbols(self):
        for u in OBSERVER_UNITS:
            for value in range(8):
                s = encode_state(value, observer=u, sample_count=64,
                                 gain=0.5 + value * 0.1, phase_offset=value * 0.13,
                                 seed=u * 100 + value)
                self.assertEqual(decode_state(s), value)

    def test_odd_units_are_the_invertible_coordinates(self):
        for u in OBSERVER_UNITS:
            inv = b31.inverse_unit_mod8(u)
            self.assertEqual((u * inv) % 8, 1)
        for bad in (0, 2, 4, 6, 8):
            with self.assertRaises(Build31Error):
                b31.inverse_unit_mod8(bad)

    def test_character_homomorphism_for_all_units(self):
        for u in OBSERVER_UNITS:
            for a in range(8):
                for b in range(8):
                    lhs = phase_symbol((u * ((a + b) % 8)) % 8)
                    rhs = phase_symbol((u * a) % 8) * phase_symbol((u * b) % 8)
                    self.assertLess(abs(lhs - rhs), 1e-12)

    def test_reframe_preserves_semantics_for_every_coordinate_pair(self):
        for source in OBSERVER_UNITS:
            for target in OBSERVER_UNITS:
                for value in range(8):
                    s = encode_state(value, observer=source, sample_count=32,
                                     seed=source * 1000 + target * 100 + value)
                    moved = reframe_state(s, target)
                    self.assertEqual(moved.observer, target)
                    self.assertEqual(decode_state(moved), value)

    def test_reframe_inverse_recovers_original_phasor(self):
        for source in OBSERVER_UNITS:
            for target in OBSERVER_UNITS:
                for value in range(8):
                    s = encode_state(value, observer=source, sample_count=32, seed=value)
                    moved = reframe_state(s, target)
                    restored = reframe_state(moved, source)
                    self.assertLess(abs(recover_phase_symbol(s.operand) -
                                        recover_phase_symbol(restored.operand)), 1e-12)

    def test_reframe_does_not_decode_integer(self):
        s = encode_state(5, observer=3, sample_count=32)
        with patch("build31_signal.decode_phase_symbol", side_effect=AssertionError("integer decode")):
            moved = reframe_state(s, 7)
        self.assertEqual(moved.observer, 7)


class BinaryAlgebraTests(unittest.TestCase):
    def test_exhaustive_add_sub_closure_all_observers(self):
        cases = errors = 0
        for u in OBSERVER_UNITS:
            for op in ("ADD8", "SUB8"):
                for a in range(8):
                    for b in range(8):
                        sa = encode_state(a, observer=u, sample_count=32, seed=100 + a)
                        sb = encode_state(b, observer=u, sample_count=32, seed=200 + b)
                        out = binary_signal_operation(op, sa, sb, output_observer=u)
                        expected = (a + b) % 8 if op == "ADD8" else (a - b) % 8
                        errors += decode_state(out) != expected
                        cases += 1
        self.assertEqual(cases, 512)
        self.assertEqual(errors, 0)

    def test_operation_is_natural_under_all_observer_changes(self):
        cases = 0
        for u in OBSERVER_UNITS:
            for op in ("ADD8", "SUB8"):
                for a in range(8):
                    for b in range(8):
                        a1 = encode_state(a, observer=1, sample_count=24)
                        b1 = encode_state(b, observer=1, sample_count=24)
                        lhs = reframe_state(binary_signal_operation(op, a1, b1, output_observer=1), u)
                        rhs = binary_signal_operation(op, reframe_state(a1, u),
                                                      reframe_state(b1, u), output_observer=u)
                        self.assertEqual(decode_state(lhs), decode_state(rhs))
                        self.assertEqual(decode_state(rhs),
                                         (a+b) % 8 if op == "ADD8" else (a-b) % 8)
                        cases += 1
        self.assertEqual(cases, 512)

    def test_invalid_opcode_is_rejected(self):
        a, b = encode_state(1), encode_state(2)
        with self.assertRaises(Build31Error):
            binary_signal_operation("MUL8", a, b)

    def test_signal_operation_does_not_call_integer_decoder(self):
        a, b = encode_state(3), encode_state(6)
        with patch("build31_signal.decode_phase_symbol", side_effect=AssertionError("premature decode")):
            out = binary_signal_operation("ADD8", a, b)
        self.assertAlmostEqual(abs(recover_phase_symbol(out.operand)), 1.0, places=12)


class CompositionTests(unittest.TestCase):
    def test_all_2048_three_operand_chains(self):
        patterns = (("ADD8", "ADD8"), ("ADD8", "SUB8"),
                    ("SUB8", "ADD8"), ("SUB8", "SUB8"))
        cases = 0
        for p, (op1, op2) in enumerate(patterns):
            for a in range(8):
                for b in range(8):
                    for c in range(8):
                        sa = encode_state(a, observer=OBSERVER_UNITS[(a+p) % 4], sample_count=24)
                        sb = encode_state(b, observer=OBSERVER_UNITS[(b+p+1) % 4], sample_count=24)
                        sc = encode_state(c, observer=OBSERVER_UNITS[(c+p+2) % 4], sample_count=24)
                        out = signal_chain(sa, sb, sc, op1, op2,
                                           intermediate_observer=OBSERVER_UNITS[(a+b+p) % 4],
                                           output_observer=OBSERVER_UNITS[(a+2*b+c+p) % 4],
                                           intermediate_pilot=make_pilot(24, phase_offset=0.2),
                                           output_pilot=make_pilot(24, phase_offset=-0.1))
                        self.assertEqual(decode_state(out), symbolic_chain(a, b, c, op1, op2))
                        cases += 1
        self.assertEqual(cases, 2048)

    def test_chain_has_no_intermediate_integer_decode(self):
        a = encode_state(3, observer=1, sample_count=32)
        b = encode_state(6, observer=3, sample_count=32)
        c = encode_state(2, observer=5, sample_count=32)
        with patch("build31_signal.decode_phase_symbol", side_effect=AssertionError("intermediate decode")):
            out = signal_chain(a, b, c, "ADD8", "SUB8",
                               intermediate_observer=7, output_observer=3)
        # Decode is deliberately performed only after the guarded execution.
        self.assertEqual(decode_state(out), 7)

    def test_inverse_translations_recover_first_operand(self):
        cases = 0
        for u in OBSERVER_UNITS:
            for a in range(8):
                for b in range(8):
                    sa = encode_state(a, observer=u, sample_count=32)
                    sb = encode_state(b, observer=u, sample_count=32)
                    for first, second in (("ADD8", "SUB8"), ("SUB8", "ADD8")):
                        middle = binary_signal_operation(first, sa, sb, output_observer=u)
                        restored = binary_signal_operation(second, middle, sb, output_observer=u)
                        self.assertEqual(decode_state(restored), a)
                        cases += 1
        self.assertEqual(cases, 512)

    def test_associative_addition_via_two_composition_orders(self):
        for u in OBSERVER_UNITS:
            for a in range(8):
                for b in range(8):
                    for c in range(8):
                        sa = encode_state(a, observer=u, sample_count=24)
                        sb = encode_state(b, observer=u, sample_count=24)
                        sc = encode_state(c, observer=u, sample_count=24)
                        ab = binary_signal_operation("ADD8", sa, sb, output_observer=u)
                        left = binary_signal_operation("ADD8", ab, sc, output_observer=u)
                        bc = binary_signal_operation("ADD8", sb, sc, output_observer=u)
                        right = binary_signal_operation("ADD8", sa, bc, output_observer=u)
                        self.assertEqual(decode_state(left), decode_state(right))


class ChannelTests(unittest.TestCase):
    def test_common_gain_and_phase_are_cancelled_by_pilot_reference(self):
        for i in range(32):
            value = i % 8
            s = encode_state(value, sample_count=64, seed=i)
            transformed = apply_channel(s, ChannelSpec(gain=0.2 + i*0.1,
                                                        phase=-2.0 + i*0.11))
            self.assertEqual(decode_state(transformed), value)

    def test_calibration_error_adds_on_add_and_subtracts_on_sub(self):
        da, db, dc = 0.11, -0.07, 0.04
        a = apply_channel(encode_state(3, sample_count=96), ChannelSpec(calibration_error=da))
        b = apply_channel(encode_state(6, sample_count=96), ChannelSpec(calibration_error=db))
        c = apply_channel(encode_state(2, sample_count=96), ChannelSpec(calibration_error=dc))
        middle = binary_signal_operation("ADD8", a, b)
        result = binary_signal_operation("SUB8", middle, c)
        measured = phase_residual(phase_symbol(7), recover_phase_symbol(result.operand))
        expected = da + db - dc
        self.assertAlmostEqual(measured, expected, places=10)
        self.assertEqual(decode_state(result), 7)

    def test_intermediate_calibration_error_propagates_to_final_state(self):
        a = encode_state(3, sample_count=96)
        b = encode_state(6, sample_count=96)
        c = encode_state(2, sample_count=96)
        middle = binary_signal_operation("ADD8", a, b)
        middle = apply_channel(middle, ChannelSpec(calibration_error=0.09))
        result = binary_signal_operation("SUB8", middle, c)
        measured = phase_residual(phase_symbol(7), recover_phase_symbol(result.operand))
        self.assertAlmostEqual(measured, 0.09, places=10)
        self.assertEqual(decode_state(result), 7)

    def test_half_decision_width_is_the_nearest_phase_boundary(self):
        self.assertAlmostEqual(math.pi / 8, 22.5 * math.pi / 180)
        a = encode_state(3, sample_count=128)
        shifted = apply_channel(a, ChannelSpec(calibration_error=0.45))
        self.assertNotEqual(decode_state(shifted), 3)

    def test_zero_gain_channel_is_rejected(self):
        a = encode_state(2)
        with self.assertRaises(Build31Error):
            apply_channel(a, ChannelSpec(gain=0.0))

    def test_noise_is_reproducible_for_fixed_seed(self):
        a = encode_state(4, sample_count=64, noise_sigma=0.2, seed=91)
        b = encode_state(4, sample_count=64, noise_sigma=0.2, seed=91)
        self.assertEqual(a.operand.signal, b.operand.signal)
        self.assertEqual(a.operand.pilot, b.operand.pilot)


if __name__ == "__main__":
    unittest.main()
