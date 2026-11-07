# Build 26 — Incremental Online Construction of a Partial Virtual Ground

## Result

Build 26 extends the online observer from Build 25 so it can build a partial predictive transition model while a continuing stream is being observed. It does not require a reset interface or a complete precompiled machine. The inferred object explicitly distinguishes known, ambiguous and unknown state/action transitions.

**Build 26 primary suite:** 27 / 27 passed.  
**Build 24 inherited suite:** 17 / 17 passed.  
**Build 25 inherited suite:** 34 / 34 passed.  
**Total executed tests:** 78 / 78 passed.  
**Evidence class:** synthetic deterministic finite-state streams only. No physical sensor or TAPS recordings were processed.

The full Build 24 source, tests, reports, original archive and recovery notes are embedded in this package because the previous Build 24 chat artifact was unavailable to the user.

## What is new

1. **No precompiled machine required:** Build 26 starts from an action/channel interface and an empty transition model.
2. **Unknown transitions remain unknown:** no edge is silently filled with an identity, no-op or guessed successor.
3. **Asynchronous channel ingestion:** individual sensor channels may arrive before/after action registration and out of order across steps; events commit in action-step order only when selected channels are complete.
4. **Two output contracts:** `observation` (post-action state observation) and `mealy` (action-conditioned response) have explicit, distinct history signatures.
5. **History-horizon refinement:** collisions in a context/action pair increase the predictive suffix horizon; unresolved collisions remain visible at the configured maximum.
6. **Partial predictive quotient:** histories merge only when observed action coverage, outputs and successor partition classes agree. Sparse data may over-split; unknown coverage is not generalized away.
7. **Executable partial ground:** JSON serialization/reload preserves the candidate specification. Known transitions execute; unknown transitions raise `UnknownTransitionError`.
8. **Bounded stream memory:** event history, pending steps, duplicate cache, audit ring and context count have explicit limits. The incomplete retained-window boundary is excluded from transition induction after truncation.
9. **Version lineage:** structural changes and horizon refinements are versioned. Support-count updates alone do not necessarily create a new ground version.
10. **Probe discipline:** known-edge information scoring is separate from unknown-edge exploration. The latter reports no information-gain estimate; it only ranks safe unknown operations by declared novelty/cost/risk. If every unknown operation exceeds the risk ceiling, it declines to probe.
11. **Bounded conflict/version lineage:** persistent unresolved collisions are retained in a bounded conflict ring; version history is capped while lifetime version counters remain available. A quarantined or context-budget-exceeded candidate cannot execute.

## Core model

A committed event is `(step, action, output)`. Let `c_t` be the bounded suffix context before event `t` and `c_(t+1)` the suffix after it. The observation contributes:

\[
(c_t,a_t)\mapsto(y_t,c_{t+1})
\]

For each context/action pair:

- one consistent observed output/successor alternative gives a `known` edge;
- multiple observed alternatives give an `ambiguous` edge;
- no observation gives an `unknown` edge.

The suffix length is increased only when an observed context/action collision requires more predictive history. This creates a provisional finite-history state representation, not a proof of physical hidden-state identity or global minimal predictive equivalence.

## Main results

### Observer quotient recovery

The same coupled-six fixture was streamed with only `HOLD` actions and post-action observation channels:

| Observer | Selected channels | Learned predictive contexts | Horizon | Known transitions | Unknown transitions |
|---|---|---:|---:|---:|---:|
| Parity only | 0 | 2 | 1 | 2 | 4 |
| Residue-3 only | 1 | 3 | 1 | 3 | 6 |
| Joint | 0, 1 | 6 | 1 | 6 | 12 |

The unobservable-eight fixture remains one predictive context, with only the exercised `HOLD` transition known. This preserves Build 24's observer-relative quotient insight without requiring a resettable membership-query teacher.

### Delayed distinction

The delayed-six Mealy fixture emits no distinguishing response for the first five repeated `PROBE_A` actions. At five committed events the learner has one provisional context. The sixth event exposes a conflict; horizon refinement reaches 5 and identifies the six-cycle predictive structure. After 12 and 18 events, the one-time startup context is absorbed through partial bisimulation and six predictive contexts remain.

This is evidence about the specific stream and declared horizon, not a proof that five quiet observations imply one underlying state.

### Partial ground compilation

After 24 `HOLD`-only joint observations, the learned quotient has six contexts and six known `HOLD` transitions. The twelve `PROBE_A`/`PROBE_B` edges remain unknown. All 24 retained events replay against the known model with zero mismatches. The evidence certificate explicitly says that it is not a proof of unseen transitions.

### Asynchronous delivery

Step 1's two channel values arrive before step 0's values. The learner retains both events, commits neither while step 0 is incomplete, and then commits steps 0 and 1 in order when the gap closes.

### Bounded long stream

A 200-event parity stream with a 64-event retention cap finishes with:

- 200 lifetime committed events;
- 64 retained events;
- 136 retired events;
- two predictive contexts;
- six structural versions (including initialization and first refinements);
- bounded pending/audit/cache state;
- bounded 128-entry version history;
- bounded 64-entry conflict history.

The truncated left boundary is excluded from learning and the original initial context is reported unknown. This avoids treating a moving window boundary as a new recurrent system state.

## Build 24 and Build 25 recovery

Build 26 embeds:
- full Build 24 documentation, source, tests, reports, learned executable specifications, original manifest and original ZIP under `notes/build24_recovery/`;
- an executable Build 24 copy under `legacy/build24/`;
- Build 25 online tracker, runner, tests and the nested Build 24 runtime they require under `legacy/build25/`.

See `BUILD_24_RECOVERY_NOTES.md` for the Build 24 mathematical and experimental summary and exact rerun instructions.

## Evidence boundary and limitations

- The action alphabet and selected channel schema are supplied by the connector.
- Build 26's `observation` and `mealy` modes are explicit interface contracts; incorrect selection changes the learned contexts.
- The learner uses finite suffix histories from one non-resettable stream, not an unrestricted formal equivalence oracle.
- The partial quotient may over-split histories under sparse evidence; it is not guaranteed to be globally minimal.
- Only deterministic exact integer outputs are modeled. Stochastic noise, missing-value likelihoods, continuous latent variables and raw sensor segmentation are not learned.
- A single stream may not exercise each action from each context. Such transitions remain unknown.
- Context collision and horizon refinement do not uniquely distinguish longer memory, measurement corruption, hidden variables or true ground change.
- The safe exploration score for unknown edges is novelty per declared cost/risk, not expected information gain.
- Clock/event identity is maintained by step keys; the separate Build 25 local-clock module is retained, but Build 26 does not independently infer physical cross-clock synchronization from raw timestamps.
- No physical sensor or TAPS data was processed.

## Run

```bash
python run_build26.py
python -m unittest discover -s tests -v
python -m unittest discover -s legacy/build24/tests -v
python -m unittest discover -s legacy/build25/tests -v
```

Python 3.10+, standard library only.
