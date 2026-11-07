# Next research direction — Build 22

## Ground inference from partial observation

Build 21 specifies a ground and tests navigation under several observers. The next challenge is inverse: can an observer recover a useful ground from observed transitions without confusing environmental variation, hidden state, noise and actual rule change?

Proposed experiments:

1. Generate trajectories from two nearby ground versions with different inflow laws or action preconditions.
2. Give observers only selected sensor projections and partial action logs.
3. Compare passive observation with active probe sequences that deliberately distinguish candidate grounds.
4. Compute the set of candidate grounds still consistent with evidence.
5. Identify when a parameter estimate is sufficient and when the state/action topology itself differs.
6. Test ground-version change detection under missing events and measurement noise.
7. Produce a migration map only when the candidate ground is sufficiently identified.

Key conjecture: a useful Virtual Ground can be refined from observations by selecting probes that maximize information about transformation rules per resource cost, while retaining uncertainty over indistinguishable grounds.

## Important distinction

A finite set of observed transitions rarely proves a unique unrestricted generative law. The compiler should report an equivalence class of candidate grounds relative to the probe family, not silently choose one as uniquely true.
