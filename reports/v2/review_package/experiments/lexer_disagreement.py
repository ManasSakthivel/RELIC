"""
Read-only experiment: oracle lexer (jcl_oracle.lexer.lex / jcl_oracle.model.build_model)
vs RELIC parser (legacy_contract.parsers.jcl_parser.JCLParser) on the evaluation corpus.

Unit of comparison = one physical-line-anchored JCL statement (JOB/EXEC/DD), keyed by
the first physical line number.  No source file is modified.

Run:  cd RELIC && PYTHONPATH=$PWD/src:$PWD .venv/bin/python reports/v2/review_package/experiments/lexer_disagreement.py
Output: reports/v2/review_package/experiments/lexer_disagreement_results.json  (+ stdout summary)
"""
from __future__ import annotations
import json, re, sys, collections
from pathlib import Path

from jcl_oracle.lexer import lex, parse_operands, unparen, split_top
from jcl_oracle.model import build_model, iter_steps
from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.ir.model import EntityType, RelationType
from relic_eval.subjects import get_subjects

OUT = Path(__file__).with_name("lexer_disagreement_results.json")
MODES = {"relic_v1_0(legacy)": dict(legacy_v1_0=True), "relic_v1_1(default)": dict(),
         "relic_v2(v2_fixes)": dict(v2_fixes=True)}


def oracle_view(text):
    stmts = lex(text)
    view = {}
    for s in stmts:
        if s.kind == "STMT" and s.op in {"JOB", "EXEC", "DD"}:
            pos, kw = parse_operands(s.operands)
            dsn = kw.get("DSN", kw.get("DSNAME"))
            disp = kw.get("DISP")
            status = None
            if dsn is not None:
                parts = split_top(unparen(disp)) if disp is not None else []
                status = (parts[0] or "NEW").upper() if parts else "NEW"   # oracle default: NEW
            view[s.first_line + 1] = dict(op=s.op, name=s.name.upper(), operands=s.operands,
                                          dsn=(dsn.strip().strip("'").upper() if dsn else None),
                                          status=status, span=(s.first_line + 1, s.last_line + 1))
    return view


def relic_view(text, path, **mode):
    p = JCLParser(**mode)
    res, ir = p.parse_lines(text.splitlines(), path)
    view = {}
    for t in res.tokens:
        if t.operation in {"JOB", "EXEC", "DD"}:
            view[t.line_number] = dict(op=t.operation, name=t.name.upper(),
                                       operands=JCLParser._operand_field(t.operands))
    # roles from IR relations, keyed by line
    roles = {}
    for r in ir.relations:
        if r.relation_type in (RelationType.PRODUCES, RelationType.CONSUMES) and r.location:
            roles.setdefault(r.location.line_start, set()).add(
                ("P" if r.relation_type == RelationType.PRODUCES else "C", r.target.name.upper()))
    n_step_entities = sum(1 for e in ir.entities.values() if e.entity_type == EntityType.STEP)
    n_exec_tokens = sum(1 for t in res.tokens if t.operation == "EXEC")
    return view, roles, res, n_step_entities, n_exec_tokens


def oracle_role(status, normal_delete):
    if status is None:
        return None
    if status in {"NEW", "MOD"}:
        return "P"
    return "C"


def main():
    per_mode = {m: collections.Counter() for m in MODES}
    examples = {m: collections.defaultdict(list) for m in MODES}
    file_rows = []
    for subj in get_subjects():
        for f in subj.jcl_files:
            text = f.read_text(errors="replace")
            rel = subj.key + "/" + subj.rel(f)
            ov = oracle_view(text)
            model = build_model(text, subj.proclib)
            o_model_steps = len(model.steps())
            o_top_steps = len({s.top_name or s.name or s.ident for s in model.steps()})
            o_exec = sum(1 for v in ov.values() if v["op"] == "EXEC")
            o_dd = sum(1 for v in ov.values() if v["op"] == "DD")
            o_dsn = {v["dsn"] for v in ov.values() if v["dsn"]}
            row = dict(file=rel, o_exec=o_exec, o_dd=o_dd, o_dsn=len(o_dsn), o_model_steps=o_model_steps)
            for m, kw in MODES.items():
                C = per_mode[m]
                rv, roles, res, n_ent, n_tok = relic_view(text, rel, **kw)
                r_exec = sum(1 for v in rv.values() if v["op"] == "EXEC")
                r_dd = sum(1 for v in rv.values() if v["op"] == "DD")
                # DSN set seen by RELIC (IR dataset entity names via roles)
                r_dsn = {n for rs in roles.values() for (_k, n) in rs}
                o_dsn_u = {d for d in o_dsn}
                C["files"] += 1
                # statement-level anchored comparison
                keys = set(ov) | set(rv)
                only_o = [k for k in keys if k in ov and k not in rv]
                only_r = [k for k in keys if k in rv and k not in ov]
                both = [k for k in keys if k in ov and k in rv]
                C["stmts_total"] += len(keys)
                C["stmts_both"] += len(both)
                C["stmts_only_oracle"] += len(only_o)
                C["stmts_only_relic"] += len(only_r)
                for k in only_o[:3]:
                    examples[m]["only_oracle"].append((rel, k, ov[k]["op"], ov[k]["name"], ov[k]["operands"][:60]))
                for k in only_r[:3]:
                    examples[m]["only_relic"].append((rel, k, rv[k]["op"], rv[k]["name"], rv[k]["operands"][:60]))
                # operand-field agreement on common statements (whitespace/case-insens.)
                for k in both:
                    a = re.sub(r"\s+", "", ov[k]["operands"].upper())
                    b = re.sub(r"\s+", "", rv[k]["operands"].upper())
                    C["operand_cmp"] += 1
                    if a == b:
                        C["operand_equal"] += 1
                    else:
                        if len(examples[m]["operand_diff"]) < 12:
                            examples[m]["operand_diff"].append((rel, k, a[:70], b[:70]))
                    C["opname_cmp"] += 1
                    if ov[k]["name"] == rv[k]["name"] and ov[k]["op"] == rv[k]["op"]:
                        C["opname_equal"] += 1
                # role agreement for DDs with a DSN (oracle sees DSN/DSNAME)
                for k, v in ov.items():
                    if v["op"] == "DD" and v["dsn"] and k in rv:
                        C["dsn_dd_total"] += 1
                        ro = {x for x, _ in roles.get(k, set())}
                        orole = oracle_role(v["status"], False)
                        if not ro:
                            C["role_relic_no_dsn_seen"] += 1       # RELIC saw no dataset on this DD
                            if len(examples[m]["relic_no_dsn"]) < 8:
                                examples[m]["relic_no_dsn"].append((rel, k, v["operands"][:70]))
                        elif ro == {orole}:
                            C["role_agree"] += 1
                        else:
                            C["role_disagree"] += 1
                            if len(examples[m]["role_diff"]) < 10:
                                examples[m]["role_diff"].append((rel, k, v["status"], sorted(ro), v["operands"][:70]))
                        if "DISP=" not in v["operands"].upper():
                            C["dd_dsn_no_disp"] += 1
                # file-level
                C["file_exec_agree"] += int(o_exec == r_exec)
                C["file_dd_agree"] += int(o_dd == r_dd)
                C["file_dsn_set_agree"] += int(o_dsn_u == r_dsn)
                C["file_stmt_set_agree"] += int(not only_o and not only_r)
                C["file_step_entities_eq_exec"] += int(n_ent == o_exec)
                # DSN set diff (case-insens.)
                if o_dsn_u != r_dsn and len(examples[m]["dsn_set_diff"]) < 10:
                    examples[m]["dsn_set_diff"].append((rel, sorted(o_dsn_u - r_dsn)[:3], sorted(r_dsn - o_dsn_u)[:3]))
                if m.startswith("relic_v1_1"):
                    row.update(r_exec=r_exec, r_dd=r_dd, r_dsn=len(r_dsn), r_step_entities=n_ent)
                if m.startswith("relic_v1_0"):
                    row.update(L_stmt_only_oracle=len(only_o), L_stmt_only_relic=len(only_r))
            file_rows.append(row)
    summary = {}
    for m, C in per_mode.items():
        d = dict(C)
        d["stmt_anchor_agreement"] = round(C["stmts_both"] / max(1, C["stmts_total"]), 4)
        d["file_level_exec_count_agreement"] = round(C["file_exec_agree"] / C["files"], 4)
        d["file_level_dd_count_agreement"] = round(C["file_dd_agree"] / C["files"], 4)
        d["file_level_dsn_set_agreement"] = round(C["file_dsn_set_agree"] / C["files"], 4)
        d["file_level_stmt_set_agreement"] = round(C["file_stmt_set_agree"] / C["files"], 4)
        d["operand_field_agreement_on_common_stmts"] = round(C["operand_equal"] / max(1, C["operand_cmp"]), 4)
        d["dd_role_agreement_on_dsn_dds"] = round(C["role_agree"] / max(1, C["dsn_dd_total"]), 4)
        d["step_entities_equal_exec_count_files"] = round(C["file_step_entities_eq_exec"] / C["files"], 4)
        summary[m] = d
    OUT.write_text(json.dumps(dict(summary=summary,
                                   examples={m: dict(e) for m, e in examples.items()},
                                   files=file_rows), indent=1, default=list))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
