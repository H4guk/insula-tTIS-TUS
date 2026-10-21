"""#16 L2: 7 本の軸索の線に沿って、TUS の音圧と組織を取り出す（Sim4Life.lite Python コンソール・読み取りのみ）。2026-10-15。

`neuron_tus_line_pressure.py` の改訂版。標的外を選び直した（`neuron_offtarget_search.py`）ので、線は次の 7 本:
  target_x/y/z : ROI 中心 (99.1, 295.0, 1562.2)
  offA_x/y/z   : (A) 3方向とも脳に収まる TI 最大点 (73.5, 266.5, 1512.5)・延髄・標的の 2.50 倍
  offB_y       : (B) y 方向だけ収まる点 (75.5, 264.5, 1509.5)・延髄・4.16 倍
長さ 10 mm、0.25 mm 刻み 41 点。音圧は `TUS_250k`（音源 1 MPa）を MI<1.9 の安全駆動 k にスケールし、三線形補間する。
組織は Input.h5 の `material_name`（脳 12 組織＝B、延髄＝M、脳脊髄液＝C、硬膜＝D、それ以外＝O）。
この値を MorphoSONIC の軸索（MRG 16 µm・無髄 Sundt）に区画ごとに与える。

出力は 1 本につき 2 行（p＝kPa の 41 個、ok＝組織の 41 文字）。全部をそのまま貼る。
"""
import numpy as np
import h5py
import s4l_v1.document as document

SIM_NAME = "TUS_250k"
FREQ_MHZ = 0.25
MI_LIMIT = 1.9
LINES = [
    ("target_x", (99.1, 295.0, 1562.2), (1, 0, 0)),
    ("target_y", (99.1, 295.0, 1562.2), (0, 1, 0)),
    ("target_z", (99.1, 295.0, 1562.2), (0, 0, 1)),
    ("offA_x", (73.5, 266.5, 1512.5), (1, 0, 0)),
    ("offA_y", (73.5, 266.5, 1512.5), (0, 1, 0)),
    ("offA_z", (73.5, 266.5, 1512.5), (0, 0, 1)),
    ("offB_y", (75.5, 264.5, 1509.5), (0, 1, 0)),
]
BRAIN = ("Cerebrum_grey_matter", "Cerebrum_white_matter", "Cerebellum", "Corpus_callosum", "Pons", "Thalamus",
         "Medulla_oblongata", "Hippocampus", "Midbrain", "Hypothalamus", "Pineal_body", "Commissura_posterior")
HALF = 5.0
STEP = 0.25


def uuid_hex(row):
    hx = bytes(np.asarray(row, dtype=np.uint8).tolist()).hex()
    return "%s-%s-%s-%s-%s" % (hx[0:8], hx[8:12], hx[12:16], hx[16:20], hx[20:32])


def text(v):
    return v.decode(errors="replace") if isinstance(v, bytes) else str(v)


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
cx = 0.5 * (np.asarray(g.XAxis)[:-1] + np.asarray(g.XAxis)[1:]) * 1000.0
cy = 0.5 * (np.asarray(g.YAxis)[:-1] + np.asarray(g.YAxis)[1:]) * 1000.0
cz = 0.5 * (np.asarray(g.ZAxis)[:-1] + np.asarray(g.ZAxis)[1:]) * 1000.0
p3 = mag.reshape((cx.size, cy.size, cz.size), order="F")
k = MI_LIMIT / ((float(p3.max()) * 1e-6) / np.sqrt(FREQ_MHZ))
print("[ref ] k = %.5f (record 0.1558)" % k)

with h5py.File(sim.GetInputFileName(), "r") as f:
    mm = f["AllMaterialMaps"][list(f["AllMaterialMaps"].keys())[0]]
    mesh = None
    for key in f["Meshes"]:
        if "voxels" in f["Meshes"][key]:
            mesh = f["Meshes"][key]
            break
    voxels = mesh["voxels"][...]
    id_map = mesh["id_map"][...]
    n = int(voxels.max()) + 1
    names = np.array(["Background"] * n, dtype=object)
    for v in range(min(n, id_map.shape[0])):
        u = uuid_hex(id_map[v])
        if u in mm:
            names[v] = text(mm[u].attrs.get("material_name", "?")).split("(")[0].strip()
name3 = names[voxels]
if name3.shape != p3.shape:
    raise SystemExit("[pre ] FAILED - voxels %s vs field %s" % (name3.shape, p3.shape))


def trilinear(x, y, z):
    out = []
    for ax, v in ((cx, x), (cy, y), (cz, z)):
        i = int(np.clip(np.searchsorted(ax, v) - 1, 0, ax.size - 2))
        t = float(np.clip((v - ax[i]) / (ax[i + 1] - ax[i]), 0.0, 1.0))
        out.append((i, t))
    (i, tx), (j, ty), (l, tz) = out
    acc = 0.0
    for di, wx in ((0, 1 - tx), (1, tx)):
        for dj, wy in ((0, 1 - ty), (1, ty)):
            for dl, wz in ((0, 1 - tz), (1, tz)):
                acc += wx * wy * wz * p3[i + di, j + dj, l + dl]
    return acc


def letter(x, y, z):
    nm = name3[int(np.argmin(np.abs(cx - x))), int(np.argmin(np.abs(cy - y))), int(np.argmin(np.abs(cz - z)))]
    if nm == "Medulla_oblongata":
        return "M"
    if nm in BRAIN:
        return "B"
    if nm == "Cerebrospinal_fluid":
        return "C"
    if nm == "Dura_mater":
        return "D"
    return "O"


s = np.arange(-HALF, HALF + 1e-9, STEP)
print("[line] %d points, step %.2f mm, start (-%.1f) -> end (+%.1f)" % (s.size, STEP, HALF, HALF))
for name, (x0, y0, z0), (dx, dy, dz) in LINES:
    pts = [(x0 + t * dx, y0 + t * dy, z0 + t * dz) for t in s]
    print("%s p  " % name + " ".join("%.2f" % (trilinear(*q) * k * 1e-3) for q in pts))
    print("%s ok " % name + "".join(letter(*q) for q in pts))
