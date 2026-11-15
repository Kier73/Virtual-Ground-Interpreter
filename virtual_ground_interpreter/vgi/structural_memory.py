"""GEOMETRY-FIRST-008: portable, independently reverified similarity-basis memory.

A record contains exact finite-field operand snapshots and a proposed structural
witness. Admission reruns every local mathematical check, but deliberately NEVER
reruns the expensive commutant/eigenbasis *search*. SHA-256 provides content
identity only; external trust and E-CPU operator authority remain separate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Mapping

from .similarity_blocks import (
    CertifiedSimilarityBlocks, SimilarityNavigationReceipt,
    _compose_block, _local_factors,
)
from .typed_operator_navigation import (
    DenseMap, DiagonalMap, FiniteSpace, OperatorChain, TypedOperatorError,
    TypedVector, _digest, _int,
)

SCHEMA = "VGI-PortableSimilarityMemory-1"
PROOF_SCHEMA = "VGI-SimilarityWitness-1"
MAX_BYTES = 1_048_576
MAX_TICK_BITS = 4096


def _object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise TypedOperatorError(f"{label} requires exact canonical fields")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise TypedOperatorError(f"{label} must be a SHA-256 identity")
    return value


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in pairs:
        if k in result:
            raise TypedOperatorError("duplicate JSON field")
        result[k] = v
    return result


def _deny_constant(value: str) -> None:
    raise TypedOperatorError("non-finite JSON number")


def _decode(data: bytes | str | Mapping[str, Any]) -> dict[str, Any]:
    """Decode bounded canonical JSON; refuse duplicate keys or ambiguous bytes."""
    if isinstance(data, Mapping):
        try:
            data = json.dumps(data, sort_keys=True, separators=(',', ':'),
                              ensure_ascii=False, allow_nan=False).encode('utf-8')
        except (TypeError, ValueError, OverflowError) as exc:
            raise TypedOperatorError("memory mapping is not JSON") from exc
    elif isinstance(data, str):
        try:
            data = data.encode('utf-8')
        except UnicodeError as exc:
            raise TypedOperatorError("invalid UTF-8 memory") from exc
    if not isinstance(data, bytes) or len(data) > MAX_BYTES:
        raise TypedOperatorError("memory must be bounded UTF-8 JSON bytes")
    try:
        decoded = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs_no_duplicates,
                             parse_constant=_deny_constant)
    except (ValueError, UnicodeError, OverflowError, RecursionError) as exc:
        raise TypedOperatorError("malformed memory JSON") from exc
    if not isinstance(decoded, dict):
        raise TypedOperatorError("memory must be a JSON object")
    return decoded


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _space(value: Any) -> FiniteSpace:
    item = _object(value, {'frame', 'dimension', 'ring', 'modulus'}, 'coordinate frame')
    if item['ring'] != 'Z/modulus Z':
        raise TypedOperatorError("unsupported coordinate ring")
    frame = FiniteSpace(item['frame'], item['dimension'], item['modulus'])
    if frame.to_dict() != item:
        raise TypedOperatorError("noncanonical coordinate frame")
    return frame


def _leaf(value: Any) -> DenseMap | DiagonalMap:
    if not isinstance(value, dict):
        raise TypedOperatorError("invalid operator snapshot")
    kind = value.get('type')
    keys = ({'type','identity','domain','codomain','rows'} if kind == 'dense'
            else {'type','identity','domain','codomain','diagonal'} if kind == 'diagonal'
            else set())
    item = _object(value, keys, 'operator snapshot')
    domain, codomain = _space(item['domain']), _space(item['codomain'])
    if kind == 'dense':
        op = DenseMap(item['identity'], domain, codomain, item['rows'])
    else:
        op = DiagonalMap(item['identity'], domain, codomain, item['diagonal'])
    if op.to_dict() != item:
        raise TypedOperatorError("operator snapshot is not canonical")
    return op


def _graph(value: Any) -> OperatorChain:
    item = _object(value, {'format','fingerprint','factors','application_order'}, 'graph snapshot')
    if (item['format'] != 'VGI-TypedOperatorChain-1'
        or item['application_order'] != 'right_to_left'
        or not isinstance(item['factors'], list)):
        raise TypedOperatorError("unsupported operator graph format")
    graph = OperatorChain(tuple(_leaf(leaf) for leaf in item['factors']))
    if graph.to_dict() != item:
        raise TypedOperatorError("graph snapshot fingerprint or data is inconsistent")
    return graph


def _matrix(value: Any) -> tuple[tuple[int, ...], ...]:
    if not isinstance(value, list) or not value:
        raise TypedOperatorError("matrix witness must be a list of rows")
    return tuple(tuple(row) if isinstance(row, list) else () for row in value)


def _certificate_from_record(graph: OperatorChain, proof: Any) -> CertifiedSimilarityBlocks:
    item = _object(proof, {'schema','certificate_fingerprint','centralizer_witness',
                           'basis','inverse_basis','blocks','eigenvalues','local_composites'},
                   'similarity proof')
    if item['schema'] != PROOF_SCHEMA:
        raise TypedOperatorError("unsupported similarity proof version")
    _sha(item['certificate_fingerprint'], 'certificate fingerprint')
    if not isinstance(item['blocks'], list) or not isinstance(item['eigenvalues'], list):
        raise TypedOperatorError("invalid eigenspace partition")
    if not isinstance(item['local_composites'], list):
        raise TypedOperatorError("invalid local products")
    # This constructor independently proves every property against *every*
    # admitted operator. It does not invoke discovery/_commutant_basis.
    cert = CertifiedSimilarityBlocks(
        graph,
        _matrix(item['centralizer_witness']),
        _matrix(item['basis']),
        _matrix(item['inverse_basis']),
        tuple(tuple(block) if isinstance(block, list) else () for block in item['blocks']),
        tuple(item['eigenvalues']),
        tuple(_matrix(mat) for mat in item['local_composites']),
    )
    if cert.fingerprint != item['certificate_fingerprint']:
        raise TypedOperatorError("similarity proof fingerprint differs from reconstructed witness")
    return cert


def _proof(cert: CertifiedSimilarityBlocks) -> dict[str, Any]:
    return {
        'schema': PROOF_SCHEMA,
        'certificate_fingerprint': cert.fingerprint,
        'centralizer_witness': [list(row) for row in cert.centralizer_witness],
        'basis': [list(row) for row in cert.basis],
        'inverse_basis': [list(row) for row in cert.inverse_basis],
        'blocks': [list(block) for block in cert.blocks],
        'eigenvalues': list(cert.eigenvalues),
        'local_composites': [[list(row) for row in block] for block in cert.local_composites],
    }


def export_similarity_memory(cert: CertifiedSimilarityBlocks) -> bytes:
    """Serialize immutable mathematical operands and certificate as content-addressed bytes."""
    if not isinstance(cert, CertifiedSimilarityBlocks):
        raise TypedOperatorError("export requires a certified mathematical basis")
    # Reconstruct a new certificate to catch forged dataclass objects that
    # bypassed __post_init__ through low-level object mutation.
    witness = _proof(cert)
    _certificate_from_record(cert.graph, witness)
    body = {'schema': SCHEMA, 'graph': cert.graph.to_dict(), 'proof': witness}
    envelope = {**body, 'sha256': _digest(body)}
    blob = _canonical_bytes(envelope)
    if len(blob) > MAX_BYTES:
        raise TypedOperatorError("memory exceeds bounded portable-record size")
    return blob


@dataclass(frozen=True, slots=True)
class AdmittedSimilarityMemory:
    """A fresh verifier's exact mathematical admission, not an execution grant."""
    certificate: CertifiedSimilarityBlocks
    memory_sha256: str
    graph_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.certificate, CertifiedSimilarityBlocks):
            raise TypedOperatorError("invalid admitted certificate")
        _sha(self.memory_sha256, 'memory digest')
        if self.graph_fingerprint != self.certificate.graph.fingerprint:
            raise TypedOperatorError("admitted memory graph differs")
        if _digest({'schema': SCHEMA, 'graph': self.certificate.graph.to_dict(),
                    'proof': _proof(self.certificate)}) != self.memory_sha256:
            raise TypedOperatorError("admission digest mismatches mathematical source")

    @property
    def graph(self) -> OperatorChain:
        return self.certificate.graph

    def state_at(self, initial: TypedVector, tick: int) -> 'PortableSimilarityReceipt':
        _int(tick, 'logical tick')
        if tick.bit_length() > MAX_TICK_BITS:
            raise TypedOperatorError("requested logical time exceeds bounded evidence size")
        inner = self.certificate.state_at(initial, tick)
        return PortableSimilarityReceipt(
            self.memory_sha256, self.graph_fingerprint,
            self.certificate.fingerprint, inner,
        )

    def rebind(self, updated_graph: OperatorChain) -> 'AdmittedSimilarityMemory':
        """Reuse coordinates after *reproving* every property for changed operands.

        No commutant or eigenbasis search occurs. Changes that break the
        admitted witness/partition refuse. The new record has a NEW digest.
        """
        if not isinstance(updated_graph, OperatorChain):
            raise TypedOperatorError("expected typed updated graph")
        if (updated_graph.domain != self.graph.domain
            or updated_graph.codomain != self.graph.codomain
            or len(updated_graph.factors) != len(self.graph.factors)):
            raise TypedOperatorError("rebinding changes the admitted graph interface")
        old = self.certificate
        p = updated_graph.domain.modulus
        local = _local_factors(updated_graph, old.basis, old.inverse_basis, old.blocks, p)
        products = tuple(_compose_block(block, p) for block in local)
        renewed = CertifiedSimilarityBlocks(
            updated_graph, old.centralizer_witness, old.basis, old.inverse_basis,
            old.blocks, old.eigenvalues, products,
        )
        return admit_similarity_memory(export_similarity_memory(renewed),
                                       expected_graph_fingerprint=updated_graph.fingerprint)


@dataclass(frozen=True, slots=True)
class PortableSimilarityReceipt:
    """Repeatable result identity, bound to admitted mathematical Ground."""
    memory_sha256: str
    graph_fingerprint: str
    certificate_fingerprint: str
    inner: SimilarityNavigationReceipt

    def to_dict(self) -> dict[str, Any]:
        return {
            'format': 'VGI-PortableSimilarityNavigation-1',
            'memory_sha256': self.memory_sha256,
            'graph_fingerprint': self.graph_fingerprint,
            'certificate_fingerprint': self.certificate_fingerprint,
            'inner': self.inner.to_dict(),
            'scope': 'declared_mathematical_ground_only_not_host_authority',
        }


def verify_portable_similarity_receipt(memory: AdmittedSimilarityMemory,
                                       receipt: PortableSimilarityReceipt) -> bool:
    if not isinstance(memory, AdmittedSimilarityMemory) or not isinstance(receipt, PortableSimilarityReceipt):
        return False
    try:
        return memory.state_at(receipt.inner.initial, receipt.inner.logical_tick) == receipt
    except (ValueError, TypeError, AttributeError):
        return False


def admit_similarity_memory(
    record: bytes | str | Mapping[str, Any], *,
    expected_graph_fingerprint: str | None = None,
    expected_memory_sha256: str | None = None,
) -> AdmittedSimilarityMemory:
    """Fresh-observer independent full-factor verification; NO discovery search.

    The self-contained record may be decoded without an external graph, but
    actual E-CPU admission must anchor the expected graph/memory identities to
    its own trusted context. JSON/SHA-256 alone establish no such authority.
    """
    data = _decode(record)
    env = _object(data, {'schema','graph','proof','sha256'}, 'portable memory')
    if env['schema'] != SCHEMA:
        raise TypedOperatorError("unsupported portable memory schema")
    claimed = _sha(env['sha256'], 'portable memory digest')
    body = {key: env[key] for key in ('schema','graph','proof')}
    if _digest(body) != claimed:
        raise TypedOperatorError("portable memory has a changed content digest")
    if expected_memory_sha256 is not None and claimed != _sha(expected_memory_sha256,'expected memory'):
        raise TypedOperatorError("portable memory does not match the trusted expected digest")
    graph = _graph(env['graph'])
    if expected_graph_fingerprint is not None and graph.fingerprint != _sha(expected_graph_fingerprint,'expected graph'):
        raise TypedOperatorError("portable memory does not match the admitted graph")
    cert = _certificate_from_record(graph, env['proof'])
    return AdmittedSimilarityMemory(cert, claimed, graph.fingerprint)