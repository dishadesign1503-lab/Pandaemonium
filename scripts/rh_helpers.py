# Shared helpers for the Theaterbrunnen site model (exec'd inside Rhino run_python)
import Rhino, System, math, json, random, os
import Rhino.Geometry as G
doc = __rhino_doc__
C = System.Drawing.Color.FromArgb
DATA = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "site_model_data.json"), encoding="utf8"))
ZP = 0.12          # plaza / sidewalk top (kerb height above road)
TOL = 0.001

LAYERS = {
 "00_Base":(146,154,138), "01_Roads":(118,124,114), "01b_Cycleways":(132,138,128), "02_Road_Markings":(236,236,230),
 "03_Green":(128,144,118), "03b_Planting_Soil":(120,112,98), "04_Plaza_Paving":(172,170,163), "04b_Paving_Joints":(112,110,104),
 "04c_Cycle_Path_Sett":(140,138,132), "04d_Sidewalks":(184,184,174), "05_Buildings":(245,243,237), "05b_DNT_Wing":(246,244,238),
 "06_Context_Trees":(236,234,226), "10_Focus_Trees":(204,56,46), "11_Bench_Timber":(214,66,50), "12_Bench_Concrete":(226,223,214),
 "13_Tree_Grates_Cages":(70,70,70), "14_Water":(108,168,200), "15_Fountain_Stone":(232,228,216), "15b_Walls":(228,225,216),
 "16_Red_Markers":(204,56,46), "17_People":(252,252,252), "18_Shrubs":(150,170,130), "19_Street_Furniture":(105,108,104),
 "20_Hoop_Guards_Red":(204,56,46), "21_Entrance":(236,234,228), "22_Windows":(196,198,196),
}
_LI = {}
def ensure_layers():
    for name, rgb in LAYERS.items():
        li = doc.Layers.FindByFullPath(name, -1)
        if li < 0:
            L = Rhino.DocObjects.Layer(); L.Name = name; li = doc.Layers.Add(L)
        L = doc.Layers[li]; L.Color = C(*rgb)
        m = Rhino.DocObjects.Material(); m.Name = name + "_mat"; m.DiffuseColor = C(*rgb); m.Shine = 0
        if name == "14_Water": m.Transparency = 0.25
        rm = Rhino.Render.RenderMaterial.CreateBasicMaterial(m, doc); doc.RenderMaterials.Add(rm); L.RenderMaterial = rm
        _LI[name] = li
def LI(name):
    if name not in _LI: _LI[name] = doc.Layers.FindByFullPath(name, -1)
    return _LI[name]
def add(g, ln, name=None):
    a = Rhino.DocObjects.ObjectAttributes(); a.LayerIndex = LI(ln)
    a.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromLayer; a.WireDensity = -1
    if name: a.Name = name
    return doc.Objects.Add(g, a)
def addmany(gs, ln, name=None):
    for g in gs or []: add(g, ln, name)

def pl_curve(pts, z=0.0, close=True):
    pp = [G.Point3d(x, y, z) for x, y in pts]
    if close and (pp[0].DistanceTo(pp[-1]) > 1e-6): pp.append(pp[0])
    return G.Polyline(pp).ToNurbsCurve()
def extrude_curve(crv, z0, h):
    crv = crv.DuplicateCurve(); crv.Translate(0, 0, z0 - crv.PointAtStart.Z)
    b = G.Extrusion.Create(crv, h, True)
    if b is None: return None
    b = b.ToBrep()
    if b.GetBoundingBox(True).Min.Z < z0 - 1e-6: b.Transform(G.Transform.Translation(0, 0, h))
    return b
def prism(pts, z0, h): return extrude_curve(pl_curve(pts), z0, h)
def extent_rect(m=0.0):
    X0, X1, Y0, Y1 = DATA["extent"]
    return pl_curve([(X0+m, Y0+m), (X1-m, Y0+m), (X1-m, Y1-m), (X0+m, Y1-m)])
def clip(crv):
    r = G.Curve.CreateBooleanIntersection(crv, extent_rect(), TOL)
    return list(r) if r else []
def cyl(x, y, z, r, h): return G.Cylinder(G.Circle(G.Plane(G.Point3d(x, y, z), G.Vector3d.ZAxis), r), h).ToBrep(True, True)
def sector(cx, cy, r1, r2, a0, a1, n=8):
    o = [(cx + r2*math.cos(a0 + (a1-a0)*i/n), cy + r2*math.sin(a0 + (a1-a0)*i/n)) for i in range(n+1)]
    i_ = [(cx + r1*math.cos(a1 - (a1-a0)*i/n), cy + r1*math.sin(a1 - (a1-a0)*i/n)) for i in range(n+1)]
    return o + i_
def rbox(cx, cy, ang, x0, x1, y0, y1, z0, z1):
    b = G.Box(G.Plane.WorldXY, G.Interval(x0, x1), G.Interval(y0, y1), G.Interval(z0, z1)).ToBrep()
    b.Transform(G.Transform.Rotation(ang, G.Vector3d.ZAxis, G.Point3d.Origin)); b.Transform(G.Transform.Translation(cx, cy, 0)); return b
def pipe(c, r, cap=G.PipeCapMode.Flat): return G.Brep.CreatePipe(c, r, False, cap, True, TOL, 0.01)
def torus(x, y, z, R, r): return G.Brep.CreateFromSurface(G.Torus(G.Plane(G.Point3d(x, y, z), G.Vector3d.ZAxis), R, r).ToNurbsSurface())
def band(pts, w):
    """polygon of a polyline offset +-w/2 (mitred)"""
    L = []; R = []; hw = w/2.0
    for i, p in enumerate(pts):
        a = pts[max(i-1, 0)]; b = pts[min(i+1, len(pts)-1)]
        dx, dy = b[0]-a[0], b[1]-a[1]; l = math.hypot(dx, dy) or 1
        n = (-dy/l, dx/l)
        L.append((p[0]+n[0]*hw, p[1]+n[1]*hw)); R.append((p[0]-n[0]*hw, p[1]-n[1]*hw))
    return L + R[::-1]
def nodes(pred): return [n for n in DATA["nodes"] if pred(n["tags"])]
def way(i):
    for k in ("buildings", "roads", "sett", "barriers"):
        for w in DATA.get(k, []):
            if w["id"] == i: return w
ensure_layers()
