"""Bounded immutable-parent insertion tree + grow-only deletion set.
Not a complete RGA/Yjs implementation. Unique IDs and well-formed parent graph required.
"""
import itertools, json, platform
ops=[('i','a1','ROOT','A'),('i','b1','ROOT','B'),('i','a2','a1','x'),('d','a1')]
def merge(order):
    nodes={}; deleted=set()
    for op in order:
        if op[0]=='i':
            _,key,parent,text=op
            if key in nodes: assert nodes[key]==(parent,text)
            nodes[key]=(parent,text)
        else: deleted.add(op[1])
    def walk(parent):
        out=[]
        for key in sorted(k for k,v in nodes.items() if v[0]==parent):
            if key not in deleted: out.append((key,nodes[key][1]))
            out.extend(walk(key))
        return out
    return walk('ROOT'), deleted
results={''.join(ch for _,ch in merge(order)[0]) for order in itertools.permutations(ops)}
assert results=={'xB'}
assert merge(ops+ops)==merge(ops)
# Cursor anchored after tombstoned a1 resolves to first surviving descendant a2.
visible,_=merge(ops)
assert visible[0][0]=='a2'
# Offset-only insertion is arrival-order dependent.
def positional(order):
    text=''
    for ch in order: text=ch+text
    return text
assert positional('AB') != positional('BA')
print(json.dumps(dict(python=platform.python_version(),permutations=24,
 converged=list(results),duplicate_idempotent=True,cursor_after_deleted_a1='before a2',
 negative_offsets=[positional('AB'),positional('BA')],pass_checks=True),indent=2))
