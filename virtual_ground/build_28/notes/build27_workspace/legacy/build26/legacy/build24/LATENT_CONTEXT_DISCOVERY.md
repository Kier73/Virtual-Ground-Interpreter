# Latent Context Discovery

## Hidden process model

The synthetic teacher has an internal finite context `z`, an input action `a`, and an emitted observation `y`:

\[
z_{t+1}=\delta(z_t,a_t), \qquad y_t=\lambda(z_t,a_t)
\]

The learner sees only the action/output history. It receives neither `z`, its cardinality, nor a candidate state list.

This is a deterministic Mealy-style process. The observable predictive state after history `h` is defined by all possible future output responses:

\[
h_1\equiv h_2 \iff \forall w\in A^*,\quad Y(h_1w)_{>|h_1|}=Y(h_2w)_{>|h_2|}
\]

When histories are equivalent, no experiment from the supplied action alphabet can distinguish their future behaviour. They should be merged for this observer.

## Test fixtures and outcomes

| Fixture | Hidden generator | Learned predictive contexts |
|---|---|---:|
| Coupled six / parity only | Six modes; parity output | 2 |
| Coupled six / mod-3 only | Six modes; mod-3 output | 3 |
| Coupled six / joint | Six modes; both outputs | 6 |
| Delayed six | Only one mode/action emits a rare signal | 6 after counterexample refinement |
| Aliased six | Six modes with mod-3-equivalent behaviour | 3 |
| Unobservable eight | Eight modes; constant output | 1 |
| Partial four | Four modes with non-bijective transition | 4 |

## Delayed distinction

For the delayed-six teacher, every action advances the hidden mode by one. Only `PROBE_A` at mode 5 emits `1`. With a conformance horizon of five actions, a one-state machine passes every tested sequence. At horizon six, the sequence `HOLD^5 PROBE_A` reveals the delayed response and becomes a counterexample. The table adds the suffix and learns six predictive states.

A finite validation horizon is therefore a declared evidence bound, not a proof that no longer distinguishing sequence exists.

## Observer quotient

For the six-mode modular fixture, action transitions are strides 1, 2 and 3 modulo six. Sensor A returns `z mod 2`; sensor B returns `z mod 3`.

- Sensor A's observable context is `z mod 2`.
- Sensor B's observable context is `z mod 3`.
- The paired residues identify `z mod 6` because 2 and 3 are coprime.

For the aliased-six fixture, the available output is only `z mod 3` and the transitions respect this quotient. The learner returns three states, not six.

For the unobservable-eight fixture, all outputs are constant and the future response is independent of the hidden mode. The learned machine has one predictive state.

## Non-group dynamics

The partial-four fixture includes a non-bijective `HOLD` transition. The resulting machine cannot be represented as a single modular phase progression. The compiler retains a finite predictive automaton.

This is why the Virtual Ground formalism should allow groups, monoids, semigroups and general transition systems as appropriate. Invertibility must be established, not presumed.
