"""Local VGI contracts for BERT's noncausal operators, independent of HFR parser."""
from __future__ import annotations

import copy
import unittest

from vgi.neural_topology import _operator_contract_failures


def port(name: str, dtype: str, shape: list) -> dict:
    """Build a typed operator port for one dimensional-contract test."""
    return {"name": name, "dtype": dtype, "shape": shape}


def operation(kind: str) -> dict:
    """Build one valid canonical BERT operator descriptor."""
    sequence = ["batch", "sequence", 4]
    mask = ["batch", "sequence"]
    if kind == "attention.padding_mask_prepare":
        return {
            "id": "mask",
            "operator": kind,
            "inputs": [port("mask", "I64", mask)],
            "outputs": [port("mask", "I64", mask)],
            "attributes": {"mask_semantics": "one_attend_zero_mask"},
        }
    if kind == "attention.bidirectional_scaled_dot_product":
        return {
            "id": "attention",
            "operator": kind,
            "inputs": [
                port("query", "F32", sequence),
                port("key", "F32", sequence),
                port("value", "F32", sequence),
                port("mask", "I64", mask),
            ],
            "outputs": [port("context", "F32", sequence)],
            "attributes": {
                "head_count": 2, "head_width": 2, "causal": False,
                "scale_by_sqrt_head_width": True,
                "mask_semantics": "one_attend_zero_mask",
            },
        }
    if kind == "sequence.select_first_token":
        return {
            "id": "pool",
            "operator": kind,
            "inputs": [port("sequence", "F32", sequence)],
            "outputs": [port("first", "F32", ["batch", 4])],
            "attributes": {"token_index": 0},
        }
    if kind in ("activation.tanh", "activation.gelu_erf"):
        return {
            "id": "activation",
            "operator": kind,
            "inputs": [port("value", "F32", sequence)],
            "outputs": [port("output", "F32", sequence)],
            "attributes": {"form": "erf"} if kind == "activation.gelu_erf" else {},
        }
    raise AssertionError("test fixture has unknown operator")


class BertOperatorContractTests(unittest.TestCase):
    def test_each_new_operator_has_a_valid_independent_structural_contract(self):
        for name in (
            "attention.padding_mask_prepare",
            "attention.bidirectional_scaled_dot_product",
            "sequence.select_first_token",
            "activation.tanh",
            "activation.gelu_erf",
        ):
            with self.subTest(name=name):
                self.assertEqual(_operator_contract_failures(operation(name)), [])

    def test_bidirectional_attention_rejects_causal_substitution(self):
        item = operation("attention.bidirectional_scaled_dot_product")
        item["attributes"]["causal"] = True
        self.assertTrue(_operator_contract_failures(item))

    def test_bidirectional_attention_rejects_invalid_attention_heads(self):
        item = operation("attention.bidirectional_scaled_dot_product")
        item["attributes"]["head_width"] = 3
        self.assertTrue(any("feature width mismatch" in msg for msg in _operator_contract_failures(item)))

    def test_bidirectional_attention_rejects_incompatible_sequence_mask(self):
        item = operation("attention.bidirectional_scaled_dot_product")
        item["inputs"][3]["shape"] = ["batch", "wrong-sequence"]
        self.assertTrue(any("padding mask" in msg for msg in _operator_contract_failures(item)))

    def test_padding_mask_rejects_incorrect_dtype_or_semantics(self):
        item = operation("attention.padding_mask_prepare")
        item["outputs"][0]["dtype"] = "F32"
        self.assertTrue(_operator_contract_failures(item))
        item = operation("attention.padding_mask_prepare")
        item["attributes"]["mask_semantics"] = "unknown"
        self.assertTrue(_operator_contract_failures(item))

    def test_first_token_selection_rejects_wrong_index_or_shape(self):
        item = operation("sequence.select_first_token")
        item["attributes"]["token_index"] = 1
        self.assertTrue(_operator_contract_failures(item))
        item = operation("sequence.select_first_token")
        item["outputs"][0]["shape"] = ["batch", "sequence", 4]
        self.assertTrue(_operator_contract_failures(item))

    def test_erf_gelu_rejects_tanh_approximation(self):
        item = operation("activation.gelu_erf")
        item["attributes"]["form"] = "tanh"
        self.assertTrue(any("tanh approximation" in msg for msg in _operator_contract_failures(item)))

    def test_existing_causal_attention_and_gelu_vocabulary_remains_available(self):
        # A change to HFR's BERT vocabulary must not erase earlier GPT-2 rules.
        op = operation("activation.gelu_erf")
        op["operator"] = "activation.gelu_tanh"
        op["attributes"] = {}
        self.assertEqual(_operator_contract_failures(op), [])


if __name__ == "__main__":
    unittest.main()
