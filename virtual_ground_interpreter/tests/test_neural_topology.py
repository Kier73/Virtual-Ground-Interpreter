"""Tests for importing typed HFR-002 topology as VGI proof obligations."""

from __future__ import annotations

import copy
import unittest

from vgi.neural_topology import (
    NeuralTopologyProofError,
    build_neural_topology_proof_ground,
)
from vgi.proof import VerifiedKernelReceipt


REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
HEADER_SHA = "a" * 64


def port(name: str, dtype: str, shape: list) -> dict:
    return {"name": name, "dtype": dtype, "shape": shape}


def make_graph() -> dict:
    operation = {
        "id": "linear",
        "operator": "linear.affine",
        "inputs": [
            port("data", "F32", ["batch", 2]),
            port("weight", "F32", [2, 2]),
        ],
        "outputs": [port("projected", "F32", ["batch", 2])],
        "attributes": {
            "input_width": 2,
            "output_width": 2,
            "weight_layout": "input_by_output",
        },
        "provenance": {
            "operator_semantics": {
                "status": "family-interpreted",
                "basis": "synthetic test contract",
                "reference": "https://example.invalid/model",
            },
            "port_shapes": {
                "status": "dimensionally-derived",
                "basis": "synthetic dimensions",
            },
        },
    }
    return {
        "schema": "in-formation-space.neural-computation-graph.v0.1",
        "ir_version": "0.1.0",
        "source_observation": {
            "repository": "openai-community/gpt2",
            "revision": REVISION,
            "license_id": "mit",
            "nsd_schema": "in-formation-space.neural-structure-description.v0.1",
            "source_files": [
                {
                    "path": "model.safetensors",
                    "role": "safetensors-shard",
                    "sha256": HEADER_SHA,
                    "sha256_scope": "8-byte-prefix-and-header-only",
                    "size_bytes": 128,
                }
            ],
        },
        "model_family_adapter": {
            "id": "test-adapter",
            "version": "0.1.0",
            "family": "test-family",
            "reference": "https://example.invalid/model",
            "status": "family-interpreted",
        },
        "dimension_symbols": {
            "batch": {"kind": "runtime", "value": None, "minimum": 1},
            "hidden": {"kind": "fixed", "value": 2},
        },
        "inputs": [
            {
                "name": "input.values",
                "dtype": "F32",
                "shape": ["batch", 2],
                "semantic_role": "test_input",
            }
        ],
        "outputs": [
            {
                "name": "output.values",
                "dtype": "F32",
                "shape": ["batch", 2],
                "semantic_role": "test_output",
            }
        ],
        "tensors": [
            {
                "name": "linear.weight",
                "dtype": "F32",
                "shape": [2, 2],
                "source": {
                    "file": "model.safetensors",
                    "data_offsets": [0, 16],
                    "data_bytes": 16,
                    "header_sha256": HEADER_SHA,
                    "header_hash_scope": "8-byte-prefix-and-header-only",
                },
                "classification": {
                    "role": "linear.weight",
                    "status": "family-interpreted",
                    "evidence": ["synthetic adapter contract"],
                },
            }
        ],
        "operations": [operation],
        "edges": [
            {
                "source": {"kind": "graph_input", "name": "input.values"},
                "target": {"kind": "operation_input", "operation": "linear", "port": "data"},
                "provenance": {"status": "inferred-connection", "basis": "test input"},
            },
            {
                "source": {"kind": "tensor", "name": "linear.weight"},
                "target": {"kind": "operation_input", "operation": "linear", "port": "weight"},
                "provenance": {"status": "inferred-connection", "basis": "test parameter"},
            },
            {
                "source": {"kind": "operation_output", "operation": "linear", "port": "projected"},
                "target": {"kind": "graph_output", "name": "output.values"},
                "provenance": {"status": "inferred-connection", "basis": "test output"},
            },
        ],
        "completeness": {
            "status": "complete-for-supported-family-template",
            "observed_tensor_count": 1,
            "classified_tensor_count": 1,
            "bound_tensor_count": 1,
            "unclassified_tensors": [],
            "unused_tensors": [],
            "unsupported_components": [],
            "missing_expected_components": [],
        },
        "verification": {
            "status": "passed",
            "passed_check_count": 12,
            "failed_check_count": 0,
            "operation_count": 1,
            "edge_count": 3,
            "input_port_count": 2,
            "output_port_count": 1,
            "checks": [],
        },
        "evidence_policy": {
            "tensor_identity_dtype_shape_offsets": "observed-from-NSD",
            "tensor_roles": "family-interpreted",
            "operator_types_and_semantics": "family-interpreted",
            "directed_connections": "inferred-connection",
            "numerical_parameter_values": "not-observed",
            "execution_behavior": "not-tested",
        },
        "assumptions_and_unresolved": ["Synthetic test graph."],
    }


class NeuralTopologyProofGroundTests(unittest.TestCase):
    def test_imports_graph_as_unverified_and_or_proof_obligations(self):
        package = build_neural_topology_proof_ground(make_graph())
        manifest = package.manifest()
        ground = package.ground

        self.assertEqual(manifest["schema"], "vgi.neural-topology-proofground-manifest.v0.1")
        self.assertEqual(manifest["source_repository"], "openai-community/gpt2")
        self.assertEqual(manifest["source_revision"], REVISION)
        self.assertEqual(manifest["local_validation"]["status"], "passed")
        self.assertFalse(manifest["kernel_acceptance_claimed"])
        self.assertTrue(manifest["all_unreceipted_obligations_remain_unverified"])
        self.assertEqual(ground.summary()["obligation_count"], 12)
        self.assertEqual(ground.summary()["hyper_transition_count"], 12)
        self.assertEqual(ground.summary()["unverified_obligations"], 12)

        root = package.obligation_keys["graph"]
        decomposition = ground.alternatives(root, "decompose_complete_neural_topology")
        self.assertEqual(len(decomposition), 1)
        self.assertEqual(len(decomposition[0].subgoal_ids), 6)
        tensor_group = package.obligation_keys["tensor_catalog"]
        expansion = ground.alternatives(tensor_group, "expand_tensor_catalog")
        self.assertEqual(len(expansion), 1)
        self.assertEqual(len(expansion[0].subgoal_ids), 1)
        self.assertEqual(ground.kernel_status(root), "unverified")

    def test_source_passed_flag_does_not_create_kernel_acceptance(self):
        graph = make_graph()
        graph["verification"]["status"] = "passed"
        package = build_neural_topology_proof_ground(graph)
        for obligation_id in package.ground.obligation_ids:
            self.assertEqual(package.ground.kernel_status(obligation_id), "unverified")

    def test_only_exact_external_receipt_admits_one_obligation(self):
        first = build_neural_topology_proof_ground(make_graph())
        root_id = first.obligation_keys["graph"]
        receipt = VerifiedKernelReceipt(
            obligation_id=root_id,
            proof_term_fingerprint="proof-term-fingerprint",
            environment_fingerprint=first.ground.environment.environment_fingerprint,
            checker_id="Lean.kernel",
            checker_version="4.15.0",
            result="accepted",
            receipt_ref="lean-run-001",
        )
        second = build_neural_topology_proof_ground(
            make_graph(),
            verified_receipts=(receipt,),
        )
        self.assertEqual(second.ground.kernel_status(root_id), "kernel_accepted")
        self.assertEqual(second.ground.summary()["unverified_obligations"], 11)
        self.assertEqual(second.ground.summary()["kernel_accepted_obligations"], 1)

    def test_receipt_for_another_graph_or_environment_is_rejected(self):
        first = build_neural_topology_proof_ground(make_graph())
        root_id = first.obligation_keys["graph"]
        receipt = VerifiedKernelReceipt(
            obligation_id=root_id,
            proof_term_fingerprint="proof-term-fingerprint",
            environment_fingerprint="wrong-environment",
            checker_id="Lean.kernel",
            checker_version="4.15.0",
            result="accepted",
            receipt_ref="lean-run-002",
        )
        with self.assertRaises(NeuralTopologyProofError):
            build_neural_topology_proof_ground(make_graph(), verified_receipts=(receipt,))

        changed = make_graph()
        changed["operations"][0]["attributes"]["input_width"] = 3
        with self.assertRaises(NeuralTopologyProofError):
            build_neural_topology_proof_ground(changed, verified_receipts=(receipt,))

    def test_rejects_edge_type_shape_and_operator_dimension_mismatch(self):
        graph = make_graph()
        graph["operations"][0]["inputs"][0]["shape"] = ["batch", 3]
        with self.assertRaisesRegex(NeuralTopologyProofError, "dtype/shape mismatch"):
            build_neural_topology_proof_ground(graph)

        graph = make_graph()
        graph["operations"][0]["inputs"][1]["shape"] = [3, 2]
        graph["tensors"][0]["shape"] = [3, 2]
        graph["tensors"][0]["source"]["data_bytes"] = 24
        graph["tensors"][0]["source"]["data_offsets"] = [0, 24]
        with self.assertRaisesRegex(NeuralTopologyProofError, "linear.affine input width mismatch"):
            build_neural_topology_proof_ground(graph)

    def test_rejects_cycle_and_incomplete_or_unverified_source_graphs(self):
        graph = make_graph()
        graph["verification"]["status"] = "pending"
        with self.assertRaisesRegex(NeuralTopologyProofError, "passed source structural verification"):
            build_neural_topology_proof_ground(graph)

        graph = make_graph()
        graph["completeness"]["status"] = "incomplete"
        with self.assertRaisesRegex(NeuralTopologyProofError, "complete for its supported"):
            build_neural_topology_proof_ground(graph)

    def test_provenance_digest_and_environment_change_with_source_description(self):
        first = build_neural_topology_proof_ground(make_graph())
        changed = make_graph()
        changed["source_observation"]["revision"] = "0123456789abcdef0123456789abcdef01234567"
        second = build_neural_topology_proof_ground(changed)
        self.assertNotEqual(first.graph_digest, second.graph_digest)
        self.assertNotEqual(
            first.ground.environment.options_fingerprint,
            second.ground.environment.options_fingerprint,
        )
        self.assertNotEqual(first.obligation_keys["graph"], second.obligation_keys["graph"])

    def test_no_weight_payload_or_numerical_claim_is_created(self):
        package = build_neural_topology_proof_ground(make_graph())
        self.assertFalse(package.manifest()["kernel_acceptance_claimed"])
        self.assertFalse(package.local_validation["raw_tensor_values_observed"])
        for obligation_id in package.ground.obligation_ids:
            self.assertNotEqual(package.ground.kernel_status(obligation_id), "kernel_accepted")

    def test_complete_flag_cannot_override_inconsistent_tensor_counts(self):
        graph = make_graph()
        graph["completeness"]["classified_tensor_count"] = 0
        with self.assertRaisesRegex(NeuralTopologyProofError, "completeness counters"):
            build_neural_topology_proof_ground(graph)

    def test_tensor_source_header_digest_must_match_graph_file_provenance(self):
        graph = make_graph()
        graph["tensors"][0]["source"]["header_sha256"] = "b" * 64
        with self.assertRaisesRegex(NeuralTopologyProofError, "header digest/scope"):
            build_neural_topology_proof_ground(graph)

    def test_tensor_offsets_must_match_the_declared_data_byte_length(self):
        graph = make_graph()
        graph["tensors"][0]["source"]["data_bytes"] = 12
        with self.assertRaisesRegex(NeuralTopologyProofError, "data offsets/length"):
            build_neural_topology_proof_ground(graph)


if __name__ == "__main__":
    unittest.main()
