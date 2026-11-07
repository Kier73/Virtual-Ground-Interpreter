# Research sources — Build 05

These sources support the established methods adapted in this experiment. They do not validate the proposed Virtual Layer architecture itself.

1. **Yang et al. (2018), “Theoretical perspectives on active sensing,” Current Opinion in Behavioral Sciences.** Describes active sensing as a closed loop between an observer that extracts task-relevant information and a planner that selects actions likely to produce informative observations.  
   https://pmc.ncbi.nlm.nih.gov/articles/PMC6116896/

2. **Go & Isaac (2022), “Robust Expected Information Gain for Optimal Bayesian Experimental Design Using Ambiguity Sets,” Proceedings of UAI / PMLR 180.** Discusses sensitivity of expected information gain to prior distributions and proposes robust EIG under prior ambiguity. This build borrows the motivation for conservative selection but currently varies noise scales only; it does not implement their ambiguity-set method.  
   https://proceedings.mlr.press/v180/go22a.html

3. **“Optimal experimental design: Formulations and computations,” Acta Numerica (2024).** Reviews optimal experimental design, discrete measurement selection and sequential design policies.  
   https://www.cambridge.org/core/journals/acta-numerica/article/optimal-experimental-design-formulations-and-computations/38BBD0DC1A0386FDF306B6C0167DF7D9

4. **“Efficient data collection for establishing practical identifiability via active learning” (2025).** Discusses selecting observations where candidate model predictions disagree, weighted by measurement uncertainty.  
   https://spj.science.org/doi/full/10.1016/j.csbj.2025.10.058

5. **Bertola et al. (2023), “Methodology for selecting measurement points that optimize information gain for model updating,” Journal of Civil Structural Health Monitoring.** Demonstrates selecting informative measurements from larger sensor datasets for model updating.  
   https://link.springer.com/article/10.1007/s13349-023-00711-7

## Scope note

Build 05 uses a standard Bayesian design objective and a simple finite Gaussian observation model. The research references are context and methodological grounding, not evidence that its synthetic results generalize to biological observers, human emotion, all codonic algorithms or a universal invariant space.
