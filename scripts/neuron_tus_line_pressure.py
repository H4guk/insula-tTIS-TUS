"""#16 やり直し 2番: 6本の軸索の線に沿って音圧と組織を取り出す（Sim4Life.lite Python コンソール・読み取りのみ）。

`neuron_ti_place_axons.py` と同じ6本（標的・標的外 × x/y/z、長さ 10 mm）に沿って、
`TUS_250k` の |p| を MI<1.9 の安全駆動（k を全体最大から出す・記録 0.1558）にそろえて 0.25 mm ごとに出す。
この値を MorphoSONIC の MRG 軸索に区画ごとに与える（3番）。

軸索の節の位置（Sim4Life の Motor MRG 20 µm）:
  titration の「最初の発火の位置」から逆算すると、node[0] は線の始点、節の間隔は 1.759 mm（node[5] は始点から 8.796 mm）。
  MorphoSONIC の MRGFiber(20 µm) は 1.700 mm なので約 3.5% 違う。3番では node[0] を線の始点に合わせて置く。

出力（1本につき2行）:
  p    : 0.25 mm ごとの |p| [kPa]（41 点、始点 → 終点）
  ok   : 各点が脳か（B）・脳脊髄液か（C）・それ以外か（O）
         脳＝c 1490〜1560 m/s かつ ρ 1035〜1058 kg/m³（`tus_safety_drive.py` と同じ定義）、CSF＝ρ 1000〜1015
|p| はセル中心の値から三線形補間する。
"""
import numpy as np
import h5py
import s4l_v1.document as document

SIM_NAME = "TUS_250k"
FREQ_MHZ = 0.25
MI_LIMIT = 1.9
SITES = {"target": (99.1, 295.0, 1562.2), "offtarget": (48.5, 274.5, 1482.5)}
DIRS = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
HALF = 5.0
STEP = 0.25

sim = document.AllSimulations[SIM_NAME]
res = sim.Results()
res.UpdateAll()
of = res["Overall Field"]
of.Update(0)
pf = of["p(x,y,z,f)"]
pf.Update()
data = pf.Data
mag = np.abs(np.asarray(data.Field(0))).ravel()
g = data.Grid
Xm = np.asarray(g.XAxis)
Ym = np.asarray(g.YAxis)
Zm = np.asarray(g.ZAxis)
cx = 0.5 * (Xm[:-1] + Xm[1:]) * 1000.0
cy = 0.5 * (Ym[:-1] + Ym[1:]) * 1000.0
cz = 0.5 * (Zm[:-1] + Zm[1:]) * 1000.0
nx, ny, nz = cx.size, cy.size, cz.size
p3 = mag.reshape((nx, ny, nz), order="F")
k = MI_LIMIT / ((float(p3.max()) * 1e-6) / np.sqrt(FREQ_MHZ))
print("[ref ] k = %.5f (record 0.1558)" % k)


def uuid_hex(row):
    hx = bytes(np.asarray(row, dtype=np.uint8).tolist()).hex()
    return "%s-%s-%s-%s-%s" % (hx[0:8], hx[8:12], hx[12:16], hx[16:20], hx[20:32])


def prop_by_type(mat, typename):
    tn = typename.encode()
    for pk in mat.keys():
        grp = mat[pk]
        ci = grp.get("_ClassInfo") if hasattr(grp, "get") else None
        if ci is not None and ci.attrs.get("_TypeName") == tn:
            try:
                return float(grp["_Object"].attrs["Value"])
            except Exception:
                return np.nan
    return np.nan


with h5py.File(sim.GetInputFileName(), "r") as f:
    mm = f["AllMaterialMaps"][list(f["AllMaterialMaps"].keys())[0]]
    mesh = None
    for key in f["Meshes"]:
        if "voxels" in f["Meshes"][key]:
            mesh = f["Meshes"][key]
            break
    voxels = mesh["voxels"][...]
    id_map = mesh["id_map"][...]
    lut_c = np.full(int(voxels.max()) + 1, np.nan)
    lut_r = np.full(int(voxels.max()) + 1, np.nan)
    for v in np.unique(voxels):
        u = uuid_hex(id_map[v])
        if u in mm:
            lut_c[v] = prop_by_type(mm[u], "CSoundSpeed")
            lut_r[v] = prop_by_type(mm[u], "CMassDensity")
c3 = lut_c[voxels]
r3 = lut_r[voxels]
if c3.shape != p3.shape:
    print("[warn] voxel shape %s != field shape %s" % (c3.shape, p3.shape))


def trilinear(x, y, z):
    out = []
    for ax, v in ((cx, x), (cy, y), (cz, z)):
        i = int(np.clip(np.searchsorted(ax, v) - 1, 0, ax.size - 2))
        t = (v - ax[i]) / (ax[i + 1] - ax[i])
        out.append((i, float(np.clip(t, 0.0, 1.0))))
    (i, tx), (j, ty), (l, tz) = out
    acc = 0.0
    for di, wx in ((0, 1 - tx), (1, tx)):
        for dj, wy in ((0, 1 - ty), (1, ty)):
            for dl, wz in ((0, 1 - tz), (1, tz)):
                acc += wx * wy * wz * p3[i + di, j + dj, l + dl]
    return acc


def tissue(x, y, z):
    i = int(np.argmin(np.abs(cx - x)))
    j = int(np.argmin(np.abs(cy - y)))
    l = int(np.argmin(np.abs(cz - z)))
    c, r = c3[i, j, l], r3[i, j, l]
    if 1490 <= c <= 1560 and 1035 <= r <= 1058:
        return "B"
    if 1000 <= r <= 1015:
        return "C"
    return "O"


s = np.arange(-HALF, HALF + 1e-9, STEP)
print("[line] %d points, step %.2f mm, from start (-%.1f) to end (+%.1f)" % (s.size, STEP, HALF, HALF))
for site, (x0, y0, z0) in SITES.items():
    for d, (dx, dy, dz) in DIRS.items():
        pts = [(x0 + t * dx, y0 + t * dy, z0 + t * dz) for t in s]
        pk = [trilinear(*q) * k * 1e-3 for q in pts]
        ts = "".join(tissue(*q) for q in pts)
        print("%s_%s p  " % (site, d) + " ".join("%.2f" % v for v in pk))
        print("%s_%s ok " % (site, d) + ts)
