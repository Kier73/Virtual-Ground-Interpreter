<!-- Markdown conversion of Invariant_Adaptive_Computation_Research_Checkpoint_01.docx -->
<!-- Converted 2026-11-01; content preserved as text, headings, equations, and tables. -->

# INVARIANT ADAPTIVE COMPUTATION

*A cross-substrate hypothesis for preserving computational identity through physical change*

**RESEARCH CHECKPOINT 01 | 1 NOVEMBER 2026**

**CURRENT CENTRAL PROPOSITION**  
A physical system can change its material realization, internal coordinates, spectral modes, network structure and memory representation while preserving a task-relevant causal relationship between inputs, internal transitions and observable outputs.

## Purpose

Consolidate the first three conceptual iterations and the latest refinement into a reusable checkpoint. The note records the minimal structure, mathematical translations, candidate natural analogues, proposed unifying relation, limitations and next experiments.

## Status

Working hypothesis, not an established universal law or completed theory. Established results are identified as precedents; the cross-substrate synthesis and proposed relational-transport construction remain hypotheses to test.

## Working distinction

Turing completeness concerns universal computability in an idealized formal model. This project asks a different question: what invariant organization allows a physical system to preserve a meaningful computational behavior while adapting to its environment?

# 1. Research question and scope

Can a common computational organization be identified across physical interactions from molecular and cellular scales through engineered materials and macroscopic systems, without defining it by a particular element, particle, device or signal carrier?

The target is not “everything computes.” Physical systems evolve, but evolution alone does not establish computation. A useful computational account needs an explicit representation relationship: which physical states stand for which abstract states, how inputs are encoded, how physical evolution realizes an abstract transition, and how outputs are interpreted. Physical-computing theory emphasizes this representation/instantiation relationship. [1]

**REFINED QUESTION**  
What must remain invariant for two physically different systems to count as performing the same task, even when their internal states and dynamics differ?

## Three boundaries

- Computational identity is task-relative: a distinction is meaningful only relative to declared observables, an objective or function, and a context.
- Substrate independence does not mean physical independence: every realization still depends on material dynamics, energy, noise, interfaces and finite resources.
- Adaptivity does not imply universal efficiency: contextual pruning can help when the environment restricts the useful search space, but it does not make every intractable problem tractable.
# 2. Iterations retained in this checkpoint

| Iteration | Main move | Retained result |
| --- | --- | --- |
| 1 — Physical continuity | Trace computation across physical scales rather than across element types. | Distinguishable states, constrained transitions, feedback and memory appear in many physical systems; no single mechanism is universal. |
| 2 — Minimal structure | Reduce the proposal to five components and a recurring process. | State, information, memory, invariant and transition; observe → distinguish → preserve → constrain → transform. |
| 3 — Multiple mathematical languages | Translate the same proposal into spectral, dynamical, relational, predictive and thermodynamic descriptions. | Fourier/wavelets, state space, Koopman, graph Fourier, information theory and thermodynamics are complementary views. |
| 3+ — Causal refinement | Replace “matching patterns” with preservation of task-relevant input/output behavior. | The strongest candidate invariant is causal/behavioral equivalence, not an unchanged spectrum or physical geometry. |

The first iteration also considered chemical reaction networks, reaction–diffusion organization in cells, and physical reservoir computing as examples of computation-like or computationally useful physical dynamics. These are anchors for investigation, not proof that natural systems are universally Turing-complete or that all self-organization is computation.

# 3. Minimal structure: five components

| Symbol | Component | Operational meaning |
| --- | --- | --- |
| S / x | State | A physically or symbolically distinguishable configuration that can change. |
| I | Information | Differences between states that affect relevant future outcomes. |
| M | Memory | Retained history or state sufficient for required prediction and continuity. |
| K | Invariant | The relationships or constraints that define the computational identity for a task. |
| T / F | Transition | A permitted state transformation under physical and contextual constraints. |

## Minimal loop

$$
OBSERVE  →  DISTINGUISH  →  PRESERVE  →  CONSTRAIN  →  TRANSFORM  →  REASSESS
$$

## Compact state update

$$
x(t+1) = F(x(t), u(t), c(t), M(t) | K(t))
$$

Here u(t) is incoming information and c(t) is estimated context. K(t) is shown as time-dependent because the latest refinement distinguishes stable meta-constraints from revisable operational objectives.

# 4. Mathematical languages: complementary views

| Representation | Core expression | What it reveals | What it cannot establish alone |
| --- | --- | --- | --- |
| Fourier / Hertz | X(f) = ∫ x(t)e^(−i2πft) dt | Temporal frequencies, amplitudes and phases. | A matching frequency signature does not prove matching computation. |
| Wavelets | W(a,b): scale- and time-localized coefficients | Transient and changing frequency content. | Does not identify which changes are task-relevant without a task model. |
| State space | ẋ = F(x,u,c) | Trajectories, reachable states and feedback. | Coordinates may be implementation-specific. |
| Koopman | (Kg)(x) = g(F(x)) | Evolution of observables for nonlinear dynamics. | Finite approximations can omit relevant modes or carry error. |
| Graph Fourier | L = D−A; L = UΛUᵀ; x̂ = Uᵀx | Relational modes over a network. | Eigenvalues or spectral magnitudes alone do not uniquely identify a network or its behavior. |
| Information theory | min[I(H;Z) − βI(Z;Y)] | Compression of history while retaining information predictive of Y. | Predictive relevance depends on which future variables Y were selected. |
| Thermodynamics | ΔS_total ≥ 0; W_erase ≥ kBT ln 2 (ideal bit erasure) | Physical costs and irreversibility of memory operations. | Thermodynamic feasibility does not by itself define computational meaning. |

## Interpretation

These are not competing claims about what computation “really is.” They are different instruments: temporal signal analysis; dynamical modeling; relational analysis; predictive compression; and physical cost accounting. Their usefulness is highest when they are tied to the same task, interfaces and observed trajectories.

# 5. Central refinement: invariance of causal behavior

## 5.1 Substrate model

Let p identify a physical substrate. Each realization has its own internal state, dynamics and measurement function:

$$
x⁽ᵖ⁾ₜ₊₁ = Fₚ(x⁽ᵖ⁾ₜ, uₜ, cₜ, ηₜ)
$$

$$
y⁽ᵖ⁾ₜ = Hₚ(x⁽ᵖ⁾ₜ)
$$

The noise term ηₜ is optional but useful for stochastic or noisy systems. A common computational contract K specifies the allowed inputs and contexts, the observables that matter, and the acceptable output behavior.

## 5.2 Behavioral equivalence

Two substrates p and q are approximately equivalent for contract K when, across the declared test conditions, their observable output distributions remain close:

$$
d( Pₚ(Y | U,C,K), Pq(Y | U,C,K) ) ≤ ε
$$

The distance d must be selected for the task: total-variation distance, Wasserstein distance, a task-specific loss, or another justified measure. ε is a stated tolerance. This comparison is stronger than matching a few summary statistics because it tests the behavior induced by input sequences and context.

## 5.3 State relation / approximate bisimulation

A relation R between states of two systems can express correspondence without forcing their internal state vectors to be identical. Paired states should have similar relevant observations, and under corresponding inputs their successor states should remain paired. Approximate bisimulation formalizes this kind of two-way behavioral correspondence for dynamical systems. [2]

## 5.4 Common abstract dynamics

A stronger construction uses a representation map φₚ from each substrate state into a shared abstract state z:

$$
φₚ(Fₚ(x,u,c)) ≈ G_K(φₚ(x),u,c)
$$

This is an approximate commuting relation: taking a physical step and then abstracting should agree with abstracting first and applying the common transition G_K. If the map is invertible, the relationship is related to conjugacy; if it merges physically distinct states, it is an abstraction or quotient. The representation must preserve the task-relevant observables.

**CURRENT BEST CANDIDATE**  
Computational identity is an equivalence class of realizations that preserve a specified causal input–output behavior within a declared context and tolerance.

# 6. Pushing the spectral curiosity: time × relationships

## 6.1 Static graph with time-varying signals

For N nodes observed over T samples, collect signals into X ∈ Rᴺˣᵀ. For an undirected weighted graph, let L = UΛUᵀ be its graph Laplacian eigendecomposition, and let Q be a temporal Fourier basis. A joint time–vertex transform can be written:

$$
X̂ = Uᵀ X Q
$$

This represents activity jointly by temporal frequency and graph frequency. Time–vertex signal processing provides a formal framework for analyzing signals defined over graph vertices and time. [3]

## 6.2 The changing-network problem

If the graph itself changes, its Laplacian and eigenbasis may change over time:

$$
Lₜ = Uₜ Λₜ Uₜᵀ     and     zₜ = Uₜᵀ xₜ
$$

A modal coordinate at t may not refer to the same relational mode at t+1 because eigenvectors can change sign, reorder, or rotate inside degenerate eigenspaces. A raw difference zₜ₊₁ − zₜ can therefore confuse a change of coordinates with a change in the physical signal.

## 6.3 Proposed relational transport

For a fixed node space and compatible orthonormal bases, define a basis-transport matrix:

$$
Pₜ = Uₜ₊₁ᵀ Uₜ
$$

$$
Δ_rel zₜ = zₜ₊₁ − Pₜ zₜ
$$

This is a candidate diagnostic, not a general solution. It requires consistent node identity and basis alignment. When dimensions or node identities change, an explicit correspondence, common embedding or coarse-graining map is needed. Within repeated or nearly repeated eigenvalues, align invariant subspaces (for example by an orthogonal Procrustes step) rather than trusting individual eigenvectors.

## 6.4 What might be invariant?

- Not necessarily a frequency, amplitude, phase, eigenvalue list or graph topology taken alone.
- Potentially, a task-conditioned relationship among inputs, evolution of observables, state correspondences and outputs.
- Temporal and graph spectra can help discover candidate modes and changes; causal behavior tests whether those modes matter to the task.
## Important caution

Spectral similarity is a descriptor, not a proof of computational equivalence. Different structures can share spectra, and magnitude-only summaries can discard phase and directional information. The stronger test is whether matched inputs induce corresponding observable behavior over time.

# 7. Allowing the invariant to adapt

The earlier model treated K as fixed. That is too rigid for a system whose context and objective may change. The refinement is a hierarchy:

| Layer | Role | Can it change? |
| --- | --- | --- |
| K₀ — meta-invariant | Rules for maintaining continuity, valid representation, constraint compliance and justified objective revision. | Only under an explicitly higher-level governance rule. |
| Kₜ — operational invariant | Current task contract: relevant distinctions, outputs, tolerances and success conditions. | Yes, when evidence or context justifies revision. |
| πₜ — implementation policy | Current encoding, topology, frequencies, pathways, memory allocation and control strategy. | Freely within constraints. |

$$
Kₜ₊₁ = Γ(Kₜ, evidenceₜ, contextₜ ; K₀)
$$

This distinguishes continuity from rigidity. The meta-invariant governs how the system revises its own operational objective; the current policy can adapt much faster. For engineered systems, K₀ and Kₜ may be specified by designers or users. In natural systems, “purpose” should not be assumed to mean conscious intention: it may be inferred from self-maintenance, viability, selection or observed function.

# 8. Contextual transformation filter

The contextual pruning idea separates three filters, because impossibility, irrelevance and inefficiency are not the same thing.

| Filter | Question | Decision |
| --- | --- | --- |
| 1. Feasibility | Can the transformation occur with the available physics, resources, time and reachable states? | Discard physically impossible or unavailable actions. |
| 2. Functional relevance | Does it preserve or advance the current contract Kₜ? | Discard actions that cannot contribute to the task, subject to uncertainty. |
| 3. Efficiency / robustness | Which viable action best balances error, energy, time, risk and complexity? | Prefer non-dominated actions; retain alternatives where uncertainty or future change warrants it. |

$$
a* = arg minₐ∈A_feasible [ L_K(a) + λE(a) + μR(a) + νC(a) ]
$$

L_K is task loss; E is energy or resource cost; R is risk/instability; C is computational or structural cost. The weights can depend on context. The expression is a design template, not a universal natural law. Do not permanently discard uncertain alternatives merely because they are currently suboptimal.

# 9. Natural and physical anchors: what they show

Chemical reaction networks (CRNs). Formal CRN models have results establishing universality under particular assumptions and encodings. Different CRN variants have different guarantees: deterministic convergence, stochastic error tolerance, continuous concentrations, inhibitors and unbounded resources are not interchangeable assumptions. The mathematical result does not mean an arbitrary naturally occurring chemical soup is a practical universal computer. [4, 5]

Min protein reaction–diffusion system. In E. coli, MinD and MinE generate spatiotemporal oscillations that help position the division machinery. A 2025 study reports robust dynamic patterns across a range of Min-protein levels and growth conditions, an invariant pattern wavelength over the tested phase diagram, and resource-optimal natural expression levels. This is an example of robust, context-sensitive physical organization—not proof of general-purpose computation. [6]

Physical reservoir computing. Researchers exploit the native dynamics of electronic, optical, mechanical and other materials as computational reservoirs. A physical system is characterized through its inputs, readout, task performance and dynamical properties. Substrate variety is real, but scaling, interfaces, controllability, memory and task generality remain practical challenges. [1, 7]

**EVIDENCE BOUNDARY**  
These examples support the plausibility of computation-like state transformation, self-organization, robustness and substrate diversity. They do not yet establish a universal natural invariant shared across all physical scales.

# 10. Proposed test program

Goal: test whether causal behavior is preserved more reliably than a spectral or structural signature when the substrate, its timescale or its network organization changes.

1. Specify one task contract K: allowed input sequences, environmental contexts, measured outputs, acceptable error ε, hard constraints and resource budget.
1. Choose two or more substrates or models with different physical dynamics (initially simulated reservoirs; later acoustic, thermal, electronic or chemical systems where measurement is practical).
1. Calibrate input/output interfaces, normalize units and record trajectories under common input and context sequences.
1. Estimate candidate internal states and representations: temporal spectra, graph spectra, Koopman observables and predictive/causal states.
1. Infer mappings or relations between states and evaluate the approximate commuting relation or bisimulation residual on held-out inputs and contexts.
1. Perturb context midway: change input statistics, coupling, frequency, noise, resource availability or network topology. Test whether the realization adapts while preserving Kₜ or revises Kₜ under K₀.
1. Compare against ablations: spectral matching alone; fixed representation; no predictive memory; no adaptive reconfiguration; and unconstrained optimization.
## Metrics

| Metric | Question answered |
| --- | --- |
| Input/output behavioral distance | Do the systems still perform the same declared task? |
| Bisimulation / transition residual | Do corresponding states remain corresponding after matched inputs? |
| Predictive information retained | Does the compressed memory preserve relevant future information? |
| Invariant drift | How much does task behavior change under perturbation? |
| Adaptation cost | How much time, energy and structural reconfiguration are required? |
| Robustness / recovery | Does performance recover under held-out disturbances? |

# 11. Open questions and failure conditions

- Task grounding: who or what defines the outputs that count as meaningful? Can that objective be inferred from behavior without circularity?
- Observable discovery: how can the system identify the smallest set of observables that preserves the task, rather than merely fitting the training environment?
- Changing topology: how should node correspondence, eigenspace alignment and relational transport be handled when nodes appear, disappear or change identity?
- Invariant revision: what prevents an adaptive system from changing its objective so much that continuity becomes meaningless?
- Universality: does a given substrate implement only a bounded task family, or can it emulate a universal machine under explicit assumptions? Test this separately.
- Complexity: contextual pruning may reduce a practical search space, but it is not a general solution to NP-hardness or undecidability.
- Thermodynamics: how much energy and entropy production are required for sensing, memory updating, erasure and reconfiguration?
The hypothesis would be weakened if spectral and state-space mappings fail to predict held-out outputs; if apparent invariance depends entirely on the chosen measurement interface; if objective revision cannot be distinguished from loss of identity; or if the proposed relation offers no advantage over simpler task-specific models.

# 12. Checkpoint summary

**WORKING DEFINITION**  
Invariant adaptive computation is a system-level property in which a physical realization can reorganize its states, memory, modes and transitions in response to context while preserving a specified causal input–output relationship within a declared tolerance.

## Minimal form

$$
Identity = task-relevant causal behavior, not fixed physical structure.
$$

$$
Adaptation = permitted change of realization under a governing meta-invariant.
$$

$$
Equivalence = corresponding outputs and transitions under comparable inputs and contexts.
$$

## Immediate next step

Build a small computational experiment with two deliberately different dynamical substrates and a shared task contract. Compare (a) spectral similarity, (b) state-space mapping, and (c) approximate behavioral equivalence under controlled context shifts. This is the shortest route from conceptual synthesis to a falsifiable result.

# Selected references

> The following sources ground the established mathematical and experimental precedents summarized above. The proposed cross-substrate synthesis is not attributed to any single source.

[1] Susan Stepney (2024). “Physical reservoir computing: a tutorial.” Natural Computing 23, 665–685. DOI / source
[2] Antoine Girard & George J. Pappas (2011). “Approximate Bisimulation: A Bridge Between Computer Science and Control Theory.” European Journal of Control 17(5–6), 568–578. DOI / source
[3] Benjamin Perraudin & Pierre Vandergheynst (2018). “A Time-Vertex Signal Processing Framework: Scalable Processing and Meaningful Representations for Time-Series on Graphs.” IEEE Transactions on Signal Processing 66(3), 817–829. DOI / source
[4] Mathieu Hemery, François Fages & Sylvain Soliman (2021). “Compiling Elementary Mathematical Functions into Finite Chemical Reaction Networks via a Polynomialization Algorithm for ODEs.” CMSB 2021. DOI / source
[5] Ho-Lin Chen, David Doty & David Soloveichik (2014). “Deterministic Function Computation with Chemical Reaction Networks.” Natural Computing 13, 517–534. DOI / source
[6] Judy E. Kim et al. (2025). “Robust and resource-optimal dynamic pattern formation of Min proteins in vivo.” Nature Physics 21, 1160–1169. DOI / source
[7] Xiangpeng Liang et al. (2024). “Physical reservoir computing with emerging electronics.” Nature Electronics 7, 193–206. DOI / source
[8] James P. Crutchfield & Cosma Rohilla Shalizi (1999). “Thermodynamic depth of causal states: Objective complexity via minimal representations.” Physical Review E 59, 275. DOI / source
[9] Bart De Schutter (2000). “Minimal state-space realization in linear system theory: an overview.” Journal of Computational and Applied Mathematics 121, 331–354. DOI / source
[10] “Koopman operator dynamical models: Learning, analysis and control.” Annual Reviews in Control 52 (2021), 197–212. DOI / source
[11] “An overview of Koopman-based control: From error bounds to closed-loop guarantees.” Annual Reviews in Control 61 (2026), 101035. DOI / source
