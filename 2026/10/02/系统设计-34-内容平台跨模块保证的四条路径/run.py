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
negative_without_filter=list(timeline)
assert negative_without_filter==['p1'] and [x for x in timeline if visible(x)]==[]
# Disconnect after event 1; cursor resumes at 2, duplicate delivery is harmless.
cursor=1
for event in inbox[cursor:]: apply(event); apply(event)
apply(('publish','p1',1))
assert search['p1']==(2,'delete')
assert [x for x in notifications if visible(x)]==[]
assert len(inbox)-cursor==1
print(json.dumps(dict(python=platform.python_version(),orphan_visible=False,
 duplicate_timeline_rows=len(timeline),negative_stale_candidate=negative_without_filter,
 authorized_results=[],search_final=search['p1'],resume_events=1,
 backlog_peak=1,pass_checks=True),indent=2))
