"""Portable project paths and explicit records of successfully completed runs."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def file_sha256(path):
    """Return the SHA-256 digest of a file without changing its contents.

    Args:
        path: Readable file path.
    Returns:
        str: Hexadecimal digest.
    Raises:
        OSError: The file cannot be read.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_project_root(start=None):
    """Find this project from its root or a nested notebook directory.

    Args:
        start: Directory to search upward from, defaulting to the working directory.
    Returns:
        pathlib.Path: Resolved directory containing this package and its configuration.
    Raises:
        FileNotFoundError: No project root can be found.
    """
    current = Path(start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        if (directory / "config/study.json").is_file() and (directory / "src/co2_project").is_dir():
            return directory
    raise FileNotFoundError("Open a notebook inside the submission project directory.")


def load_settings(root):
    """Read the shared fixed experiment settings from config/study.json.

    Args:
        root: Project directory.
    Returns:
        dict: Seeds, ppm magnitudes, reading counts and model settings.
    Raises:
        OSError, ValueError: The configuration is missing or invalid JSON.
    """
    return json.loads((Path(root) / "config/study.json").read_text(encoding="utf-8"))


def resolve_data_csv(root):
    """Locate authorized course data without embedding a personal computer path.

    Priority: CO2_DATA_CSV, ignored config/local.json data_csv, then data/input.csv.
    Accepts a raw course CSV or full-channel extract. Relative paths are resolved
    against the project root; local.json is never intended for Git submission.
    The source is never copied or downloaded by this function.

    Args:
        root: Project directory.
    Returns:
        pathlib.Path: Existing resolved CSV path.
    Raises:
        FileNotFoundError: The configured CSV is unavailable.
        ValueError: The local configuration is invalid.
    """
    root = Path(root).resolve()
    configured = os.environ.get("CO2_DATA_CSV")
    local = root / "config/local.json"
    if not configured and local.is_file():
        settings = json.loads(local.read_text(encoding="utf-8-sig"))
        configured = settings.get("data_csv") if isinstance(settings, dict) else None
        if not isinstance(configured, str) or not configured.strip():
            raise ValueError("config/local.json must contain a nonempty data_csv path.")
    path = Path(configured).expanduser() if configured else Path("data/input.csv")
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError("Course data are not bundled. Set config/local.json data_csv, "
                                "CO2_DATA_CSV, or provide data/input.csv; see data/README.md.")
    return path


def record_run(root, role, directory):
    """Record a completed main or input-comparison run using relative paths.

    Args:
        root: Project directory.
        role: 'main' or 'input_comparison'.
        directory: Completed run directory inside the project's private results folder.
    Returns:
        pathlib.Path: Registry path. No registration occurs for an incomplete run.
    Raises:
        ValueError: The role or directory is invalid.
        FileNotFoundError: The completion report does not exist.
    """
    root, directory = Path(root).resolve(), Path(directory).resolve()
    if role not in ("main", "input_comparison"):
        raise ValueError("Unknown run role.")
    relative = directory.relative_to(root)
    if not relative.parts or relative.parts[0] != "results":
        raise ValueError("Run directories must be inside the project's results folder.")
    report_path = directory / "run_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    registry = root / "results/run_registry.json"
    content = json.loads(registry.read_text(encoding="utf-8")) if registry.exists() else {}
    content[role] = {"path": relative.as_posix(), "report_sha256": file_sha256(report_path),
                     "source_sha256": report.get("source_sha256", report.get("audit", {}).get("source_sha256")),
                     "prepared_sha256": report.get("audit", {}).get("prepared_sha256"),
                     "completed_utc": datetime.now(timezone.utc).isoformat()}
    temporary = registry.with_suffix(".tmp")
    temporary.write_text(json.dumps(content, indent=2), encoding="utf-8")
    temporary.replace(registry)
    return registry


def get_run(root, role):
    """Read and integrity-check an explicitly registered successful run.

    Args:
        root: Project directory.
        role: 'main' or 'input_comparison'.
    Returns:
        pathlib.Path: Completed private run directory.
    Raises:
        FileNotFoundError: The preceding notebook has not completed.
        ValueError: A recorded report was changed or the path escapes the project.
    """
    root = Path(root).resolve()
    registry = root / "results/run_registry.json"
    if not registry.exists():
        raise FileNotFoundError("Run notebook 01 before reading registered results.")
    entry = json.loads(registry.read_text(encoding="utf-8")).get(role)
    if entry is None:
        raise FileNotFoundError(f"No completed {role} run. Follow notebooks 01, 02, then 03.")
    directory = (root / entry["path"]).resolve()
    relative = directory.relative_to(root)
    if relative.parts[0] != "results":
        raise ValueError("Registry path must point inside results.")
    if file_sha256(directory / "run_report.json") != entry["report_sha256"]:
        raise ValueError("The recorded completion report changed; inspect the run registry.")
    return directory
