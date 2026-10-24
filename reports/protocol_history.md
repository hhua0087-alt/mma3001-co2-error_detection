# Calibration amendment and evidence boundaries

The six-input trial originally used the same CUSUM decision-limit grid as the
eight-input NN: 0.5 to 40.5 training residual standard deviations in 0.25-SD steps.
The six-input model could not meet the unmodified-validation budget of at most
25 alarms. That initial execution stopped at calibration.

Before injecting or scoring test faults, the common calibration algorithm was
amended to extend the same grid in quarter-SD steps until feasible, using only
unmodified validation alert counts. The allowance remained 0.1 training SD. No
additional NN architecture, training seed or allowance search was introduced.

At the time of amendment, unmodified test prediction errors had already been
computed, and the test period had been inspected in earlier work. The amendment
therefore does not create an independent unseen test set. The study remains
exploratory. In the reference result, eight inputs select h=127.806 (11 SD) with
24 validation alarms; six inputs require h=1540.680 (62.25 SD) with 25 alarms.

The initial executed failure copy is retained privately with the research records
because it contains course measurements. This repository retains the textual
amendment, the common algorithm and numeric aggregate reference. CUSUM limits are
cumulative-statistic limits, not point CO2 thresholds.

## Raw input support, 25 October 2026

The input adapter now accepts the original course CSV directly as well as a
full-channel long-format extract. This changes input handling and provenance,
without changing features, eligibility, training, calibration, injection or scoring.
The actual raw file's prepared timestamps and float64 values were compared exactly
with the historical full extract. Both have the same prepared-data fingerprint.
The original file SHA-256 remains recorded separately from that fingerprint.
The supplied CO2-only extract is explicitly rejected because temperature and
humidity are required. No covariates or measurements are synthesized.

This is a reproducibility check using another representation of the same record;
it is not a new period, independent test or newly validated fault dataset.
