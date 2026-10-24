# Implementation verification summary

The original clean-package verification on 25 October 2026 used the authorized
full-channel extract in a relocated directory with no saved runs. After adding
raw-input support, a separate fresh source copy ran the complete experiment chain
using the actual original `5EnvSensor_MayToDec2024_180kRows.csv` directly through
ignored `config/local.json`, with no CO2_DATA_CSV override. Both checks used the
existing Python 3.13.17 environment and fresh real Jupyter kernels per notebook.

| Check after raw-input update | Observed result |
|---|---|
| Original CSV streaming | 179,447 source rows; 29,341 selected sensor rows; zero invalid JSON rows for this sensor |
| Prepared input equality | All 13,800 ordered timestamps and float64 values exactly equal to the historical full extract |
| Duplicates and eligibility | 46,623 identical channel duplicates removed; split 7,373 / 2,458 / 2,458, with 1,511 excluded |
| Main experiment | All 26 code cells executed from raw data |
| NN input comparison | All 21 code cells executed from raw data |
| Results analysis | All 21 code cells executed; no model training |
| Automated tests | 43 passed, 0 skipped, 0 failed in the completed-run environment |
| Default replay comparison | All 30 per-reading detector output files matched earlier research |
| Sensitivity metrics | All 378 main and 504 combined setting rows matched aggregate references |
| Sensitivity event outcomes | All 3,672 main and 2,448 controlled per-event rows matched earlier research |
| Model/control comparison | Exact eight/six-input NN weight hashes and calibrated parameters matched |
| Input preservation | The actual raw CSV, supplied CO2-only CSV and historical full extract retained their original hashes |
| Research preservation | 113 durable original research files retained recorded hashes |
| Source packaging | Three English, output-free notebooks; portable source; ignored local configuration; no bundled measurements |
| HTML documentation | Shared API and notebook orchestration functions documented in 12 local pages |

Nine additional manufactured-data tests cover raw/full-extract equality, distinct
source digests with identical prepared fingerprints, source preservation, malformed
JSON counts, missing-channel errors, fingerprint changes and path precedence.
The supplied CO2-only extract is rejected with an explanation that humidity and
temperature are missing. The models are not changed to accommodate missing inputs.

One pandas timestamp-format warning occurs in the deliberately invalid-timestamp
negative test; the intended ValueError is raised. The HTML/JSON test reports record
actual pytest output and hashes of public computation source (excluding local.json).
Full logs, executed notebooks and measurement-level comparisons remain private.

These are implementation and regression checks in the same installed environment
using two representations of the same record. They do not constitute a new test
period, another sensor, repeated NN training seeds, verified health labels, a fresh
dependency installation on another operating system, or validation of real faults.
Human authorship and learning claims must be completed by the student using actual
personal actions. The previous research report's numerical findings are unchanged.

## Fresh GitHub clone replay, 25 October 2026

The uploaded main commit `a690ee10cdc8528bb0d2bdad53d39eeae66814c3` was cloned
into a new directory without saved runs, data or local configuration. Using the
authorized original CSV and the existing Python environment, all 26 / 21 / 21
notebook code cells executed in fresh real kernels and 43 tests passed without skips.
The original CSV and all 61 downloaded tracked files retained their hashes after
new test reports were saved separately. The downloaded clone was otherwise clean.

Review found two outdated teaching descriptions in notebook 01: the shared NN is
trained in code cell 10, and the final comparison contains six detectors. Those
markdown descriptions have been corrected without changing any executable cell.
The clarified notebooks were then replayed in full, and all 43 tests passed again.
All 30 default per-reading files and sensitivity event outcomes matched the first
GitHub replay. Updated test reports correspond to the clarified notebook source.

This verifies a fresh clone with no saved experiment state; it does not claim a
new dependency installation, another operating system or independent fault data.
Raw data and measurement-level execution evidence remain local.
