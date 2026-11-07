# Build 10 — Research references

## System identification and modal analysis

1. Lök, Ş. İ., Pappalardo, C. M., La Regina, R., & Guida, D. (2025). *A Numerical and Experimental Investigation of the Most Fundamental Time-Domain Input–Output System Identification Methods for the Normal Modal Analysis of Flexible Structures*. Sensors, 25(4), 1259. https://doi.org/10.3390/s25041259  
   Comparative treatment of ARX, state-space estimation, N4SID, ERA/OKID, transfer-function estimation, and practical noise issues in damping identification.

2. Adhikari, S. (2004). *Optimal complex modes and an index of damping non-proportionality*. Mechanical Systems and Signal Processing, 18(1), 1–27. https://doi.org/10.1016/S0888-3270(03)00048-7  
   Establishes the need to treat complex modes in systems with non-proportional damping.

3. Yu, M., Hahn, E. J., Liu, J., & Lu, Z. (2016). *A quasi-modal parameter based system identification procedure with non-proportional hysteretic damping*. Journal of Sound and Vibration, 382, 43–62. https://doi.org/10.1016/j.jsv.2016.07.002

## Nonlinear system identification and experiment design

4. Karimshoushtari, M., & Novara, C. (2020). *Design of experiments for nonlinear system identification: A set membership approach*. Automatica. https://doi.org/10.1016/j.automatica.2020.109036  
   Supports the premise that input design determines the information content and achievable accuracy of an identification experiment.

5. *An Approximate Bayesian Approach to Optimal Input Signal Design for System Identification* (2025). Entropy, 27(10), 1041. https://doi.org/10.3390/e27101041  
   Uses mutual information as a Bayesian input-design utility under model uncertainty; Build 10 uses a simpler, explicitly approximate one-coordinate quadrature rather than reproducing the paper's method.

6. Breunung, T., & Balachandran, B. (2025). *Frequency response based identification of nonlinear oscillators*. Journal of Sound and Vibration, 594, 118651. https://doi.org/10.1016/j.jsv.2024.118651

## Candidate empirical data sources for Build 11

7. Brambilla, M., Dertimanis, V., Chatzi, E., Chiariotti, P., & Cigada, A. (2025). *Experimental Campaign for Dynamic Characterization of a Laboratory-Scale Structure* [Dataset]. Zenodo. https://doi.org/10.5281/zenodo.15516419  
   The record describes impact-hammer modal measurements and 6-DOF shaker tests with documented sensor configurations. Review the accompanying data guide and licence/terms before using or redistributing files.

8. Théâtre Acoustique. *Room Impulse Response Library — Download*. https://www.lieuxperdus.com/convolver/download/  
   The page states a CC BY-NC 4.0 licence for its room impulse responses (48 kHz / 24-bit stereo).

9. Bhattu, A., Hermann, S., Jamia, N., Müller, F., Scheel, M., Schwingshackl, C., Özgüven, H. N., & Krack, M. (2024). *TRChallenge — experimental results 2022* [Dataset]. DaRUS. https://doi.org/10.18419/DARUS-4484  
   The dataset page states CC BY 4.0 and describes linear modal and multiple nonlinear test types. The configuration archives are large; use a small selected subset if this becomes part of Build 11.

## Interpretation note

The literature informs the modelling choices and experimental design. It does not validate the synthetic Build 10 numerical results. Those results are established only by the generated code, parameters, tests, and accompanying data in this package.
