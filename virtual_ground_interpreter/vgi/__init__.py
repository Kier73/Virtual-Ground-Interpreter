"""Virtual Ground Interpreter: a bounded signal-state execution reference."""
from .ground import GroundSpec, SIGNAL8_GROUND
from .compiler import (AddExpr, ConditionalExpr, EqualityGuard, IdentityGuard, InputExpr,
                       OutputSpec, ReframeExpr, SubExpr, TaskCompileError, TaskCompiler, TaskSpec)
from .ir import Instruction, Program, ProgramError
from .machine import (
    AmbiguousBranchError, ExecutionResult, MissingMemoryCell, MissingRegister,
    RuntimeErrorVGI, SignalStateMachine, StepLimitExceeded, VirtualGroundInterpreter,
)
from .values import EqualityDecision, OBSERVERS, Signal8Backend, SignalValue, ValueErrorVGI

__version__ = "0.1.0"

__all__ = [
    "__version__", "GroundSpec", "SIGNAL8_GROUND", "Instruction", "Program", "ProgramError",
    "AddExpr", "ConditionalExpr", "EqualityGuard", "IdentityGuard", "InputExpr",
    "OutputSpec", "ReframeExpr", "SubExpr", "TaskCompileError", "TaskCompiler", "TaskSpec",
    "AmbiguousBranchError", "ExecutionResult", "MissingMemoryCell", "MissingRegister",
    "RuntimeErrorVGI", "SignalStateMachine", "StepLimitExceeded", "VirtualGroundInterpreter",
    "EqualityDecision", "OBSERVERS", "Signal8Backend", "SignalValue", "ValueErrorVGI",
]
