# Perspective: what it is like to organize a research program that keeps disproving itself

*This essay was written for the original 15-build archive. An addendum at the end covers Builds 16–30 after the later packages were unpacked.*

I spent this project unpacking the first fifteen self-contained builds of the "VL Response Geometry" program, running every test, checking every manifest, reproducing the reported numbers, and then taking the empirical branch further than the archives do. The experience was less like reading a finished thesis than like excavating a sediment core. Each build preserves the assumptions of the moment it was written. Read in order, the same functions reappear with small changes, and you can watch a research question sharpen, overreach, recover, and finally meet a real measurement — twice.

My overall view is that this is a better research program than its most exciting numbers suggest, and a less conclusive one than its language sometimes implies. Its real achievement is methodological: it repeatedly built the control that could kill its own favorite result, and then reported the killing. The most valuable files in the archive are not the near-perfect correlations. They are the weaker ones that survived, and the null results that did not.

## 1. The shape of the archive

The first six builds form a mathematical overture. Build 01 separates algebraic identity, observer response and geometric representation, then maps four response coefficients onto S³. Build 02 distinguishes shape from movement, showing that geometric phase survives monotone reparameterization while temporal signatures do not. Build 03 composes shears into holonomy-like transport and shows path dependence. Build 04 lifts the construction to the Hopf fibration and checks fibre phase under reversal, representative shifts and sampling refinement. Builds 05 and 06 add active observation: probes chosen for an intention, observer-specific quotients, antipodal controls.

These builds are elegant, and they are internally honest. Their documents say, more or less explicitly, that they demonstrate mechanisms rather than discover facts about the world. But there is a seduction in this kind of mathematics. Once you have a Hopf fibration, a holonomy, and an observer-dependent quotient, it is easy to feel that a deep invariant must be nearby. The notation does some of the persuading. A correlation between two observer views starts to look like a property of observer geometry itself, rather than a property of the paths and features that happened to be chosen.

That is the attractive mistake the program spends the next eight builds correcting.

Organizing the archive meant resisting the temptation to fix the past. The original ZIPs are preserved with checksums, each build remains self-contained, and the Build 12 correction lives beside the frozen build rather than inside it. A research record is more useful when you can see exactly what was believed at each step, including the step that was wrong.

## 2. The first discovery, and the first cold shower

Build 07 is the first moment that feels like a discovery. Across a designed library of codonic paths, the base-shape observer and the local-transition observer produce strongly aligned response-distance matrices: Spearman ρ = 0.693, empirical p = 0.011, Holm-adjusted p = 0.022. Nearest-neighbour overlap and block-aware permutations support the same story. After six builds of machinery, here is a number that looks like a law.

Build 08 is the necessary cold shower. It replaces the designed path library with forty independently randomized spherical path families, adds noise and feature-dropout sweeps, and repeats the comparison. The shape ↔ local-transition correlation falls to ρ = 0.272, with a bootstrap interval of 0.208–0.464 and a 5-NN Jaccard of 0.143. Shape ↔ temporal is 0.095 and not significant. The Build 07 result was not nothing, but it was substantially a property of the original path family and feature choices.

I find this sequence more impressive than the original result. It would have been easy to present 0.693 as the headline and put the randomized study in an appendix. Instead the later build foregrounds the weakening and explicitly says the earlier pairing “may have depended substantially on the original designed path families and feature choices.” That is what a functioning research program looks like.

The same pattern repeats, more sharply, in Builds 09 and 10. Build 09 constructs an acoustic-like resonator and a mechanical oscillator and reports cross-modal RDM correlations of 0.9999999 for spectral, phase and temporal views. The number is almost too perfect, and the build says why: both systems were deliberately parameterized with the same second-order pole structure. It is a positive control for the measurement pipeline, not evidence of a universal acoustic/mechanical geometry.

Build 10 then does the obvious but difficult thing. It generates thirty-two independently parameterized systems per domain, across four structural classes, with different orders, coupling, damping, anti-resonances and nonlinearities. There is no justified one-to-one pairing between an acoustic system and a mechanical system, so it does not compute a paired RDM correlation. Instead it compares distributional geometry against a column-shuffled null that preserves feature marginals. The observed MST-edge Wasserstein gap is 0.0719; the null mean is 0.0533. There is no evidence of shared cross-domain geometry beyond the control.

The 0.9999999 did not generalize. The build says so plainly: the near-perfect alignment was strongly dependent on matched dynamics, and the earlier positive control should not be promoted into a general invariant claim. This is the intellectual center of the whole archive for me. A program that can produce a 0.9999999 and then explain why it should not be believed has learned something that no single correlation can teach.

## 3. The real world bites

Build 11 is the first empirical step: 411 rows in eight source-contiguous windows from a real smartphone G-Force recording. The reported pre/event/post contrasts are descriptive and plausible. Median-centred vector RMS is roughly 0.50–0.52 g in the strict pre-interval windows, 0.61–0.90 g in the windows inside the annotated interval, and 1.51–1.74 g in the selected post windows. The time-derivative RMS rises from about 10.9–12.4 g/s to 18.1–36.0 g/s to 54.4–61.6 g/s.

These numbers are interesting, but the build is careful: eight windows from one recording, no population claim, no cross-modal comparison, no emotion inference. That restraint is correct. The step from “a sensor recorded something while a person moved” to “the geometry of emotional tone” is enormous, and Build 11 does not take it.

Build 12 is where the real world bites hardest. The Rochester room-impulse-response corpus is exactly the kind of data the program needed: 90 WAV files across 15 room folders, documented sample rate and bit depth, a real acoustic environment, and a license that permits analysis. The pipeline ingests the WAVs with no third-party libraries, extracts decay, early/late, spectral, temporal and level views, aggregates by room median, and builds within-acoustic-domain RDMs.

Then the first run produces EDT values of 19–44 seconds and C50 values around −40 to −53 dB. Those numbers are not merely imprecise; they are physically absurd. A room with a 20-second EDT is not a room, it is a cave the size of a stadium. The unit tests all pass. The manifests are intact. The code is doing exactly what it was written to do.

The bug is a convention mismatch. Build 12 defines onset as the first sample whose absolute value reaches 0.001 times the peak. That is a reasonable rule for a signal that begins at the impulse. The Rochester files do not. Every one of the 90 recordings contains a 1.000 s pre-roll of low-level noise before the direct sound. The noise crosses the −60 dB threshold almost immediately, so the detector fires at a median of 968.8 ms before the actual peak. The Schroeder integral then spends its first second integrating noise. The 50 ms and 80 ms “early” windows land in the pre-roll. C50, C80, D50 and Ts are all measured from the wrong origin.

This is the most instructive failure in the archive. The synthetic tests could not catch it, because synthetic fixtures begin at the impulse. The manifests could not catch it, because the files were exactly the files that were shipped. Only running the pipeline on real data and asking whether the output made physical sense could catch it. A test suite validates implementation; it does not validate measurement semantics. The gap between those two things is where most empirical errors live.

## 4. What the corrected rooms actually say

I did not patch the frozen build. I wrote a separate reanalysis that trims each channel at its direct-sound peak and reruns the unmodified Build 12 feature functions. The correction is documented in `theory_development/empirical_results/build_12/corrected/FINDINGS.md`, with the script, per-file features, room medians, RDMs and a side-by-side comparison.

The first thing the correction reveals is a diagnostic dissociation. T20 barely moves: shipped and corrected room medians have Pearson 0.99996 and Spearman 1.0. That makes sense, because the −5 to −25 dB fit range lands on the real decay even when the origin is wrong. EDT, which fits 0 to −10 dB, absorbs the pre-roll plateau and is destroyed. The shipped EDT ordering is actually negatively correlated with the corrected ordering (Spearman −0.89), because rooms with more pre-roll noise accumulated longer spurious EDTs. A stable T20 next to an impossible EDT is a fingerprint of an origin error, not a bad decay estimator.

After correction, the room values are ordinary: EDT 0.23–3.10 s, T20 0.28–3.16 s, C50 −2.8 to +13.7 dB, D50 0.34–0.96. The small rooms (Room2a/b, Room3) sit near 0.23–0.28 s EDT; the large/reverberant rooms (Room11–14) sit at 1.1–3.1 s. That ordering is physically sensible, and it is the first time in the program that a real dataset produces a result I would be comfortable defending in a room-acoustics context.

The second thing the correction reveals is a coherent view geometry. In the shipped run, decay ↔ early/late is 0.099, which is implausible for two descriptions of the same decay process. After correction it is 0.631. Decay ↔ temporal rises from 0.338 to 0.666, and early/late ↔ temporal is 0.737. Spectral shape stays comparatively independent (0.08–0.28), and absolute level stays weakly related (0.08–0.32). The corrected pattern is exactly what one hopes for: a block of views that all describe the same physical decay, and separate views for spectral shape and acquisition gain.

This is the strongest empirical result in the archive, but it is also a narrow one. It is within one corpus, with 15 rooms and 90 files, using compact second-order filters rather than a certified ISO 3382 implementation. It says that the measurement pipeline can recover a physically coherent room geometry once the origin is right. It does not say that this geometry is universal, cross-modal, or emotionally meaningful.

## 5. The frontier: paired sensors and local clocks

Builds 13 and 14 make the right conceptual move. Instead of comparing unrelated datasets, they use TAPS: the same Korean utterance recorded simultaneously by an accelerometer-based throat microphone and an acoustic microphone. That is a genuine paired-sensor design. The throat channel measures tissue-conducted vibration; the acoustic channel measures airborne pressure. The question is whether the two channels preserve similar within-speaker utterance neighborhoods under a common-band feature view.

The design is careful in the ways that matter. It restricts the cross-modal view to 80–3500 Hz, below the throat sensor's original 4 kHz Nyquist limit. It keeps the acoustic-only 4–7.8 kHz band separate rather than pretending the throat channel can supply it. It reports residual alignment diagnostics without re-aligning the released data. It groups by speaker, shuffles pairings within speaker, and bootstraps over speakers rather than utterances. It does not export transcripts or raw speaker IDs. And it explicitly refuses emotion inference.

Build 14 adds a temporal-emission layer: event landmarks from a 20 ms RMS envelope, normalized interval shape separated from absolute rate, normalization-sensitivity and leave-one-feature-out diagnostics. The mathematical claims are modest and correct: normalized interval shape is invariant to origin and uniform clock scale, while absolute rate and dwell time are not. The event detector is presented as a transparent baseline, not a learned segmenter.

Then I ran the held-out test split: 1,000 pairs, ten speakers, 100 utterances each, zero skips. The files are already globally aligned, with a median residual envelope lag of 0 ms and a median envelope correlation of 0.728, so the run is not secretly re-aligning the data. The RDM results are the first positive paired-sensor result in the program:

| View | Median RDM Spearman | Speaker bootstrap 95% CI | Shuffled-pair null |
|---|---:|---:|---:|
| periodicity | **0.488** | 0.450–0.517 | ≈ 0 |
| combined common | **0.359** | 0.347–0.428 | ≈ 0 |
| temporal | **0.293** | 0.198–0.373 | ≈ 0 |
| shared spectral | **0.233** | 0.153–0.327 | ≈ 0 |
| temporal rate | **0.189** | 0.124–0.303 | ≈ 0 |
| temporal emission | **0.120** | 0.085–0.174 | ≈ 0 |

All six views beat their within-speaker shuffled-pair nulls at p = 0.01 with 99 permutations. The result is stable across robust, z-score and rank normalization, and no single feature drives the temporal-emission view. The ordering is physically sensible. Periodicity is strongest because both sensors are recording the same voicing process; shared spectral shape is weaker because the transfer functions differ; normalized event shape is weakest because it discards the most information.

Build 15 asks a harder question: can the two event streams be aligned without using the shared timestamps, and can an affine clock relation be recovered after matching? On synthetic data the monotone matcher looks strong — precision 0.917, recall 0.948, F1 0.932 — but the synthetic marks are informative and near-linearly related. On TAPS the frozen matcher aligns a median of 34 events per pair, with throat/acoustic coverage of 0.912/0.860. Its reported matched-interval correlation is only 0.122, and the post-match clock residual is 0.183 s, despite the files already sharing a time base.

The external controls explain why. The frozen combined objective weights mark rank 0.78 and interval shape 0.22. Against a within-speaker mismatched-pair null, that combined matcher produces an interval correlation of 0.107, versus 0.085–0.094 for mismatched utterances. Shuffling the marks within each stream gives 0.101, and shuffling the interval order gives 0.064. The mark weight is doing most of the work, and the reported mark-rank correlation of 0.705 is circular: the matcher selects pairs by mark rank, and the shuffled-mark control still yields 0.709. When I match on interval shape alone, the correlation rises to **0.439**, far above the 0.085–0.094 mismatch null. But shuffling the gap order within the same utterance's streams leaves 0.356, so the matcher can manufacture a substantial interval correlation from similar marginals; the order-specific increment is about 0.083. The interval signal is real and utterance-specific, but smaller and less decisive than the raw 0.439 suggests. The frozen matcher buries it.

The clock result does not survive. Interval-only matching reduces the median residual from 0.183 s to 0.117 s, but that is still far too large for genuine landmark correspondence in a globally aligned corpus. A detector sweep moves the frozen interval correlation between 0.055 and 0.158 and leaves the residual at 0.17–0.21 s. The affine fit is a diagnostic of how well the inferred matches happen to lie on a line, not evidence that the clocks were synchronized.

This is the program's central pattern one more time, but with a twist. Build 15's synthetic validation encoded an assumption — informative mark ranks — that the real domain does not satisfy. The correct conclusion is not that the local-clock idea is false in every respect. The interval-shape part survives a stronger null than the build itself used. The event-identity and clock-recovery parts do not. The RDM result from Builds 13/14 is the robust empirical finding; the event-level matcher is a promising method that needs reweighting and a labelled correspondence corpus before it can claim more.

The build's own falsification criteria remain the right ones: exceed within-speaker shuffled controls, stay stable across normalization, avoid single-feature dominance, respond predictably to clock and detector changes, and replicate in a second paired-sensor domain. TAPS passes the RDM criteria and fails the event-level ones. It is one corpus, ten speakers and one held-out split, and TAPS is preprocessed and globally aligned, so even the positive result is not a universal invariant.

## 6. Reproducibility is not validity

The program is unusually reproducible for a research archive. All fifteen builds of this first arc are standard-library-only, self-contained, and tested. All 319 tests pass on Python 3.14. The nine builds that ship manifests have 225 matching hashes, with no mismatches or missing files. The original ZIPs are preserved and checksummed. The test logs capture the exact commands and outcomes.

But the project also shows the limits of reproducibility. Build 08's `local_clean__temporal_clean` correlation shifts from 0.4635 to 0.5280 between the author's Python 3.13 and my Python 3.14, because a turning-angle calculation in `local_signature` is numerically unstable. Builds 13–15 salt pair ordering with `secrets.token_bytes(32)`, so shuffled-null and bootstrap decimals change between runs even with fixed seeds. Build 15's cyclic mismatch controls inherit that ordering, so the exact null sample changes between runs; the null band is stable, the last digits are not. Build 12's tests pass while the empirical output is invalid. A manifest proves that the bytes are the bytes; it does not prove that the measurement means what the label says.

The right response is not to demand bit-identical outputs everywhere. It is to separate the claims that should be stable from the decimals that should not. Structural conclusions, sign and ordering should be stable; last digits across Python versions should not be treated as findings. The archive would be stronger if every build stated which of its numbers are expected to be invariant and which are environment-dependent. Build 08 and Build 12 already provide the cautionary examples.

## 7. What I would keep, and what I would change

**Keep:**

- The frozen-build convention. Each iteration is a record of what was believed and measured at that point; refactoring across builds would erase the history that makes the program legible.
- The negative results. Build 08's 0.272 and Build 10's null are more valuable than the numbers they replaced.
- The separation of views. Decay, early/late, spectral, temporal and level are genuinely different descriptions, and keeping them separate prevented the program from collapsing into a single "signature" score.
- The explicit pairing and privacy rules in Builds 13/14. They are the right foundation for any future cross-modal claim.
- The TAPS RDM result. It is modest, local and positive, and it survived the shuffled-pair null, three normalization modes and leave-one-feature-out inspection. It is the program's best cross-sensor evidence.
- The refusal to infer emotion. The program studies response geometry, not emotional semantics, and it says so repeatedly.

**Change:**

- Replace threshold-onset detection with an envelope/noise-floor detector, and add a regression fixture with a long noise pre-roll. Build 12's bug should become a permanent test, not a footnote.
- Treat Build 10's negative result as the default prior. Any future cross-domain claim should have to beat a shuffled null and a heterogeneous-system control, not just a matched positive control.
- Pre-register the feature views and the falsification criteria before running a new corpus. The builds list them; the next step is to freeze them before seeing the result.
- Run at least one second paired-sensor corpus, ideally the PMA plate/microphone data, before using the word "invariant" without a qualifier.
- Replace "tone" with "response signature" unless an emotional label is actually measured. The word "tone" carries semantics the data do not.
- Separate circular from independent metrics in event-matching reports. Coverage, match cost and matched mark-rank correlation are partly consequences of the matcher; interval agreement and clock residual are the metrics that can fail. Build 15's report mixed them without that warning.
- Weight event marks by their empirically demonstrated informativeness, not by what made the synthetic stress test look good. The 0.78 mark weight is the specific reason the frozen TAPS matcher missed the interval signal.

## 8. Closing

What I will remember from this project is not the Hopf fibration or the 0.9999999. It is the moment the Rochester numbers came out at 20 seconds of reverberation, and the recognition that every test had passed. That moment is the whole argument for empirical work. A research program can be internally consistent, beautifully documented, fully tested, and still be measuring the wrong interval.

The VL Response Geometry archive is at its best when it behaves like an instrument rather than a theory. It builds a measurement, checks it against a null, watches the beautiful number weaken, and writes down why. The corrected Build 12 result — a coherent decay/early-late/temporal block in real rooms, with spectral shape and level separate — is modest, local, and far more convincing than any universal claim the earlier builds could have made. The TAPS result is the second empirical leg: a clear positive RDM geometry, strongest for periodicity and weaker for normalized event shape, alongside an event-level matcher whose synthetic assumptions did not survive the real domain. That split is more informative than a single headline. It says the shared cross-sensor geometry is real at the distributional level, while the local-clock story is not yet validated at the event level.

I came away thinking that the program's deepest subject is not a hidden geometry of tone. It is the observer-dependence of measurement itself: what changes when the observer changes, what survives when the paths are randomized, what disappears when the systems are heterogeneous, what remains when the origin is finally placed correctly, and what a matcher finds when its synthetic assumptions are removed. On that question, the archive has something real to say. It says that most of what looked invariant was an artifact of the observer's choices — and that the way to find out is to keep building the control that could prove you wrong. The TAPS RDM result survives that test. The TAPS clock claim does not, yet.

## Addendum (2026-11-06): the second arc

Unpacking the 13 later ZIPs changes the shape of the archive rather than merely extending it. Builds 16–19 continue the representation-geometry line: matcher falsification, temporal representations under clock symmetries, SU(2)/S³ harmonics, and the endpoint/path/observer equivalence audit. Builds 20–30 then pivot to a different program. The pivot is explicit in the source package: Build 20 begins from a document called “Questions On the Virtual Ground” and asks what generative operational logic underlies a state space, an observer and an intention. These builds are not empirical acoustics. They are a synthetic methods program about interpretation.

The second arc repeats the first arc's best habit in a different medium: it keeps building the control that could kill its own favorite result. Build 16 demotes Build 15's combined event matcher by showing that mark-only matching is as good or better on its benchmark. Build 19 discovers that endpoint harmonics are informationally redundant once the start and first path-signature level are known. Build 22's out-of-family holdout defeats its own closed-family identification. Build 24's one-context model passes depth five and fails at depth six. Build 27 reports a deliberate held-out failure instead of repairing the law silently. Build 28's shuffled control reduces 42 raw motif candidates to zero. Build 29 shows harmonic segmentation collapsing on amplitude-coded events. Build 30 admits that its selected observer is only a near-optimal member of a set. Read in sequence, this is the same intellectual pattern as Builds 08 and 10, transferred from measurement to interpretation.

The technical spine is coherent. Build 20 defines a Virtual Ground as generative operational logic. Build 21 separates controlled, endogenous and exogenous variables and adds viability and versioning. Build 22 discovers a ground by intervention. Build 23 synthesizes executable ground programs within a declared grammar. Build 24 infers latent predictive contexts from action/output traces. Build 25 tracks an unknown context online, with asynchronous channels and local clocks. Build 26 keeps the ground partial and refuses to invent unknown edges. Build 27 keeps multiple explanations alive and discovers opaque operations. Builds 28–30 then move down the stack: from supplied boundaries to inferred motif boundaries, from tokens to raw continuous signals, and finally to signal-coded instructions whose group law performs the arithmetic. The most integrated work is Builds 24–26; the most speculative is Build 30.

What the second arc does not do is equally important. It processes no physical sensor data. It does not prove general program synthesis, a universal observer, or that the inferred ground is the true hidden system. Its perfect synthetic scores are implementation checks on controlled fixtures. The missing standalone Builds 16 and 24 are part of the record too: Build 16 survives inside Build 17, and Build 24 survives inside Builds 25 and 26. The archive's self-containment is real, but it is the self-containment of a sediment core, not of a clean dependency graph.

The two arcs now answer different questions. Builds 01–15 ask what survives real measurement, and answer: a corrected room-acoustic geometry and a modest paired-sensor RDM signal, not a universal invariant. Builds 16–30 ask what an interpreter can infer from controlled streams, and answer: a bounded pipeline that keeps its unknowns visible, not a general self-constructing ground. The same lesson holds in both. The control, not the headline, is the result.
