# Sources and Provenance

## Project source

- `Questions_On_the_Virtual_Ground_SOURCE.md` is the user-provided Virtual Ground questions document preserved from the conversation.
- `legacy/build23_ground_synthesis.py` is copied from Build 23 and included only for a regression test.

## Mathematical and algorithmic background

Build 24 uses an L*-style observation-table method for learning deterministic Mealy behaviour. Relevant background:

- Steffen, B. (2012), *Active Automata Learning: From DFAs to Interface Programs and Beyond*, Proceedings of the International Conference on Formal Methods for Industrial Critical Systems. https://proceedings.mlr.press/v21/steffen12a/steffen12a.pdf
- *Efficient Black-Box Checking with Specification-Guided Abstraction*, ACM Transactions on Embedded Computing Systems. The paper describes Mealy-machine observation tables, closedness, consistency and counterexample refinement. https://doi.org/10.1145/3762659
- Vaandrager, F. et al. (2022), *A New Approach to Active Automata Learning Based on Apartness*, TACAS 2022. https://link.springer.com/chapter/10.1007/978-3-030-99524-9_12

This build does not claim to invent active Mealy-machine learning. Its project-specific contribution is the use of predictive quotient states as latent Virtual Ground contexts, observer-dependent context quotients, active distinguishing policies, and compilation into phase or non-bijective finite grounds.

## Experiment provenance

All hidden generators, traces, models and reports in `reports/` are synthetic and deterministic. No external dataset, live system, TAPS recording, or physical sensor stream was used.
