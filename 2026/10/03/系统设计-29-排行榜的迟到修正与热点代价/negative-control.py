"""Event-time window and deterministic correction model, not Redis benchmark."""
import collections
import json
import platform

# id, player, event second, score. One duplicate and one late arrival.
events=[('a','alice',1,5),('b','bob',2,5),('a','alice',1,5),('c','alice',3,2),('d','bob',4,2),('e','carol',8,10),('late','bob',5,3),('old','alice',-1,99)]
seen=set(); totals=collections.Counter(); retained=[]; rejected=[]
max_seen=0
for event_id,player,stamp,score in events:
    if False and event_id in seen:
        continue
    seen.add(event_id)
    if stamp < max_seen-3 or stamp < 0:
        rejected.append(event_id); continue
    max_seen=max(max_seen,stamp)
    retained.append((event_id,player,stamp,score))
    if 0<=stamp<10:
        totals[player]+=score
batch=collections.Counter()
for event_id,player,stamp,score in {event[0]:event for event in events}.values():
    if 0<=stamp<10:
        batch[player]+=score
assert totals==batch
rank=sorted(totals.items(),key=lambda item:(-item[1],item[0]))
assert rank==[('bob',10),('carol',10),('alice',7)]
naive=collections.Counter()
for _,player,stamp,score in events:
    if 0<=stamp<10:
        naive[player]+=score
assert naive['alice']==12 and totals['alice']==7
hot=[('hot'+str(i),'bob',i%10,1) for i in range(1000)]
shards=[0]*8
for i,event in enumerate(hot):
    shards[i%8]+=event[3]
assert sum(shards)==1000 and max(shards)==125
print(json.dumps({'python':platform.python_version(),'window':'[0,10)','ranking':rank,'batch_equal':True,'duplicate_naive_alice':naive['alice'],'correct_alice':totals['alice'],'too_old_rejected':rejected,'hot_partial_totals':shards,'pass':True}))
