"""Cross-module event model; authority checks filter stale projections."""
import json, platform
posts={}; timeline=[]; search={}; notifications=[]; inbox=[]; seen=set()
def publish(key,uploaded):
    if not uploaded: return False
    posts[key]={'version':1,'state':'LIVE'}
    inbox.append(('publish',key,1)); return True
def apply(event):
    kind,key,version=event
    if event in seen: return
    seen.add(event)
    if search.get(key,(-1,''))[0] < version: search[key]=(version,kind)
    if kind=='publish': timeline.append(key); notifications.append(key)
def visible(key): return posts.get(key,{}).get('state')=='LIVE'
assert not publish('orphan',False)
assert publish('p1',True)
apply(inbox[0]); apply(inbox[0]); assert len(timeline)==1
posts['p1']={'version':2,'state':'DELETED'}
inbox.append(('delete','p1',2))
backlog_before_drain=len(inbox)-1
negative_without_filter=list(timeline)
assert negative_without_filter==['p1'] and [x for x in timeline if visible(x)]==[]
# An unacknowledged inbox item is resent on reconnect; clients deduplicate by ID.
messages=[(1,'m1'),(2,'m2')]
displayed={'m1'}
replayed=[message_id for sequence,message_id in messages if sequence>=1]
for sequence, message_id in messages:
    if sequence>=1:
        displayed.add(message_id)
assert displayed=={'m1','m2'}
cursor=1
resume_events=0
while cursor<len(inbox):
    event=inbox[cursor]
    apply(event); apply(event)
    cursor+=1
    resume_events+=1
apply(('publish','p1',1))
assert search['p1']==(2,'delete')
# Distinct event tuples identify operations; the late publish has never been seen.
posts['p2']={'version':2,'state':'DELETED'}
apply(('delete','p2',2))
late_unseen=('publish','p2',1)
assert late_unseen not in seen
apply(late_unseen)
assert late_unseen in seen and search['p2']==(2,'delete')
authorized=[key for key in timeline if visible(key)]
assert authorized==[] and [x for x in notifications if visible(x)]==[]
assert len(inbox)-cursor==0 and backlog_before_drain==1
print(json.dumps(dict(python=platform.python_version(),orphan_visible=False,
 duplicate_timeline_rows=timeline.count('p1'),negative_stale_candidate=negative_without_filter,
 authorized_results=authorized,search_final=search['p1'],unseen_older_event_final=search['p2'],resume_events=resume_events,
 displayed_message_ids=sorted(displayed),negative_without_dedup=['m1']+replayed,
 backlog_peak=backlog_before_drain,backlog_after_drain=len(inbox)-cursor,pass_checks=True),indent=2))
