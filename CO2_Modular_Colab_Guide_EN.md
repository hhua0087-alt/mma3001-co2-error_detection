**This version has 25 code cells, ten detectors and six distinct prediction curves. Chinese and English versions use the same computations.**

- [English notebook](MMA3001_CO2_Modular_Experiment_EN.ipynb)
- [Chinese notebook](MMA3001_CO2_Modular_Experiment.ipynb)
- [Chinese guide](CO2_Modular_Colab_Guide_zh.md)

Upload the updated notebook to Colab and run from the top. Comparison, prediction metrics, plotting and export are now cells 22-25. Replacing the old plot cell alone cannot construct the new methods.

**Start**

1. In Colab, select File -> Upload notebook and upload either .ipynb.
2. A normal CPU runtime is sufficient; the NN is small.
3. Run numbered code cells from 1 downward. Markdown explanations do not count toward code numbers.
4. At cell 3, upload only `env_6012002000869_all.csv`; no extra Python files are required.

The long-format CSV needs sensor_id, timestamp_utc, variable and value, with Carbon dioxide, Temperature and Humidity. Independent references include Pressure by default. Set `ADD_PRESSURE_TO_REFERENCE=False` if pressure is absent or incomplete. The loader does not silently change the common cohort for pressure.

**Cell map**

| Cell | Purpose |
|---|---|
| 1-5 | Dependencies, settings, upload, preparation and time split; no training |
| 6 | Continuous separated event windows |
| 7 | Spike copy |
| 8 | Drift copy |
| 9 | Bias copy |
| 10 | OLS and threshold helpers |
| 11 | Adjacent change rule |
| 12 | Fit history CO2 regression |
| 13 | Fit a small history CO2 NN |
| 14 | Fit independent environmental regression |
| 15 | History regression residual EWMA |
| 16 | Independent reference residual EWMA |
| 17 | Fit history CO2 decision tree |
| 18 | Fit independent environmental decision tree |
| 19 | CUSUM recurrence, reset and calibration helpers |
| 20 | History regression residual CUSUM |
| 21 | History NN residual CUSUM and full threshold table |
| 22 | Compare ten detectors across three fault types |
| 23 | MAE/RMSE for six distinct predictors |
| 24 | Three local fault panels and all prediction curves |
| 25 | Download private results |

**Training and fault copies**

Default splits contain 7,373 training, 2,458 validation and 2,458 test records. Predictors fit only original training X/y; thresholds use original validation. Faults enter test copies only. The source CSV is untouched. There is no pretrained model: training occurs when training cells execute.

History regression, NN and history tree rebuild lagged inputs from observed, possibly faulty CO2. Independent regression and independent tree share the same environmental/time inputs, including optional pressure, and exclude target CO2 history.

Trees have maximum depth 5 and minimum leaf size 50 by default. They are CO2 regressors, not fault-label classifiers. Settings are fixed before fault evaluation.

CUSUM reuses existing predictions. Center residuals on their training mean, accumulate positive and negative evidence separately, and alarm when the maximum exceeds h. Default k is 0.1 times training residual SD. Choose the smallest h candidate meeting a validation budget of ceil(1%*2458)=25 alerts. This budget is comparable to the original validation quantile approach; test alert rates need not match.

Reset CUSUM on alarms or gaps over 20 minutes, never on fault labels. Validation state continues into test. h is a cumulative-statistic threshold, not directly comparable with a single-reading residual threshold.

**Read results**

`detected` counts events with at least one alarm during injection, not complete detection of all faulty readings. `paired_additional_events` compares alarms with the unmodified copy at matching timestamps. `reading_recall` counts flagged injected readings.

`unmodified_test_alert_rate` describes background alerts, not verified false positives: original health is unknown. `recovery_alert_rate` covers 30 post-event readings. Delay statistics use detected events only; missed events do not become zero-delay detections.

Prediction accuracy and detection recall answer different questions. A predictor can follow corrupted observations and leave small residuals while missing drift. Use cells 22-23 for overall comparison; local examples are explanatory.

**Plot controls in cell 24**

```python
PLOT_SCENARIOS = ["spike", "drift", "bias"]
PLOT_EVENT_IDS = {"spike": 1, "drift": 1, "bias": 1}
ALARM_METHOD = "history_neural_cusum"
POINTS_BEFORE = 6
POINTS_AFTER = 6
SHOW_ALARM_TABLE = True
```

One event per fault type gives 13, 36 and 36 readings by default. Panels share colors, CO2 limits and a legend. Time is relative to each event start at minute zero, with separate panel ranges. Constant bias means observed-minus-original is constant, not that observed is flat.

Colors: black original, gray observed, brown previous reading, blue history regression, purple NN, green independent regression, cyan history tree, olive independent tree. EWMA/CUSUM reuse predictions, giving six distinct curves for ten detectors.

Alarm keys:

```text
change_rule
history_regression
history_neural
independent_regression
history_regression_ewma
independent_regression_ewma
history_tree
independent_tree
history_regression_cusum
history_neural_cusum
```

Rerun only cell 24 to change views or alarms; changing fault/model settings requires rerunning from cell 2 downward. Render desired plots before cell 25 to include them in the private archive.

CUSUM targets sustained deviations and can miss isolated spikes. The default NN-CUSUM spike panel may have no red cross. Set `ALARM_METHOD="history_neural"` to see original NN alarms.

**Verification and limitations**

Both 25-cell versions were executed locally, with one NN fit and two tree fits per version. NN weights, point predictions, thresholds, alarms and numerical metrics match. Existing local libraries replaced installation, and Colab file UI was stubbed. Actual Colab cloud execution is not claimed.

Default simulated drift: history tree 5/8, original NN 3/8, regression CUSUM 5/8, NN-CUSUM 7/8. NN-CUSUM background alerts are about 0.69%, versus 0.12% for original NN. Misses, delays and alert costs remain; simulation is not proof of real-fault performance.

Independent tree now includes optional pressure to match independent regression. The earlier exploratory independent tree excluded pressure and is a different configuration. Finite drift/bias windows return to the original record afterward; permanent faults are not tested. This previously inspected period makes the study exploratory.

[Bilingual verification](CO2_Modular_Bilingual_local_verification.json), [English comparison CSV](CO2_Modular_local_example_comparison_EN.csv).

The code package contains two notebooks, two guides and verification, without course CSV, weights or execution outputs. Cell 25's PRIVATE ZIP contains course observations and references and should stay private. Clear notebook outputs before sharing code after execution.
