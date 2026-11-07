# Concept and test-improvement review

Prepared from the published repository state at commit `7e1b65720b7556ba901dd47bb32c7ce1c53c913b`, 2026-11-06.

## Bottom line

The Virtual Ground idea is most defensible as a **task-relative operational semantics**: a generative transition specification, an observer/quotient, an intention, a cost model, and rules for revising the specification when its logic changes. That is a useful research object. It is much less defensible if “Virtual Ground” is expected to be a unique, universally most generative, constant-time coordinate system for arbitrary systems.

The test suite is strong at the wrong level for that stronger claim. It proves that many frozen implementations are internally consistent on exact, small, controlled fixtures. It does not yet prove that the ground is **productive**, general, empirically valid, or equivalent to a latent system beyond a bounded horizon. The highest-value test improvements are therefore not “more unit tests” in the same style; they are:

1. productivity benchmarks against explicit baselines,
2. property-based and metamorphic tests over generated domains,
3. equivalence/conformance tests for learned automata,
4. statistically calibrated controls, held-out data, and adversarial perturbations,
5. mutation and coverage testing to find untested code paths.

## 1. Concept anatomy

### 1.1 The strongest version of the idea

Build 20 and its formalization define a Virtual Ground as

\[
\mathfrak G=(\mathcal S,\mathcal A,T,\mathcal I,\mathcal O,\mathcal J,\mathcal C,\mathcal R; s_0),
\]

i.e. admissible states, primitive operations, a partial transition law, invariants, observers, intention, cost model, revision rules and a reference state. A separate `INDEX.md` statement captures the intended distinction: the ground is the generative operational logic, not the materialized transition graph. The best tests support this version:

- `virtual_ground/build_20/BUILD_20.md` reports exact reachability, coordinates, observer quotients, macro expansion and irreversible Support-9 navigation.
- `virtual_ground/build_20/tests/test_build20.py` checks coordinate bijectivity, composition, inverses, all reachable Rotor-4 states, observer class counts, quotient navigation and ground revision.
- `virtual_ground/build_22/tests/test_ground_discovery.py` includes an out-of-family holdout test: a candidate can win inside the declared family and still fail a held-out probe.
- `virtual_ground/build_23/tests/test_build23.py` tests sparse-capacity failure, missing interventions, grammar expansion, held-out transitions and full-domain coverage.
- `virtual_ground/build_24/tests/test_build24.py` is explicit about bounded equivalence: the certificate is horizon-limited, and Build 24 is designed to punish overclaiming.
- `virtual_ground/build_28` through `build_30` also include important guards: Build 28 uses a permutation null, Build 29 includes stationary controls, and Build 30 exhaustively checks all 64 ADD8/SUB8 operand pairs.

This makes the program a good bounded-interpreter research arc, not a universal theory of systems.

### 1.2 Fault lines

#### Bare existence is nearly trivial

The formalization already says this. For any formally specified transition system, calling its own state and transition rules a ground makes existence nearly definitional. The nontrivial claim is productivity: does the ground reduce total observer/system cost for a task while preserving required semantics? The present tests mainly verify exactness, not productivity. A graph lookup, transition table, compressed encoding, or macro planner should be compared against baselines using description length, precomputation, memory, query time, expansion length and execution risk.

#### Constant time is not established

The source asks for navigation in constant time, but the formalization reasonably backtracks. A precomputed table can answer queries in constant time after \(O(|\mathcal S|)\) storage, and an explicit output of \(k\) primitive operations has an \(\Omega(k)\) cost. Thus tests should measure scaling, not just path existence. “Constant time” should be replaced by task-relative acceleration and an explicit Pareto frontier.

#### Grounds can be underidentified

Build 24 shows observer-relative predictive contexts and Build 27 notes hidden variables/stochasticity can be observationally equivalent. That is a strength only if the tests make non-identifiability measurable. The current Build 24 tests show that a one-context model can pass a bounded certificate at depth 5 and fail at depth 6; they do not generally quantify the set of indistinguishable models or the information needed to distinguish them.

#### The symbolic front end is assumed before the ground begins

Build 28 assumes tokenization and supplied trace boundaries. Build 29 uses fixed frame/hop settings and greedy nearest-prototype token clustering. Build 30 uses four calibration traces per task and a limited family of observer views. That means the Virtual Ground is often tested **after** the hard perception problem has been solved by a separate deterministic pipeline. A stronger test layer must quantify sensitivity to the front end: multiresolution frames, threshold sweeps, noise, drift, jitter, unknown alignment and clustering order.

#### No empirical sensor evidence in the second arc

The README and limitation documents are clear: Builds 16–30 use synthetic data. The empirical evidence lives in Builds 12–15. That is acceptable for a methods program, but tests should not let synthetic F1/accuracy be read as physical validity. The Build 12 case is the cautionary example: unit tests passed with impulses starting at sample 0, while the real Rochester corpus exposed a pre-roll onset bug.

## 2. What the current tests measure

The top-level scan of the repository (not counting duplicate nested snapshots) finds:

- **765 top-level test functions**, matching the published run.
- **1,448 assertion-like calls** in top-level test modules.
- **489 loop constructs** in top-level tests.
- **187 approximate assertions** (`assertAlmostEqual`, tolerances, `delta`).
- **84 `assertRaises`-style negative tests** at top level.
- **123 random/seed mentions** at top level.
- **6,717 lines** of top-level test code.
- Only **2 `subTest` occurrences across all test files**, including duplicated nested copies.

Those numbers describe a substantial unit-test suite, but not a balanced evidence system. The suite has good bones in five areas:

1. **Exact finite-domain verification.** Build 20 enumerates states, checks bijective coordinates, inverses, composition and graph reachability. This is much stronger than example tests alone.
2. **Safety and malformed-input rejection.** Builds 12, 13, 28, 29 and 30 contain many negative tests for invalid WAVs, bad rates, nonfinite values, invalid traces and unsafe archive extraction.
3. **Negative controls.** Build 28 has an order-permutation motif screen; Build 29 has stationary tone/noise controls; Build 30 checks wrong opcode/complement and pilot miscalibration.
4. **Explicit falsifiability.** Build 22 has an out-of-family holdout; Build 24 has the depth-5 versus depth-6 lesson; Build 27 reports an out-of-family rejection rather than a proof.
5. **Coverage of revision discipline.** Builds 20–23 and 25–27 test that uncertainty remains partial, conflicts are quarantined and revisions are proposals rather than automatic commits.

The suite is weaker in five other areas:

1. **Independent oracles are rare.** Many expected values come from the same design assumptions as the code under test. Good examples: fixed motif lists, fixed candidate families, hand-selected fixtures, and reports regenerated by the same pipeline.
2. **Generalization is sampled thin.** Builds 22 and 23 use 32 candidates and five hidden grounds. That is enough to test mechanisms, not enough to estimate discovery performance over a distribution of systems.
3. **Failure information is low.** With only two `subTest` uses, exhaustive loops often stop at the first failing case. A property suite should report failing inputs and aggregate counts.
4. **Statistical uncertainty is under-reported.** Fixed seeds and small held-out sets are common. Build 30’s four calibration traces per task are especially thin. Builds 13–15 use salted pair order (`secrets.token_bytes`), making exact decimals run-dependent.
5. **Performance/productivity is not a test target.** The suite checks shortest paths and exact predictions, but not planning memory, preprocessing cost, query latency, expansion cost, execution energy or risk.

## 3. Methods for improving the tests

### 3.1 Separate five kinds of claim

Every future test should be tagged by claim type:

| Claim type | Question | Typical verdict |
|---|---|---|
| Implementation correctness | Does the code do what the local definition says? | unit/algebraic tests |
| Equivalence | Do two machines/grounds make the same predictions? | canonical minimization, distinguishing sequences, certificates |
| Generalization | Does it work on unseen generated cases? | held-out generated domains, cross-validation |
| Productivity | Is it cheaper/better than a baseline? | Pareto cost benchmark |
| Empirical validity | Does it survive real measurements and controls? | external corpora, negative controls, uncertainty |

Many current tests answer the first question only. The Build 12 onset bug is exactly what happens when an implementation-correctness test is mistaken for empirical validity: the WAV fixtures all start at the impulse, so the measurement convention was never stressed.

### 3.2 Property-based and metamorphic testing

The repository is standard-library-only, but that does not prevent property-based testing. A small deterministic harness can use `random.Random(seed)` to generate finite transition systems, observers, action sets, signals and ground hypotheses. Useful properties include:

- **Soundness:** every generated legal transition belongs to the declared valid-transition set.
- **Completeness within scope:** every in-family valid transition can be generated or is marked unknown.
- **Composition:** for all sampled operations, \(T_{a\circ b}(s)=T_b(T_a(s))\).
- **Quotient congruence:** if two states are observer-equivalent and the quotient is claimed valid, their futures must agree on all task-relevant futures.
- **Observer-rate invariance:** gain scaling, DC offset, monotone time warps or token-label renaming should change only the predicted metadata, not the claimed invariant.
- **Revision locality:** a conflict quarantines evidence unless the conflict pattern meets a predeclared revision rule.
- **Deterministic regeneration:** rerunning the same seed and inputs produces bit-stable outputs where determinism is claimed.

Metamorphic relations are especially valuable here because many natural oracles do not exist:

- A spatial label permutation should not change motif discovery except for names.
- A delay of all channels should not change interval-shape conclusions.
- A gain change should not change normalized decay or boundary class.
- An observer projection must not create distinctions absent in the observed output.
- Out-of-family laws should either be rejected or produce calibrated uncertainty, not silent high-confidence identification.

### 3.3 Differential and model-based testing

For small domains, implement an independent brute-force oracle and compare it against the optimized implementation:

- exhaustive edge generation versus macro planner;
- reference RDM/Spearman implementation versus optimized implementation;
- direct finite automaton versus compiled phase program;
- reference dynamic-programming matcher versus production matcher;
- running the learned program against the full transition relation rather than only training records.

For Build 24, replace or augment bounded certificates with:

- canonical minimization of Mealy machines;
- distinguishing-word search via partition refinement;
- random Mealy-machine generation for many state counts;
- reset/non-reset and asynchronous output-order stress tests;
- counterexample minimization and report of the smallest distinguishing word.

A bounded certificate should be an explicit limitation, not the final equivalence proof.

### 3.4 Adversarial, fault-injection and negative-control tests

Each build should have a named “kill” test: a case designed to falsify its strongest claim.

- **Build 12:** noise pre-roll, impulses at nonzero offsets, clipping, silence, multiple channels, sample-rate mismatch. The key regression is: onset detection should not be allowed to fire hundreds of milliseconds before the direct-sound peak without flagging a measurement problem.
- **Builds 13–15:** second paired corpus, speaker/sentence cross-validation, labelled event correspondences, deterministic seed injection, within-speaker nulls, transcript/speaker privacy audits.
- **Build 20–23:** random grammars, out-of-family laws, stochastic observations, missing interventions, capacity censoring, nonstationary phase, variable renaming. Measure false identification and calibration, not only exactness.
- **Builds 25–26:** out-of-order delivery, duplicate events, missing steps, contradictory channels, longer pending horizons, unknown actions. The important outcome is bounded belief, quarantine and no silent invented edges.
- **Builds 27–28:** confusable alternatives, hidden variables, decoy motifs, token insertions/substitutions, rare patterns and high-cardinality noise. Report precision/recall with uncertainty and ambiguous cases retained.
- **Builds 29–30:** multiresolution frames, frequency drift, clipping, multipath-like reflections, sample jitter, nonstationary noise, weak events, pilot mismatch and hidden transfer functions. Measure ROC/PR, boundary error distributions and calibration.

### 3.5 Statistical validation

For stochastic or empirical claims, require at minimum:

- **Multiple seeds/replicates:** report mean, median, worst case, and 95% intervals rather than a single fixed seed.
- **Resampling units that match the design:** bootstrap by speaker, room, session or trace, not by correlated rows.
- **Permutation/null tests that preserve structure:** preserve marginals and pairing structure, as the stronger Builds 08, 10, 13 and 28 already do.
- **Multiple comparisons:** correct for many views/candidates using familywise or false-discovery methods; Build 28’s maximum-statistic null is a good pattern.
- **Effect sizes and tolerance margins:** for numerical tests, use interval assertions tied to measurement scale rather than fragile exact decimals.
- **Power analysis:** for negative controls, report the smallest effect the design could detect.
- **Calibration:** for ordinal evidence, check reliability; if scores remain heuristic, do not treat them as probabilities.

### 3.6 Productivity and scaling benchmarks

The concept of a productive Virtual Ground should become a benchmark, not a slogan. For each build, define:

- description length or parameter count;
- precomputation time and memory;
- query/planning time and memory;
- expansion length;
- execution count;
- failure risk and uncertainty.

Then compare against baselines such as:

- full transition graph or lookup table;
- direct shortest-path search;
- nearest-neighbor memorization;
- materialized state list;
- hand-coded rule baseline;
- no-ground baseline.

The benchmark should report a Pareto frontier across costs. That is the cleanest way to test the “most generative” and “constant-time” language without overclaiming.

### 3.7 Mutation and coverage testing

Mutation testing is a powerful way to ask whether the tests actually exercise the claimed logic. Practical mutations include:

- swapping composition order in `compose`;
- weakening `observer_view` or `inverse`;
- changing cost weights in Dijkstra/BFS;
- dropping a candidate family member;
- treating unknown edges as recoverable;
- turning bounded equivalence into unbounded equivalence;
- replacing a calibrated pilot with a nominal pilot;
- changing threshold or motif boundaries.

A killed mutant is one that at least one test fails. Core modules should have a high killed-mutant target, with surviving mutants reviewed as potential specification gaps. Branch coverage should be required for observer maps, partial transitions, failure paths and revision monitors. The standard library can support this with `trace` or small AST-based mutation harnesses; no third-party dependency is required.

### 3.8 Traceability and acceptance gates

Every claim in `INDEX.md` should have one of:

- a named test or experiment,
- an explicit “not established” note,
- or a limitation entry.

A claim-to-test matrix would prevent synthetic fixture success from silently becoming a general claim. New validation gates could include:

1. no new universal claim without a general-domain or external benchmark;
2. no equivalence claim from bounded conformance alone;
3. no probabilistic interpretation of ordinal scores;
4. no deterministic tolerance test that fails across supported Python versions without a numeric-stability note;
5. no stochastic result reported from one seed unless it is labelled a smoke test;
6. no empirical claim without a negative control and a predeclared falsification rule.

## 4. Prioritized test backlog

### P0 — Fix known blind spots

1. **Build 12 pre-roll regression fixture.** Add a golden fixture with one second of low-level noise before the impulse, plus impulses at multiple offsets. Require the onset detector to either locate the direct-sound peak or emit a clear uncertainty/failure marker. This is the clearest known empirical bug missed by unit tests.

2. **Productivity benchmark for Builds 20–23.** Compare ground-based navigation against a materialized graph and lookup baseline across state-space sizes. Report precompute, memory, query time and expansion cost. Require the ground to beat a specified baseline on at least one cost dimension without losing semantics.

3. **Random generated domains for discovery/synthesis.** Generate many finite grounds from a declared grammar, including out-of-family and noisy cases. Measure identification accuracy, calibration, false rejection and cost. A 32-candidate closed family is a mechanism test; a distribution of families is a discovery test.

4. **Automata equivalence for Build 24.** Add canonical minimization, distinguishing sequences and random Mealy machines. The depth-5/depth-6 result should become the smallest member of a broader counterexample family, not an isolated demonstration.

5. **Front-end robustness for Builds 29–30.** Add frame/hop sweeps, many calibration traces, noise/drift/jitter distributions, pilot miscalibration and transfer-function variation. Report detection performance as a distribution, not a single held-out score.

### P1 — Strengthen statistical and empirical evidence

1. **Deterministic seed injection for Builds 13–15.** Replace run-dependent salts with explicit seed parameters and log them. Keep randomized nulls, but make them reproducible.

2. **Cross-validation by speaker, room and session.** The Rochester and TAPS results should report stability across folds and units of independence. Single-corpus results should remain local claims.

3. **Second empirical corpus.** Especially for Builds 13–15, a second paired-sensor corpus or at least a speaker/sentence holdout would separate “TAPS geometry” from “paired-sensor geometry.”

4. **Numeric-stability oracles.** Build 08’s Python-version drift shows that turning-angle computations need a reference oracle and environment tolerances. Similar treatment should apply to FFTs, decay fits and signal features.

5. **Calibrated uncertainty for Builds 27–28.** Either convert ordinal scores into calibrated probabilities with reliability checks, or keep them explicitly non-probabilistic and report error rates under permutations.

### P2 — Improve suite quality and maintainability

1. **Use `subTest` for exhaustive loops.** This preserves the value of enumeration while reporting all failing cases.
2. **Add branch coverage and mutation testing.** Measure whether tests kill changes in algebra, observers, cost models, automata learning and signal coding.
3. **Add property-based generators.** A stdlib property harness can still be deterministic, separated from the frozen builds and used in a future validation package.
4. **Separate smoke, unit, property, benchmark and empirical tiers.** The full 765-test run is a regression suite, not a single evidentiary tier.
5. **Claim traceability.** Link each claim in the index to test names, reports and limitation entries.

## 5. Closing judgment

The concept is coherent if read narrowly and testable definitions are attached. The present suite verifies a large amount of local computation, and its best tests are genuinely informative because they include exhaustive finite checks, negative controls and explicit “do not overclaim” boundaries. The shortfall is not test count; it is evidence level. The program needs tests that compare against baselines, expose underidentification, stress the perception front end, report uncertainty and penalize bounded equivalence.

A one-sentence verdict: **it is a good bounded interpreter whose tests mostly prove self-consistency; the next generation should prove productivity, equivalence and robustness under adversarial cases.**
