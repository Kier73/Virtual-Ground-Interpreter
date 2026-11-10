import math
import unittest
from unittest.mock import patch

from vgi.values import OBSERVERS, Signal8Backend, SignalValue, ValueErrorVGI


class SignalDomainTests(unittest.TestCase):
    def setUp(self):
        self.backend = Signal8Backend()

    def test_encode_observe_all_symbols_and_observers(self):
        for observer in OBSERVERS:
            for k in range(8):
                self.assertEqual(self.backend.observe_symbol(self.backend.encode_symbol(k, observer)), k)

    def test_reframe_all_observer_pairs_round_trip(self):
        for source in OBSERVERS:
            for target in OBSERVERS:
                for k in range(8):
                    value = self.backend.encode_symbol(k, source)
                    reframed = self.backend.reframe(value, target)
                    self.assertEqual(reframed.observer, target)
                    self.assertEqual(self.backend.observe_symbol(reframed), k)
                    round_trip = self.backend.reframe(reframed, source)
                    self.assertLess(abs(round_trip.phasor - value.phasor), 1e-10)
                    self.assertEqual(round_trip.observer, source)

    def test_add_sub_all_pairs_and_mixed_observers(self):
        for a in range(8):
            for b in range(8):
                for ua, ub in ((1, 3), (3, 5), (5, 7), (7, 1)):
                    x, y = self.backend.encode_symbol(a, ua), self.backend.encode_symbol(b, ub)
                    self.assertEqual(self.backend.observe_symbol(self.backend.add(x, y)), (a + b) % 8)
                    self.assertEqual(self.backend.observe_symbol(self.backend.sub(x, y)), (a - b) % 8)

    def test_operation_does_not_call_terminal_decoder(self):
        a, b = self.backend.encode_symbol(4, 1), self.backend.encode_symbol(7, 5)
        with patch.object(self.backend, "observe_symbol", side_effect=AssertionError("decode called")):
            out = self.backend.add(a, b)
            out = self.backend.reframe(out, 3)
            out = self.backend.sub(out, b)
        self.assertIsInstance(out, SignalValue)

    def test_reframe_propagates_phase_error_bound(self):
        value = self.backend.encode_symbol(2, 1, phase_error_bound=0.01)
        reframed = self.backend.reframe(value, 7)
        self.assertAlmostEqual(reframed.phase_error_bound, 0.07)

    def test_arithmetic_propagates_error_bounds(self):
        a = self.backend.encode_symbol(2, 1, phase_error_bound=0.03)
        b = self.backend.encode_symbol(5, 3, phase_error_bound=0.04)
        out = self.backend.add(a, b)
        self.assertAlmostEqual(out.phase_error_bound, 0.03 + 0.12)  # b is reframed 3 -> 1 with exponent 3

    def test_terminal_decoder_refuses_symbol_boundary_ambiguity(self):
        from vgi.values import AmbiguousSymbolObservation
        boundary = SignalValue(complex(math.cos(math.pi / 8), math.sin(math.pi / 8)), 1, 0.0)
        with self.assertRaises(AmbiguousSymbolObservation) as caught:
            self.backend.observe_symbol(boundary)
        self.assertEqual(caught.exception.candidates, (0, 1))

        uncertain = SignalValue(1.0 + 0.0j, 1, math.pi / 8)
        with self.assertRaises(AmbiguousSymbolObservation):
            self.backend.observe_symbol(uncertain)

    def test_possible_symbols_respects_observer_coordinate(self):
        value = self.backend.encode_symbol(5, observer=3)
        self.assertEqual(self.backend.possible_symbols(value), (5,))

    def test_comparison_three_way_decision(self):
        identity = self.backend.encode_symbol(0, 1)
        near = SignalValue(complex(math.cos(0.05), math.sin(0.05)), 1, 0.01)
        certain_true = self.backend.compare_identity(identity, 0.02)
        certain_false = self.backend.compare_identity(self.backend.encode_symbol(2, 1), 0.02)
        ambiguous = self.backend.compare_identity(near, 0.05)
        self.assertIs(certain_true.result, True)
        self.assertIs(certain_false.result, False)
        self.assertIsNone(ambiguous.result)

    def test_iq_ingress_and_egress_round_trip(self):
        original = self.backend.encode_symbol(5, observer=3)
        pilot = [complex(0.5 + 0.1 * i, 0.2 - 0.03 * i) for i in range(1, 12)]
        signal = self.backend.emit_iq(original, pilot)
        recovered = self.backend.ingest_iq(signal, pilot, observer=3)
        self.assertLess(abs(recovered.phasor - original.phasor), 1e-10)
        self.assertEqual(recovered.observer, 3)
        self.assertEqual(self.backend.observe_symbol(recovered), 5)

    def test_iq_ingress_rejects_invalid_pilot(self):
        with self.assertRaises(ValueErrorVGI):
            self.backend.ingest_iq([1 + 0j], [0j])
        with self.assertRaises(ValueErrorVGI):
            self.backend.ingest_iq([1 + 0j], [])

    def test_invalid_signal_values_rejected(self):
        with self.assertRaises(ValueErrorVGI):
            SignalValue(2 + 0j, 1, 0)
        with self.assertRaises(ValueErrorVGI):
            SignalValue(1 + 0j, 2, 0)
        with self.assertRaises(ValueErrorVGI):
            self.backend.encode_symbol(8, 1)


if __name__ == "__main__":
    unittest.main()
