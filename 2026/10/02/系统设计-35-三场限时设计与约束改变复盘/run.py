"""Arithmetic/design-review checks, not elapsed interview measurement."""
import json, platform
agenda=[5,8,12,15,5]
assert sum(agenda)==45
cases=[dict(name='shortlink',base_rps=2000,peak_rps=20000,capacity=5000,
 old='database-only',new='cache immutable payload; authoritative revoke'),
 dict(name='dispatch',base_rps=100,peak_rps=1000,capacity=300,
 old='one matcher',new='spatial workers plus per-driver conditional commit'),
 dict(name='tickets',base_rps=500,peak_rps=5000,capacity=800,
 old='direct checkout',new='bounded admission plus database seat constraint')]
for c in cases:
    assert c['base_rps']<c['capacity']<c['peak_rps']
    assert c['peak_rps']==10*c['base_rps']
    c['negative_unchanged_utilization']=c['peak_rps']/c['capacity']
    c['assumed_old_slo_still_valid']=False
print(json.dumps(dict(python=platform.python_version(),agenda_minutes=agenda,
 actual_45min_sessions_performed=False,cases=cases,pass_checks=True),indent=2))
