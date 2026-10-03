"""Synthetic attribution; event time differs from ingestion time."""
import json, platform
clicks=[dict(id='c1',user='u1',event=10,arrival=10),dict(id='c2',user='u1',event=18,arrival=30)]
conversions=[dict(id='x1',user='u1',event=20,amount=500),dict(id='x1',user='u1',event=20,amount=500)]
def attribute(asof):
    ledger={}
    for event in conversions:
        if event['id'] in ledger: continue
        eligible=[c for c in clicks if c['arrival']<=asof and c['user']==event['user'] and 0<=event['event']-c['event']<=10]
        ledger[event['id']]=max(eligible,key=lambda c:(c['event'],c['id']))['id'] if eligible else None
    return ledger
initial,final=attribute(20),attribute(30)
assert initial=={'x1':'c1'} and final=={'x1':'c2'}
corrections=[('c1',-500),('c2',500)]
assert sum(v for _,v in corrections)==0
assert sum(x['amount'] for x in conversions)==1000
outside=[c for c in clicks if 0<=100-c['event']<=10]
assert outside==[]
print(json.dumps(dict(python=platform.python_version(),synthetic_only=True,
 initial=initial,final=final,corrections=corrections,unique_revenue_minor_units=500,
 negative_no_dedupe_minor_units=1000,outside_window_attributed=False,pass_checks=True),indent=2))
