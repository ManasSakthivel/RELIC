"""
Subject systems used in the evaluation.

Each subject is an independently authored, publicly licensed corpus of z/OS
JCL. Only files that contain at least one JOB statement are evaluation
units; files that only define a PROC form the subject's procedure library.
COBOL sources are indexed by PROGRAM-ID (and file stem) so the oracle can
derive file-access modes of in-house batch programs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from jcl_oracle.lexer import lex
from jcl_oracle.model import ProcLibrary

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Subject:
    key: str
    title: str
    root: Path
    url: str
    license: str
    pinned: str
    role: str                     # "primary" or "secondary"
    notes: str = ""
    exclude: tuple[str, ...] = field(default_factory=tuple)

    # -- files ------------------------------------------------------------

    def _all_files(self, exts: set[str]) -> list[Path]:
        out = []
        for p in sorted(self.root.rglob("*")):
            if p.is_file() and p.suffix.lower() in exts and not any(x in str(p) for x in self.exclude):
                out.append(p)
        return out

    @cached_property
    def jcl_files(self) -> list[Path]:
        """JCL files that contain at least one JOB statement (evaluation units)."""
        units = []
        for p in self._all_files({".jcl"}):
            stmts = lex(p.read_text(errors="replace"))
            if any(s.kind == "STMT" and s.op == "JOB" for s in stmts):
                units.append(p)
        return units

    def rel(self, p: Path) -> str:
        return str(p.relative_to(self.root))

    def artifact_path(self, p: Path) -> str:
        """Stable artifact identifier handed to RELIC (repository-relative)."""
        return str(p.relative_to(ROOT))

    @cached_property
    def proclib(self) -> ProcLibrary:
        texts: dict[str, str] = {}
        for p in self._all_files({".prc", ".proc", ".jcl"}):
            t = p.read_text(errors="replace")
            stmts = lex(t)
            has_job = any(s.kind == "STMT" and s.op == "JOB" for s in stmts)
            has_proc = any(s.kind == "STMT" and s.op == "PROC" for s in stmts)
            if has_proc and not has_job:
                texts[p.stem.upper()] = t
        return ProcLibrary.from_texts(texts)

    @cached_property
    def cobol_sources(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for p in self._all_files({".cbl", ".cob", ".cobol"}):
            t = p.read_text(errors="replace")
            m = re.search(r"PROGRAM-ID\.\s+'?([A-Z0-9@#$-]+)'?", t, re.I)
            if m:
                out.setdefault(m.group(1).upper(), t)
            out.setdefault(p.stem.upper(), t)
        return out


SUBJECTS: dict[str, Subject] = {
    "carddemo": Subject(
        key="carddemo",
        title="AWS CardDemo",
        root=ROOT / "datasets/carddemo/extracted/aws-mainframe-modernization-carddemo-main",
        url="https://github.com/aws-samples/aws-mainframe-modernization-carddemo",
        license="Apache-2.0",
        pinned="archive in datasets/carddemo (see datasets/carddemo/DATASET_VERSION.txt)",
        role="primary",
        notes="Credit-card batch/online demo application built for mainframe-modernization tooling.",
    ),
    "omp_course": Subject(
        key="omp_course",
        title="Open Mainframe Project COBOL Programming Course",
        root=ROOT / "datasets/public_cobol/extracted/cobol-programming-course-master",
        url="https://github.com/openmainframeproject/cobol-programming-course",
        license="CC-BY-4.0 (course material) / Apache-2.0 (repository)",
        pinned="archive in datasets/public_cobol (see datasets/public_cobol/DATASET_VERSION.txt)",
        role="secondary",
        notes="Teaching labs: compile/link/run jobs guarded by IF/THEN, DB2 labs.",
    ),
    "genapp": Subject(
        key="genapp",
        title="IBM CICS General Insurance Application (GenApp)",
        root=ROOT / "datasets/genapp/source",
        url="https://github.com/cicsdev/cics-genapp",
        license="EPL-2.0",
        pinned="f6f3f4b2580d31b7d8dcc31ce3e3676f4cceaaaa",
        role="secondary",
        notes="Installation/build jobs: COBOL compile+link via in-stream PROC, DB2 DDL, CICS/VSAM definitions.",
    ),
}


def get_subjects(keys: list[str] | None = None) -> list[Subject]:
    if not keys:
        return list(SUBJECTS.values())
    return [SUBJECTS[k] for k in keys]
