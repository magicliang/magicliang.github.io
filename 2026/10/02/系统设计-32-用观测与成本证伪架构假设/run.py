"""Fixed request ledger: timeout denominator and sampled-tail counterexample."""
import json, math, platform
rows=[dict(id=i, ms=100 if i<95 else 2000, ok=i<95, correct=i!=12) for i in range(100)]
def p99(xs): return sorted(xs)[math.ceil(len(xs)*.99)-1]
full=p99([r['ms'] for r in rows]); sampled=p99([r['ms'] for r in rows if r['id']%10==0])
errors=sum(not r['ok'] for r in rows)
correctness=sum(not r['correct'] for r in rows)
backlog=[max(0,(120-100)*t) for t in range(61)]
cost=10000000*400*7/1e9*.02
assert (full,sampled,errors,correctness,backlog[-1])==(2000,100,5,1,1200)
assert errors/len(rows)==.05
print(json.dumps(dict(python=platform.python_version(),requests=100,error_rate=.05,
 correctness_violations=correctness,full_p99_ms=full,negative_sampled_p99_ms=sampled,
 backlog_after_60s=backlog[-1],raw_log_GB=28,storage_cost_units=cost,pass_checks=True),indent=2))
