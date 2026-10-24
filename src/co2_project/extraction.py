"""Stream the course environmental CSV into the documented long-format input.

The source is read only. JSON timestamps are Unix seconds converted to UTC.
Malformed source rows are counted; preparation subsequently validates numeric
channels, complete timestamps and conflicting duplicates.
"""
import csv
from datetime import datetime,timezone
import io,json,os,tempfile
from pathlib import Path
OUTPUT_COLUMNS=("sensor_id","timestamp_utc","variable","unit","value","source_row_id")

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
    """Stream an authorized raw CSV into a new long-format sensor extract.

    Args:
        source: Raw CSV Path with id, sensorid and jsondata fields.
        output: Destination CSV Path, different from the raw source.
        sensor: String sensor identifier.
        variable_filter: Optional exact channel name; None retains all channels.
        progress_every: Positive number of source rows between progress messages.
        force: Whether an existing destination may be replaced.
    Returns:
        None: Writes the six-column extract and prints actual extraction counts.
    Raises:
        ValueError: Invalid source schema, progress setting, identical paths or no matching measurements.
        FileNotFoundError: Source is missing.
        FileExistsError: Destination exists and force is False.
    """
    source,output=Path(source),Path(output)
    if source.resolve()==output.resolve():
        raise ValueError('Source and destination must differ; the raw source is read only.')
    if type(progress_every) is not int or progress_every<1:
        raise ValueError('progress_every must be a positive integer.')
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

