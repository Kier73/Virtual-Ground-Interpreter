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
    ContextualQuotient, ObserverContext, QuotientEdge, RelationalError,
    behavioral_distance, contextual_quotient, quotient_map,
    quotient_transition_table, refinement_series,
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
    "QuotientEdge", "refinement_series", "contextual_quotient", "quotient_map",
    "quotient_transition_table", "behavioral_distance",
]
