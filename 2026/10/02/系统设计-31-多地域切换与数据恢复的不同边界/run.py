"""Deterministic regional timeline; no network or replicated database."""
import json, platform

def run(fenced):
    primary = [(t, f'w{t}') for t in range(1, 101)]
    backup = primary[:95]
    failure, detect, isolate, promote, verify = 100, 10, 5, 12, 8
    epoch, stale_epoch = 2, 1
    accepted_stale = (not fenced) or stale_epoch == epoch
    new = {'account': 'new-region-value'}
    if accepted_stale:
        new['account'] = 'stale-region-value'
    return dict(lost_ids=[x[1] for x in primary if x not in backup],
                rpo_seconds=failure-backup[-1][0],
                rto_seconds=detect+isolate+promote+verify,
                old_writer_rejected=not accepted_stale, value=new['account'])

safe, unsafe = run(True), run(False)
assert safe['rpo_seconds'] == 5 and len(safe['lost_ids']) == 5
assert safe['rto_seconds'] == 35 and safe['old_writer_rejected']
assert unsafe['value'] != safe['value']
assert 800 * 400 * 5 == 1600000
print(json.dumps(dict(python=platform.python_version(), model='integer-time asynchronous replication',
 safe=safe, negative_unfenced=unsafe, gap_bytes=1600000, pass_checks=True),ensure_ascii=False,indent=2))
