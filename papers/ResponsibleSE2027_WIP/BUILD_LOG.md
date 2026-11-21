# Build log

Date: 2026-11-21. Working directory: papers/ResponsibleSE2027_WIP.

| Output | Source | Command | Exit | Pages | Overfull boxes | Undefined refs |
|---|---|---|---|---|---|---|
| paper_anonymous.pdf | main_anonymous.tex | tectonic main_anonymous.tex (renamed) | 0 | 4 | 0 | none |
| paper_camera_ready.pdf | main_camera_ready.tex | tectonic main_camera_ready.tex (renamed) | 0 | 4 | 0 | none |

References: references.bib, 14 entries, all cited in both PDFs.

Earlier failures, kept for transparency: (1) an undefined control sequence from \resizebox without graphicx (fixed); (2) an overfull author line in the camera-ready draft (fixed with the IEEE multi-author layout); (3) an earlier build log overstated a stale PDF (corrected; the PDFs above are fresh builds).

Visual rendering (all 4 pages of both PDFs, rendered with pypdfium2 at scale 1.4 and inspected):
- Table I: on page 2 beside its discussion. Readable.
- Table II: moved from page 4 to top of page 3, directly after its introducing paragraph. Changed to a single-column float at footnote size with two rows per label set (MCC, then interval); no resizebox shrink. Verified at 3x zoom: aligned and legible.
- Table III: top of page 4, after the framework paragraph on page 3. Not stranded on a near-empty page, but not directly below its paragraph; the references follow it.
- Camera-ready page 1: author block renders correctly.
Remaining build warnings: underfull boxes only (table p-columns and body text); no overfull boxes after the Table II padding change.
