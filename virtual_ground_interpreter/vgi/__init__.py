"""Virtual Ground Interpreter: a bounded signal-state execution reference."""
from .ground import GroundSpec, SIGNAL8_GROUND
from .compiler import (AddExpr, ConditionalExpr, EqualityGuard, IdentityGuard, InputExpr,
                       OutputSpec, ReframeExpr, SubExpr, TaskCompileError, TaskCompiler, TaskSpec)
from .ir import Instruction, Program, ProgramError
from .machine import (
    AmbiguousBranchError, ExecutionResult, MissingMemoryCell, MissingRegister,
    RuntimeErrorVGI, SignalStateMachine, StepLimitExceeded, VirtualGroundInterpreter,
)
from .values import (AmbiguousSymbolObservation, EqualityDecision, OBSERVERS,
                     Signal8Backend, SignalValue, ValueErrorVGI)
from .transitions import (
    AmbiguousTransitionError, CompiledTransitionProgram, CompiledTransitionRun,
    GroundTransitionSystem, TransitionCompileError, TransitionCompiler,
    TransitionObservation, TransitionOutcome, TransitionRun, TransitionStep,
    TransitionSystemError, UnknownTransitionError, differential_verify,
)
from .relational import (
    ContextualQuotient, ObserverContext, PartialContextualComparison,
    PartialPairBlocker, QuotientEdge,
    RelationalError, behavioral_distance, contextual_quotient,
    partial_contextual_comparison, partial_refinement_series, quotient_map,
    quotient_transition_table, refinement_series,
)
from .attention import (
    AttentionCandidate, AttentionError, AttentionPlan, AttentionScore,
    exhaustive_attention_plan, greedy_attention_plan, rank_attention_probes,
    unresolved_pair_count,
)
from .joint_attention import (
    AttentionRouteStep, AttentionSearchRecord, JointAttentionPlan,
    beam_attention_plan,
)
from .inquiry import (
    BlockedTransition, DistinguishingWitness, InquiryError, OpenWorldBoundary,
    PairInquiry, PerceptionInquiryReport, inquire_unresolved_pairs,
)
from .encounters import (
    AssociationAssessment, AssociationError, AssociationHypothesis,
    AssociationLedger, Encounter, EncounterError, EncounterLedger,
    EncounterProvenance,
)
from .channels import (
    ChannelAdapter, ChannelContract, ChannelError, ChannelExchangeLedger,
    ChannelMessage, PredictiveGroundAdapter,
)
from .signal8_trace import (
    SIGNAL8_EXECUTION_CONTRACT,
    Signal8ExecutionAdapter as LegacySignal8ExecutionAdapter,
    Signal8ExecutionCapture, Signal8TraceError, runtime_configuration,
    runtime_state_id, runtime_state_id_from_configuration,
)
from .evidence import (
    EvidenceError, GroundReconstructionCertificate, GroundReconstructionVerifier,
    ObservedOutcome, TransitionEvidence, TransitionEvidenceDecision,
    TransitionEvidenceFinalization, TransitionEvidenceLedger, TransitionEvidencePolicy,
    TransportFrameReceipt,
)
from .execution import (
    ExecutionReplayReport, ExecutionTraceError, ExecutionTraceFrame,
    ExecutionTransitionObservation, ExecutionTransitionProjection,
    Signal8ExecutionAdapter, Signal8ExecutionTrace,
    project_execution_transitions, verify_execution_replay,
)
from .reference import (
    ReferenceExecutionError, ReferenceExecutionReport, verify_execution_reference,
)
from .orbit import (
    ExecutionOrbitAdapter, ExecutionOrbitIngestion, EventToken,
    FrameDeliveryRecord, OrbitError, OrbitIndex, OrbitNavigationResult,
    OrbitNavigator, OrbitPathStep, OrbitPolicy, OrbitTimeCoordinate,
    TraceDeliverySummary,
)

__version__ = "0.2.0"

__all__ = [
    "__version__", "GroundSpec", "SIGNAL8_GROUND", "Instruction", "Program", "ProgramError",
    "AddExpr", "ConditionalExpr", "EqualityGuard", "IdentityGuard", "InputExpr",
    "OutputSpec", "ReframeExpr", "SubExpr", "TaskCompileError", "TaskCompiler", "TaskSpec",
    "AmbiguousBranchError", "ExecutionResult", "MissingMemoryCell", "MissingRegister",
    "RuntimeErrorVGI", "SignalStateMachine", "StepLimitExceeded", "VirtualGroundInterpreter",
    "EqualityDecision", "OBSERVERS", "Signal8Backend", "SignalValue", "ValueErrorVGI",
    "AmbiguousSymbolObservation", "GroundTransitionSystem", "TransitionObservation",
    "TransitionOutcome", "TransitionStep", "TransitionRun", "TransitionSystemError",
    "UnknownTransitionError", "AmbiguousTransitionError", "TransitionCompileError",
    "TransitionCompiler", "CompiledTransitionProgram", "CompiledTransitionRun",
    "differential_verify", "RelationalError", "ObserverContext", "ContextualQuotient",
    "PartialContextualComparison", "PartialPairBlocker", "partial_refinement_series",
    "partial_contextual_comparison", "QuotientEdge", "refinement_series",
    "contextual_quotient", "quotient_map",
    "quotient_transition_table", "behavioral_distance",
    "AttentionError", "AttentionCandidate", "AttentionScore", "AttentionPlan",
    "unresolved_pair_count", "rank_attention_probes", "greedy_attention_plan",
    "exhaustive_attention_plan", "AttentionRouteStep", "AttentionSearchRecord",
    "JointAttentionPlan", "beam_attention_plan",
    "InquiryError", "BlockedTransition", "DistinguishingWitness", "PairInquiry",
    "OpenWorldBoundary", "PerceptionInquiryReport", "inquire_unresolved_pairs",
    "EncounterError", "EncounterProvenance", "Encounter", "EncounterLedger",
    "AssociationError", "AssociationHypothesis", "AssociationAssessment", "AssociationLedger",
    "ChannelError", "ChannelContract", "ChannelMessage", "ChannelAdapter",
    "ChannelExchangeLedger", "PredictiveGroundAdapter",
    "EvidenceError", "ObservedOutcome", "TransitionEvidencePolicy", "TransitionEvidence",
    "TransitionEvidenceDecision", "TransitionEvidenceFinalization", "TransitionEvidenceLedger",
    "TransportFrameReceipt", "GroundReconstructionCertificate", "GroundReconstructionVerifier",
    "SIGNAL8_EXECUTION_CONTRACT", "LegacySignal8ExecutionAdapter",
    "Signal8ExecutionCapture", "Signal8TraceError", "runtime_configuration",
    "runtime_state_id", "runtime_state_id_from_configuration",
    "ExecutionTraceError", "ExecutionTraceFrame", "Signal8ExecutionTrace",
    "Signal8ExecutionAdapter", "ExecutionReplayReport",
    "ExecutionTransitionObservation", "ExecutionTransitionProjection",
    "project_execution_transitions", "verify_execution_replay",
    "ReferenceExecutionError", "ReferenceExecutionReport", "verify_execution_reference",
    "OrbitError", "OrbitTimeCoordinate", "EventToken", "FrameDeliveryRecord",
    "TraceDeliverySummary", "ExecutionOrbitIngestion", "ExecutionOrbitAdapter",
    "OrbitPolicy", "OrbitPathStep", "OrbitNavigationResult", "OrbitIndex",
    "OrbitNavigator",
]
