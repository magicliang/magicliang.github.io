"""Planar local metric fixture, not global latitude/longitude or PostGIS."""
import json
import math
import platform
import random

rng = random.Random(2401)
points = {str(i):(rng.uniform(-2000,2000),rng.uniform(-2000,2000),100,True) for i in range(1000)}
points.update({'boundary':(1000.01,0,100,True),'stale':(999.9,0,0,True),'private':(1000,0,100,False)})
for i in range(100):
    points['dense'+str(i)] = (999 + rng.random(), rng.random(),100,True)
size = 500
cells = {}
for key,(x,y,stamp,visible) in points.items():
    cells.setdefault((math.floor(x/size),math.floor(y/size)),[]).append(key)
def query(x,y,radius,indexed):
    if indexed:
        candidates=[]
        for cx in range(math.floor((x-radius)/size),math.floor((x+radius)/size)+1):
            for cy in range(math.floor((y-radius)/size),math.floor((y+radius)/size)+1):
                candidates.extend(cells.get((cx,cy),[]) if (cx,cy)==(math.floor(x/size),math.floor(y/size)) else [])
    else:
        candidates=list(points)
    result=[]
    for key in candidates:
        px,py,stamp,visible=points[key]
        if visible and 110-stamp <= 30 and math.hypot(px-x,py-y)<=radius:
            result.append(key)
    return sorted(result),len(candidates)
observations=[]
for x,y,radius in [(999.99,0,1),(0,0,300),(-500,-500,500),(1000,0,50)]:
    indexed,count=query(x,y,radius,True)
    full,total=query(x,y,radius,False)
    assert indexed==full
    assert 'stale' not in indexed and 'private' not in indexed
    observations.append({'center':[x,y],'radius_m':radius,'candidates':count,'full':total,'hits':len(indexed)})
assert 'boundary' in query(999.99,0,1,True)[0]
wrong= cells.get((math.floor(999.99/size),0),[])
assert 'boundary' not in wrong, 'single-cell negative control must miss boundary'
print(json.dumps({'python':platform.python_version(),'seed':2401,'queries':observations,'single_cell_missed_boundary':True,'pass':True}))
