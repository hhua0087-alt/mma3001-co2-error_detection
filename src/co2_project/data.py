"""Sensor preparation and causal input construction with shared row eligibility."""
import csv
import hashlib
import io
from pathlib import Path
import numpy as np
import pandas as pd
from .project import file_sha256
from .extraction import measurements, OUTPUT_COLUMNS

REQUIRED_CHANNELS = ["Carbon dioxide", "Temperature", "Humidity"]
PREPARED_FINGERPRINT_VERSION = "utc_ns_float64_v1"


def prepared_fingerprint(frame):
    """Hash ordered UTC timestamps and the three model channels, independent of CSV layout.

    Uses nanosecond timestamps and little-endian float64 values. The source file
    retains its own separate SHA-256 digest; this digest compares prepared inputs.
    """
    digest = hashlib.sha256()
    header = f"{PREPARED_FINGERPRINT_VERSION}\n{REQUIRED_CHANNELS!r}\n{len(frame)}\n"
    digest.update(header.encode("utf-8"))
    index = frame.index.tz_convert("UTC").as_unit("ns").asi8
    digest.update(np.ascontiguousarray(index, dtype="<i8").tobytes())
    digest.update(np.ascontiguousarray(frame[REQUIRED_CHANNELS], dtype="<f8").tobytes())
    return digest.hexdigest()


def read_environment_input(path, sensor_id):
    """Read a long-format extract or stream a raw course CSV, selecting one sensor.

    Raw rows contain sensorid and a jsondata measurement list. Only the selected
    sensor's three required channels are retained in memory. The in-memory CSV
    conversion uses the same numeric parser as a saved extract, preserving the
    established training values. No extract is written and the source is read only.
    Returns a long-format frame and format/extraction audit counts. Malformed JSON
    rows are counted and skipped, consistently with the standalone extraction tool.
    """
    header = pd.read_csv(path, nrows=0).columns
    if {"sensor_id", "timestamp_utc", "variable", "value"}.issubset(header):
        raw = pd.read_csv(path, dtype={"sensor_id": str, "variable": str})
        return raw, {"input_format": "long_format_extract"}
    if not {"sensorid", "jsondata"}.issubset(header):
        raise ValueError("CSV must contain sensorid/jsondata (raw course data), or "
                         "sensor_id/timestamp_utc/variable/value (long-format extract).")

    counts = dict(input_format="raw_course_csv", source_rows_read=0,
                  selected_sensor_rows=0, invalid_json_rows=0, required_channel_records=0)
    with io.StringIO(newline="") as buffer:
        writer = csv.DictWriter(buffer, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        with Path(path).open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                counts["source_rows_read"] += 1
                if row["sensorid"] != str(sensor_id):
                    continue
                counts["selected_sensor_rows"] += 1
                try:
                    for record in measurements(row):
                        if record["variable"] in REQUIRED_CHANNELS:
                            writer.writerow(record)
                            counts["required_channel_records"] += 1
                except ValueError:
                    counts["invalid_json_rows"] += 1
        buffer.seek(0)
        raw = pd.read_csv(buffer, dtype={"sensor_id": str, "variable": str})
    return raw, counts

def prepare_environment_csv(path, sensor_id, minimum_rows=500):
    """Prepare one sensor directly from raw course data or a long-format CSV.

    Args:
        path: Raw course CSV or long-format extract with all required channels.
        sensor_id: String sensor identifier.
        minimum_rows: Positive minimum number of complete timestamps.
    Returns:
        (frame, audit): UTC-indexed CO2 ppm, temperature, humidity and audit metadata.
    Raises:
        ValueError: Missing columns/channels, invalid values, conflicts or too few rows."""
    if type(minimum_rows) is not int or minimum_rows < 1:
        raise ValueError('Reading counts, event counts and minimum_rows must be positive integers.')
    raw, input_audit = read_environment_input(path, sensor_id)
    needed = REQUIRED_CHANNELS
    selected = raw[(raw.sensor_id == str(sensor_id)) & raw.variable.isin(needed)].copy()
    missing = sorted(set(needed) - set(selected.variable))
    if missing:
        raise ValueError(f"Sensor {sensor_id} is missing required channels: {', '.join(missing)}. "
                         "Use the original raw course CSV or a full-channel extract. "
                         "A CO2-only extract cannot supply this model's environmental inputs.")
    selected["timestamp_utc"] = pd.to_datetime(selected.timestamp_utc, utc=True, errors="coerce")
    selected["value"] = pd.to_numeric(selected.value, errors="coerce")
    if selected.timestamp_utc.isna().any() or not np.isfinite(selected.value.to_numpy()).all():
        raise ValueError('Selected records contain invalid timestamps or non-finite values.')
    keys = ["timestamp_utc", "variable"]
    if (selected.groupby(keys).value.nunique() > 1).any():
        raise ValueError('Conflicting values exist at the same timestamp and variable; investigate first.')
    duplicates_removed = int(selected.duplicated(keys).sum())
    selected = selected.drop_duplicates(keys)
    prepared = selected.pivot(index="timestamp_utc", columns="variable", values="value").sort_index()
    prepared = prepared.dropna(subset=needed).copy()
    if len(prepared) < minimum_rows:
        raise ValueError('Too few complete timestamps.')
    details = {"sensor_id": str(sensor_id), "complete_timestamps": len(prepared),
               "identical_duplicates_removed": duplicates_removed,
               "source_filename": Path(path).name, "source_sha256": file_sha256(path),
               "prepared_sha256": prepared_fingerprint(prepared),
               "prepared_fingerprint_version": PREPARED_FINGERPRINT_VERSION,
               **input_audit}
    return prepared, details


def make_features(observed):
    # Build inputs from observations; injected drift also contaminates these lags.
    """Build eight features from UTC-indexed observations; CO2 lags use past readings only."""
    co2 = observed["Carbon dioxide"]
    hour = observed.index.hour+observed.index.minute/60+observed.index.second/3600
    x = pd.DataFrame(index=observed.index)
    x["co2_lag1"] = co2.shift(1)  # Previous reading
    x["co2_lag6"] = co2.shift(6)  # Sixth previous reading, not necessarily one hour earlier
    x["temperature"] = observed["Temperature"]
    x["humidity"] = observed["Humidity"]
    x["hour_sin"] = np.sin(2*np.pi*hour/24)
    x["hour_cos"] = np.cos(2*np.pi*hour/24)
    x["weekend"] = (observed.index.dayofweek>=5).astype(float)  # Keep the existing UTC encoding.
    x["minutes_since_previous"] = observed.index.to_series().diff().dt.total_seconds()/60
    return x


HISTORY_FEATURES=["co2_lag1","co2_lag6","temperature","humidity","hour_sin","hour_cos","weekend","minutes_since_previous"]

def chronological_split(original,max_gap_minutes=20,minimum_rows=500):
    """Construct a common 60/20/20 time split for both input groups.

    Args:
        original: Sorted UTC-indexed complete sensor channels.
        max_gap_minutes: Largest allowed gap within the six-reading history.
        minimum_rows: Required eligible observations.
    Returns:
        dict: Feature frame, eligible/train/validation/test indices and row labels.
    Raises:
        ValueError: Too few eligible observations or invalid gap setting.
    """
    if not np.isfinite(max_gap_minutes) or max_gap_minutes<=0:
        raise ValueError('max_gap_minutes must be positive and finite.')
    features=make_features(original)
    gaps=original.index.to_series().diff().dt.total_seconds()/60
    eligible=features[HISTORY_FEATURES].notna().all(axis=1)&(gaps.rolling(6).max()<=max_gap_minutes)
    index=original.index[eligible]
    if len(index)<minimum_rows:raise ValueError('Too few eligible observations.')
    n_train,n_train_val=int(.6*len(index)),int(.8*len(index))
    train,validation,test=index[:n_train],index[n_train:n_train_val],index[n_train_val:]
    split=pd.Series('excluded',index=original.index,name='split')
    split.loc[train],split.loc[validation],split.loc[test]='train','validation','test'
    return dict(features=features,eligible=index,train=train,validation=validation,test=test,split=split)
