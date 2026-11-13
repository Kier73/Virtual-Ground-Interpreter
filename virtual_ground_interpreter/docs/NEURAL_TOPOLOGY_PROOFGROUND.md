# Neural topology ProofGround intake

## Purpose

HFR-002 produces a versioned, framework-independent neural computation graph with typed tensors, operation ports, and directed connections. This adapter maps that graph into VGI's existing `ProofGround` representation so its structural claims can be decomposed into explicit proof obligations.

It is a **proof-planning and evidence-intake adapter**. It does not execute the neural graph, run a theorem prover, validate proof terms, or infer that an upstream tool's `verification.status = passed` is a kernel result.

## Input and source binding

The adapter accepts only `in-formation-space.neural-computation-graph.v0.1` with:
- a pinned 40-character lowercase source commit SHA;
- a source graph marked complete for its supported family template;
- the source graph's structural verification marked passed;
- supported canonical operator types with typed ports;
- resolved edges with exact dtype/shape compatibility.

Before constructing a ProofGround, VGI independently checks its own supported subset of:
- graph input, tensor, operation and graph output endpoint resolution;
- one producer for each operation input and connectivity for each output;
- tensor and graph input coverage;
- local operator-dimensional contracts;
- operation dependency acyclicity.

This local structural pass is reported separately from kernel proof status. The source model-family interpretation remains a declared assumption. For example, VGI does not prove from Safetensors headers alone that a fused projection represents query/key/value or that an attention mask is causal.

## AND/OR obligation structure

A root obligation,

`all_supported_neural_topology_obligations_hold`,

is connected to six jointly required subgoals:

1. Pinned source provenance.
2. Complete tensor catalog classification and binding.
3. Operation port and local dimensional contracts.
4. Typed edge endpoint and compatibility contracts.
5. Acyclic operation dependency topology.
6. Complete graph input/output and operation-port connectivity.

The tensor, operation and edge groups expand into individual obligations. Hyper-transitions use VGI's existing semantics: subgoals on one transition are an AND bundle; multiple transition alternatives for one source are OR alternatives.

Each obligation includes the source graph digest, repository and revision, plus the relevant typed descriptor. This makes a change in the source description produce new obligation identities and a new proof environment options fingerprint.

## What "passed" means here

The package manifest has a `local_validation.status = passed` section for the adapter's deterministic structural checks. It separately reports a ProofGround summary. Every obligation starts as `unverified`.

The source graph's own passed flag does not promote any VGI obligation. A claim becomes `kernel_accepted` only when a caller supplies an explicit `VerifiedKernelReceipt` whose:
- obligation ID matches the exact ProofGround obligation fingerprint;
- environment fingerprint matches the exact adapter/rule environment;
- checker identity, version, proof-term fingerprint and receipt reference are present;
- result is explicitly accepted.

Raw source flags or proof claims are not converted into receipts. VGI still does not check the proof term; receipt creation must be performed by a separate, trusted proof-checking path.

## Usage

```python
import json
from pathlib import Path

from vgi import build_neural_topology_proof_ground

graph = json.loads(Path("gpt2-typed-topology.json").read_text())
package = build_neural_topology_proof_ground(graph)

print(package.manifest())
print(package.ground.summary())
```

The resulting object is suitable for proof exploration, obligation partitioning, and later import of exact external kernel receipts. It is not an executable neural program or a completed formal proof.

## Evidence boundary

The adapter uses graph descriptors and declared operator-family semantics; it does not load the numerical weight payloads. Its local checks establish internal consistency of the supported typed topology representation. They do not establish that the source model's learned parameters, tokenizer, forward pass, or semantic behavior have been reconstructed.

The signal-state interpreter remains Signal8-specific. This ProofGround intake does not extend that runtime to floating-point matrix multiplication, attention, or arbitrary tensor operators.
