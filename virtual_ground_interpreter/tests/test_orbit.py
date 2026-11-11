import hashlib
import unittest
from dataclasses import replace

from vgi import (
    Instruction,
    Program,
    Signal8Backend,
    Signal8ExecutionAdapter,
    SignalValue,
    VirtualGroundInterpreter,
    ObservedOutcome,
    verify_execution_reference,
)
from vgi.orbit import (
    ExecutionOrbitAdapter,
    OrbitNavigator,
    OrbitPolicy,
    OrbitTimeCoordinate,
)
from vgi.transitions import (
    GroundTransitionSystem,
    TransitionObservation,
    TransitionOutcome,
)


def arithmetic_program():
    return Program("orbit-arithmetic", (
        Instruction("LOAD", {"dst": "a", "address": "a"}),
        Instruction("LOAD", {"dst": "b", "address": "b"}),
        Instruction("ADD", {"dst": "sum", "left": "a", "right": "b"}),
        Instruction("EMIT", {"src": "sum", "label": "sum"}),
        Instruction("HALT"),
    ))


def looping_program():
    return Program("orbit-loop", (
        Instruction("LOAD", {"dst": "x", "address": "x"}),
        Instruction("JUMP", {"target": 0}),
        Instruction("HALT"),
    ))


class ExecutionOrbitIngestionTests(unittest.TestCase):
    def setUp(self):
        self.backend = Signal8Backend()
        self.adapter = Signal8ExecutionAdapter(
            VirtualGroundInterpreter(backend=self.backend)
        )
        self.orbit_adapter = ExecutionOrbitAdapter()

    def capture_arithmetic(self, trace_id="orbit-arithmetic-trace"):
        trace = self.adapter.capture(
            arithmetic_program(),
            {
                "a": self.backend.encode_symbol(2, observer=1),
                "b": self.backend.encode_symbol(3, observer=3),
            },
            trace_id=trace_id,
        )
        return trace, verify_execution_reference(trace)

    def test_reference_match_is_required_and_bound_to_exact_trace(self):
        trace, report = self.capture_arithmetic()
        ingestion = self.orbit_adapter.ingest((trace,), (report,))
        self.assertEqual(ingestion.trace_summaries[0].trace_fingerprint, trace.fingerprint)
        self.assertEqual(ingestion.trace_summaries[0].reference_fingerprint, report.fingerprint)
        self.assertEqual(ingestion.initial_time, OrbitTimeCoordinate(ingestion.clock_id, 0))

        with self.assertRaises(ValueError):
            self.orbit_adapter.ingest(
                (trace,),
                (report.__class__(
                    trace_id=report.trace_id,
                    trace_fingerprint=report.trace_fingerprint,
                    program_fingerprint=report.program_fingerprint,
                    ground_fingerprint=report.ground_fingerprint,
                    numerical_tolerance_rad=report.numerical_tolerance_rad,
                    status="unsupported",
                    checked_steps=report.checked_steps,
                    checked_writes=report.checked_writes,
                    decoded_inputs=report.decoded_inputs,
                    unsupported_reason="deliberate test rejection",
                ),),
            )

    def test_reordered_duplicate_and_missing_deliveries_remain_distinct(self):
        trace, report = self.capture_arithmetic("delivery-disorder")
        ingestion = self.orbit_adapter.ingest(
            (trace,),
            (report,),
            delivery_orders={trace.trace_id: (3, 1, 1, 2)},
        )
        summary = ingestion.trace_summaries[0]
        self.assertEqual(summary.arrival_order, (3, 1, 1, 2))
        self.assertEqual(summary.accepted_sequences, (3, 1, 2))
        self.assertEqual(summary.duplicate_sequences, (1,))
        self.assertEqual(summary.missing_sequences, (4, 5))
        self.assertEqual(ingestion.duplicate_count, 1)
        self.assertEqual(ingestion.missing_count, 2)
        self.assertEqual(len(ingestion.evidence_ledger.evidence), 3)
        delayed_delivery = next(
            item for item in ingestion.deliveries
            if item.sequence == 3 and item.disposition == "accepted_transition"
        )
        self.assertEqual(delayed_delivery.arrival_index, 0)
        self.assertEqual(delayed_delivery.logical_tick, 2)
        self.assertEqual(ingestion.time_for(trace.trace_id, 3).tick, 2)

        # No transition is admitted merely because it was observed.
        candidate = ingestion.build_ground()
        self.assertEqual(candidate.observations, ())
        self.assertEqual(candidate.status(trace.initial_state_digest, ingestion.actions[0]), "unknown")

    def test_one_event_requires_explicit_policy_finalization(self):
        trace, report = self.capture_arithmetic("explicit-finalization")
        ingestion = self.orbit_adapter.ingest(
            (trace,), (report,), delivery_orders={trace.trace_id: (1,)}
        )
        evidence = ingestion.evidence_ledger.evidence[0]
        decision = ingestion.decision(evidence.source_state, evidence.action)
        self.assertEqual(decision.status, "QUORUM")
        self.assertEqual(ingestion.evidence_ledger.finalizations, ())

        finalized = ingestion.finalize(evidence.source_state, evidence.action)
        self.assertEqual(finalized.evidence_ledger.decision(
            evidence.source_state, evidence.action
        ).status, "AUTHORIZED")
        ground = finalized.build_ground()
        self.assertEqual(ground.status(evidence.source_state, evidence.action), "known")
        self.assertEqual(ground.observations[0].evidence, (evidence.evidence_id,))
        self.assertTrue(ground.unknown_pairs)

    def test_quorum_shortfall_does_not_admit_a_transition(self):
        trace, report = self.capture_arithmetic("quorum-shortfall")
        source = trace.exchange.messages[0].provenance.source
        # Two independent sources are required, but only one has supplied evidence.
        ingestion = self.orbit_adapter.ingest(
            (trace,), (report,), allowed_sources=(source, "independent-peer"),
            quorum=2, strict=True, delivery_orders={trace.trace_id: (1,)},
        )
        evidence = ingestion.evidence_ledger.evidence[0]
        self.assertEqual(ingestion.decision(evidence.source_state, evidence.action).status, "PENDING")
        refused = ingestion.finalize(evidence.source_state, evidence.action)
        self.assertEqual(refused.evidence_ledger.decision(
            evidence.source_state, evidence.action
        ).status, "REFUSED")
        self.assertEqual(refused.build_ground().observations, ())

    def test_synthetic_competing_source_conflict_is_retained_but_not_admitted(self):
        trace, report = self.capture_arithmetic("synthetic-source-conflict")
        runtime_source = trace.exchange.messages[0].provenance.source
        ingestion = self.orbit_adapter.ingest(
            (trace,),
            (report,),
            allowed_sources=(runtime_source, "independent-peer"),
            quorum=1,
            strict=True,
            delivery_orders={trace.trace_id: (1,)},
        )
        original = ingestion.evidence_ledger.evidence[0]
        alternative_target = next(
            state for state in ingestion.states
            if state != original.outcomes[0].target
        )
        alternative_output = tuple(
            (value + 1) % 8 for value in original.outcomes[0].output
        )
        # This is a synthetic competing-source claim for policy-path testing,
        # not an authenticated observation from a real peer adapter.
        competing = replace(
            original,
            evidence_id="synthetic-peer-evidence",
            encounter_id="synthetic-peer-encounter",
            message_id="synthetic-peer-message",
            transport_id="synthetic-peer-transport",
            frame_id="synthetic-peer-frame",
            transport_sequence=1,
            source="independent-peer",
            outcomes=(ObservedOutcome(alternative_target, alternative_output),),
            payload_digest=hashlib.sha256(b"synthetic conflicting payload").hexdigest(),
        )
        ledger = ingestion.evidence_ledger.ingest(competing)
        conflict = ledger.status(original.source_state, original.action)
        self.assertEqual(conflict.status, "CONFLICT")

        finalized = replace(ingestion, evidence_ledger=ledger).finalize(
            original.source_state, original.action
        )
        self.assertEqual(
            finalized.evidence_ledger.decision(original.source_state, original.action).status,
            "CONFLICT",
        )
        self.assertEqual(finalized.build_ground().observations, ())

    def test_failed_attempt_is_retained_but_never_projected_as_a_transition(self):
        program = Program("orbit-failed-attempt", (
            Instruction("LOAD", {"dst": "missing", "address": "not-present"}),
            Instruction("HALT"),
        ))
        trace = self.adapter.capture(program, {}, trace_id="failed-orbit-attempt")
        report = verify_execution_reference(trace)
        self.assertEqual(trace.status, "failed")
        ingestion = self.orbit_adapter.ingest((trace,), (report,))
        self.assertEqual(ingestion.ignored_failure_count, 1)
        self.assertEqual(ingestion.evidence_ledger.evidence, ())
        self.assertEqual(ingestion.trace_summaries[0].failure_sequences, (1,))
        self.assertEqual(ingestion.build_ground().observations, ())

    def test_event_codebook_is_stable_under_trace_order(self):
        trace_a, report_a = self.capture_arithmetic("codebook-a")
        trace_b, report_b = self.capture_arithmetic("codebook-b")
        left = self.orbit_adapter.ingest((trace_a, trace_b), (report_a, report_b))
        right = self.orbit_adapter.ingest((trace_b, trace_a), (report_b, report_a))
        self.assertEqual(
            tuple(item.to_dict() for item in left.event_tokens),
            tuple(item.to_dict() for item in right.event_tokens),
        )
        self.assertEqual(left.channels, right.channels)
        self.assertNotEqual(left.context_digest, right.context_digest)


class LogicalOrbitNavigationTests(unittest.TestCase):
    def setUp(self):
        self.backend = Signal8Backend()
        self.adapter = Signal8ExecutionAdapter(
            VirtualGroundInterpreter(backend=self.backend)
        )
        self.orbit_adapter = ExecutionOrbitAdapter()

    def compile_loop_orbit(self):
        trace = self.adapter.capture(
            looping_program(),
            {"x": self.backend.encode_symbol(5, observer=1)},
            trace_id="verified-loop-orbit",
            max_steps=12,
        )
        report = verify_execution_reference(trace)
        self.assertEqual(report.status, "match")
        ingestion = self.orbit_adapter.ingest((trace,), (report,), base_tick=40)
        events = tuple(sorted({
            item.event for item in ingestion.evidence_ledger.evidence
        }))
        for source_state, action in events:
            ingestion = ingestion.finalize(source_state, action)
        ground = ingestion.build_ground()
        policy = OrbitPolicy.derive(ground)
        return ingestion, ground, policy

    def test_repeated_loop_visits_share_semantic_effects_not_occurrence_indices(self):
        trace = self.adapter.capture(
            looping_program(),
            {"x": self.backend.encode_symbol(5, observer=1)},
            trace_id="repeated-semantic-effect-loop",
            max_steps=12,
        )
        report = verify_execution_reference(trace)
        self.assertEqual(report.status, "match")

        ingestion = self.orbit_adapter.ingest((trace,), (report,))
        # Every raw event has a unique step index, but the semantic effect
        # codebook must identify recurring LOAD and JUMP effects consistently.
        self.assertEqual(len(ingestion.event_tokens), 2)
        repeated = {}
        for item in ingestion.evidence_ledger.evidence:
            repeated.setdefault((item.source_state, item.action), []).append(item)
        repeated_groups = [items for items in repeated.values() if len(items) > 1]
        self.assertTrue(repeated_groups)
        for items in repeated_groups:
            self.assertEqual(len({item.signature for item in items}), 1)
            decision = ingestion.decision(items[0].source_state, items[0].action)
            self.assertEqual(decision.status, "QUORUM")

    def test_closed_cycle_supports_verified_large_logical_time_jump(self):
        ingestion, ground, policy = self.compile_loop_orbit()
        self.assertEqual(len(ground.observations), 3)
        self.assertEqual(len(policy.actions_by_state), 3)
        index = OrbitNavigator.compile(
            ground,
            policy,
            start_state=ground.initial_state,
            start_time=ingestion.initial_time,
        )
        self.assertTrue(index.closed)
        self.assertEqual(index.cycle_start_index, 1)
        self.assertEqual(index.cycle_period, 2)

        distant = ingestion.initial_time.advance(10**12)
        result = index.state_at(distant)
        self.assertEqual(result.status, "located")
        self.assertEqual(result.method, "cycle_skip")
        self.assertGreater(result.skipped_cycles, 0)
        self.assertEqual(result.resolved_time, distant)
        self.assertIn(result.state, ground.states)

    def test_target_state_can_be_located_at_a_future_skipped_coordinate(self):
        ingestion, ground, policy = self.compile_loop_orbit()
        index = OrbitNavigator.compile(
            ground, policy,
            start_state=ground.initial_state,
            start_time=ingestion.initial_time,
        )
        target = index.states[2]
        from_time = ingestion.initial_time.advance(10**12)
        result = index.locate_state(target, from_time=from_time)
        self.assertEqual(result.status, "located")
        self.assertEqual(result.state, target)
        self.assertGreater(result.skipped_cycles, 0)
        self.assertGreaterEqual(result.resolved_time.tick, from_time.tick)

    def test_closed_orbit_can_prove_a_target_absent_from_that_orbit(self):
        ingestion, ground, policy = self.compile_loop_orbit()
        index = OrbitNavigator.compile(
            ground, policy,
            start_state=ground.initial_state,
            start_time=ingestion.initial_time,
        )
        # HALT is in the declared Program action vocabulary but never selected
        # by this closed two-state orbit.
        unreachable = "f" * 64
        extended_states = ground.states + (unreachable,)
        expanded = GroundTransitionSystem(
            states=extended_states,
            actions=ground.actions,
            initial_state=ground.initial_state,
            channels=ground.channels,
            observations=ground.observations,
            metadata={"test": "unreachable-state"},
        )
        expanded_policy = OrbitPolicy.from_mapping(
            expanded, policy.actions_by_state
        )
        expanded_index = OrbitNavigator.compile(
            expanded, expanded_policy,
            start_state=expanded.initial_state,
            start_time=ingestion.initial_time,
        )
        result = expanded_index.locate_state(unreachable)
        self.assertEqual(result.status, "unreachable_on_closed_orbit")

    def test_incomplete_ground_blocks_future_skip_instead_of_guessing(self):
        states = ("s0", "s1", "s2")
        ground = GroundTransitionSystem(
            states=states,
            actions=("A",),
            initial_state="s0",
            channels=("y",),
            observations=(
                TransitionObservation("s0", "A", (TransitionOutcome("s1", (1,)),)),
            ),
        )
        policy = OrbitPolicy.from_mapping(ground, {"s0": "A", "s1": "A"})
        index = OrbitNavigator.compile(
            ground, policy,
            start_state="s0",
            start_time=OrbitTimeCoordinate("partial-clock", 7),
        )
        self.assertFalse(index.closed)
        self.assertEqual(index.stop_status, "blocked_unknown")
        beyond = index.state_at(OrbitTimeCoordinate("partial-clock", 1000))
        self.assertEqual(beyond.status, "blocked_unknown")
        self.assertIsNone(beyond.state)

    def test_ambiguous_edge_blocks_orbit_without_selecting_an_outcome(self):
        ground = GroundTransitionSystem(
            states=("s0", "s1"),
            actions=("A",),
            initial_state="s0",
            channels=("y",),
            observations=(
                TransitionObservation(
                    "s0", "A",
                    (
                        TransitionOutcome("s0", (0,)),
                        TransitionOutcome("s1", (1,)),
                    ),
                    support_count=2,
                    evidence=("candidate-a", "candidate-b"),
                ),
            ),
        )
        policy = OrbitPolicy.from_mapping(ground, {"s0": "A"})
        index = OrbitNavigator.compile(
            ground, policy,
            start_state="s0",
            start_time=OrbitTimeCoordinate("ambiguous-clock", 0),
        )
        self.assertEqual(index.stop_status, "blocked_ambiguous")
        result = index.state_at(OrbitTimeCoordinate("ambiguous-clock", 10))
        self.assertEqual(result.status, "blocked_ambiguous")

    def test_orbit_clock_identity_is_not_interchangeable(self):
        _, ground, policy = self.compile_loop_orbit()
        index = OrbitNavigator.compile(
            ground, policy,
            start_state=ground.initial_state,
            start_time=OrbitTimeCoordinate("scheduler-A", 12),
        )
        result = index.state_at(OrbitTimeCoordinate("scheduler-B", 100))
        self.assertEqual(result.status, "clock_mismatch")
        self.assertIsNone(result.resolved_time)

    def test_policy_conflicts_are_not_silently_resolved(self):
        ground = GroundTransitionSystem(
            states=("s0", "s1", "s2"),
            actions=("A", "B"),
            initial_state="s0",
            channels=("y",),
            observations=(
                TransitionObservation("s0", "A", (TransitionOutcome("s1", (0,)),)),
                TransitionObservation("s0", "B", (TransitionOutcome("s2", (0,)),)),
            ),
        )
        policy = OrbitPolicy.derive(ground)
        self.assertNotIn("s0", policy.actions_by_state)
        self.assertEqual(policy.policy_ambiguous_states["s0"], ("A", "B"))
        index = OrbitNavigator.compile(
            ground, policy,
            start_state="s0",
            start_time=OrbitTimeCoordinate("policy-clock", 0),
        )
        self.assertEqual(index.stop_status, "policy_ambiguous")


if __name__ == "__main__":
    unittest.main()
