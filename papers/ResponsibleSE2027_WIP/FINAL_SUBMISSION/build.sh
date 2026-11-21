#!/bin/sh
# Regenerates both PDFs from ResponsibleSE2027_Final_Manuscript.tex (the single source).
set -e
cd "$(dirname "$0")"
python3 - <<'PY'
s = open("ResponsibleSE2027_Final_Manuscript.tex", encoding="utf-8").read()
anon = s.replace(r"\documentclass[conference]{IEEEtran}", r"\documentclass[conference]{IEEEtran}" + "\n\\def\\AnonFlag{1}", 1)
assert anon != s
open("build_anonymous.tex", "w", encoding="utf-8").write(anon)
open("build_author_identified.tex", "w", encoding="utf-8").write(s)
PY
mkdir -p build_logs
tectonic build_anonymous.tex > build_logs/build_anon.txt 2>&1
tectonic build_author_identified.tex > build_logs/build_auth.txt 2>&1
cp build_anonymous.pdf ResponsibleSE2027_Anonymous_Submission.pdf
cp build_author_identified.pdf ResponsibleSE2027_Author_Identified.pdf
echo "built both PDFs"
