"""Raw/extracted input equivalence and local path selection on manufactured data."""
import csv
import json
import numpy as np
import pandas as pd
import pytest
from co2_project.data import prepare_environment_csv, prepared_fingerprint
from co2_project.extraction import extract
from co2_project.project import file_sha256, resolve_data_csv


def write_raw(path, extra_rows=()):
    """Write a toy raw measurement payload with floats, duplicates and another sensor."""
    payload = [{"variable": {"name": name, "unit": unit},
                "values": [{"time": 1577836800 + i * 600, "value": value + i / 7}
                           for i in range(4)]}
               for name, unit, value in [("Carbon dioxide", "ppm", 405.1234567891234),
                                         ("Temperature", "C", 20.1234567891234),
                                         ("Humidity", "%", 51.1234567891234)]]
    rows = [{"id": "1", "sensorid": "toy", "jsondata": json.dumps(payload)},
            {"id": "2", "sensorid": "toy", "jsondata": json.dumps(payload[:1])},
            {"id": "3", "sensorid": "other", "jsondata": "not JSON"}, *extra_rows]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id", "sensorid", "jsondata"])
        writer.writeheader(); writer.writerows(rows)


def test_raw_and_full_extract_prepare_identically(tmp_path):
    raw, long = tmp_path / "raw.csv", tmp_path / "all.csv"
    write_raw(raw)
    before = file_sha256(raw)
    extract(raw, long, "toy", None, 100, False)
    a, aa = prepare_environment_csv(raw, "toy", minimum_rows=2)
    b, ba = prepare_environment_csv(long, "toy", minimum_rows=2)
    pd.testing.assert_frame_equal(a, b, check_exact=True)
    assert aa["prepared_sha256"] == ba["prepared_sha256"]
    assert aa["source_sha256"] != ba["source_sha256"]
    assert aa["identical_duplicates_removed"] == 4
    assert aa["source_rows_read"] == 3 and aa["selected_sensor_rows"] == 2
    assert aa["required_channel_records"] == 16 and aa["invalid_json_rows"] == 0
    assert file_sha256(raw) == before


def test_raw_invalid_json_is_counted_for_selected_sensor(tmp_path):
    raw = tmp_path / "raw.csv"
    write_raw(raw, [{"id": "4", "sensorid": "toy", "jsondata": "bad JSON"}])
    frame, audit = prepare_environment_csv(raw, "toy", minimum_rows=2)
    assert len(frame) == 4 and audit["invalid_json_rows"] == 1
    assert audit["source_rows_read"] == 4 and audit["selected_sensor_rows"] == 3


def test_co2_only_extract_explains_missing_channels(tmp_path):
    path = tmp_path / "co2_only.csv"
    pd.DataFrame({"sensor_id": ["toy"], "timestamp_utc": ["2020-01-01"],
                  "variable": ["Carbon dioxide"], "value": [400.]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="Humidity, Temperature.*original raw course CSV"):
        prepare_environment_csv(path, "toy", minimum_rows=1)


@pytest.mark.parametrize("change", ["value", "timestamp"])
def test_prepared_fingerprint_detects_changed_model_input(change):
    frame = pd.DataFrame({"Carbon dioxide": [400.], "Temperature": [20.], "Humidity": [50.]},
                         index=pd.date_range("2020-01-01", periods=1, tz="UTC"))
    before = prepared_fingerprint(frame)
    if change == "value":
        frame.loc[frame.index[0], "Carbon dioxide"] = np.nextafter(400., np.inf)
    else:
        frame.index += pd.Timedelta(1, unit="ns")
    assert prepared_fingerprint(frame) != before


def test_local_configuration_and_environment_precedence(tmp_path, monkeypatch):
    monkeypatch.delenv("CO2_DATA_CSV", raising=False)
    (tmp_path / "config").mkdir(); (tmp_path / "data").mkdir()
    default, local, override = [tmp_path / "data" / name for name in ["input.csv", "raw.csv", "override.csv"]]
    for path in (default, local, override): path.write_text("manufactured")
    assert resolve_data_csv(tmp_path) == default
    (tmp_path / "config/local.json").write_text(json.dumps({"data_csv": "data/raw.csv"}))
    assert resolve_data_csv(tmp_path) == local
    monkeypatch.setenv("CO2_DATA_CSV", str(override))
    assert resolve_data_csv(tmp_path) == override


@pytest.mark.parametrize("content", ["{}", '{"data_csv":""}', "[]"])
def test_invalid_local_configuration_is_actionable(tmp_path, monkeypatch, content):
    monkeypatch.delenv("CO2_DATA_CSV", raising=False)
    (tmp_path / "config").mkdir()
    (tmp_path / "config/local.json").write_text(content)
    with pytest.raises(ValueError, match="data_csv"):
        resolve_data_csv(tmp_path)
