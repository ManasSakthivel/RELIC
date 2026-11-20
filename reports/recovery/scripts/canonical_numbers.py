"""Single source of numbers for the recovery sprint.

Reads only committed prediction/case files; writes reports/recovery/CANONICAL_NUMBERS.json.
Predictions are binary (no scores), so each detector has exactly one operating point.
Run from repo root: python reports/recovery/scripts/canonical_numbers.py
"""
import json, math, collections

def jl(p): return [json.loads(l) for l in open(p)]

def cm(rows, det):
    tp=fp=fn=tn=0
    for r in rows:
        p=r["pred"][det]; t=bool(r["truth"])
        if t and p: tp+=1
        elif t: fn+=1
        elif p: fp+=1
        else: tn+=1
    d=(tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)
    mcc=(tp*tn-fp*fn)/math.sqrt(d) if d else None
    f1=2*tp/(2*tp+fp+fn) if (2*tp+fp+fn) else None
    return dict(tp=tp,fp=fp,fn=fn,tn=tn,n=len(rows),
        precision=tp/(tp+fp) if tp+fp else None, recall=tp/(tp+fn) if tp+fn else None,
        specificity=tn/(tn+fp) if tn+fp else None, f1=f1, mcc=mcc)

def overlap(rows, a, b):
    o={}
    for truth in (True, False):
        c=collections.Counter()
        for r in rows:
            if bool(r["truth"])!=truth: continue
            c[("A" if r["pred"][a] else "-")+("B" if r["pred"][b] else "-")]+=1
        o["truth_"+("positive" if truth else "negative")]=dict(
            both=c["AB"], only_A=c["A-"], only_B=c["-B"], neither=c["--"])
    return dict(A=a, B=b, **o)

out={"note":"Predictions are binary; no score/confidence exists, so no PR curve is computable."}

# ---- SemBench
cases={c["id"]:c for c in jl("benchmarks/sembench/cases.jsonl")}
sb=jl("results/sembench/predictions.jsonl")
for r in sb:
    c=cases[r["id"]]
    r["identical"]=c["original_sha256"]==c["transformed_sha256"]
    r["disagrees"]=c["oracle_agrees_with_expected"] is False
    r["abstains"]=c["validation_status"]=="ORACLE_ABSTAINS"
ident=[r["id"] for r in sb if r["identical"]]
disagree=[r["id"] for r in sb if r["disagrees"]]
noop_changing=[r["id"] for r in sb if r["identical"] and r["truth"]]
core=[r for r in sb if not r["identical"] and not r["disagrees"] and not r["abstains"]]
pops={
  "ALL_180": sb,
  "EXCL_25_IDENTICAL": [r for r in sb if not r["identical"]],
  "EXCL_15_NOOP_CHANGING_ONLY": [r for r in sb if r["id"] not in noop_changing],
  "CLEAN_CORE_(no identical, no disagree, no abstain)": core,
}
dets=sorted(sb[0]["pred"].keys())
out["sembench"]={
  "identical_pair_ids":ident,"n_identical":len(ident),
  "identical_by_truth":dict(collections.Counter(bool(r["truth"]) for r in sb if r["identical"])),
  "oracle_disagree_ids_all":disagree,"n_disagree_all":len(disagree),
  "oracle_disagree_non_identical_ids":[i for i in disagree if i not in ident],
  "n_disagree_non_identical":len([i for i in disagree if i not in ident]),
  "abstain_ids":[r["id"] for r in sb if r["abstains"]],
  "populations":{},
}
for name,rows in pops.items():
    out["sembench"]["populations"][name]={
      "n":len(rows),"n_changing":sum(bool(r["truth"]) for r in rows),
      "detectors":{d:cm(rows,d) for d in dets},
      "overlap_relic_v2_vs_normalized_text_B":overlap(rows,"relic_v2","normalized_text_B"),
      "overlap_relic_v2_vs_normalized_text_A":overlap(rows,"relic_v2","normalized_text_A"),
    }
cat=collections.defaultdict(list)
for r in sb: cat[r["category"]].append(r)
out["sembench"]["per_category_ALL_180"]={k:{"n":len(v),"n_changing":sum(bool(x["truth"]) for x in v),
  "relic_v2":cm(v,"relic_v2"),"normalized_text_B":cm(v,"normalized_text_B")} for k,v in sorted(cat.items())}

# ---- External
ex=[r for r in jl("results/external/predictions.jsonl") if r["status"]=="EVALUABLE"]
edets=sorted(ex[0]["pred"].keys())
out["external"]={"n_evaluable":len(ex),"detectors":{d:cm(ex,d) for d in edets},
  "overlap_relic_v2_vs_textdiff":overlap(ex,"relic_v2","textdiff"),
  "overlap_relic_v2_vs_textdiff_ignore_job_parameters":overlap(ex,"relic_v2","textdiff_ignore_job_parameters"),
  "truth_counts":dict(collections.Counter(bool(r["truth"]) for r in ex)),
  "per_repo":{}, "per_operator":{}}
by=collections.defaultdict(list)
for r in ex: by[r["repo"]].append(r)
for k,v in sorted(by.items()):
    out["external"]["per_repo"][k]={"n":len(v),"n_positive":sum(bool(x["truth"]) for x in v),
      "relic_v2":cm(v,"relic_v2"),"textdiff":cm(v,"textdiff"),
      "overlap":overlap(v,"relic_v2","textdiff")}
byo=collections.defaultdict(list)
for r in ex: byo[r["operator"]].append(r)
for k,v in sorted(byo.items()):
    out["external"]["per_operator"][k]={"n":len(v),"n_positive":sum(bool(x["truth"]) for x in v),
      "relic_v2":cm(v,"relic_v2"),"textdiff":cm(v,"textdiff"),"overlap":overlap(v,"relic_v2","textdiff")}

json.dump(out,open("reports/recovery/CANONICAL_NUMBERS.json","w"),indent=1,default=str)
print("ok")
