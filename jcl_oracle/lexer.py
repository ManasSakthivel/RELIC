"""
JCL lexer: physical lines -> logical statements.

Implements the statement-format rules of the IBM z/OS MVS JCL Reference:

* columns 1-71 hold the statement; column 72 is a continuation indicator for
  comments; columns 73-80 are sequence numbers and are ignored;
* ``//*`` is a comment statement; ``/*`` is a delimiter (or JES2 control
  statement); ``//`` followed only by blanks is a null statement;
* the name field starts in column 3; the operation follows one or more blanks;
* an operand field that ends with a comma is continued on the next
  ``//`` line, where the continuation may start anywhere in columns 4-16;
* ``DD *`` / ``DD DATA`` start in-stream data, terminated by ``/*``
  (or the DLM= delimiter); ``DD *`` data is also ended by any ``//`` line;
* an IF statement's expression runs until the ``THEN`` keyword.

Each Statement keeps the physical line numbers it spans so that the mutation
generator can edit and move text precisely.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

STMT_COLS = 71
DATA_COLS = 72

_NAME_RE = re.compile(r"^[A-Z@#$][A-Z0-9@#$]{0,7}(\.[A-Z@#$][A-Z0-9@#$]{0,7})?$", re.I)


@dataclass
class Statement:
    """One logical JCL statement (possibly spanning several physical lines)."""

    kind: str                  # STMT, COMMENT, DELIM, NULL, DATA, OTHER
    name: str = ""             # name field (may be "" or "stepname.ddname")
    op: str = ""               # operation (JOB, EXEC, DD, IF, ...)
    operands: str = ""         # operand field (continuations merged)
    first_line: int = 0        # 0-based index of first physical line
    last_line: int = 0         # 0-based index of last physical line (inclusive)
    data: list[str] = field(default_factory=list)   # in-stream data lines (DD * / DATA)
    data_last_line: int = -1   # last physical line of in-stream data (incl. delimiter)

    @property
    def end_line(self) -> int:
        """Last physical line belonging to this statement including its data."""
        return max(self.last_line, self.data_last_line)


def _stmt_text(line: str) -> str:
    return line[:STMT_COLS].rstrip()


def _split_fields(body: str) -> tuple[str, str, str]:
    """Split text after '//' into (name, operation, rest)."""
    if not body or body[0] == " ":
        name = ""
        rest = body.lstrip()
    else:
        parts = body.split(None, 1)
        name = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
    parts = rest.split(None, 1)
    op = parts[0].upper() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    return name.upper(), op, rest


def operand_field(rest: str) -> str:
    """Return the operand field: text up to the first blank outside quotes/parens."""
    out = []
    in_quote = False
    depth = 0
    i = 0
    while i < len(rest):
        ch = rest[i]
        if ch == "'":
            if in_quote and i + 1 < len(rest) and rest[i + 1] == "'":
                out.append("''")
                i += 2
                continue
            in_quote = not in_quote
        elif not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            elif ch == " " and depth == 0:
                break
        out.append(ch)
        i += 1
    return "".join(out)


def _instream_kind(operands: str) -> tuple[str | None, str]:
    """Return ('*'|'DATA'|None, delimiter) for a DD operand field."""
    first = operands.split(",", 1)[0].strip().upper()
    m = re.search(r"\bDLM=('?)([^,'\s]{2})\1", operands, re.I)
    dlm = m.group(2) if m else "/*"
    if first == "*":
        return "*", dlm
    if first == "DATA":
        return "DATA", dlm
    return None, dlm


def lex(text: str) -> list[Statement]:
    """Lex JCL source text into logical statements."""
    lines = text.splitlines()
    stmts: list[Statement] = []
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        line = _stmt_text(raw)
        if line.startswith("//*"):
            stmts.append(Statement("COMMENT", first_line=i, last_line=i))
            i += 1
            continue
        if line.startswith("/*") and not line.startswith("//"):
            stmts.append(Statement("DELIM", operands=line, first_line=i, last_line=i))
            i += 1
            continue
        if line.startswith("//") and line[2:].strip() == "":
            stmts.append(Statement("NULL", first_line=i, last_line=i))
            i += 1
            continue
        if not line.startswith("//"):
            # Data without a preceding DD * (system-generated SYSIN) or stray text.
            stmts.append(Statement("DATA", data=[raw[:DATA_COLS].rstrip()],
                                   first_line=i, last_line=i, data_last_line=i))
            i += 1
            continue

        name, op, rest = _split_fields(line[2:])
        start = i
        if op == "IF":
            # Expression runs until THEN; may span lines.
            expr = rest
            while not re.search(r"\bTHEN\b", expr, re.I) and i + 1 < n \
                    and _stmt_text(lines[i + 1]).startswith("//") \
                    and not _stmt_text(lines[i + 1]).startswith("//*"):
                i += 1
                expr += " " + _stmt_text(lines[i])[2:].strip()
            m = re.search(r"\bTHEN\b", expr, re.I)
            expr = expr[: m.start()] if m else expr
            stmts.append(Statement("STMT", name=name, op="IF", operands=expr.strip(),
                                   first_line=start, last_line=i))
            i += 1
            continue

        operands = operand_field(rest)
        # Continuation: operand field ends with a comma.
        while operands.endswith(",") and i + 1 < n:
            nxt = _stmt_text(lines[i + 1])
            if nxt.startswith("//*"):
                # Comment statements may be interleaved with continuations.
                i += 1
                continue
            if not nxt.startswith("//") or len(nxt) < 3 or nxt[2] != " ":
                break
            body = nxt[2:]
            lead = len(body) - len(body.lstrip())
            # IBM: continued operand starts in column 4-16 (i.e. 1..13 blanks
            # after '//').  We accept deeper indentation too, since many
            # sources use it; the operand field begins at the first non-blank.
            if lead < 1:
                break
            i += 1
            operands += operand_field(body.lstrip())
        st = Statement("STMT", name=name, op=op, operands=operands,
                       first_line=start, last_line=i)
        i += 1

        if op == "DD":
            kind, dlm = _instream_kind(operands)
            if kind is not None:
                data: list[str] = []
                while i < n:
                    dl = lines[i]
                    if dl.startswith(dlm):
                        st.data_last_line = i
                        i += 1
                        break
                    if kind == "*" and dl.startswith("//"):
                        break
                    data.append(dl[:DATA_COLS].rstrip())
                    st.data_last_line = i
                    i += 1
                st.data = data
        stmts.append(st)
    return stmts


# ---------------------------------------------------------------------------
# Operand parsing
# ---------------------------------------------------------------------------

def split_top(s: str, sep: str = ",") -> list[str]:
    """Split on *sep* at parenthesis depth 0 and outside quotes."""
    parts: list[str] = []
    cur: list[str] = []
    depth = 0
    in_quote = False
    for ch in s:
        if ch == "'":
            in_quote = not in_quote
        elif not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == sep and depth == 0:
                parts.append("".join(cur))
                cur = []
                continue
        cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts]


def parse_operands(s: str) -> tuple[list[str], dict[str, str]]:
    """Return (positional operands, keyword operands) with upper-cased keys."""
    positional: list[str] = []
    keywords: dict[str, str] = {}
    if not s.strip():
        return positional, keywords
    for part in split_top(s):
        if not part:
            continue
        m = re.match(r"^([A-Z@#$][A-Z0-9@#$]*(?:\.[A-Z@#$][A-Z0-9@#$]*)?)=(.*)$", part, re.I | re.S)
        if m:
            keywords[m.group(1).upper()] = m.group(2)
        else:
            positional.append(part)
    return positional, keywords


def unparen(s: str) -> str:
    s = s.strip()
    if s.startswith("(") and s.endswith(")"):
        return s[1:-1]
    return s


def is_valid_name(s: str) -> bool:
    return bool(_NAME_RE.match(s))
