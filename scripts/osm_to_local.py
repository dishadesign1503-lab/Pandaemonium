import json,math,sys
d=json.load(open(sys.argv[1],encoding='utf8'))
lat0,lon0=50.97959,11.32395
kx=111320*math.cos(math.radians(lat0)); ky=110574
def xy(la,lo): return [round((lo-lon0)*kx,3), round((la-lat0)*ky,3)]
R=95
out={'ways':[],'nodes':[],'rels':[]}
def near(pts): return any(abs(p[0])<R and abs(p[1])<R for p in pts)
for e in d['elements']:
    t=e.get('tags',{})
    if e['type']=='node' and t:
        p=xy(e['lat'],e['lon'])
        if abs(p[0])<R and abs(p[1])<R: out['nodes'].append({'id':e['id'],'p':p,'tags':t})
    elif e['type']=='way' and t:
        pts=[xy(g['lat'],g['lon']) for g in e.get('geometry',[])]
        if pts and near(pts): out['ways'].append({'id':e['id'],'pts':pts,'tags':t})
    elif e['type']=='relation' and t:
        mem=[]
        for m in e.get('members',[]):
            if m['type']=='way' and 'geometry' in m:
                pts=[xy(g['lat'],g['lon']) for g in m['geometry'] if g]
                if pts: mem.append({'role':m.get('role'),'pts':pts})
        if any(near(m['pts']) for m in mem):
            out['rels'].append({'id':e['id'],'tags':t,'members':mem})
json.dump(out,open('site_local.json','w',encoding='utf8'))
for r in out['rels']: print('REL',r['id'],{k:v for k,v in r['tags'].items() if k in('type','building','name','building:levels','height','area:highway','highway','landuse','roof:shape')},len(r['members']))
