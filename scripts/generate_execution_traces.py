#!/usr/bin/env python3
"""
generate_execution_traces.py — Generate execution traces using GnuCOBOL.

This script:
1. Attempts to compile simple standalone COBOL programs from the public_cobol dataset
   using the GnuCOBOL compiler (resolved from COBC_PATH env var, PATH, or common locations)
2. Runs each compiled program and captures stdout output as an execution trace
3. Generates JCL job-ordering simulation traces for CardDemo batch sequences
   by simulating the JCL step order from parsed JCL files

Source labeling:
    - COBOL programs compiled and run by GnuCOBOL: EXECUTION
    - JCL step-ordering derived from JCL parser + simulated execution: EXECUTION_SIMULATED

IMPORTANT:
    - EXECUTION traces may be used to update contract validation states
    - EXECUTION_SIMULATED traces may be used only for ordering verification
    - SYNTHETIC_STATIC is no longer used for any new traces in this session
    - All traces carry gnucobol_version field for reproducibility

GnuCOBOL resolution order:
    1. COBC_PATH environment variable (explicit override)
    2. `cobc` on PATH (standard Linux/macOS install)
    3. /usr/bin/cobc (common Linux location)
    4. /usr/local/bin/cobc (Homebrew Linux / manual install)
    5. NOT hardcoded to any machine-specific path

Output: traces/dev/<program>_execution.json (EXECUTION or EXECUTION_SIMULATED)
        traces/dev/manifest_execution.json
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from legacy_contract.parsers.jcl_parser import JCLParser

TRACES_DIR = ROOT / "traces" / "dev"
TRACES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# GnuCOBOL resolution — portable, no hardcoded paths
# ---------------------------------------------------------------------------

def _find_gnucobol() -> tuple[str | None, str | None]:
    """
    Locate GnuCOBOL (cobc / cobcrun) executables.

    Resolution order:
    1. COBC_PATH env var (e.g. export COBC_PATH=/custom/bin/cobc)
    2. shutil.which("cobc") — uses PATH
    3. /usr/bin/cobc
    4. /usr/local/bin/cobc

    Returns (cobc_path, cobcrun_path) or (None, None) if not found.
    """
    # 1. Explicit environment override
    env_path = os.environ.get("COBC_PATH")
    if env_path:
        cobc = env_path.strip()
        cobcrun = str(pathlib.Path(cobc).parent / "cobcrun")
        if pathlib.Path(cobc).is_file():
            return cobc, cobcrun

    # 2. PATH-based discovery (covers most Linux and macOS installs)
    cobc_on_path = shutil.which("cobc")
    if cobc_on_path:
        cobcrun_on_path = shutil.which("cobcrun") or str(
            pathlib.Path(cobc_on_path).parent / "cobcrun"
        )
        return cobc_on_path, cobcrun_on_path

    # 3. Common fixed locations (non-machine-specific standard paths)
    for candidate in ["/usr/bin/cobc", "/usr/local/bin/cobc"]:
        if pathlib.Path(candidate).is_file():
            cobcrun_candidate = str(pathlib.Path(candidate).parent / "cobcrun")
            return candidate, cobcrun_candidate

    return None, None


COBC, COBRUN = _find_gnucobol()


# ---------------------------------------------------------------------------
# Verify GnuCOBOL
# ---------------------------------------------------------------------------

def _get_gnucobol_version() -> str | None:
    if not COBC:
        return None
    try:
        result = subprocess.run(
            [COBC, "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            line = result.stdout.splitlines()[0]
            return line.strip()
    except Exception:
        pass
    return None


GNUCOBOL_VERSION = _get_gnucobol_version()
GNUCOBOL_AVAILABLE = GNUCOBOL_VERSION is not None


# ---------------------------------------------------------------------------
# Helper — write trace file
# ---------------------------------------------------------------------------

def _write_trace(name: str, data: dict) -> pathlib.Path:
    path = TRACES_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


# ---------------------------------------------------------------------------
# Compile and run a standalone COBOL program
# ---------------------------------------------------------------------------

def _compile_and_run_cobol(cobol_file: pathlib.Path) -> dict | None:
    """
    Compile a standalone COBOL program with GnuCOBOL and capture execution output.

    Returns a trace dict (EXECUTION source_type) or None on failure.
    """
    if not GNUCOBOL_AVAILABLE or not COBC:
        return None

    stem = cobol_file.stem.upper()
    exec_id = f"exec-{stem.lower()}-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}"

    with tempfile.TemporaryDirectory() as tmpdir:
        out_bin = pathlib.Path(tmpdir) / stem.lower()
        compile_result = subprocess.run(
            [COBC, "-x", "-o", str(out_bin), str(cobol_file)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if compile_result.returncode != 0:
            return None

        run_result = subprocess.run(
            [str(out_bin)],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "COB_FILE_PATH": tmpdir, "COB_LIBRARY_PATH": tmpdir},
        )

        return {
            "source_type": "EXECUTION",
            "gnucobol_version": GNUCOBOL_VERSION,
            "gnucobol_available": True,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "generator": "generate_execution_traces.py — GnuCOBOL compilation",
            "program": stem,
            "execution_id": exec_id,
            "return_code": run_result.returncode,
            "stdout_lines": run_result.stdout.splitlines(),
            "events": [
                {
                    "event_id": str(uuid.uuid4()),
                    "execution_id": exec_id,
                    "artifact_id": stem,
                    "operation": "EXECUTE",
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    "source_type": "EXECUTION",
                    "resource": None,
                    "return_code": run_result.returncode,
                    "metadata": {"program": stem, "gnucobol_version": GNUCOBOL_VERSION},
                }
            ],
        }


# ---------------------------------------------------------------------------
# Generate JCL step-ordering simulation trace
# ---------------------------------------------------------------------------

def _simulate_jcl_trace(jcl_path: pathlib.Path, ir) -> dict | None:
    """
    Produce an EXECUTION_SIMULATED trace from parsed JCL by recording
    the step execution order as timed events.

    These traces provide temporal ordering evidence only. They do NOT
    represent actual program execution. DO NOT use for CONTROL_FLOW
    or RESOURCE contract validation.
    """
    steps = [
        (eid, ent)
        for eid, ent in ir.entities.items()
        if str(ent.entity_type).upper().endswith("STEP")
    ]

    if not steps:
        return None

    job_name = jcl_path.stem.upper()
    exec_id = f"jclsim-{job_name.lower()}-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S%f')[:20]}"
    base_time = datetime.now(tz=timezone.utc)

    events = []

    # Find the JOB entity for JOB_START
    job_entities = [
        (eid, ent)
        for eid, ent in ir.entities.items()
        if str(ent.entity_type).upper().endswith("JOB")
    ]
    if job_entities:
        job_eid, job_ent = job_entities[0]
        events.append({
            "event_id": str(uuid.uuid4()),
            "execution_id": exec_id,
            "artifact_id": job_eid,
            "operation": "JOB_START",
            "timestamp": base_time.isoformat(),
            "source_type": "EXECUTION_SIMULATED",
            "resource": None,
            "return_code": None,
            "metadata": {
                "job": job_name,
                "job_entity_id": job_eid,
                "simulation": "JCL_ordering_from_parser",
            },
        })

    for i, (step_eid, step_ent) in enumerate(steps):
        step_time = base_time + timedelta(seconds=i + 1)
        step_name = step_ent.name or step_eid
        events.append({
            "event_id": str(uuid.uuid4()),
            "execution_id": exec_id,
            "artifact_id": step_eid,
            "operation": "STEP_START",
            "timestamp": step_time.isoformat(),
            "source_type": "EXECUTION_SIMULATED",
            "resource": None,
            "return_code": None,
            "metadata": {"step": step_name, "step_index": i, "jcl_file": jcl_path.name},
        })
        events.append({
            "event_id": str(uuid.uuid4()),
            "execution_id": exec_id,
            "artifact_id": step_eid,
            "operation": "STEP_END",
            "timestamp": (step_time + timedelta(milliseconds=500)).isoformat(),
            "source_type": "EXECUTION_SIMULATED",
            "resource": None,
            "return_code": 0,
            "metadata": {"step": step_name, "step_index": i, "jcl_file": jcl_path.name},
        })

    return {
        "source_type": "EXECUTION_SIMULATED",
        "gnucobol_version": GNUCOBOL_VERSION or "not_available",
        "gnucobol_available": GNUCOBOL_AVAILABLE,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "generator": "generate_execution_traces.py — JCL step-ordering simulation",
        "program": job_name,
        "execution_id": exec_id,
        "source_jcl": str(jcl_path.relative_to(ROOT)),
        "n_steps_ordered": len(steps),
        "events": events,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not GNUCOBOL_AVAILABLE:
        print(
            "WARNING: GnuCOBOL not available. "
            "To enable EXECUTION traces, either:\n"
            "  - Install GnuCOBOL (e.g. 'brew install gnucobol' or 'apt-get install gnucobol')\n"
            "  - Set COBC_PATH=/path/to/cobc environment variable\n"
            "EXECUTION_SIMULATED traces (JCL ordering) will still be generated."
        )
    else:
        print(f"GnuCOBOL found: {GNUCOBOL_VERSION}")
        print(f"  cobc:    {COBC}")
        print(f"  cobcrun: {COBRUN}")

    generated = []

    # --- EXECUTION traces from standalone COBOL programs ---
    cobol_dirs = [ROOT / "datasets" / "public_cobol"]
    for cobol_dir in cobol_dirs:
        if not cobol_dir.exists():
            continue
        for cobol_file in sorted(cobol_dir.rglob("*.cbl")) + sorted(cobol_dir.rglob("*.CBL")):
            trace = _compile_and_run_cobol(cobol_file)
            if trace:
                name = f"{cobol_file.stem.upper()}_execution"
                path = _write_trace(name, trace)
                print(f"  EXECUTION trace: {path.name}")
                generated.append({"file": path.name, "source_type": "EXECUTION", "program": cobol_file.stem.upper()})

    # --- EXECUTION_SIMULATED traces from JCL parsing ---
    jcl_dir = (
        ROOT / "datasets" / "carddemo" / "extracted"
        / "aws-mainframe-modernization-carddemo-main" / "app" / "jcl"
    )
    if jcl_dir.exists():
        parser = JCLParser()
        for jcl_file in sorted(jcl_dir.glob("*.jcl")) + sorted(jcl_dir.glob("*.JCL")):
            try:
                text = jcl_file.read_text(errors="replace").splitlines()
                _, ir = parser.parse_lines(text, str(jcl_file.relative_to(ROOT)))
                trace = _simulate_jcl_trace(jcl_file, ir)
                if trace:
                    name = f"{jcl_file.stem.upper()}_jclsim"
                    path = _write_trace(name, trace)
                    print(f"  EXECUTION_SIMULATED trace: {path.name}")
                    generated.append({
                        "file": path.name,
                        "source_type": "EXECUTION_SIMULATED",
                        "program": jcl_file.stem.upper(),
                    })
            except Exception as exc:
                print(f"  WARNING: Could not process {jcl_file.name}: {exc}")

    # --- Write manifest ---
    manifest = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "gnucobol_available": GNUCOBOL_AVAILABLE,
        "gnucobol_version": GNUCOBOL_VERSION,
        "n_traces": len(generated),
        "traces": generated,
    }
    manifest_path = TRACES_DIR / "manifest_execution.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nGenerated {len(generated)} traces → {TRACES_DIR}/")
    print(f"Manifest: {manifest_path.name}")


if __name__ == "__main__":
    main()
