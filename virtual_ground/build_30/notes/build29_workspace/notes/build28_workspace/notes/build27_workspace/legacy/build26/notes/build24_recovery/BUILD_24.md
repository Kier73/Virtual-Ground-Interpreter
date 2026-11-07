# Build 24 — Latent Context Discovery and Predictive Virtual Grounds

## Result

Build 24 removes the hidden environmental phase from the learner's input. The learner receives only action/output traces through a deterministic resettable interface. It infers the minimal predictive context machine that explains the observable future, then compiles that machine either to a modular phase program or to a general finite automaton.

**Tests:** 17 / 17 passed. The package also includes one Build 23 synthesis regression test.

All results are synthetic and deterministic. No real sensor, TAPS, or physical-system data were used.

## Why this is a different step

Build 23 learned a symbolic update law while `phase` was an explicitly supplied state field. Build 24 does not receive a phase field, a mode label, or a hidden-state count. It receives:

- a known finite action alphabet;
- a reproducible reset-to-start protocol;
- observed output sequences from those actions;
- selected sensor channels.

The hidden context is internal to the teacher. The learner never reads it.

## Experimental results

| Fixture / observer | Physical modes in test oracle only | Learned predictive contexts | Clock interpretation |
|---|---:|---:|---|
| Coupled six / parity sensor | 6 | 2 | 2-cycle |
| Coupled six / residue-3 sensor | 6 | 3 | 3-cycle |
| Coupled six / joint sensors | 6 | 6 | 6-cycle |
| Delayed six / rare-event sensor | 6 | 6 | 6-cycle |
| Aliased six / residue-3 sensor | 6 | 3 | 3-cycle |
| Unobservable eight / constant sensor | 8 | 1 | No observable progression |
| Partial four / modulo-2 sensor | 4 | 4 | Non-bijective; no single cycle |

The physical-mode column is retained only in the test report so that the test harness can score the learner. It is not part of the learner's information.

### Observer quotients

A six-mode fixture emits two sensor channels: mode modulo 2 and mode modulo 3. The first observer learns two predictive contexts; the second learns three; the joint observer learns six. Over the mode set `{0,...,5}`, the pair of residues uniquely identifies the mode, consistent with the Chinese remainder relationship.

A different fixture has six hidden physical modes but only modulo-3 outputs and phase increments that respect that quotient. The learner correctly returns three predictive contexts. It does not invent a distinction between modes that have identical future observable behaviour.

An eight-mode fixture emits a constant output under every action. The learned predictive quotient contains one state. The eight physical modes are not identifiable under that observer and probe family.

### Delayed evidence

The delayed-six fixture emits a positive sensor output only when `PROBE_A` is applied in one hidden mode. A learner tested only through input-word depth 1–5 returns a one-state model and passes **only that bounded test**. At depth 6, the sequence `HOLD HOLD HOLD HOLD HOLD PROBE_A` becomes a counterexample; the observation table adds a distinguishing suffix and expands to six predictive contexts.

This is a core result: bounded equivalence at depth `d` does not imply equivalence at all depths. The report preserves the tested horizon.

### Irreversible context dynamics

The partial-four fixture uses a non-bijective `HOLD` transition. The learner recovers four predictive states, but `HOLD` is not a single cycle. The compiler retains a finite automaton rather than forcing the ground into a reversible phase/group representation.

## Active diagnostic policy

The learner includes a cost-aware distinguishing-probe selector:

\[
P^* = \arg\max_P \frac{H(Y_P\mid H)}{c(P)}
\]

where `H` is the current set of candidate access histories and `Y_P` is the observed response to probe word `P`.

For the delayed-six fixture, the adaptive policy uses repeated one-step `PROBE_A` observations. It identifies all six predictive contexts with worst-case probe cost 5 and mean cost 20/6 under a uniform initial-context weighting. For the joint parity/modulo-3 sensor, one `PROBE_B` is sufficient to distinguish all six contexts.

The selector's empirical entropy is a finite decision score, not a guarantee of optimal probing for arbitrary systems.

## Observation-table learner

The learner uses an L*-style observation table for deterministic Mealy behaviour. Let `A` be the action alphabet, `Y` the output alphabet, `S` a set of access sequences, and `E` a finite set of distinguishing suffixes. Define:

\[
\operatorname{row}(s)(e) = \operatorname{output}(s e)[|s|:]
\]

Histories with identical rows are provisionally treated as one predictive context. The table is refined using:

- **closedness:** every one-action extension of a represented history maps to an existing row;
- **consistency:** equal rows have equal one-action output and successor behaviour;
- **counterexample refinement:** a failing bounded conformance word contributes a suffix beginning at its first output mismatch.

The resulting state identity is an observable predictive equivalence class, not a claim about the hidden system's ontological variables.

This follows the established active Mealy-machine learning approach using observation tables and counterexamples. Build 24's contribution is the integration of that procedure into the Virtual Ground workflow: observer quotients, latent clock-coordinate detection, cost-aware distinguishing policies, ground compilation, and explicit evidence limits.

## Compiler outputs

1. **`modular_phase_program`** when a chosen action (here `HOLD`) induces a single cycle across all learned contexts and every action has a constant stride in that coordinate:
   \[
   z'=(z+\Delta(a))\bmod n
   \]
   The phase/action output table is retained.
2. **`finite_predictive_automaton`** otherwise. This retains the learned transition and output tables without imposing invertibility.

Every compiler output is checked against the learned machine for every state/action pair before being serialized.

## Evidence and limitations

- The teacher supports deterministic reset to a fixed initial hidden context. This is a strong assumption; real systems may be non-resettable or may not expose controlled interventions.
- The action alphabet and available sensor channels are supplied by the interface. They are not discovered from arbitrary raw signals.
- The learner discovers a minimal predictive quotient under the tested observer. It cannot prove how many physical hidden states exist if some are observationally equivalent.
- Equivalence checks are exhaustive only for all action words up to the reported depth. They are a finite test oracle, not an equivalence oracle for arbitrary live systems.
- The experiments are noiseless and stationary. Stochastic dynamics, continuous state, time drift, asynchronous sensors, nonstationarity and changing action alphabets remain open.
- The active probe selector optimizes a bounded empirical information score; it does not yet account for risk, irreversible actions, or belief-state control over a physical process.
- A single-cycle `HOLD` coordinate is an inferred representation when supported by the predictive machine. A trivial one-state quotient is explicitly reported as no observable progression.

## Files

- `latent_ground.py`: hidden-context teacher, observation-table learner, counterexample refinement, active diagnostic tree and compiler.
- `run_build24.py`: deterministic experiment and report generation.
- `tests/test_build24.py`: 17 tests including Build 23 regression.
- `legacy/build23_ground_synthesis.py`: copied Build 23 module used for the regression check.
- `reports/`: numerical outputs, learned executable specifications, observer quotients and delayed-horizon study.
