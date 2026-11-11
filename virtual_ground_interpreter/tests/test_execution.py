import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from vgi import (
    ExecutionTraceError,
    Program,
    Instruction,
    Signal8Backend,
    Signal8ExecutionAdapter,
    VirtualGroundInterpreter,
    project_execution_transitions,
    verify_execution_replay,
)


def add_program():
    return Program("signal8-add-trace", (
        Instruction("LOAD", {"dst": "a", "address": "input.a"}),
        Instruction("LOAD", {"dst": "b", "address": "input.b"}),
        Instruction("ADD", {"dst": "sum", "left": "a", "right": "b"}),
        Instruction("EMIT", {"src": "sum", "label": "sum"}),
        Instruction("HALT"),
    ))


def memory(backend, a=3, b=5):
    return {
        "input.a": backend.encode_symbol(a, observer=1),
        "input.b": backend.encode_symbol(b, observer=3),
    }


class Signal8ExecutionTraceTests(unittest.TestCase):
    def setUp(self):
        self.backend = Signal8Backend()
        self.interpreter = VirtualGroundInterpreter(backend=self.backend)
        self.adapter = Signal8ExecutionAdapter(self.interpreter)

    def test_capture_retains_every_committed_event_and_frame_lineage(self):
        trace = self.adapter.capture(
            add_program(), memory(self.backend),
            trace_id="capture-001", max_steps=20,
        )
        self.assertEqual(trace.status, "completed")
        self.assertEqual(len(trace.entries), 5)
        self.assertEqual(len(trace.exchange.messages), 5)
        self.assertEqual(len(trace.encounters.encounters), 5)
        self.assertEqual([item.receipt.sequence for item in trace.entries], [1, 2, 3, 4, 5])
        self.assertEqual(trace.entries[2].record_type, "execution_step")
        add_message = trace.exchange.messages[2]
        self.assertEqual(add_message.payload["event"]["opcode"], "ADD")
        self.assertIn("write_values", add_message.payload["event"])
        self.assertTrue(all(item.receipt.payload_digest for item in trace.entries))
        self.assertEqual(trace.to_dict()["format"], "VGI-Signal8ExecutionTrace-1")
        self.assertEqual(len(trace.fingerprint), 64)

    def test_trace_json_roundtrip_preserves_fingerprint_and_replay(self):
        original = self.adapter.capture(
            add_program(), memory(self.backend), trace_id="json-roundtrip-001",
        )
        restored = type(original).from_json(original.to_json())
        self.assertEqual(restored.fingerprint, original.fingerprint)
        replay = self.adapter.replay(restored, trace_id="json-roundtrip-replay")
        self.assertTrue(verify_execution_replay(restored, replay).matched)

    def test_trace_rejects_receipt_with_wrong_source_identity(self):
        from vgi import Signal8ExecutionTrace
        trace = self.adapter.capture(
            add_program(), memory(self.backend), trace_id="receipt-binding-001",
        )
        bad_receipt = replace(trace.entries[0].receipt, source="forged-source")
        bad_frame = replace(trace.entries[0], receipt=bad_receipt)
        with self.assertRaises(ExecutionTraceError):
            replace(trace, entries=(bad_frame,) + trace.entries[1:])

    def test_capture_does_not_decode_semantic_integers(self):
        with patch.object(
            self.backend, "observe_symbol",
            side_effect=AssertionError("execution capture must not decode symbols"),
        ):
            trace = self.adapter.capture(
                add_program(), memory(self.backend),
                trace_id="no-decode-001",
            )
        self.assertEqual(trace.status, "completed")

    def test_trace_rejects_event_metadata_detached_from_message(self):
        from vgi import Signal8ExecutionTrace
        trace = self.adapter.capture(
            add_program(), memory(self.backend), trace_id="event-binding-001",
        )
        altered = replace(trace.entries[2], event_digest="0" * 64)
        with self.assertRaises(ExecutionTraceError):
            replace(trace, entries=trace.entries[:2] + (altered,) + trace.entries[3:])

    def test_trace_rejects_a_missing_prefix_from_the_execution_chain(self):
        trace = self.adapter.capture(
            add_program(), memory(self.backend), trace_id="missing-prefix-001",
        )
        with self.assertRaises(ExecutionTraceError):
            replace(trace, entries=trace.entries[1:])

    def test_package_exposes_distinct_current_and_legacy_adapters(self):
        from vgi import LegacySignal8ExecutionAdapter
        self.assertIsNot(Signal8ExecutionAdapter, LegacySignal8ExecutionAdapter)
        self.assertEqual(Signal8ExecutionAdapter.__module__, "vgi.execution")
        self.assertEqual(LegacySignal8ExecutionAdapter.__module__, "vgi.signal8_trace")

    def test_replay_matches_exact_instruction_and_signal_state_trace(self):
        first = self.adapter.capture(
            add_program(), memory(self.backend),
            trace_id="observed-001",
        )
        replay = self.adapter.replay(first, trace_id="replay-001")
        report = verify_execution_replay(first, replay)
        self.assertTrue(report.matched)
        self.assertEqual(report.checked_entries, len(first.entries))
        self.assertEqual(report.mismatches, ())

    def test_different_initial_signal_state_fails_replay_comparison(self):
        observed = self.adapter.capture(
            add_program(), memory(self.backend, 3, 5),
            trace_id="observed-different-input",
        )
        other = self.adapter.capture(
            add_program(), memory(self.backend, 3, 4),
            trace_id="replayed-different-input",
        )
        report = verify_execution_replay(observed, other)
        self.assertFalse(report.matched)
        self.assertIn("initial_state_digest differs", report.mismatches)

    def test_projection_groups_only_repeatedly_observed_transitions(self):
        first = self.adapter.capture(
            add_program(), memory(self.backend), trace_id="projection-a",
        )
        second = self.adapter.replay(first, trace_id="projection-b")
        projection = project_execution_transitions((first, second))
        self.assertEqual(len(projection.observations), 5)
        self.assertEqual(projection.conflict_count, 0)
        self.assertTrue(all(item.occurrence_count == 2 for item in projection.observations))
        self.assertEqual(len(projection.state_digests), 6)
        self.assertEqual(
            projection.to_dict()["scope"],
            "only successful instruction transitions present in the supplied traces; "
            "unseen state/action pairs remain unqueried and are not classified as impossible",
        )

    def test_loop_repetition_is_visible_without_inventing_other_actions(self):
        program = Program("bounded-loop", (
            Instruction("JUMP", {"target": 0}),
            Instruction("HALT"),
        ))
        trace = self.adapter.capture(
            program, {}, trace_id="loop-001", max_steps=3,
        )
        self.assertEqual(trace.status, "step_limit")
        self.assertEqual(len(trace.entries), 3)
        projection = project_execution_transitions((trace,))
        self.assertEqual(len(projection.observations), 1)
        item = projection.observations[0]
        self.assertEqual(item.occurrence_count, 3)
        self.assertEqual(item.source_state_digest, item.target_state_digests[0])
        self.assertEqual(item.status, "one_observed_successor")
        self.assertEqual(len(projection.action_descriptors), 1)

    def test_failed_instruction_is_retained_but_not_projected_as_a_transition(self):
        program = Program("missing-memory", (
            Instruction("LOAD", {"dst": "x", "address": "missing"}),
            Instruction("HALT"),
        ))
        trace = self.adapter.capture(program, {}, trace_id="failure-001")
        self.assertEqual(trace.status, "failed")
        self.assertEqual(len(trace.entries), 1)
        entry = trace.entries[0]
        self.assertEqual(entry.record_type, "execution_failure")
        self.assertEqual(entry.state_before_digest, entry.state_after_digest)
        message = trace.exchange.messages[0]
        self.assertEqual(message.payload["exception_type"], "MissingMemoryCell")
        self.assertTrue(trace.encounters.contains(entry.encounter_id))
        with self.assertRaises(ExecutionTraceError):
            project_execution_transitions((trace,))

    def test_replay_rejects_a_different_ground(self):
        trace = self.adapter.capture(
            add_program(), memory(self.backend), trace_id="ground-guard-001",
        )
        from vgi import GroundSpec, SIGNAL8_GROUND
        ground = GroundSpec(
            ground_id=SIGNAL8_GROUND.ground_id,
            version="changed",
            domain_id=SIGNAL8_GROUND.domain_id,
            observer_profiles=SIGNAL8_GROUND.observer_profiles,
            instruction_set=SIGNAL8_GROUND.instruction_set,
            branch_ambiguity_policy=SIGNAL8_GROUND.branch_ambiguity_policy,
            assumptions=SIGNAL8_GROUND.assumptions,
            evidence=SIGNAL8_GROUND.evidence,
        )
        other = Signal8ExecutionAdapter(VirtualGroundInterpreter(ground, self.backend))
        with self.assertRaises(ExecutionTraceError):
            other.replay(trace, trace_id="wrong-ground")


if __name__ == "__main__":
    unittest.main()
