"""Post-freeze validation tests for the six proposed fix areas."""
from __future__ import annotations

import json
import math
import random
import struct
import tempfile
import unittest
from pathlib import Path

from build12_preroll import diagnose_preroll, summarize_preroll
from build24_equivalence import all_pairs_distinguishable, delayed_counterexample_summary, equivalence_summary, learn_machine, minimize_mealy
from productivity import all_builds_exact, build20_productivity, build22_productivity, build23_productivity
from random_grounds import random_build22_summary, random_build23_summary
from salt_cv import corpus_status, cross_validated_mean, deterministic_pair_hash, explicit_pair_salt, rochester_room_loro_summary, salt_audit, second_corpus_manifest, seeded_pair_order
from taps_seeded_runner import run_seeded_taps
from signal_stress import build29_multiresolution_summary, build29_perturbation_summary, build30_adaptive_stress_summary, build30_phase_robustness_summary


def _write_pcm16(path: Path, samples, fs: int = 16000) -> None:
    vals = [max(-32768, min(32767, int(round(float(x) * 32767)))) for x in samples]
    payload = struct.pack("<" + "h" * len(vals), *vals)
    fmt = struct.pack("<HHIIHH", 1, 1, fs, fs * 2, 2, 16)

    def chunk(tag, data):
        return tag + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) & 1 else b"")

    body = b"WAVE" + chunk(b"fmt ", fmt) + chunk(b"data", payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def _synth_voice(fs: int = 16000, duration: float = 0.7, f0: float = 120.0, seed: int = 1):
    rng = random.Random(seed)
    out = []
    for i in range(int(fs * duration)):
        t = i / fs
        env = 0.45 + 0.25 * math.sin(2 * math.pi * 2.1 * t) ** 2
        value = (math.sin(2 * math.pi * f0 * t) + 0.45 * math.sin(4 * math.pi * f0 * t)) * env
        out.append(0.22 * value + 0.001 * (rng.random() - 0.5))
    return out


class Build12PrerollTests(unittest.TestCase):
    def test_frozen_onset_bug_is_detected_by_preroll_fixture(self):
        rows = summarize_preroll((2699, 2700, 2701))
        for row in rows:
            with self.subTest(seed=row["seed"]):
                self.assertLess(row["frozen_onset_index"], row["true_peak_index"] * 0.01)
                self.assertGreater(row["pre_peak_energy_fraction"], 0.20)
                self.assertGreater(row["onset_to_peak_ms_frozen"], 900.0)

    def test_peak_trimmed_correction_recovers_ordinary_decay(self):
        row = diagnose_preroll(2699)
        self.assertGreaterEqual(row["corrected_edt_s"], 0.10)
        self.assertLessEqual(row["corrected_edt_s"], 0.60)
        self.assertGreaterEqual(row["corrected_t20_s"], 0.20)
        self.assertLessEqual(row["corrected_t20_s"], 0.50)
        self.assertLess(row["corrected_peak_index"], 5)


class ProductivityTests(unittest.TestCase):
    def test_build20_baseline_counts(self):
        result = build20_productivity(sample_limit=48)
        self.assertEqual(result["state_count"], 648)
        self.assertEqual(result["graph_edge_count"], 5832)
        self.assertEqual(result["materialized_transition_entries"], 5832)
        self.assertEqual(result["lookup_path_entries"], 648)
        self.assertLessEqual(result["max_macro_commands"], 2)
        self.assertGreater(result["materialized_transition_entries"], result["lookup_path_entries"])

    def test_build22_active_beats_passive_inside_closed_family(self):
        result = build22_productivity()
        self.assertEqual(result["candidate_count"], 32)
        self.assertEqual(result["active_identified_count"], 32)
        self.assertLessEqual(result["active_probe_count_max"], 2)
        self.assertEqual(result["passive_identified_count"], 0)
        self.assertGreaterEqual(result["passive_min_remaining_hypotheses"], 2)

    def test_build23_programs_cover_finite_domain_from_compact_syntax(self):
        result = build23_productivity()
        self.assertEqual(len(result["grounds"]), 5)
        for row in result["grounds"]:
            with self.subTest(ground=row["ground"]):
                self.assertEqual(row["heldout_correct"], row["heldout_count"])
                self.assertEqual(row["transition_coverage"], 1.0)
                self.assertLess(
                    row["program_syntax_cost_units"],
                    row["explicit_transition_entries"],
                )

    def test_all_productivity_checks_exact(self):
        self.assertTrue(all_builds_exact())


class RandomGroundTests(unittest.TestCase):
    def test_random_build22_in_family_identified_and_oof_exposed(self):
        result = random_build22_summary(seed=20261106, cases=48)
        self.assertEqual(result["in_family_identified"], result["in_family_count"])
        self.assertLessEqual(result["in_family_probe_count_max"], 4)
        self.assertEqual(
            result["out_of_family_identified_without_extended_mismatch"],
            0,
        )
        self.assertGreater(
            result["out_of_family_rejected"]
            + result["out_of_family_identified_with_extended_mismatch"],
            0,
        )

    def test_random_build23_induction_generalizes_when_grammar_fits(self):
        result = random_build23_summary(seed=20261107, cases=16)
        self.assertGreaterEqual(result["induced"], 12)
        accuracy = (
            result["induced_heldout_correct"] / result["induced_heldout_total"]
            if result["induced_heldout_total"]
            else 0.0
        )
        self.assertGreaterEqual(accuracy, 0.98)
        self.assertGreaterEqual(result["induced_full_coverage_min"], 0.95)


class Build24EquivalenceTests(unittest.TestCase):
    def test_learned_fixture_machines_are_minimal(self):
        summary = equivalence_summary()
        for row in summary["fixtures"]:
            with self.subTest(fixture=row["fixture"], channels=row["channels"]):
                self.assertTrue(row["is_minimal"])
                self.assertEqual(row["minimized_state_count"], row["state_count"])
                self.assertTrue(row["bounded_equivalent"])
                self.assertEqual(row["distinguishable_pairs"], row["pair_count"])
                self.assertEqual(row["missing_distinguishing_pairs"], [])

    def test_all_state_pairs_have_short_distinguishing_words(self):
        for name in ("coupled_six", "delayed_six", "partial_four"):
            _, _, result = learn_machine(name)
            pairs = all_pairs_distinguishable(result.machine, max_depth=8)
            with self.subTest(fixture=name):
                self.assertEqual(pairs["missing_distinguishing_pairs"], [])
                self.assertLessEqual(pairs["longest_distinguishing_word"], 8)

    def test_delayed_counterexample_is_minimal_and_length_six(self):
        summary = delayed_counterexample_summary()
        self.assertEqual(summary["shallow_state_count"], 1)
        self.assertEqual(summary["deep_state_count"], 6)
        self.assertEqual(summary["counterexample_word_length"], 6)
        self.assertEqual(summary["deep_round_counterexample_length"], 6)

    def test_minimizer_reports_nonminimal_counterexample(self):
        # A deliberately duplicated state should be merged by partition refinement.
        _, _, result = learn_machine("unobservable_eight")
        self.assertEqual(minimize_mealy(result.machine)["minimized_state_count"], 1)


class SignalStressTests(unittest.TestCase):
    def test_build29_multiresolution_baseline(self):
        result = build29_multiresolution_summary(max_traces=6)
        baseline = result["configs"]["frame_256_hop_64"]
        self.assertGreaterEqual(baseline["f1"], 0.90)
        for config, metrics in result["configs"].items():
            with self.subTest(config=config):
                self.assertTrue(math.isfinite(metrics["f1"]))

    def test_build29_perturbations_preserve_some_boundary_signal(self):
        result = build29_perturbation_summary(max_traces=4)
        conditions = result["conditions"]
        self.assertGreaterEqual(conditions["baseline"]["f1"], 0.90)
        self.assertGreaterEqual(conditions["gain_low"]["f1"], 0.80)
        self.assertGreaterEqual(conditions["noise_0.01"]["f1"], 0.70)
        self.assertGreaterEqual(conditions["noise_0.03"]["f1"], 0.50)

    def test_build30_many_calibration_traces_keep_expected_views(self):
        result = build30_adaptive_stress_summary(calibration_count=6, heldout_count=6, n_events=7)
        expected = {
            "frequency": ("harmonic", "harmonic"),
            "amplitude": ("temporal", "temporal"),
            "mixed": ("combined", "combined"),
        }
        for task, (boundary_view, token_view) in expected.items():
            with self.subTest(task=task):
                row = result[task]
                self.assertEqual(row["calibration_count"], 6)
                self.assertEqual(row["heldout_count"], 6)
                self.assertIn(row["boundary_view"], (boundary_view, "combined"))
                self.assertEqual(row["token_view"], token_view)
                self.assertGreaterEqual(row["heldout_boundary_f1"], 0.50)

    def test_build30_phase_robustness_boundaries(self):
        result = build30_phase_robustness_summary()
        self.assertEqual(result["noise_sigma"]["0.0"], 0)
        self.assertLessEqual(result["noise_sigma"]["0.1"], 8)
        self.assertGreater(result["pilot_shift_pi_over_4_errors"], 0)
        self.assertLess(result["noise_sigma"]["0.5"], result["total_operations"])


class SaltCrossValidationTests(unittest.TestCase):
    def test_salt_audit_finds_ephemeral_pair_salts(self):
        result = salt_audit()
        self.assertEqual(result["total_salt_definitions"], 3)
        self.assertTrue(all(x["hash_uses_salt"] for x in result["files"]))
        self.assertEqual(result["replacement"], "deterministic_pair_hash(seed, parts)")

    def test_deterministic_pair_hash_is_seeded_and_stable(self):
        ids = ["speaker/utt-a", "speaker/utt-b", "speaker/utt-c"]
        first = seeded_pair_order(13, ids)
        again = seeded_pair_order(13, ids)
        different = seeded_pair_order(14, ids)
        self.assertEqual(first, again)
        self.assertNotEqual(first, different)
        self.assertEqual(
            deterministic_pair_hash(13, ("a", "b")),
            deterministic_pair_hash(13, ("a", "b")),
        )
        self.assertNotEqual(
            deterministic_pair_hash(13, ("a", "b")),
            deterministic_pair_hash(14, ("a", "b")),
        )

    def test_group_cross_validation_keeps_groups_together(self):
        rows = []
        for group in range(10):
            for replicate in range(3):
                rows.append({"speaker": f"s{group:02d}", "score": 0.1 * group + replicate / 100.0})
        result = cross_validated_mean(rows, "speaker", "score", k=5, seed=13)
        self.assertEqual(result["group_count"], 10)
        self.assertEqual(result["row_count"], 30)
        self.assertEqual(len(result["fold_means"]), 5)
        self.assertLessEqual(result["min_fold_mean"], result["overall_mean"])
        self.assertGreaterEqual(result["max_fold_mean"], result["overall_mean"])

    def test_external_corpus_status_is_explicit_when_absent(self):
        result = corpus_status(None)
        self.assertEqual(result["status"], "not_run")
        self.assertFalse(result["second_paired_corpus"])
        self.assertEqual(result["manifest"], "validation/second_paired_corpus_manifest.json")
        self.assertEqual(result["manifest_status"], "unavailable_in_repository")

    def test_second_corpus_manifest_records_limitation(self):
        manifest = second_corpus_manifest()
        self.assertEqual(manifest["status"], "unavailable_in_repository")
        self.assertFalse(manifest["second_paired_corpus"]["dataset_attached"])
        self.assertIn("paired", manifest["second_paired_corpus"]["reason_not_added"])
        self.assertIn("aggregate", manifest["second_paired_corpus"]["minimum_evaluation_protocol"]["privacy"])
        self.assertEqual(manifest["execution_path"]["default_taps_path"], "validation/run_taps_cv.py")

    def test_rochester_room_leave_one_room_out_is_stable(self):
        result = rochester_room_loro_summary()
        self.assertGreaterEqual(result["room_count"], 14)
        metrics = result["metrics"]
        self.assertLess(metrics["edt_s"]["max"], 5.0)
        self.assertLess(metrics["t20_s"]["max"], 5.0)
        self.assertGreater(metrics["c50_db"]["min"], -10.0)
        self.assertLess(metrics["c50_db"]["max"], 20.0)
        for metric in ("edt_s", "t20_s", "c50_db", "d50"):
            with self.subTest(metric=metric):
                self.assertLess(metrics[metric]["loo_mean_range"], 1.5)
                self.assertGreaterEqual(metrics[metric]["loo_mean_min"], metrics[metric]["min"])
                self.assertLessEqual(metrics[metric]["loo_mean_max"], metrics[metric]["max"])


class SeededRunnerTests(unittest.TestCase):
    def test_explicit_pair_salt_is_32_deterministic_bytes(self):
        salt = explicit_pair_salt(99)
        self.assertEqual(len(salt), 32)
        self.assertEqual(salt, explicit_pair_salt(99))
        self.assertNotEqual(salt, explicit_pair_salt(100))

    def test_seeded_wrapper_writes_logged_salt_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "raw"
            out = Path(td) / "out"
            for speaker in range(2):
                for utterance in range(8):
                    directory = root / "test" / f"speaker_{speaker:02d}" / f"utt_{utterance:03d}"
                    throat = _synth_voice(f0=110 + utterance * 7, seed=utterance)
                    acoustic = _synth_voice(f0=110 + utterance * 7, seed=utterance)
                    _write_pcm16(directory / "throat_microphone.wav", throat)
                    _write_pcm16(directory / "acoustic_microphone.wav", acoustic)
                    (directory / "features.json").write_text(
                        json.dumps(
                            {
                                "speaker_id": f"speaker_{speaker:02d}",
                                "sentence_id": f"utt_{utterance:03d}",
                                "text": "PRIVATE TRANSCRIPT SHOULD NOT BE EXPORTED",
                                "throat_microphone": {"sampling_rate": 16000, "num_samples": len(throat)},
                                "acoustic_microphone": {"sampling_rate": 16000, "num_samples": len(acoustic)},
                            }
                        ),
                        encoding="utf-8",
                    )
            result = run_seeded_taps(
                14,
                root,
                out,
                split="test",
                max_speakers=2,
                max_utterances_per_speaker=8,
                permutations=3,
                seed=99,
            )
            provenance_file = out / "seeded_salt_provenance.json"
            self.assertTrue(provenance_file.exists())
            provenance = json.loads(provenance_file.read_text(encoding="utf-8"))
            self.assertEqual(provenance["seed"], 99)
            self.assertEqual(provenance["salt"]["salt_sha256"], result["provenance"]["salt"]["salt_sha256"])
            serialized = (out / "build_14_report.json").read_text(encoding="utf-8")
            self.assertNotIn("speaker_00", serialized)
            self.assertNotIn("PRIVATE TRANSCRIPT", serialized)


if __name__ == "__main__":
    unittest.main(verbosity=2)
