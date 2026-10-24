# Project versions and development history

These three stage labels were added retrospectively on 25 October 2026 using
the repository's actual commits and their Australia/Sydney dates. They describe
historical content; no commits or upload dates have been fabricated or backdated.
Earlier merge commits and branch names remain unchanged. In particular, the
historical `co2-detection-v1` branch named the first detection trial; it was not
a repository-wide release tag. The stage labels below make that distinction explicit.

| Stage tag | Recorded development date | Historical reference | Contents |
|---|---|---|---|
| `v1-extraction` | 27-28 September 2026 | [`4abf29d`](https://github.com/hhua0087-alt/mma3001-co2-error_detection/commit/4abf29db935c2c4c25b29db68958d0d61acc8732) | Initial repository, `extract_env.py` and extractor tests; a data-preparation stage, not a completed detection study |
| `v2-colab-detection` | 22 October 2026 | [`9bf29e6`](https://github.com/hhua0087-alt/mma3001-co2-error_detection/commit/9bf29e63a5b50c0d89084efed0ae3147e92da472) | Modular English Colab detection notebook and guide, merged through PR #1 |
| `v3-reproducible-workflow` | 25 October 2026 | The completed workflow update merged after PR #2 | Three local English notebooks, shared modules, raw/full-extract loading, sensitivity analysis, tests, HTML documentation and aggregate references |

## v3: complete the reproducible workflow

PR #2 updated root documentation and environment files on 25 October, but the
main branch still lacked the notebook, module, configuration, documentation and
reference directories described by that README. This update supplies those
verified files and removes the four obsolete root/legacy entry files from the
latest tree. All earlier versions remain accessible through Git history and tags.

The primary run order is now:

1. `notebooks/01_main_experiment.ipynb`: prediction models, calibration and fault detection.
2. `notebooks/02_nn_input_comparison.ipynb`: eight/six-input NN comparison.
3. `notebooks/03_results_analysis.ipynb`: analysis of both completed runs.

The original `5EnvSensor_MayToDec2024_180kRows.csv` and the historical full-channel
extract produce exactly the same 13,800 prepared timestamps and numeric values.
The actual raw file was used to execute all 68 notebook code cells; 43 tests passed,
including integration checks. Thirty default per-reading files, 63 sensitivity
settings and NN weights/calibration matched earlier research. See
[`reports/verification_summary.md`](reports/verification_summary.md).

Raw data, personal `config/local.json`, generated measurements and Python
environments are excluded from the repository. Source notebooks have empty outputs.
The existing inspected period and fixed model seeds remain unchanged; this code
packaging does not create an independent evaluation of real sensor faults.

Future changes should be recorded through actual, descriptive commits. Three stage
tags are navigation aids, not evidence of three independent experimental datasets
or a course requirement to reach a particular commit count.
