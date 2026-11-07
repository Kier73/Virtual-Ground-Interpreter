from __future__ import annotations
import math, random, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from adaptive_observer import ObserverProfile, select_observer, evaluate_on_heldout
from signal_code import (Instruction, SignalCodeError, encode_fsk_symbols, decode_fsk_program,
                         encode_phase_operand, phase_domain_execute, decode_phase_symbol,
                         encode_program, execute_program, phase_symbol)
from run_build30 import make_signal_trace, build_adaptive_experiment, build_signal_program_experiment

class AdaptiveObserverTests(unittest.TestCase):
    def test_frequency_task_selects_harmonic_family(self):
        train=[make_signal_trace("frequency",4100+i) for i in range(4)]
        sel=select_observer(train)
        self.assertIn(sel["selected_profile"].boundary_view,("harmonic","combined"))
        self.assertEqual(sel["selected_profile"].token_view,"harmonic")

    def test_amplitude_task_selects_temporal_boundary_view(self):
        train=[make_signal_trace("amplitude",5100+i) for i in range(4)]
        sel=select_observer(train)
        self.assertIn(sel["selected_profile"].boundary_view,("temporal","combined"))
        self.assertGreater(sel["selected_utility"],0.5)

    def test_mixed_task_selects_combined_boundary_view(self):
        train=[make_signal_trace("mixed",6100+i) for i in range(4)]
        sel=select_observer(train)
        self.assertEqual(sel["selected_profile"].boundary_view,"combined")

    def test_selector_rejects_too_small_calibration(self):
        with self.assertRaises(ValueError): select_observer([make_signal_trace("frequency",1)])

    def test_heldout_is_not_part_of_selection_contract(self):
        train=[make_signal_trace("frequency",4100+i) for i in range(4)]
        selection=select_observer(train)
        test=[make_signal_trace("frequency",4200+i) for i in range(2)]
        result=evaluate_on_heldout(selection["selected_profile"],test)
        self.assertGreaterEqual(result.utility,0.4)

class FSKCodingTests(unittest.TestCase):
    def test_control_program_decodes_all_opcodes(self):
        ins=[Instruction("ADD8",3,6),Instruction("SUB8",1,4),Instruction("ADD8",7,7)]
        enc=encode_program(ins,leading_offset=37,noise_sigma=.001)
        ops,offset,_=decode_fsk_program(enc.control_samples,frame_size=enc.frame_size)
        self.assertEqual(ops,[x.opcode for x in ins]); self.assertEqual(offset,37)

    def test_fsk_gain_and_dc_offset_invariance(self):
        syms=[15,0,15,0,1,14,2,13]
        base=list(encode_fsk_symbols(syms,leading_offset=19))
        changed=[.37*x+.12 for x in base]
        # Repackage a simple control-only stream: preamble + opcode/complement.
        ops,offset,_=decode_fsk_program(changed,frame_size=512)
        self.assertEqual(ops,["ADD8","SUB8"]); self.assertEqual(offset,19)

    def test_fsk_rejects_wrong_opcode_complement(self):
        syms=[15,0,15,0,1,1]
        bad=encode_fsk_symbols(syms)
        with self.assertRaises(SignalCodeError): decode_fsk_program(bad,frame_size=512)

class PhaseArithmeticTests(unittest.TestCase):
    def test_all_add8_pairs(self):
        for a in range(8):
            for b in range(8):
                pa=encode_phase_operand(a,sample_count=64,seed=a,gain=.7,phase_offset=.3*a)
                pb=encode_phase_operand(b,sample_count=64,seed=b+8,gain=1.3,phase_offset=-.2*b)
                got=decode_phase_symbol(phase_domain_execute("ADD8",pa,pb))
                self.assertEqual(got,(a+b)%8)

    def test_all_sub8_pairs(self):
        for a in range(8):
            for b in range(8):
                pa=encode_phase_operand(a,sample_count=64,seed=a,gain=.6,phase_offset=.2*a)
                pb=encode_phase_operand(b,sample_count=64,seed=b+8,gain=1.1,phase_offset=-.3*b)
                got=decode_phase_symbol(phase_domain_execute("SUB8",pa,pb))
                self.assertEqual(got,(a-b)%8)

    def test_phase_symbol_representation_is_homomorphism(self):
        for a in range(8):
            for b in range(8):
                self.assertLess(abs(phase_symbol(a)*phase_symbol(b)-phase_symbol((a+b)%8)),1e-12)

    def test_phase_operation_uses_phasors_not_decoded_integers(self):
        pa=encode_phase_operand(3,sample_count=64)
        pb=encode_phase_operand(6,sample_count=64)
        z=phase_domain_execute("ADD8",pa,pb)
        self.assertEqual(decode_phase_symbol(z),1)

    def test_noise_robustness_at_moderate_noise(self):
        errors=0
        for a in range(8):
            for b in range(8):
                pa=encode_phase_operand(a,sample_count=256,noise_sigma=.02,seed=100+a,gain=.7,phase_offset=.2*a)
                pb=encode_phase_operand(b,sample_count=256,noise_sigma=.02,seed=200+b,gain=1.2,phase_offset=-.17*b)
                got=decode_phase_symbol(phase_domain_execute("ADD8",pa,pb))
                errors+=int(got!=(a+b)%8)
        self.assertEqual(errors,0)

    def test_bad_opcode_rejected(self):
        pa=encode_phase_operand(1);pb=encode_phase_operand(2)
        with self.assertRaises(SignalCodeError): phase_domain_execute("MUL8",pa,pb)

    def test_pilot_phase_miscalibration_changes_decoded_result(self):
        from signal_code import PhaseOperand
        import cmath
        pa=encode_phase_operand(3,sample_count=128,seed=901)
        pb=encode_phase_operand(6,sample_count=128,seed=902)
        shifted=PhaseOperand(pa.signal,tuple(p*cmath.exp(1j*math.pi/4) for p in pa.pilot))
        self.assertEqual(decode_phase_symbol(phase_domain_execute("ADD8",pa,pb)),1)
        self.assertNotEqual(decode_phase_symbol(phase_domain_execute("ADD8",shifted,pb)),1)

    def test_operands_are_not_integer_decoded_before_operation(self):
        from unittest.mock import patch
        pa=encode_phase_operand(3,sample_count=128)
        pb=encode_phase_operand(6,sample_count=128)
        with patch("signal_code.decode_phase_symbol",side_effect=AssertionError("premature decode")):
            z=phase_domain_execute("ADD8",pa,pb)
        self.assertAlmostEqual(abs(z),1.0,places=12)

class EndToEndProgramTests(unittest.TestCase):
    def test_signal_coded_program_executes(self):
        result=build_signal_program_experiment()
        self.assertTrue(result["program_correct"])
        self.assertEqual(result["exhaustive_pair_coverage"]["errors"],0)

    def test_fsk_program_offset_recovered(self):
        result=build_signal_program_experiment()
        self.assertEqual(result["preamble_offset_samples_recovered"],37)

    def test_build29_signal_observer_finds_fsk_symbol_events(self):
        result=build_signal_program_experiment()
        temporal=result["fsk_event_boundary_audit_via_build29"]["temporal"]
        self.assertGreaterEqual(temporal["recall"],14/15)

    def test_program_output_matches_modular_arithmetic(self):
        result=build_signal_program_experiment()
        self.assertEqual(result["expected_outputs"],result["actual_outputs"])

class ProvenanceAndSanityTests(unittest.TestCase):
    def test_all_task_views_present(self):
        r=build_adaptive_experiment()
        self.assertEqual(set(r["task_results"]),{"frequency","amplitude","mixed"})

    def test_signal_computation_scope_explicit(self):
        r=build_signal_program_experiment()
        self.assertIn("not universal",r["scope"])
        self.assertEqual(r["exhaustive_pair_coverage"]["errors"],0)

    def test_noise_sweep_exposes_error_floor(self):
        r=build_signal_program_experiment()
        sweep=r["noise_robustness"]
        self.assertEqual(sweep[0]["accuracy"],1.0)
        self.assertLess(sweep[-1]["accuracy"],1.0)
        self.assertGreater(sweep[-1]["accuracy"],.8)

    def test_pilot_miscalibration_is_reported(self):
        r=build_signal_program_experiment()["pilot_calibration_control"]
        self.assertTrue(r["calibration_required"])

if __name__=="__main__": unittest.main()
