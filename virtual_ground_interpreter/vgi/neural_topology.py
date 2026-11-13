"""Import HFR-002 typed neural topology into VGI's AND/OR proof-planning Ground.

This adapter creates structured proof obligations. It does not execute neural
operators, validate theorem prover terms, or turn a source graph's
self-reported verification into an accepted kernel result. Kernel status is
admitted only through an explicit VerifiedKernelReceipt.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

from .proof import (
    ProofEnvironment,
    ProofGround,
    ProofGroundError,
    ProofHyperTransition,
    ProofObligation,
    VerifiedKernelReceipt,
)

GRAPH_SCHEMA = "in-formation-space.neural-computation-graph.v0.1"
ADAPTER_ID = "vgi.hfr-neural-topology-proofground"
ADAPTER_VERSION = "0.2.0"
_REVISION = re.compile(r"^[0-9a-f]{40}$")


class NeuralTopologyProofError(ValueError):
    """A neural topology graph cannot be admitted into the VGI proof-planning Ground."""


def _canonical(value: Any) -> bytes:
    """Encode a finite JSON value using the canonical proof-record representation."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise NeuralTopologyProofError(f"graph contains non-canonical JSON data: {exc}") from exc


def _digest(value: Any) -> str:
    """Return the SHA-256 identity of one canonical JSON-compatible description."""
    return hashlib.sha256(_canonical(value)).hexdigest()


def _unique(items: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    """Index a JSON descriptor array and reject missing or repeated stable identifiers."""
    if not isinstance(items, list):
        raise NeuralTopologyProofError(f"{label} must be an array")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise NeuralTopologyProofError(f"{label} entries must be objects")
        identifier = item.get(key)
        if not isinstance(identifier, str) or not identifier:
            raise NeuralTopologyProofError(f"{label} entries require a non-empty {key}")
        if identifier in result:
            raise NeuralTopologyProofError(f"{label} repeats {key} {identifier!r}")
        result[identifier] = dict(item)
    return result


def _shape(value: Any, label: str) -> list[int | str]:
    """Validate a graph shape containing fixed dimensions and symbolic dimensions."""
    if not isinstance(value, list):
        raise NeuralTopologyProofError(f"{label} must be an array")
    for dimension in value:
        if not (
            (type(dimension) is int and dimension >= 0)
            or (isinstance(dimension, str) and dimension)
        ):
            raise NeuralTopologyProofError(f"{label} contains an invalid dimension")
    return list(value)


def _ports(operation: Mapping[str, Any], direction: str) -> dict[str, dict[str, Any]]:
    """Validate the unique typed ports declared by one graph operation."""
    values = operation.get(direction)
    if not isinstance(values, list):
        raise NeuralTopologyProofError(
            f"operation {operation.get('id')!r} {direction} must be an array"
        )
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        if not isinstance(value, Mapping):
            raise NeuralTopologyProofError(f"operation {operation.get('id')!r} has a malformed port")
        name = value.get("name")
        dtype = value.get("dtype")
        if not isinstance(name, str) or not name or name in result:
            raise NeuralTopologyProofError(f"operation {operation.get('id')!r} repeats or omits a port name")
        if not isinstance(dtype, str) or not dtype:
            raise NeuralTopologyProofError(f"port {operation.get('id')}.{name} has no dtype")
        result[name] = {"name": name, "dtype": dtype, "shape": _shape(
            value.get("shape"), f"{operation.get('id')}.{name}"
        )}
    return result


def _positive_int(value: Any, label: str) -> bool:
    return type(value) is int and value > 0


def _operator_contract_failures(operation: Mapping[str, Any]) -> list[str]:
    """Check the local rank, width, dtype and shape law of each canonical HFR operator."""
    identifier = str(operation.get("id", "<unknown>"))
    operator = operation.get("operator")
    attributes = operation.get("attributes", {})
    if not isinstance(attributes, Mapping):
        return [f"{identifier}: attributes must be an object"]
    inputs = _ports(operation, "inputs")
    outputs = _ports(operation, "outputs")
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(f"{identifier}: {message}")

    if operator == "embedding.lookup":
        require(set(inputs) == {"indices", "table"}, "embedding.lookup needs indices and table ports")
        require(set(outputs) == {"embeddings"}, "embedding.lookup needs one embeddings output")
        if set(inputs) == {"indices", "table"} and set(outputs) == {"embeddings"}:
            indices, table, result = inputs["indices"], inputs["table"], outputs["embeddings"]
            require(len(table["shape"]) == 2, "embedding table must have rank 2")
            require(len(result["shape"]) == len(indices["shape"]) + 1, "embedding output rank is invalid")
            if len(table["shape"]) == 2 and result["shape"]:
                require(result["shape"][:-1] == indices["shape"], "embedding output leading dimensions mismatch")
                require(result["shape"][-1] == table["shape"][-1], "embedding output width mismatch")
                require(indices["dtype"] == "I64", "embedding indices must be I64")
                require(table["dtype"] == result["dtype"], "embedding table/output dtype mismatch")
    elif operator == "tensor.add":
        require(len(inputs) == 2 and len(outputs) == 1, "tensor.add requires two inputs and one output")
        if len(inputs) == 2 and len(outputs) == 1:
            left, right = list(inputs.values())
            result = next(iter(outputs.values()))
            require(left["shape"] == right["shape"] == result["shape"], "tensor.add shapes must match")
            require(left["dtype"] == right["dtype"] == result["dtype"], "tensor.add dtypes must match")
    elif operator == "regularization.dropout":
        require(set(inputs) == {"value"} and set(outputs) == {"output"}, "dropout port signature is invalid")
        if set(inputs) == {"value"} and set(outputs) == {"output"}:
            require(inputs["value"]["shape"] == outputs["output"]["shape"], "dropout must preserve shape")
            require(inputs["value"]["dtype"] == outputs["output"]["dtype"], "dropout must preserve dtype")
        probability = attributes.get("probability")
        require(
            isinstance(probability, (int, float))
            and not isinstance(probability, bool)
            and math.isfinite(float(probability))
            and 0.0 <= probability < 1.0,
            "dropout probability must be finite and in [0, 1)",
        )
    elif operator == "normalization.layer_norm":
        require(set(inputs) == {"value", "scale", "offset"}, "layer_norm port signature is invalid")
        require(set(outputs) == {"normalized"}, "layer_norm output signature is invalid")
        if set(inputs) == {"value", "scale", "offset"} and set(outputs) == {"normalized"}:
            value = inputs["value"]["shape"]
            require(bool(value), "layer_norm input must have rank >= 1")
            if value:
                expected = [value[-1]]
                require(inputs["scale"]["shape"] == expected, "layer_norm scale width mismatch")
                require(inputs["offset"]["shape"] == expected, "layer_norm offset width mismatch")
                require(outputs["normalized"]["shape"] == value, "layer_norm must preserve shape")
                require(outputs["normalized"]["dtype"] == inputs["value"]["dtype"], "layer_norm dtype mismatch")
        epsilon = attributes.get("epsilon")
        require(
            isinstance(epsilon, (int, float))
            and not isinstance(epsilon, bool)
            and math.isfinite(float(epsilon))
            and epsilon > 0,
            "layer_norm epsilon must be finite and positive",
        )
    elif operator == "linear.affine":
        require(set(inputs) in ({"data", "weight"}, {"data", "weight", "bias"}), "linear.affine port signature is invalid")
        require(len(outputs) == 1, "linear.affine must have one output")
        if "data" in inputs and "weight" in inputs and len(outputs) == 1:
            data, weight, result = inputs["data"], inputs["weight"], next(iter(outputs.values()))
            require(bool(data["shape"]) and len(weight["shape"]) == 2, "linear.affine ranks are invalid")
            layout = attributes.get("weight_layout")
            if data["shape"] and len(weight["shape"]) == 2:
                if layout == "input_by_output":
                    input_width, output_width = weight["shape"]
                elif layout == "output_by_input":
                    output_width, input_width = weight["shape"]
                else:
                    input_width, output_width = None, None
                    require(False, "linear.affine weight_layout is unsupported")
                require(data["shape"][-1] == input_width, "linear.affine input width mismatch")
                require(result["shape"] == data["shape"][:-1] + [output_width], "linear.affine output shape mismatch")
                require(result["dtype"] == data["dtype"] == weight["dtype"], "linear.affine dtype mismatch")
                if "bias" in inputs:
                    require(inputs["bias"]["shape"] == [output_width], "linear.affine bias width mismatch")
                    require(inputs["bias"]["dtype"] == data["dtype"], "linear.affine bias dtype mismatch")
    elif operator == "attention.causal_scaled_dot_product":
        require(set(inputs) == {"fused_query_key_value", "causal_mask"}, "causal attention inputs are invalid")
        require(set(outputs) == {"context"}, "causal attention output is invalid")
        heads, width = attributes.get("head_count"), attributes.get("head_width")
        require(_positive_int(heads, "head_count"), "attention head_count must be positive")
        require(_positive_int(width, "head_width"), "attention head_width must be positive")
        if set(inputs) == {"fused_query_key_value", "causal_mask"} and set(outputs) == {"context"}:
            qkv, mask, result = inputs["fused_query_key_value"], inputs["causal_mask"], outputs["context"]
            if _positive_int(heads, "head_count") and _positive_int(width, "head_width"):
                require(bool(qkv["shape"]) and qkv["shape"][-1] == 3 * heads * width, "fused QKV width mismatch")
                if qkv["shape"]:
                    require(result["shape"] == qkv["shape"][:-1] + [heads * width], "attention context shape mismatch")
            require(len(mask["shape"]) == 4, "causal mask must have rank 4")
            if len(mask["shape"]) == 4:
                require(mask["shape"][0:2] == [1, 1], "causal mask leading dimensions mismatch")
                require(mask["shape"][2] == mask["shape"][3], "causal mask must be square")
            require(attributes.get("causal") is True, "attention must declare causal masking")
            require(attributes.get("scale_by_sqrt_head_width") is True, "attention must declare scaled dot-product")
    elif operator == "attention.padding_mask_prepare":
        require(set(inputs) == {"mask"} and set(outputs) == {"mask"}, "padding mask prepare port signature is invalid")
        if set(inputs) == {"mask"} and set(outputs) == {"mask"}:
            require(inputs["mask"]["dtype"] == outputs["mask"]["dtype"] == "I64", "padding mask prepare must preserve I64 mask dtype")
            require(inputs["mask"]["shape"] == outputs["mask"]["shape"], "padding mask prepare must preserve shape")
            require(len(inputs["mask"]["shape"]) == 2, "padding mask prepare expects a batch/sequence mask")
        require(attributes.get("mask_semantics") == "one_attend_zero_mask", "padding mask convention must be explicit")
    elif operator == "attention.bidirectional_scaled_dot_product":
        require(set(inputs) == {"query", "key", "value", "mask"}, "bidirectional attention inputs are invalid")
        require(set(outputs) == {"context"}, "bidirectional attention output is invalid")
        if set(inputs) == {"query", "key", "value", "mask"} and set(outputs) == {"context"}:
            query, key, value = inputs["query"], inputs["key"], inputs["value"]
            mask, result = inputs["mask"], outputs["context"]
            require(query["shape"] == key["shape"] == value["shape"] == result["shape"], "bidirectional Q/K/V/context shapes must match")
            require(query["dtype"] == key["dtype"] == value["dtype"] == result["dtype"], "bidirectional Q/K/V/context dtypes must match")
            require(len(query["shape"]) == 3, "bidirectional attention projected inputs must be rank three")
            if len(query["shape"]) == 3:
                require(mask["shape"] == query["shape"][:2], "padding mask batch/sequence dims mismatch")
            require(mask["dtype"] == "I64", "bidirectional padding mask must be I64")
            heads, width = attributes.get("head_count"), attributes.get("head_width")
            require(_positive_int(heads, "head_count"), "bidirectional attention head_count must be positive")
            require(_positive_int(width, "head_width"), "bidirectional attention head_width must be positive")
            if _positive_int(heads, "head_count") and _positive_int(width, "head_width") and len(query["shape"]) == 3:
                require(query["shape"][-1] == heads * width, "bidirectional attention feature width mismatch")
            require(attributes.get("causal") is False, "bidirectional attention cannot use a causal mask")
            require(attributes.get("scale_by_sqrt_head_width") is True, "bidirectional attention must declare scaling")
            require(attributes.get("mask_semantics") == "one_attend_zero_mask", "bidirectional padding-mask convention must be explicit")
    elif operator == "sequence.select_first_token":
        require(set(inputs) == {"sequence"} and set(outputs) == {"first"}, "first-token selection ports are invalid")
        if set(inputs) == {"sequence"} and set(outputs) == {"first"}:
            sequence, first = inputs["sequence"], outputs["first"]
            require(len(sequence["shape"]) == 3, "first-token selection input must be rank three")
            if len(sequence["shape"]) == 3:
                require(first["shape"] == [sequence["shape"][0], sequence["shape"][2]], "first-token output must be batch/hidden")
            require(sequence["dtype"] == first["dtype"], "first-token selection dtype mismatch")
        require(attributes.get("token_index") == 0, "first-token selection must target index zero")
    elif operator == "activation.tanh":
        require(set(inputs) == {"value"} and set(outputs) == {"output"}, "tanh ports are invalid")
        if set(inputs) == {"value"} and set(outputs) == {"output"}:
            require(inputs["value"]["shape"] == outputs["output"]["shape"], "tanh must preserve shape")
            require(inputs["value"]["dtype"] == outputs["output"]["dtype"], "tanh must preserve dtype")
    elif operator == "activation.gelu_erf":
        require(set(inputs) == {"value"} and set(outputs) == {"output"}, "erf GELU ports are invalid")
        if set(inputs) == {"value"} and set(outputs) == {"output"}:
            require(inputs["value"]["shape"] == outputs["output"]["shape"], "erf GELU must preserve shape")
            require(inputs["value"]["dtype"] == outputs["output"]["dtype"], "erf GELU must preserve dtype")
        require(attributes.get("form") == "erf", "erf GELU cannot be silently replaced by tanh approximation")
    elif operator == "activation.gelu_tanh":
        require(set(inputs) == {"value"} and set(outputs) == {"output"}, "GELU port signature is invalid")
        if set(inputs) == {"value"} and set(outputs) == {"output"}:
            require(inputs["value"]["shape"] == outputs["output"]["shape"], "GELU must preserve shape")
            require(inputs["value"]["dtype"] == outputs["output"]["dtype"], "GELU must preserve dtype")
    else:
        failures.append(f"{identifier}: unsupported canonical operator {operator!r}")
    return failures


def _validate_graph(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Independently validate typed endpoint connectivity, local operator dimensions and operation-DAG acyclicity."""
    source = graph.get("source_observation")
    completeness = graph.get("completeness")
    verification = graph.get("verification")
    if not isinstance(source, Mapping):
        raise NeuralTopologyProofError("source_observation is required")
    if not isinstance(completeness, Mapping):
        raise NeuralTopologyProofError("source completeness record is required")
    if not isinstance(verification, Mapping):
        raise NeuralTopologyProofError("source verification record is required")
    repository = source.get("repository")
    revision = source.get("revision")
    if not isinstance(repository, str) or not repository:
        raise NeuralTopologyProofError("source repository is required")
    if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
        raise NeuralTopologyProofError("source revision must be a pinned lowercase 40-character commit SHA")

    graph_inputs = _unique(graph.get("inputs"), "name", "graph inputs")
    graph_outputs = _unique(graph.get("outputs"), "name", "graph outputs")
    tensors = _unique(graph.get("tensors"), "name", "tensor catalog")
    operations = _unique(graph.get("operations"), "id", "operations")
    edges = graph.get("edges")
    source_files = _unique(source.get("source_files"), "path", "source files")
    if not isinstance(edges, list):
        raise NeuralTopologyProofError("edges must be an array")

    # The "complete" flag is a source claim; check its counters against the
    # actual imported collections before using it to construct the proof plan.
    if (
        completeness.get("observed_tensor_count") != len(tensors)
        or completeness.get("classified_tensor_count") != len(tensors)
        or completeness.get("bound_tensor_count") != len(tensors)
        or completeness.get("unclassified_tensors") != []
        or completeness.get("unused_tensors") != []
        or completeness.get("unsupported_components") != []
        or completeness.get("missing_expected_components") != []
    ):
        raise NeuralTopologyProofError("source completeness counters do not match the imported tensor catalog")
    if (
        verification.get("failed_check_count") != 0
        or verification.get("operation_count") != len(operations)
        or verification.get("edge_count") != len(edges)
    ):
        raise NeuralTopologyProofError("source verification counters do not match the imported graph")

    tensor_provenance_failures: list[str] = []
    for name, tensor in tensors.items():
        dtype = tensor.get("dtype")
        shape = tensor.get("shape")
        source_ref = tensor.get("source")
        classification = tensor.get("classification")
        if not isinstance(dtype, str) or not dtype:
            tensor_provenance_failures.append(f"{name}: dtype is missing")
        if not isinstance(shape, list) or any(type(dimension) is not int or dimension < 0 for dimension in shape):
            tensor_provenance_failures.append(f"{name}: tensor shape is invalid")
        if not isinstance(source_ref, Mapping):
            tensor_provenance_failures.append(f"{name}: source reference is missing")
            continue
        file_record = source_files.get(source_ref.get("file"))
        if file_record is None:
            tensor_provenance_failures.append(f"{name}: source file is absent from graph provenance")
            continue
        offsets = source_ref.get("data_offsets")
        if (
            not isinstance(offsets, list)
            or len(offsets) != 2
            or any(type(offset) is not int or offset < 0 for offset in offsets)
            or offsets[1] < offsets[0]
            or source_ref.get("data_bytes") != offsets[1] - offsets[0]
        ):
            tensor_provenance_failures.append(f"{name}: source data offsets/length are invalid")
        if (
            source_ref.get("header_sha256") != file_record.get("sha256")
            or source_ref.get("header_hash_scope") != file_record.get("sha256_scope")
        ):
            tensor_provenance_failures.append(f"{name}: source header digest/scope differs from source file record")
        if (
            not isinstance(classification, Mapping)
            or classification.get("status") != "family-interpreted"
            or not isinstance(classification.get("role"), str)
            or not classification.get("role")
        ):
            tensor_provenance_failures.append(f"{name}: tensor classification is not a typed family interpretation")
    if tensor_provenance_failures:
        raise NeuralTopologyProofError(
            "source tensor provenance is inconsistent: " + "; ".join(tensor_provenance_failures[:8])
        )

    input_ports = {
        (operation_id, name): port
        for operation_id, operation in operations.items()
        for name, port in _ports(operation, "inputs").items()
    }
    output_ports = {
        (operation_id, name): port
        for operation_id, operation in operations.items()
        for name, port in _ports(operation, "outputs").items()
    }

    incoming: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    output_consumers: dict[tuple[str, str], int] = defaultdict(int)
    tensor_uses: dict[str, int] = defaultdict(int)
    input_uses: dict[str, int] = defaultdict(int)
    output_uses: dict[str, int] = defaultdict(int)
    adjacency: dict[str, set[str]] = defaultdict(set)
    failures: list[str] = []

    for index, edge in enumerate(edges):
        if not isinstance(edge, Mapping):
            failures.append(f"edge {index} is not an object")
            continue
        src, dst = edge.get("source"), edge.get("target")
        if not isinstance(src, Mapping) or not isinstance(dst, Mapping):
            failures.append(f"edge {index} endpoints are invalid")
            continue
        if dst.get("kind") == "operation_input":
            key = (dst.get("operation"), dst.get("port"))
            expected = input_ports.get(key)
            if expected is None:
                failures.append(f"edge {index} targets unknown operation input {key}")
                continue
            kind = src.get("kind")
            if kind == "graph_input":
                descriptor = graph_inputs.get(src.get("name"))
                if descriptor is not None:
                    input_uses[src["name"]] += 1
            elif kind == "tensor":
                descriptor = tensors.get(src.get("name"))
                if descriptor is not None:
                    tensor_uses[src["name"]] += 1
            elif kind == "operation_output":
                source_key = (src.get("operation"), src.get("port"))
                descriptor = output_ports.get(source_key)
                if descriptor is not None:
                    output_consumers[source_key] += 1
                    adjacency[source_key[0]].add(key[0])
            else:
                descriptor = None
            if descriptor is None:
                failures.append(f"edge {index} has an unresolved source endpoint")
                continue
            if descriptor.get("dtype") != expected["dtype"] or descriptor.get("shape") != expected["shape"]:
                failures.append(f"edge {index} has a dtype/shape mismatch")
            incoming[key].append({"source": dict(src), "target": dict(dst)})
        elif dst.get("kind") == "graph_output":
            name = dst.get("name")
            expected = graph_outputs.get(name)
            source_key = (src.get("operation"), src.get("port")) if src.get("kind") == "operation_output" else None
            actual = output_ports.get(source_key) if source_key else None
            if expected is None or actual is None:
                failures.append(f"edge {index} has an unresolved graph output endpoint")
                continue
            if actual.get("dtype") != expected.get("dtype") or actual.get("shape") != expected.get("shape"):
                failures.append(f"edge {index} graph output dtype/shape mismatch")
            output_consumers[source_key] += 1
            output_uses[name] += 1
        else:
            failures.append(f"edge {index} has an unsupported destination endpoint")

    if any(len(incoming.get(key, ())) != 1 for key in input_ports):
        failures.append("not every operation input has exactly one producer")
    if any(output_consumers.get(key, 0) < 1 for key in output_ports):
        failures.append("not every operation output has a consumer")
    if any(tensor_uses.get(name, 0) < 1 for name in tensors):
        failures.append("one or more tensors are unused")
    if any(input_uses.get(name, 0) != 1 for name in graph_inputs):
        failures.append("every graph input must have exactly one consumer")
    if any(output_uses.get(name, 0) != 1 for name in graph_outputs):
        failures.append("every graph output must have exactly one producer")

    operation_failures = [
        failure
        for operation in operations.values()
        for failure in _operator_contract_failures(operation)
    ]
    failures.extend(operation_failures)

    # Kahn topological sort over operation-to-operation connections.
    indegree = {identifier: 0 for identifier in operations}
    for source_id, targets in adjacency.items():
        if source_id not in operations:
            failures.append(f"edge source operation {source_id!r} is unknown")
            continue
        for target_id in targets:
            if target_id not in operations:
                failures.append(f"edge target operation {target_id!r} is unknown")
            else:
                indegree[target_id] += 1
    ready = deque(sorted(identifier for identifier, degree in indegree.items() if degree == 0))
    visited: list[str] = []
    while ready:
        identifier = ready.popleft()
        visited.append(identifier)
        for target in sorted(adjacency.get(identifier, set())):
            if target in indegree:
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)
    if len(visited) != len(operations):
        failures.append("operation dependency relation contains a cycle")
    if failures:
        raise NeuralTopologyProofError("source graph failed independent VGI structural validation: " + "; ".join(failures[:12]))

    return {
        "repository": repository,
        "revision": revision,
        "graph_input_count": len(graph_inputs),
        "graph_output_count": len(graph_outputs),
        "tensor_count": len(tensors),
        "operation_count": len(operations),
        "edge_count": len(edges),
        "operation_input_count": len(input_ports),
        "operation_output_count": len(output_ports),
        "tensor_binding_count": sum(tensor_uses.values()),
        "graph_input_binding_count": sum(input_uses.values()),
        "graph_output_binding_count": sum(output_uses.values()),
    }


@dataclass(frozen=True, slots=True)
class NeuralTopologyProofPackage:
    """A VGI ProofGround plus exact source identity and obligation-key catalogue."""

    graph_digest: str
    source_repository: str
    source_revision: str
    ground: ProofGround
    obligation_keys: Mapping[str, str]
    local_validation: Mapping[str, Any]

    def manifest(self) -> dict[str, Any]:
        """Return a detached proof-planning manifest without promoting unverified claims to kernel status."""
        summary = self.ground.summary()
        return {
            "schema": "vgi.neural-topology-proofground-manifest.v0.1",
            "adapter": ADAPTER_ID,
            "adapter_version": ADAPTER_VERSION,
            "source_graph_schema": GRAPH_SCHEMA,
            "source_graph_digest": self.graph_digest,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "local_validation": dict(self.local_validation),
            "proof_ground": summary,
            "obligation_keys": dict(self.obligation_keys),
            "kernel_acceptance_claimed": False,
            "all_unreceipted_obligations_remain_unverified": True,
        }


def build_neural_topology_proof_ground(
    graph: Mapping[str, Any],
    *,
    verified_receipts: Sequence[VerifiedKernelReceipt] = (),
) -> NeuralTopologyProofPackage:
    """Translate a complete typed topology into VGI AND/OR obligations, not neural execution."""
    if not isinstance(graph, Mapping):
        raise NeuralTopologyProofError("neural computation graph must be an object")
    _canonical(dict(graph))
    if graph.get("schema") != GRAPH_SCHEMA:
        raise NeuralTopologyProofError(f"unsupported graph schema {graph.get('schema')!r}")
    verification = graph.get("verification")
    completeness = graph.get("completeness")
    if not isinstance(verification, Mapping) or verification.get("status") != "passed":
        raise NeuralTopologyProofError("HFR graph must carry a passed source structural verification")
    if not isinstance(completeness, Mapping) or completeness.get("status") != "complete-for-supported-family-template":
        raise NeuralTopologyProofError("HFR graph must be complete for its supported family template")

    facts = _validate_graph(graph)
    graph_digest = _digest(dict(graph))
    source = graph["source_observation"]
    rules = {
        "adapter": ADAPTER_ID,
        "version": ADAPTER_VERSION,
        "graph_schema": GRAPH_SCHEMA,
        "operator_contracts": [
            "embedding.lookup",
            "tensor.add",
            "regularization.dropout",
            "normalization.layer_norm",
            "linear.affine",
            "attention.causal_scaled_dot_product",
            "attention.padding_mask_prepare",
            "attention.bidirectional_scaled_dot_product",
            "sequence.select_first_token",
            "activation.tanh",
            "activation.gelu_tanh",
            "activation.gelu_erf",
        ],
        "edge_contract": "exact source/target dtype and symbolic-shape equality",
        "topology_contract": "finite acyclic operation dependency graph",
        "kernel_policy": "only explicit matching VerifiedKernelReceipt can admit kernel status",
    }
    environment = ProofEnvironment(
        assistant=ADAPTER_ID,
        assistant_version=ADAPTER_VERSION,
        environment_fingerprint=_digest(rules),
        imports_fingerprint=_digest({"graph_schema": GRAPH_SCHEMA, "proof_schema": "VGI-ProofGroundSummary-1"}),
        options_fingerprint=_digest({"source_graph_digest": graph_digest}),
    )

    obligation_objects: dict[str, ProofObligation] = {}

    def add_obligation(key: str, proposition: str, subject: Mapping[str, Any]) -> str:
        if key in obligation_objects:
            raise NeuralTopologyProofError(f"duplicate proof obligation key {key!r}")
        obligation = ProofObligation(
            environment=environment,
            goal={
                "kind": "neural_topology_property",
                "proposition": proposition,
                "subject": dict(subject),
                "source_graph_digest": graph_digest,
                "source_repository": facts["repository"],
                "source_revision": facts["revision"],
            },
            local_context=(
                {
                    "graph_schema": GRAPH_SCHEMA,
                    "adapter": ADAPTER_ID,
                    "adapter_version": ADAPTER_VERSION,
                    "local_validation_status": "passed",
                    "evidence_source": "HFR-002 typed graph descriptor",
                },
            ),
            assumptions=(
                {
                    "kind": "family_interpretation",
                    "description": (
                        "Operator meanings and tensor roles are supplied by the model-family adapter; "
                        "this proof-planning Ground does not prove those semantics from weight payloads."
                    ),
                },
            ),
        )
        obligation_objects[key] = obligation
        return obligation.fingerprint

    root = add_obligation(
        "graph",
        "all_supported_neural_topology_obligations_hold",
        {
            "tensor_count": facts["tensor_count"],
            "operation_count": facts["operation_count"],
            "edge_count": facts["edge_count"],
        },
    )
    provenance = add_obligation(
        "provenance",
        "graph_source_identity_and_header_provenance_are_pinned",
        {
            "repository": facts["repository"],
            "revision": facts["revision"],
            "graph_digest": graph_digest,
        },
    )
    tensor_group = add_obligation(
        "tensor_catalog",
        "every_observed_tensor_has_one_classified_and_bound_graph_descriptor",
        {"tensor_count": facts["tensor_count"]},
    )
    operation_group = add_obligation(
        "operation_contracts",
        "every_operation_has_well_typed_ports_and_satisfies_its_local_dimensional_contract",
        {"operation_count": facts["operation_count"]},
    )
    edge_group = add_obligation(
        "edge_contracts",
        "every_connection_resolves_and_preserves_source_target_dtype_and_shape",
        {"edge_count": facts["edge_count"]},
    )
    topology = add_obligation(
        "acyclic_topology",
        "operation_dependency_relation_is_a_finite_directed_acyclic_graph",
        {"operation_count": facts["operation_count"]},
    )
    completeness = add_obligation(
        "interface_completeness",
        "all_graph_inputs_outputs_and_operation_ports_are_connected_exactly_as_declared",
        {
            "graph_input_count": facts["graph_input_count"],
            "graph_output_count": facts["graph_output_count"],
            "operation_input_count": facts["operation_input_count"],
            "operation_output_count": facts["operation_output_count"],
        },
    )

    graph_data = dict(graph)
    tensors = _unique(graph_data.get("tensors"), "name", "tensor catalog")
    operations = _unique(graph_data.get("operations"), "id", "operations")
    edges = graph_data["edges"]

    tensor_keys = []
    for name, tensor in sorted(tensors.items()):
        tensor_keys.append(
            add_obligation(
                f"tensor:{name}",
                "tensor_descriptor_matches_its_source_shard_header_record",
                {
                    "name": name,
                    "dtype": tensor["dtype"],
                    "shape": tensor["shape"],
                    "source": tensor["source"],
                    "classification": tensor["classification"],
                },
            )
        )

    operation_keys = []
    for identifier, operation in sorted(operations.items()):
        operation_keys.append(
            add_obligation(
                f"operation:{identifier}",
                "operation_input_output_ports_and_local_operator_contract_are_well_typed",
                {
                    "id": identifier,
                    "operator": operation["operator"],
                    "inputs": operation["inputs"],
                    "outputs": operation["outputs"],
                    "attributes": operation.get("attributes", {}),
                    "provenance": operation.get("provenance", {}),
                },
            )
        )

    edge_keys = []
    for index, edge in enumerate(edges):
        edge_keys.append(
            add_obligation(
                f"edge:{index}",
                "edge_endpoints_exist_and_source_target_port_types_are_equal",
                {
                    "source": edge["source"],
                    "target": edge["target"],
                    "provenance": edge.get("provenance", {}),
                },
            )
        )

    obligation_keys = {
        key: item.fingerprint for key, item in obligation_objects.items()
    }
    transitions: list[ProofHyperTransition] = [
        ProofHyperTransition(
            source_id=root,
            tactic="decompose_complete_neural_topology",
            subgoal_ids=(provenance, tensor_group, operation_group, edge_group, topology, completeness),
            attempt_status="candidate",
            evidence_ref=graph_digest,
        ),
        ProofHyperTransition(
            source_id=tensor_group,
            tactic="expand_tensor_catalog",
            subgoal_ids=tuple(tensor_keys),
            attempt_status="candidate",
            evidence_ref=graph_digest,
        ),
        ProofHyperTransition(
            source_id=operation_group,
            tactic="expand_operation_dimensional_contracts",
            subgoal_ids=tuple(operation_keys),
            attempt_status="candidate",
            evidence_ref=graph_digest,
        ),
        ProofHyperTransition(
            source_id=edge_group,
            tactic="expand_typed_connection_contracts",
            subgoal_ids=tuple(edge_keys),
            attempt_status="candidate",
            evidence_ref=graph_digest,
        ),
    ]
    # Each leaf carries explicit candidate strategies. Empty subgoal lists are
    # tactic candidates, not proofs; accepted status still needs a kernel receipt.
    for key, identifier in sorted(obligation_keys.items()):
        if key == "graph":
            continue
        if key in ("tensor_catalog", "operation_contracts", "edge_contracts"):
            continue
        transitions.append(
            ProofHyperTransition(
                source_id=identifier,
                tactic="candidate_exact_structural_reflection",
                subgoal_ids=(),
                attempt_status="candidate",
                evidence_ref=graph_digest,
            )
        )

    receipts = tuple(verified_receipts)
    if any(not isinstance(item, VerifiedKernelReceipt) for item in receipts):
        raise NeuralTopologyProofError("verified_receipts must contain VerifiedKernelReceipt values")
    try:
        ground = ProofGround(
            environment=environment,
            obligations=tuple(obligation_objects.values()),
            transitions=tuple(transitions),
            receipts=receipts,
            observed_kernel_claims=(),
        )
    except ProofGroundError as exc:
        raise NeuralTopologyProofError(f"VGI refused neural topology ProofGround: {exc}") from exc

    local_validation = {
        **facts,
        "status": "passed",
        "operator_contract_failures": 0,
        "edge_type_shape_failures": 0,
        "dependency_cycles": 0,
        "raw_tensor_values_observed": False,
        "external_kernel_validation_performed": False,
    }
    return NeuralTopologyProofPackage(
        graph_digest=graph_digest,
        source_repository=facts["repository"],
        source_revision=facts["revision"],
        ground=ground,
        obligation_keys=obligation_keys,
        local_validation=local_validation,
    )


__all__ = [
    "ADAPTER_ID",
    "ADAPTER_VERSION",
    "NeuralTopologyProofError",
    "NeuralTopologyProofPackage",
    "build_neural_topology_proof_ground",
]
