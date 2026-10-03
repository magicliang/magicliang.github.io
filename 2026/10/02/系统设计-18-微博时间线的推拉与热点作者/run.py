"""Fixed social graph: equal posts/reads, operation counts, not a throughput benchmark."""
import json
import sys


def run(strategy):
    follows={u:{'normal','star'} if u<10 else {'star'} for u in range(1000)}
    posts=[('normal',2,'n2'),('star',1,'s1'),('normal',3,'n3'),('star',4,'s4')]
    inbox={u:[] for u in follows}
    write_copies=read_candidates=0
    for author,seq,key in posts:
        if strategy=='push' or (strategy=='hybrid' and author=='normal'):
            for user,authors in follows.items():
                if author in authors:
                    inbox[user].append((seq,key));write_copies+=1
    result={}
    for user in [0,1,15,30,900]:
        candidates=list(inbox[user])
        read_candidates+=len(candidates)
        for author,seq,key in posts:
            if author in follows[user] and (strategy=='pull' or (strategy=='hybrid' and author=='star')):
                candidates.append((seq,key));read_candidates+=1
        result[user]=sorted(set(candidates),reverse=True)
    return dict(write_copies=write_copies,read_candidates=read_candidates,feeds=result)


if __name__=='__main__':
    values={strategy:run(strategy) for strategy in ['push','pull','hybrid']}
    assert values['push']['feeds']==values['pull']['feeds']==values['hybrid']['feeds']
    assert [values[s]['write_copies'] for s in values]==[2020,0,20]
    first=values['hybrid']['feeds'][0][:2]
    cursor=first[-1]
    next_page=[x for x in values['hybrid']['feeds'][0] if x<cursor][:2]
    assert not set(first)&set(next_page)
    print(json.dumps(dict(comparison=values,first_page=first,next_page=next_page)))
    if '--unsafe' in sys.argv:
        if values['push']['write_copies']>100:
            print('EXPECTED_REJECTION: universal push exceeds fixed write-copy budget 100')
            sys.exit(2)
    print('PASS: same workload yields equal feeds; fanout cost differs and cursor does not repeat')
