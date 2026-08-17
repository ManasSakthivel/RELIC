"""
Dataset Download and Preparation Module.

Downloads and verifies public legacy datasets:
1. AWS CardDemo (Apache 2.0) from GitHub
2. Open Mainframe Project COBOL samples (Apache 2.0)

Verifies checksums after download.
Creates ARTIFACTS.json inventory.
Splits into dev/validation/held-out sets.

Usage:
  python -m legacy_contract.datasets.download carddemo
  python -m legacy_contract.datasets.download public_cobol
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# Dataset source definitions (public, Apache 2.0 licensed)
# ---------------------------------------------------------------------------

# AWS CardDemo — COBOL and JCL banking application
# https://github.com/aws-samples/aws-mainframe-modernization-carddemo
_CARDDEMO_ARCHIVE_URL = (
    "https://github.com/aws-samples/aws-mainframe-modernization-carddemo"
    "/archive/refs/heads/main.zip"
)
_CARDDEMO_ARCHIVE_NAME = "aws-mainframe-modernization-carddemo-main.zip"
_CARDDEMO_INNER_DIR = "aws-mainframe-modernization-carddemo-main"

# Open Mainframe Project COBOL Programming Course samples
# https://github.com/openmainframeproject/cobol-programming-course
_OMP_COBOL_ARCHIVE_URL = (
    "https://github.com/openmainframeproject/cobol-programming-course"
    "/archive/refs/heads/master.zip"
)
_OMP_COBOL_ARCHIVE_NAME = "cobol-programming-course-master.zip"
_OMP_COBOL_INNER_DIR = "cobol-programming-course-master"

# Supported legacy file extensions
_LEGACY_EXTENSIONS: set[str] = {
    ".jcl", ".cbl", ".cob", ".cpy", ".copy",
    ".JCL", ".CBL", ".COB", ".CPY", ".COPY",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ArtifactEntry:
    """Inventory entry for a single dataset artifact."""
    path: str               # relative to dataset root
    artifact_type: str      # JCL | COBOL | COPYBOOK | UNKNOWN
    sha256: str
    size_bytes: int


@dataclass
class DatasetSplit:
    """Train/validation/held-out split of artifact paths."""
    dev: list[str] = field(default_factory=list)
    validation: list[str] = field(default_factory=list)
    held_out: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Split: dev={len(self.dev)}, "
            f"validation={len(self.validation)}, "
            f"held_out={len(self.held_out)}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_path(path: Path) -> str:
    """Return hex SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _detect_type(path: Path) -> str:
    """Classify a legacy file by extension."""
    ext = path.suffix.lower()
    if ext == ".jcl":
        return "JCL"
    if ext in {".cbl", ".cob"}:
        return "COBOL"
    if ext in {".cpy", ".copy"}:
        return "COPYBOOK"
    return "UNKNOWN"


def _download_with_progress(url: str, dest: Path) -> None:
    """
    Download *url* to *dest* using urllib, logging progress every 5 MB.

    Parameters
    ----------
    url:
        HTTPS URL to download.
    dest:
        Destination file path.  Parent directory must exist.

    Raises
    ------
    urllib.error.URLError
        On network or HTTP error.
    """
    logger.info(f"Downloading {url} → {dest}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "legacy-contract-research/1.0 (dataset downloader)"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        total = response.headers.get("Content-Length")
        total_mb = int(total) / 1_048_576 if total else None

        written = 0
        last_log_mb = 0
        with open(dest, "wb") as fh:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                fh.write(chunk)
                written += len(chunk)
                written_mb = written / 1_048_576
                if written_mb - last_log_mb >= 5:
                    if total_mb:
                        logger.info(
                            f"  {written_mb:.1f} / {total_mb:.1f} MB downloaded"
                        )
                    else:
                        logger.info(f"  {written_mb:.1f} MB downloaded")
                    last_log_mb = written_mb

    logger.info(
        f"Download complete: {dest.name} "
        f"({dest.stat().st_size / 1_048_576:.2f} MB)"
    )


def _extract_zip(archive: Path, dest_dir: Path) -> None:
    """Extract *archive* into *dest_dir*."""
    logger.info(f"Extracting {archive.name} → {dest_dir}")
    with zipfile.ZipFile(archive, "r") as zf:
        zf.extractall(dest_dir)
    logger.info("Extraction complete")


def _collect_legacy_files(root: Path) -> list[Path]:
    """Walk *root* and return all legacy-extension files."""
    files: list[Path] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix in _LEGACY_EXTENSIONS:
            files.append(p)
    return files


def _build_inventory(root: Path, files: list[Path]) -> list[ArtifactEntry]:
    """Build ArtifactEntry list relative to *root*."""
    entries: list[ArtifactEntry] = []
    for p in files:
        rel = str(p.relative_to(root))
        entries.append(
            ArtifactEntry(
                path=rel,
                artifact_type=_detect_type(p),
                sha256=_sha256_path(p),
                size_bytes=p.stat().st_size,
            )
        )
    return entries


def _write_artifacts_json(output_dir: Path, entries: list[ArtifactEntry]) -> None:
    """Write ARTIFACTS.json manifest to *output_dir*."""
    manifest = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "artifact_count": len(entries),
        "artifacts": [asdict(e) for e in entries],
    }
    dest = output_dir / "ARTIFACTS.json"
    dest.write_text(json.dumps(manifest, indent=2))
    logger.info(f"ARTIFACTS.json written: {dest} ({len(entries)} entries)")


def _get_git_commit(repo_dir: Path) -> str:
    """
    Return the HEAD git commit hash for *repo_dir*, or 'unknown' if git
    is unavailable or the directory is not a git repository.
    """
    try:
        import subprocess  # noqa: PLC0415
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    return "unknown"


def _write_dataset_version(output_dir: Path, dataset_name: str, url: str) -> None:
    """Write DATASET_VERSION.txt with provenance metadata."""
    commit = _get_git_commit(output_dir)
    lines = [
        f"dataset: {dataset_name}",
        f"source_url: {url}",
        f"downloaded_at: {datetime.now(tz=timezone.utc).isoformat()}",
        f"git_commit: {commit}",
        f"tool: legacy-contract dataset downloader",
    ]
    dest = output_dir / "DATASET_VERSION.txt"
    dest.write_text("\n".join(lines) + "\n")
    logger.info(f"DATASET_VERSION.txt written: {dest}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_carddemo(output_dir: str = "datasets/carddemo") -> list[ArtifactEntry]:
    """
    Download and prepare the AWS CardDemo dataset.

    The dataset is downloaded from GitHub as a ZIP archive, extracted, and
    scanned for JCL, COBOL, and copybook files.  An ARTIFACTS.json manifest
    and a DATASET_VERSION.txt provenance file are written to *output_dir*.

    Parameters
    ----------
    output_dir:
        Directory where the dataset will be stored.

    Returns
    -------
    list[ArtifactEntry]
        Inventory of all legacy artifacts found in the dataset.

    Notes
    -----
    License: Apache 2.0
    Source: https://github.com/aws-samples/aws-mainframe-modernization-carddemo
    """
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    archive_path = root / _CARDDEMO_ARCHIVE_NAME
    if not archive_path.exists():
        try:
            _download_with_progress(_CARDDEMO_ARCHIVE_URL, archive_path)
        except urllib.error.URLError as exc:
            logger.error(
                f"Failed to download CardDemo: {exc}\n"
                f"Manual download: {_CARDDEMO_ARCHIVE_URL}"
            )
            raise

    extract_dir = root / "extracted"
    if not extract_dir.exists():
        _extract_zip(archive_path, extract_dir)

    dataset_root = extract_dir / _CARDDEMO_INNER_DIR
    if not dataset_root.exists():
        # Fallback: the archive may have been extracted flat
        dataset_root = extract_dir

    files = _collect_legacy_files(dataset_root)
    logger.info(f"CardDemo: {len(files)} legacy artifacts found")

    entries = _build_inventory(dataset_root, files)
    _write_artifacts_json(root, entries)
    _write_dataset_version(root, "aws-carddemo", _CARDDEMO_ARCHIVE_URL)

    # Type summary
    type_counts: dict[str, int] = {}
    for e in entries:
        type_counts[e.artifact_type] = type_counts.get(e.artifact_type, 0) + 1
    logger.info(f"CardDemo artifact types: {type_counts}")

    return entries


def download_public_cobol(
    output_dir: str = "datasets/public_cobol",
) -> list[ArtifactEntry]:
    """
    Download and prepare the Open Mainframe Project COBOL Programming Course samples.

    Parameters
    ----------
    output_dir:
        Directory where the dataset will be stored.

    Returns
    -------
    list[ArtifactEntry]
        Inventory of all legacy artifacts found in the dataset.

    Notes
    -----
    License: Apache 2.0
    Source: https://github.com/openmainframeproject/cobol-programming-course
    """
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    archive_path = root / _OMP_COBOL_ARCHIVE_NAME
    if not archive_path.exists():
        try:
            _download_with_progress(_OMP_COBOL_ARCHIVE_URL, archive_path)
        except urllib.error.URLError as exc:
            logger.error(
                f"Failed to download OMP COBOL samples: {exc}\n"
                f"Manual download: {_OMP_COBOL_ARCHIVE_URL}"
            )
            raise

    extract_dir = root / "extracted"
    if not extract_dir.exists():
        _extract_zip(archive_path, extract_dir)

    dataset_root = extract_dir / _OMP_COBOL_INNER_DIR
    if not dataset_root.exists():
        dataset_root = extract_dir

    files = _collect_legacy_files(dataset_root)
    logger.info(f"OMP COBOL: {len(files)} legacy artifacts found")

    entries = _build_inventory(dataset_root, files)
    _write_artifacts_json(root, entries)
    _write_dataset_version(root, "omp-cobol-programming-course", _OMP_COBOL_ARCHIVE_URL)

    type_counts: dict[str, int] = {}
    for e in entries:
        type_counts[e.artifact_type] = type_counts.get(e.artifact_type, 0) + 1
    logger.info(f"OMP COBOL artifact types: {type_counts}")

    return entries


def verify_checksums(directory: str, manifest: str) -> bool:
    """
    Verify SHA-256 checksums for all artifacts listed in *manifest*.

    Parameters
    ----------
    directory:
        Root directory from which artifact paths in the manifest are resolved.
    manifest:
        Path to an ARTIFACTS.json manifest file (as written by this module).

    Returns
    -------
    bool
        True if all checksums match; False if any mismatch or missing file.

    Notes
    -----
    The function continues checking after individual failures so the caller
    receives a complete picture of all mismatches in a single pass.
    """
    root = Path(directory)
    manifest_path = Path(manifest)

    if not manifest_path.exists():
        logger.error(f"verify_checksums: manifest not found: {manifest}")
        return False

    data = json.loads(manifest_path.read_text())
    artifacts = data.get("artifacts", [])

    all_ok = True
    checked = 0
    failures = 0

    for entry in artifacts:
        rel_path = entry["path"]
        expected_sha = entry["sha256"]
        artifact_file = root / rel_path

        if not artifact_file.exists():
            logger.error(
                f"verify_checksums: MISSING {rel_path}"
            )
            failures += 1
            all_ok = False
            continue

        actual_sha = _sha256_path(artifact_file)
        if actual_sha != expected_sha:
            logger.error(
                f"verify_checksums: MISMATCH {rel_path} "
                f"(expected {expected_sha[:12]}…, got {actual_sha[:12]}…)"
            )
            failures += 1
            all_ok = False
        else:
            checked += 1

    logger.info(
        f"verify_checksums: {checked} OK, {failures} failures "
        f"(total {len(artifacts)} entries in manifest)"
    )
    return all_ok


def create_split(
    inventory: list[ArtifactEntry],
    dev_ratio: float = 0.70,
    val_ratio: float = 0.15,
    held_out_ratio: float = 0.15,
    seed: int = 42,
) -> DatasetSplit:
    """
    Partition an artifact inventory into dev / validation / held-out sets.

    Stratified by artifact type to maintain type distribution across splits.
    Ratios must sum to 1.0 (within floating-point tolerance).

    Parameters
    ----------
    inventory:
        List of ArtifactEntry objects to partition.
    dev_ratio:
        Fraction of artifacts allocated to the development set.
    val_ratio:
        Fraction of artifacts allocated to the validation set.
    held_out_ratio:
        Fraction of artifacts allocated to the held-out test set.
    seed:
        Random seed for reproducibility.

    Returns
    -------
    DatasetSplit
        Named lists of artifact paths for each split.

    Raises
    ------
    ValueError
        If ratios do not sum to approximately 1.0.
    """
    total_ratio = dev_ratio + val_ratio + held_out_ratio
    if abs(total_ratio - 1.0) > 1e-6:
        raise ValueError(
            f"Ratios must sum to 1.0, got {total_ratio:.6f} "
            f"(dev={dev_ratio}, val={val_ratio}, held_out={held_out_ratio})"
        )

    rng = random.Random(seed)

    # Group by artifact type for stratification
    by_type: dict[str, list[ArtifactEntry]] = {}
    for entry in inventory:
        by_type.setdefault(entry.artifact_type, []).append(entry)

    split = DatasetSplit()

    for artifact_type, entries in by_type.items():
        shuffled = list(entries)
        rng.shuffle(shuffled)
        n = len(shuffled)

        n_dev = max(1, round(n * dev_ratio)) if n >= 3 else n
        n_val = max(0, round(n * val_ratio)) if n >= 3 else 0
        # Held-out gets the remainder to avoid rounding loss
        n_held = max(0, n - n_dev - n_val)

        dev_entries = shuffled[:n_dev]
        val_entries = shuffled[n_dev : n_dev + n_val]
        held_entries = shuffled[n_dev + n_val :]

        split.dev.extend(e.path for e in dev_entries)
        split.validation.extend(e.path for e in val_entries)
        split.held_out.extend(e.path for e in held_entries)

        logger.debug(
            f"create_split [{artifact_type}]: "
            f"total={n}, dev={len(dev_entries)}, "
            f"val={len(val_entries)}, held_out={len(held_entries)}"
        )

    logger.info(split.summary())
    return split


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main() -> None:
    """
    Minimal CLI for dataset download.

    Usage
    -----
    python -m legacy_contract.datasets.download carddemo [output_dir]
    python -m legacy_contract.datasets.download public_cobol [output_dir]
    """
    if len(sys.argv) < 2:
        print(
            "Usage: python -m legacy_contract.datasets.download "
            "<carddemo|public_cobol> [output_dir]",
            file=sys.stderr,
        )
        sys.exit(1)

    dataset = sys.argv[1].lower()
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    if dataset == "carddemo":
        kwargs: dict[str, Any] = {}
        if output_dir:
            kwargs["output_dir"] = output_dir
        entries = download_carddemo(**kwargs)
        split = create_split(entries)
        print(split.summary())

    elif dataset == "public_cobol":
        kwargs = {}
        if output_dir:
            kwargs["output_dir"] = output_dir
        entries = download_public_cobol(**kwargs)
        split = create_split(entries)
        print(split.summary())

    else:
        print(f"Unknown dataset: {dataset!r}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _main()
