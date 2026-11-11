"""AND/OR proof-obligation graph and provenance-preserving Lean trace adapter.

VGI manages candidate proof exploration. It does not validate proof terms.
An accepted kernel status requires a separate upstream receipt whose
obligation and environment fingerprints match the imported proof state.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, Sequence

class ProofGroundError(ValueError):
    """Invalid proof state, hyper-transition, trace, or kernel receipt."""

def _canonical(value):
    try:
        return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
    except (TypeError,ValueError) as exc:
        raise ProofGroundError(f"proof data must be finite canonical JSON: {exc}") from exc

def _freeze(value):
    if isinstance(value,Mapping):
        if any(not isinstance(k,str) for k in value): raise ProofGroundError("proof object keys must be strings")
        return MappingProxyType({k:_freeze(v) for k,v in value.items()})
    if isinstance(value,(tuple,list)): return tuple(_freeze(v) for v in value)
    if value is None or isinstance(value,(str,int,float,bool)): return value
    raise ProofGroundError(f"unsupported proof value {type(value).__name__}")

def _thaw(value):
    if isinstance(value,Mapping): return {k:_thaw(v) for k,v in value.items()}
    if isinstance(value,tuple): return [_thaw(v) for v in value]
    return value

def _hash(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()

@dataclass(frozen=True,slots=True)
class ProofEnvironment:
    assistant: str
    assistant_version: str
    environment_fingerprint: str
    imports_fingerprint: str
    options_fingerprint: str
    def __post_init__(self):
        for name in ("assistant","assistant_version","environment_fingerprint","imports_fingerprint","options_fingerprint"):
            if not isinstance(getattr(self,name),str) or not getattr(self,name):
                raise ProofGroundError(f"{name} must be non-empty")
    def to_dict(self):
        return {"assistant":self.assistant,"assistant_version":self.assistant_version,
                "environment_fingerprint":self.environment_fingerprint,
                "imports_fingerprint":self.imports_fingerprint,"options_fingerprint":self.options_fingerprint}

@dataclass(frozen=True,slots=True)
class ProofObligation:
    """Scope-sensitive obligation; surface goal text alone is never its identity."""
    environment: ProofEnvironment
    goal: Mapping[str,Any]
    local_context: tuple[Mapping[str,Any],...]=()
    metavariables: Mapping[str,Any]|None=None
    assumptions: tuple[Mapping[str,Any],...]=()
    def __post_init__(self):
        if not isinstance(self.environment,ProofEnvironment): raise ProofGroundError("ProofEnvironment required")
        if not isinstance(self.goal,Mapping): raise ProofGroundError("goal must be a structured expression object")
        goal=_freeze(self.goal); context=tuple(_freeze(x) for x in self.local_context)
        assumptions=tuple(_freeze(x) for x in self.assumptions); metas=_freeze(self.metavariables or {})
        if any(not isinstance(x,Mapping) for x in context+assumptions) or not isinstance(metas,Mapping):
            raise ProofGroundError("context, assumptions and metavariables must be structured objects")
        _canonical({"goal":_thaw(goal),"local_context":_thaw(context),"metavariables":_thaw(metas),"assumptions":_thaw(assumptions)})
        object.__setattr__(self,"goal",goal);object.__setattr__(self,"local_context",context)
        object.__setattr__(self,"metavariables",metas);object.__setattr__(self,"assumptions",assumptions)
    def to_dict(self):
        return {"environment":self.environment.to_dict(),"goal":_thaw(self.goal),
                "local_context":_thaw(self.local_context),"metavariables":_thaw(self.metavariables),
                "assumptions":_thaw(self.assumptions)}
    @property
    def fingerprint(self): return _hash(self.to_dict())

@dataclass(frozen=True,slots=True)
class ProofHyperTransition:
    """One OR alternative; all subgoals on this hyperedge are jointly required (AND)."""
    source_id: str
    tactic: str
    subgoal_ids: tuple[str,...]
    attempt_status: str="candidate"
    evidence_ref: str=""
    transition_id: str=""
    def __post_init__(self):
        allowed={"candidate","elaborated","timeout","rejected"}
        if not self.source_id or not self.tactic: raise ProofGroundError("source and tactic are required")
        subgoals=tuple(self.subgoal_ids)
        if len(set(subgoals))!=len(subgoals): raise ProofGroundError("hyperedge cannot repeat a subgoal")
        if self.attempt_status not in allowed: raise ProofGroundError(f"attempt_status must be one of {sorted(allowed)}")
        object.__setattr__(self,"subgoal_ids",subgoals)
        if not self.transition_id:
            object.__setattr__(self,"transition_id",_hash({
                "source":self.source_id,"tactic":self.tactic,"subgoals":list(subgoals),
                "status":self.attempt_status,"evidence_ref":self.evidence_ref
            }))

@dataclass(frozen=True,slots=True)
class VerifiedKernelReceipt:
    """Separately verified kernel result bound to obligation, term and environment."""
    obligation_id: str
    proof_term_fingerprint: str
    environment_fingerprint: str
    checker_id: str
    checker_version: str
    result: str
    receipt_ref: str
    def __post_init__(self):
        for name in ("obligation_id","proof_term_fingerprint","environment_fingerprint","checker_id","checker_version","receipt_ref"):
            if not getattr(self,name): raise ProofGroundError(f"kernel receipt {name} is required")
        if self.result not in ("accepted","rejected"): raise ProofGroundError("kernel receipt result must be accepted or rejected")

class ProofGround:
    """Finite AND/OR hypergraph of obligations and tactic attempts."""
    def __init__(self,environment,obligations,transitions,receipts=(),observed_kernel_claims=()):
        self.environment=environment;self.obligations=tuple(obligations)
        self.transitions=tuple(transitions);self.receipts=tuple(receipts)
        self.observed_kernel_claims=tuple(_freeze(item) for item in observed_kernel_claims)
        by_id={item.fingerprint:item for item in self.obligations}
        if len(by_id)!=len(self.obligations): raise ProofGroundError("duplicate canonical proof obligations")
        if any(item.environment!=environment for item in self.obligations):
            raise ProofGroundError("obligations must share one trace environment")
        for edge in self.transitions:
            if edge.source_id not in by_id or any(x not in by_id for x in edge.subgoal_ids):
                raise ProofGroundError("hyper-transition references an undeclared obligation")
        receipt_map={}
        for receipt in self.receipts:
            if not isinstance(receipt,VerifiedKernelReceipt) or receipt.obligation_id not in by_id:
                raise ProofGroundError("receipt references an undeclared obligation")
            if receipt.environment_fingerprint!=environment.environment_fingerprint:
                raise ProofGroundError("kernel receipt environment does not match trace")
            previous=receipt_map.get(receipt.obligation_id)
            if previous is not None and previous!=receipt:
                raise ProofGroundError("conflicting kernel receipts for one obligation")
            receipt_map[receipt.obligation_id]=receipt
        self._by_id=MappingProxyType(by_id);self._receipts=MappingProxyType(receipt_map)
    @property
    def obligation_ids(self): return tuple(self._by_id)
    def obligation(self,obligation_id):
        try:return self._by_id[obligation_id]
        except KeyError as exc:raise ProofGroundError("unknown obligation") from exc
    def kernel_status(self,obligation_id):
        receipt=self._receipts.get(obligation_id)
        if receipt is None:return "unverified"
        return "kernel_accepted" if receipt.result=="accepted" else "kernel_rejected"
    def alternatives(self,source_id,tactic):
        if source_id not in self._by_id: raise ProofGroundError("unknown source obligation")
        return tuple(x for x in self.transitions if x.source_id==source_id and x.tactic==tactic)
    def unresolved_obligations(self):
        return tuple(key for key in self._by_id if self.kernel_status(key)=="unverified")
    def summary(self):
        return {"format":"VGI-ProofGroundSummary-1","environment":self.environment.to_dict(),
                "obligation_count":len(self.obligations),"hyper_transition_count":len(self.transitions),
                "candidate_attempts":sum(x.attempt_status=="candidate" for x in self.transitions),
                "timed_out_attempts":sum(x.attempt_status=="timeout" for x in self.transitions),
                "rejected_attempts":sum(x.attempt_status=="rejected" for x in self.transitions),
                "kernel_accepted_obligations":sum(self.kernel_status(x)=="kernel_accepted" for x in self._by_id),
                "kernel_rejected_obligations":sum(self.kernel_status(x)=="kernel_rejected" for x in self._by_id),
                "unverified_obligations":len(self.unresolved_obligations()),
                "observed_untrusted_kernel_claims":[_thaw(x) for x in self.observed_kernel_claims]}

class ProofGroundAdapter:
    """Import a normalized Lean trace; raw JSON kernel claims are never trusted."""
    FORMAT="VGI-LeanProofTrace-1"
    @classmethod
    def from_lean_trace(cls,payload:Mapping[str,Any],*,verified_receipts:Sequence[VerifiedKernelReceipt]=()):
        if not isinstance(payload,Mapping) or payload.get("format")!=cls.FORMAT:
            raise ProofGroundError(f"expected {cls.FORMAT}")
        try:
            environment=ProofEnvironment(**payload["environment"])
            key_to_id={};obligations=[]
            for row in payload["obligations"]:
                item=ProofObligation(environment,row["goal"],tuple(row.get("local_context",())),
                                     row.get("metavariables",{}),tuple(row.get("assumptions",())))
                key=row["key"]
                if not isinstance(key,str) or not key or key in key_to_id:
                    raise ProofGroundError("obligation keys must be unique non-empty strings")
                key_to_id[key]=item.fingerprint;obligations.append(item)
            transitions=[]
            for row in payload.get("transitions",()):
                source=row["source"];subgoals=tuple(row.get("subgoals",()))
                if source not in key_to_id or any(key not in key_to_id for key in subgoals):
                    raise ProofGroundError("transition references unknown obligation key")
                transitions.append(ProofHyperTransition(
                    key_to_id[source],row["tactic"],tuple(key_to_id[key] for key in subgoals),
                    row.get("attempt_status","candidate"),row.get("evidence_ref","")))
        except (KeyError,TypeError) as exc:
            raise ProofGroundError(f"malformed Lean proof trace: {exc}") from exc
        # Raw claims are retained for audit but never promoted to kernel status.
        raw_claims = payload.get("kernel_claims", payload.get("kernel_accepted", ()))
        if not isinstance(raw_claims, (list, tuple)):
            raise ProofGroundError("observed kernel claims must be a list")
        return ProofGround(
            environment, obligations, transitions, tuple(verified_receipts),
            observed_kernel_claims=tuple(raw_claims),
        )

__all__=["ProofGroundError","ProofEnvironment","ProofObligation","ProofHyperTransition",
         "VerifiedKernelReceipt","ProofGround","ProofGroundAdapter"]
