"""Extract MSI environmental measurements directly from the supplied CSV.

Example (PowerShell)::

    python extract_env.py --sensor 6012002000869 --variable "Carbon dioxide"

The source CSV is read only. Output is a long-format CSV with one row per
measurement, so the choice of a later modelling question remains open.
"""

import argparse
import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import tempfile


DEFAULT_CSV = Path(
    r"E:\Study\MMA3001\project\MMA3001 Dataset - MSI Occupancy and Environmental -20260927T041718Z-1-001\MMA3001 Dataset - MSI Occupancy and Environmental\5EnvSensor_MayToDec2024_180kRows\5EnvSensor_MayToDec2024_180kRows.csv"
)
OUTPUT_COLUMNS = ("sensor_id", "timestamp_utc", "variable", "unit", "value", "source_row_id")


def measurements(row, variable_filter=None):
    """Convert one raw CSV row's JSON into measurement records.

    Invalid measurements are skipped; malformed JSON raises ValueError so the
    caller can count bad source rows. Timestamps are Unix seconds in UTC.
    """
    try:
        payload = json.loads(row["jsondata"])
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("invalid jsondata") from exc
    if not isinstance(payload, list):
        raise ValueError("jsondata is not a list")

    for item in payload:
        if not isinstance(item, dict):
            continue
        variable = item.get("variable") or {}
        if not isinstance(variable, dict):
            continue
        name = variable.get("name")
        if not isinstance(name, str) or (variable_filter and name != variable_filter):
            continue
        for reading in item.get("values") or []:
            if not isinstance(reading, dict) or reading.get("value") is None:
                continue
            try:
                timestamp = datetime.fromtimestamp(int(reading["time"]), timezone.utc)
            except (KeyError, TypeError, ValueError, OverflowError, OSError):
                continue
            yield {
                "sensor_id": row["sensorid"],
                "timestamp_utc": timestamp.isoformat(timespec="seconds"),
                "variable": name,
                "unit": variable.get("unit", ""),
                "value": reading["value"],
                "source_row_id": row.get("id", ""),
            }


def extract(source, output, sensor, variable_filter, progress_every, force):
    """Stream the environmental CSV and write selected readings to a new CSV."""
    if not source.is_file():
        raise FileNotFoundError(f"Input CSV not found: {source}")
    if output.exists() and not force:
        raise FileExistsError(f"Output exists: {output} (use --force to replace it)")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    read_rows = selected_rows = written_rows = bad_json_rows = 0
    total_bytes = source.stat().st_size

    try:
        # Read line by line; the entire 353 MB CSV is never loaded into memory.
        with source.open("rb") as raw:
            with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
                reader = csv.DictReader(text)
                required = {"id", "sensorid", "jsondata"}
                if not required.issubset(reader.fieldnames or []):
                    raise ValueError(f"CSV missing required columns: {sorted(required)}")

                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", newline="", delete=False,
                    dir=output.parent, prefix=f".{output.name}.", suffix=".tmp"
                ) as target:
                    temp_name = Path(target.name)
                    writer = csv.DictWriter(target, fieldnames=OUTPUT_COLUMNS)
                    writer.writeheader()
                    for row in reader:
                        read_rows += 1
                        if row["sensorid"] == sensor:
                            selected_rows += 1
                            try:
                                for record in measurements(row, variable_filter):
                                    writer.writerow(record)
                                    written_rows += 1
                            except ValueError:
                                bad_json_rows += 1
                        if read_rows % progress_every == 0:
                            percent = 100 * raw.tell() / total_bytes
                            print(f"Progress ~{percent:5.1f}% | source rows {read_rows:,} | output rows {written_rows:,}", flush=True)

        if written_rows == 0:
            raise ValueError("No measurements matched. Check --sensor and --variable.")
        os.replace(temp_name, output)
        temp_name = None
    finally:
        if temp_name is not None:
            temp_name.unlink(missing_ok=True)

    print(f"Done: {read_rows:,} source rows; {selected_rows:,} sensor rows; {written_rows:,} measurements")
    print(f"Invalid JSON rows for this sensor: {bad_json_rows:,}")
    print(f"Saved: {output.resolve()}")


def main():
    """Parse command-line options and start extraction."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_CSV, help="Environmental sensor CSV")
    parser.add_argument("--sensor", default="6012002000869", help="Environmental sensor ID")
    parser.add_argument("--variable", help='Exact variable name, e.g. "Carbon dioxide"; default: all')
    parser.add_argument("--output", type=Path, help="Destination CSV; default: data/processed/env_<sensor>_direct.csv")
    parser.add_argument("--progress-every", type=int, default=10000, help="Show progress every N source rows")
    parser.add_argument("--force", action="store_true", help="Replace an existing output file")
    args = parser.parse_args()
    if args.progress_every < 1:
        parser.error("--progress-every must be at least 1")
    output = args.output or Path("data/processed") / f"env_{args.sensor}_direct.csv"
    try:
        extract(args.input, output, args.sensor, args.variable, args.progress_every, args.force)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
