# Aggregate reference results

These tables contain event/reading statistics and prediction-error summaries from the completed research, without timestamps or measurement-level CO2, temperature or humidity values. They are references for regression checks, not new independent validation. Labels use method keys; the main README explains those keys.

`main_sensitivity.csv` contains 378 rows (six detectors across 63 cases). `input_sensitivity.csv` retains the main six and appends two six-input rules, giving 504 rows. Counts can be shared across simulated copies of the same record; do not interpret them as independent real faults. Protocol metadata retain data and weight hashes for reproducibility without redistributing the raw source or model weights.
