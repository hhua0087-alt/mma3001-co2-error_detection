# Authorized course data

Obtain Dataset 2 MSI Occupancy and Environmental through the MMA3001 course
channel. The repository does not distribute any course measurements.

## Use the original file directly

The supported raw file is `5EnvSensor_MayToDec2024_180kRows.csv`. Point
`config/local.json` at it (copy `config/local.example.json`, then edit `data_csv`),
or set `CO2_DATA_CSV` before launching the notebook kernel. The same loader also
accepts local `data/input.csv`. A separate extraction step is optional.

The raw schema includes `sensorid` and `jsondata` (the original also has `id`,
`devicetype`, status and processing/date fields). `jsondata` is a list of variables
with nested `values`: each reading has a Unix-second `time` and a `value`.
The loader streams the original file, selects sensor `6012002000869`, and retains
only `Carbon dioxide`, `Temperature` and `Humidity`. No pressure channel is needed.
Invalid JSON source rows are counted and skipped; the actual reference file has
zero for this sensor. The audit reports source rows, sensor rows and retained records.

## Or use a full-channel extract

The supported long-format columns are:

| Column | Meaning |
|---|---|
| sensor_id | String device identifier |
| timestamp_utc | Timestamp parseable as UTC |
| variable | Carbon dioxide, Temperature or Humidity |
| value | Numeric measurement: ppm, degrees Celsius or relative humidity percent |

Additional fields such as `unit` and `source_row_id` are permitted. The historical
input was `env_6012002000869_all.csv`. A file containing only CO2, such as the
supplied `env_6012002000869.csv`, is insufficient for these fixed multivariable
models. The loader explains which channels are missing; it never invents them.

If a saved extract is useful, run:

```text
python tools/extract_environment.py --input /path/to/authorized/5EnvSensor_MayToDec2024_180kRows.csv --sensor 6012002000869
```

Omit `--variable` to preserve all channels. The default output is local
`data/input.csv`; the source cannot be overwritten by the extraction helper.

## Shared preparation and provenance

The supplied location is Building 60, G.38, Compactus_upper. Both supported input
routes yield exactly 13,800 complete distinct timestamps for the reference sensor;
46,623 identical channel duplicates are removed. The eligible chronological split
is 7,373 training / 2,458 validation / 2,458 test, with 1,511 excluded history rows.
Conflicting duplicates, invalid numeric values and invalid selected timestamps are
rejected. Missing channels at a timestamp are not interpolated. Original readings
are not verified health labels.

Audit records distinguish actual input format, filename and source SHA-256 from
`prepared_sha256`, which hashes ordered UTC nanosecond timestamps and the three
float64 model channels. This permits equivalent raw and extracted files to be
compared without pretending their file bytes match. Digests and fingerprint version
are in `results_summary/reference/protocol.json`; the historical file digest remains
recorded there. The raw file has 179,447 source rows, 29,341 for this sensor and
88,023 retained required-channel records before duplicate removal.

Use your own authorized path. `config/local.json`, all source/extracted data and
measurement-level results are ignored by Git. Only the empty schema example CSV
is included here. Do not ZIP ignored local files into a public submission. A code
license does not grant permission to share course data.
