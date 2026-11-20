"""Error-analysis trace for relic_v2 FN/FP on SemBench. Read-only. Run: PYTHONPATH=src:. python this.py"""
import json, difflib, sys, time
sys.path.insert(0, '.')
from relic_eval.detectors import _bcg, RelicDetector
r=[json.loads(l) for l in open('results/sembench/predictions.jsonl')]
out=[]
for x in r:
    p=x['pred']['relic_v2']
    if x['truth']==p: continue
    d=f"benchmarks/sembench/cases/{x['id']}/"
    a=open(d+'original.jcl').read(); b=open(d+'transformed.jcl').read()
    b0=_bcg(a,'f.jcl',False,True); b1=_bcg(b,'f.jcl',False,True)
    diff=[l for l in difflib.unified_diff(a.splitlines(),b.splitlines(),lineterm='',n=0) if l[:1] in '+-' and l[:3] not in ('+++','---')]
    ty={}
    for c in b0.contracts.values(): ty[c.contract_type.value]=ty.get(c.contract_type.value,0)+1
    sig=lambda B:{(c.contract_type.value,c.subject_id,c.object_id) for c in B.contracts.values()}
    out.append(dict(id=x['id'],kind='FN' if x['truth'] else 'FP',cat=x['category'],sub=x['subcategory'],identical=a==b,
      types0=ty,sig_equal=sig(b0)==sig(b1),n0=len(b0.contracts),n1=len(b1.contracts),
      has_if=' IF ' in a or '// IF' in a,has_proc='PROC' in a.upper().replace('PROCESSED',''),gdg='(+1)' in a or '(0)' in a or '(-1)' in a,diff=diff[:8]))
json.dump(out,open('<SCRATCHPAD>/algo_trace.json','w'),indent=1)
for o in out: print(o['id'],o['kind'],o['sub'],'ident' if o['identical'] else '',o['types0'],'SIGEQ' if o['sig_equal'] else 'sigdiff',o['n0'],o['n1']); [print('     ',l[:110]) for l in o['diff'][:6]]
