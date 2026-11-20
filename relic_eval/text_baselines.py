"""
Transparent text baselines for RELIC evaluation (RELIC final sprint, Agent 4).

Every baseline has ``.name`` and ``.predict(original, mutated, path) -> Prediction``
(same contract as ``relic_eval.detectors``) and sees ONLY the two texts and the
path - never an operator, a label or an oracle verdict.

Baselines
---------
raw_text                         any byte-level difference at all
textdiff                         EXISTING detector (relic_eval.detectors.TextDiffDetector),
                                 any change outside comment statements - reused, not copied
textdiff_ignore_job_parameters   EXISTING trivial reference (relic_eval.v2_eval),
                                 textdiff that also ignores JOB-statement parameters - reused
normalized_text_A                documented normalisation pipeline, NO operand reordering
normalized_text_B                version A + keyword-operand sorting

The normalisation pipeline is a list of explicit, individually switchable rules
(``RULES``, ``RULE_DOCS``).  Each rule documents its rationale, the fields it
excludes from comparison, and the semantic loss it can introduce.  The rule set is
FROZEN before any JCL-SemBench case is read (results/sembench/BASELINE_FREEZE.json
holds the rule list and the SHA-256 of this file).

Structural model (used by every rule; it is infrastructure, not a rule)
-----------------------------------------------------------------------
* A *statement* starts with ``//`` (not ``//*``) or ``/*``.  ``//*`` is a comment.
* Structure is decided on columns 1-71 only (columns 73-80 are sequence numbers;
  column 72 is the continuation column).
* A statement is *continued* when its operand field ends with a comma, or when a
  quoted string is open at column 71 and column 72 is non-blank.  Comment lines
  between continuation lines belong to the continued statement.
* In-stream data follows a ``DD *`` / ``DD DATA`` statement and ends at the
  delimiter (``/*`` or ``DLM=xx``), or - for ``DD *`` only - at any ``//`` line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from relic_eval.detectors import Prediction, TextDiffDetector
from relic_eval.v2_eval import TextDiffIgnoreJobCard

STMT_COLS = 71          # JCL statement text ends in column 71

# ---------------------------------------------------------------------------
# rule registry
# ---------------------------------------------------------------------------

RULES: tuple[str, ...] = (
    "preserve_instream_data",
    "strip_comment_lines",
    "drop_blank_lines",
    "truncate_col71",
    "rstrip_whitespace",
    "join_continuations",
    "strip_trailing_comment_field",
    "collapse_whitespace",
    "uppercase_outside_quotes",
    "ignore_job_parameters",
)
OPTIONAL_RULES: tuple[str, ...] = ("sort_keyword_operands",)   # on in version B only
DEFAULT_RULES: frozenset[str] = frozenset(RULES)

RULE_DOCS: dict[str, dict[str, str]] = {
    "preserve_instream_data": {
        "rationale": "Data between 'DD *'/'DD DATA' and its delimiter is program input, "
                     "not JCL: it must not be re-formatted by any other rule. When ON, data "
                     "lines are compared byte-for-byte; when OFF they are treated like "
                     "ordinary text lines (and so subject to whitespace/case rules).",
        "excluded": "nothing is excluded; this rule PROTECTS in-stream data from the rules below",
        "limitation": "Data-region detection is heuristic (DD * / DD DATA, DLM=xx, '//' ends "
                      "DD * data). Mis-detection (e.g. PROC-internal SYSIN, symbolic-driven DD) "
                      "makes the rule protect the wrong lines or normalise real data.",
    },
    "strip_comment_lines": {
        "rationale": "'//*' statements are ignored by the system; changing them cannot change "
                     "behaviour.",
        "excluded": "whole comment statements (outside in-stream data)",
        "limitation": "Comments may carry out-of-band meaning (operator instructions, "
                      "scheduler directives embedded as comments, '//*%OPC' style control "
                      "comments); such changes ARE behavioural for those tools.",
    },
    "drop_blank_lines": {
        "rationale": "Empty lines outside in-stream data carry no JCL content.",
        "excluded": "empty / blank-only lines outside in-stream data",
        "limitation": "z/OS treatment of a blank record is not asserted here; a blank record "
                      "can be an error or terminate the job stream in some contexts.",
    },
    "truncate_col71": {
        "rationale": "Columns 73-80 are sequence numbers and column 72 is the continuation "
                     "column; the system does not use text beyond column 71 as statement text.",
        "excluded": "columns 72-80 of statement lines (outside in-stream data)",
        "limitation": "Column 72 of a continued quoted string is semantically a continuation "
                      "flag; it is consulted by the (always-on) structure detector only. "
                      "Source lines >80 columns or in non-fixed-record files lose real text.",
    },
    "rstrip_whitespace": {
        "rationale": "Trailing blanks on a record are not significant in JCL statements.",
        "excluded": "trailing whitespace of non-data lines",
        "limitation": "Inside a quoted string continued at column 71 trailing blanks ARE "
                      "significant; they are kept only when join_continuations handles that "
                      "case.",
    },
    "join_continuations": {
        "rationale": "Re-flowing a statement over different physical lines (or splitting a "
                     "long operand field differently) does not change the logical statement.",
        "excluded": "line-break positions within a logical statement (and the '//' + blank "
                    "prefix of continuation lines)",
        "limitation": "Continuation detection is textual; a comma that ends a comment field or "
                      "a statement with no operand field but trailing text is mis-read. "
                      "strip_trailing_comment_field and sort_keyword_operands need this rule "
                      "(they are no-ops without it).",
    },
    "strip_trailing_comment_field": {
        "rationale": "Text after the operand field of a logical statement (separated by "
                     "blanks) is the JCL comment field and has no effect.",
        "excluded": "the comment field after the operand field (not for IF/ELSE/ENDIF/SET, "
                    "whose operands may contain blanks)",
        "limitation": "Re-serialises the kept fields with single blanks (so it also hides "
                      "blank-count differences even if collapse_whitespace is off). "
                      "A statement without operands but with trailing text, or an operand "
                      "containing an unquoted blank (e.g. arithmetic in SET, IF expressions in "
                      "continued form), is mis-split; the exemption list is explicit and "
                      "incomplete.",
    },
    "collapse_whitespace": {
        "rationale": "Runs of blanks between fields are not significant (fields are blank "
                     "delimited).",
        "excluded": "number/amount of blanks between fields and around the statement",
        "limitation": "Blank-vs-nonblank in column 3 (name present or not) is preserved as a "
                      "single blank after '//'; blanks INSIDE quotes are never collapsed. "
                      "Wrong for in-stream data (hence preserve_instream_data).",
    },
    "uppercase_outside_quotes": {
        "rationale": "JCL keywords, ddnames and stepnames are upper-case by convention and "
                     "lower case in them is not distinguished by writers reformatting code.",
        "excluded": "letter case of all text outside apostrophes in statements",
        "limitation": "Real semantic loss for case-sensitive content that is not quoted "
                      "(z/OS UNIX paths in PATH= are quoted by rule, but unquoted symbolic or "
                      "member names in some dialects are case-significant); wrong for "
                      "in-stream data (hence preserve_instream_data).",
    },
    "ignore_job_parameters": {
        "rationale": "A JOB statement's name identifies the job; its parameters (CLASS, "
                     "MSGCLASS, NOTIFY, accounting ...) are largely scheduling/reporting "
                     "attributes. Mirrors the pre-existing trivial reference "
                     "textdiff_ignore_job_parameters.",
        "excluded": "operand field and continuations of every JOB statement "
                    "(name and existence kept)",
        "limitation": "REAL semantic loss: JOB parameters such as COND=, TYPRUN=HOLD/SCAN, "
                      "REGION=, TIME=, RESTART= and CLASS can change whether/how the job "
                      "runs. A genuine behavioural change confined to JOB parameters becomes "
                      "invisible.",
    },
    "sort_keyword_operands": {
        "rationale": "VERSION B ONLY. Keyword operands of EXEC/DD/PROC/OUTPUT may be coded in "
                     "any order; sorting them makes pure operand reordering invisible.",
        "excluded": "order of top-level KEY=VALUE operands after the positional prefix "
                    "(sub-parameters inside parentheses are never reordered)",
        "limitation": "Changes positional meaning if a positional operand follows a keyword "
                      "(then the statement is left unsorted, by design). Order IS significant "
                      "inside parenthesised sub-parameter lists (not touched) and for duplicate "
                      "keywords (invalid JCL). Requires join_continuations; skips JOB/IF/SET.",
    },
}

assert set(RULE_DOCS) == set(RULES) | set(OPTIONAL_RULES)


# ---------------------------------------------------------------------------
# quote-aware text helpers (each also used by exactly one rule)
# ---------------------------------------------------------------------------

def _split_outside_quotes(text: str, seps: str) -> list[str]:
    """Split on any char in ``seps`` that is outside apostrophes and top-level
    (parenthesis depth 0 when ``seps`` contains ','; blanks are split at any depth
    only when not ','). Separators are dropped; empty pieces are kept for ','."""
    out: list[str] = []
    cur: list[str] = []
    in_q = False
    depth = 0
    for ch in text:
        if ch == "'":
            in_q = not in_q
        elif not in_q:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            if ch in seps and (depth == 0 or "," not in seps):
                out.append("".join(cur))
                cur = []
                continue
        cur.append(ch)
    out.append("".join(cur))
    return out


def _tokens(core: str) -> list[str]:
    """Blank-delimited, quote-aware tokens of a statement body (after '//')."""
    return [t for t in _split_outside_quotes(core, " \t") if t != ""]


def _quote_open(text: str) -> bool:
    return text.count("'") % 2 == 1


def rule_collapse_whitespace(text: str) -> str:
    """collapse_whitespace: runs of blanks outside quotes -> one blank; trim ends."""
    out: list[str] = []
    in_q = False
    prev_blank = False
    for ch in text:
        if ch == "'":
            in_q = not in_q
        if not in_q and ch in " \t":
            if not prev_blank:
                out.append(" ")
            prev_blank = True
            continue
        prev_blank = False
        out.append(ch)
    return "".join(out).strip()


def rule_uppercase_outside_quotes(text: str) -> str:
    """uppercase_outside_quotes: upper-case everything outside apostrophes."""
    out: list[str] = []
    in_q = False
    for ch in text:
        if ch == "'":
            in_q = not in_q
            out.append(ch)
        else:
            out.append(ch if in_q else ch.upper())
    return "".join(out)


def rule_strip_trailing_comment_field(text: str) -> str:
    """strip_trailing_comment_field: keep ``[name] op operands`` of a (joined,
    collapsed-or-not) statement, drop everything after the operand field."""
    if text.startswith("/*"):
        return text
    body = text[2:]
    named = not body[:1].isspace() and body != ""
    toks = _tokens(body)
    op_i = 1 if named else 0
    if len(toks) <= op_i or toks[op_i].upper() in _NO_COMMENT_STRIP:
        return text
    keep = toks[: op_i + 2]                       # name?, op, operands
    return "//" + (" " if not named else "") + " ".join(keep)


_NO_COMMENT_STRIP = {"IF", "ELSE", "ENDIF", "SET", "JOB"}
_SORTABLE_OPS = {"EXEC", "DD", "PROC", "OUTPUT"}


def rule_sort_keyword_operands(text: str) -> str:
    """sort_keyword_operands (version B): sort top-level KEY=VALUE operands after
    the positional prefix; leave the statement alone if a positional operand
    follows a keyword or the operand list is incomplete."""
    if text.startswith("/*"):
        return text
    body = text[2:]
    named = not body[:1].isspace() and body != ""
    toks = _tokens(body)
    op_i = 1 if named else 0
    if len(toks) <= op_i + 1 or toks[op_i].upper() not in _SORTABLE_OPS:
        return text
    operands = toks[op_i + 1]
    pieces = _split_outside_quotes(operands, ",")
    if len(pieces) < 2 or any(p == "" for p in pieces):
        return text
    is_kw = ["=" in _split_outside_quotes(p, "(")[0] and not p.startswith("'") for p in pieces]
    first_kw = next((i for i, k in enumerate(is_kw) if k), None)
    if first_kw is None or not all(is_kw[first_kw:]):
        return text
    kws = sorted(pieces[first_kw:], key=lambda p: (p.split("=", 1)[0].upper(), p))
    new_operands = ",".join(pieces[:first_kw] + kws)
    rebuilt = toks[: op_i + 1] + [new_operands] + toks[op_i + 2:]
    return "//" + (" " if not named else "") + " ".join(rebuilt)


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------

@dataclass
class _Rec:
    kind: str                                   # STMT, COMMENT, DATA, BLANK, OTHER
    lines: list[str]                            # physical lines (STMT: >=1)
    inner_comments: list[str] = field(default_factory=list)
    op: str = ""
    name: str = ""
    logical: str = ""                           # STMT: joined columns 1-71 text
    quoted: list[bool] = field(default_factory=list)   # quoted[k]: line k+1 continues a quoted string


def _core(line: str) -> str:
    return line[:STMT_COLS]


def _is_stmt_start(line: str) -> bool:
    return (line.startswith("//") and not line.startswith("//*")) or line.startswith("/*")


def _quoted_continuation(line: str, acc: str) -> bool:
    """A quoted string is open at column 71 and column 72 is non-blank."""
    return len(line) > STMT_COLS and line[STMT_COLS].strip() != "" and _quote_open(acc)


def _append(acc: str, line: str, quoted: bool, cut) -> str:
    """Append continuation ``line`` to ``acc`` (quoted strings resume in column 16)."""
    body = cut(line)
    return acc + body[15:] if quoted else acc.rstrip() + body[2:].lstrip()


def _continues(last: str, acc: str, is_first: bool) -> tuple[bool, bool]:
    """(continues, quoted) - does the statement continue after physical line ``last``?"""
    if last.startswith("/*"):
        return False, False
    if _quoted_continuation(last, acc):
        return True, True
    c = _core(last).rstrip()
    if not c.endswith(","):
        return False, False
    toks = _tokens(c[2:])
    named = not c[2:3].isspace()
    # only the operand field may end the line with a comma (else it is comment text)
    limit = (3 if named else 2) if is_first else 1
    return len(toks) <= limit, False


def _op_name(logical: str) -> tuple[str, str]:
    if logical.startswith("/*"):
        return "", ""
    body = logical[2:]
    toks = _tokens(body)
    if not toks:
        return "", ""
    if body[:1].isspace():
        return toks[0].upper(), ""
    return (toks[1].upper() if len(toks) > 1 else ""), toks[0]


def _dd_data(logical: str) -> tuple[bool, str | None, bool]:
    """(is_instream, custom_delimiter, ends_at_slashslash) for a statement."""
    op, _ = _op_name(logical)
    if op != "DD":
        return False, None, False
    toks = _tokens(logical[2:])
    oi = 1 if logical[2:3].isspace() else 2
    if len(toks) <= oi:
        return False, None, False
    operands = _split_outside_quotes(toks[oi], ",")
    head = operands[0].upper()
    if head not in ("*", "DATA"):
        return False, None, False
    dlm = None
    for p in operands[1:]:
        if p.upper().startswith("DLM="):
            dlm = p[4:].strip("'")[:2] or None
    return True, dlm, head == "*"


def _structure(text: str, preserve_data: bool) -> list[_Rec]:
    lines = text.splitlines()
    recs: list[_Rec] = []
    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i]
        if ln.startswith("//*"):
            recs.append(_Rec("COMMENT", [ln]))
            i += 1
        elif _is_stmt_start(ln):
            group = [ln]
            comments: list[str] = []
            quoted: list[bool] = []
            acc = _core(ln)
            j = i + 1
            while j <= n and ln.startswith("//"):
                cont, q = _continues(group[-1], acc, len(group) == 1)
                if not cont:
                    break
                # next statement line (comment lines in between belong to this statement)
                while j < n and lines[j].startswith("//*"):
                    comments.append(lines[j])
                    j += 1
                if j >= n or not (lines[j].startswith("//") and lines[j][2:3].isspace()):
                    break
                nxt = lines[j]
                acc = _append(acc, nxt, q, _core)
                quoted.append(q)
                group.append(nxt)
                j += 1
            op, name = _op_name(acc)
            recs.append(_Rec("STMT", group, comments, op, name, acc, quoted))
            i = j
            if preserve_data:
                is_data, dlm, slash_ends = _dd_data(acc)
                if is_data:
                    while i < n:
                        d = lines[i]
                        if dlm is not None and d.startswith(dlm):
                            break
                        if dlm is None and (d.startswith("/*") or (slash_ends and d.startswith("//"))):
                            break
                        recs.append(_Rec("DATA", [d]))
                        i += 1
        elif ln.strip() == "":
            recs.append(_Rec("BLANK", [ln]))
            i += 1
        else:
            recs.append(_Rec("OTHER", [ln]))
            i += 1
    return recs


# ---------------------------------------------------------------------------
# pipeline
# ---------------------------------------------------------------------------

def _render_stmt(rec: _Rec, rules: frozenset[str], sort_operands: bool) -> list[str]:
    cut = _core if "truncate_col71" in rules else (lambda x: x)
    lines = [cut(x) for x in rec.lines]
    if "join_continuations" in rules:
        text = lines[0]
        for k, ln in enumerate(lines[1:]):
            text = _append(text, ln, rec.quoted[k], lambda x: x)
        lines = [text]
        if "strip_trailing_comment_field" in rules:
            lines = [rule_strip_trailing_comment_field(lines[0])]
        if sort_operands:
            lines = [rule_sort_keyword_operands(lines[0])]
    if "rstrip_whitespace" in rules:
        lines = [x.rstrip() for x in lines]
    if "collapse_whitespace" in rules:
        lines = [rule_collapse_whitespace(x) for x in lines]
    if "uppercase_outside_quotes" in rules:
        lines = [rule_uppercase_outside_quotes(x) for x in lines]
    return lines


def normalize(text: str, rules: frozenset[str] | set[str] = DEFAULT_RULES,
              sort_operands: bool = False) -> list[str]:
    """Apply the enabled rules; return the normalised line list (comparison key)."""
    rules = frozenset(rules)
    unknown = rules - set(RULES)
    if unknown:
        raise ValueError(f"unknown rules: {sorted(unknown)}")
    out: list[str] = []
    for rec in _structure(text, "preserve_instream_data" in rules):
        if rec.kind == "COMMENT":
            if "strip_comment_lines" not in rules:
                out.extend(_render_other(rec.lines, rules))
        elif rec.kind == "BLANK":
            if "drop_blank_lines" not in rules:
                out.extend(_render_other(rec.lines, rules))
        elif rec.kind == "DATA":
            out.extend(rec.lines)                   # verbatim
        elif rec.kind == "OTHER":
            out.extend(_render_other(rec.lines, rules))
        else:  # STMT
            if "ignore_job_parameters" in rules and rec.op == "JOB":
                head = f"//{rec.name} JOB"
                out.append(rule_uppercase_outside_quotes(head)
                           if "uppercase_outside_quotes" in rules else head)
            else:
                out.extend(_render_stmt(rec, rules, sort_operands))
            if "strip_comment_lines" not in rules:
                out.extend(_render_other(rec.inner_comments, rules))
    return out


def _render_other(lines: list[str], rules: frozenset[str]) -> list[str]:
    res = list(lines)
    if "truncate_col71" in rules:
        res = [x[:STMT_COLS] if x.startswith("//") else x for x in res]
    if "rstrip_whitespace" in rules:
        res = [x.rstrip() for x in res]
    if "collapse_whitespace" in rules:
        res = [rule_collapse_whitespace(x) for x in res]
    if "uppercase_outside_quotes" in rules:
        res = [rule_uppercase_outside_quotes(x) for x in res]
    return res


# ---------------------------------------------------------------------------
# detectors
# ---------------------------------------------------------------------------

class RawTextDetector:
    """Flags ANY difference between the two texts (no normalisation at all)."""
    name = "raw_text"

    def predict(self, original: str, mutated: str, path: str) -> Prediction:
        return Prediction(original != mutated)


class NormalizedTextDetector:
    """Flags a difference between the normalised line lists.

    ``sort_operands=False`` -> version A; ``True`` -> version B (adds
    sort_keyword_operands). ``rules`` is switchable for ablations.
    """

    def __init__(self, sort_operands: bool = False,
                 rules: frozenset[str] | set[str] | None = None, name: str | None = None) -> None:
        self.sort_operands = sort_operands
        self.rules = DEFAULT_RULES if rules is None else frozenset(rules)
        self.name = name or ("normalized_text_B" if sort_operands else "normalized_text_A")

    def predict(self, original: str, mutated: str, path: str) -> Prediction:
        try:
            a = normalize(original, self.rules, self.sort_operands)
            b = normalize(mutated, self.rules, self.sort_operands)
        except Exception as exc:   # visible, never silently negative
            return Prediction(None, "ERROR", {"error": repr(exc)[:300]})
        return Prediction(a != b)


def all_text_baselines() -> list:
    return [RawTextDetector(), TextDiffDetector(), TextDiffIgnoreJobCard(),
            NormalizedTextDetector(False), NormalizedTextDetector(True)]


def frozen_rule_spec() -> dict:
    """Machine-readable rule list written to BASELINE_FREEZE.json."""
    return {
        "rules_in_application_order": list(RULES),
        "optional_rules_version_B_only": list(OPTIONAL_RULES),
        "version_A_rules": list(RULES),
        "version_B_rules": list(RULES) + list(OPTIONAL_RULES),
        "statement_columns": STMT_COLS,
        "rule_docs": RULE_DOCS,
    }
