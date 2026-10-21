"""#16 再開 (2): 新しい標的外の点で、長さ 10 mm の軸索の線が脳の中に収まるかを確かめる（Sim4Life.lite・読み取りのみ）。2026-10-14。

GH #17 で、tTIS の脳内 TI 最大は延髄の表面 (72.5, 276.5, 1511.5)・標的の 4.59 倍と分かった。
#16 の標的外は、そのすぐ内側で値もほぼ同じ (72.5, 275.5, 1511.5)（4.34 倍）を候補にする。
延髄は細い（最大点のまわり 125 セル中、脳は 29）ので、x・y・z の 10 mm の線が延髄に収まるとは限らない。

出力: 候補点を通る線ごとに、0.25 mm 刻みの組織を1文字で並べる。
  M＝延髄（Medulla_oblongata）・B＝ほかの脳 12 組織・C＝脳脊髄液・D＝硬膜・O＝それ以外
向きは x・y・z の3方向と、延髄の長軸の向き（延髄のセルの主成分）を出す。
長さは 10 mm（#16 の標的と同じ）と、短い 6 mm・4 mm で、何割が脳かも出す。
組織名は `TUS_250k` の Input.h5 の `material_name`（頭部 1 mm・tTIS と同じ脳）。
"""
import numpy as np
import h5py
import s4l_v1.document as document

SITE = np.array([72.5, 275.5, 1511.5])
BRAIN = ('Cerebrum_grey_matter', 'Cerebrum_white_matter', 'Cerebellum', 'Corpus_callosum', 'Pons', 'Thalamus',
         'Medulla_oblongata', 'Hippocampus', 'Midbrain', 'Hypothalamus', 'Pineal_body', 'Commissura_posterior')
STEP = 0.25


def uuid_hex(row):
    hx = bytes(np.asarray(row, dtype=np.uint8).tolist()).hex()
    return "%s-%s-%s-%s-%s" % (hx[0:8], hx[8:12], hx[12:16], hx[16:20], hx[20:32])


def text(v):
    return v.decode(errors="replace") if isinstance(v, bytes) else str(v)


sim = document.AllSimulations["TUS_250k"]
with h5py.File(sim.GetInputFileName(), "r") as f:
    mm = f["AllMaterialMaps"][list(f["AllMaterialMaps"].keys())[0]]
    mesh = None
    for key in f["Meshes"]:
        if "voxels" in f["Meshes"][key]:
            mesh = f["Meshes"][key]
            break
    voxels = mesh["voxels"][...]
    id_map = mesh["id_map"][...]
    ax = [np.asarray(mesh[a][...]) * 1000.0 for a in ("axis_x", "axis_y", "axis_z")]
    n = int(voxels.max()) + 1
    names = np.array(["Background"] * n, dtype=object)
    for v in range(min(n, id_map.shape[0])):
        u = uuid_hex(id_map[v])
        if u in mm:
            names[v] = text(mm[u].attrs.get("material_name", "?")).split("(")[0].strip()
cx, cy, cz = [0.5 * (a[:-1] + a[1:]) for a in ax]
name3 = names[voxels]


def letter(p):
    i = int(np.argmin(np.abs(cx - p[0])))
    j = int(np.argmin(np.abs(cy - p[1])))
    l = int(np.argmin(np.abs(cz - p[2])))
    nm = name3[i, j, l]
    if nm == "Medulla_oblongata":
        return "M"
    if nm in BRAIN:
        return "B"
    if nm == "Cerebrospinal_fluid":
        return "C"
    if nm == "Dura_mater":
        return "D"
    return "O"


print("[site] (%.1f, %.1f, %.1f) = %s" % (SITE[0], SITE[1], SITE[2], letter(SITE)))

i0 = int(np.argmin(np.abs(cx - SITE[0])))
j0 = int(np.argmin(np.abs(cy - SITE[1])))
l0 = int(np.argmin(np.abs(cz - SITE[2])))
r = 15
sub = name3[i0 - r:i0 + r + 1, j0 - r:j0 + r + 1, l0 - r:l0 + r + 1] == "Medulla_oblongata"
idx = np.array(np.nonzero(sub)).T
pts = np.stack([cx[i0 - r + idx[:, 0]], cy[j0 - r + idx[:, 1]], cz[l0 - r + idx[:, 2]]], axis=1)
w, v = np.linalg.eigh(np.cov((pts - pts.mean(axis=0)).T))
long_axis = v[:, -1] / np.linalg.norm(v[:, -1])
print("[medulla] cells within +-15 mm: %d  long axis = (%.2f, %.2f, %.2f)  spread sd = %s mm"
      % (len(pts), long_axis[0], long_axis[1], long_axis[2], np.round(np.sqrt(w[::-1]), 2)))

dirs = {"x": np.array([1.0, 0, 0]), "y": np.array([0, 1.0, 0]), "z": np.array([0, 0, 1.0]), "long": long_axis}
for length in (10.0, 6.0, 4.0):
    s = np.arange(-length / 2, length / 2 + 1e-9, STEP)
    print("")
    print("[length %.0f mm] %d points" % (length, s.size))
    for d, u in dirs.items():
        row = "".join(letter(SITE + t * u) for t in s)
        frac = sum(ch in "MB" for ch in row) / float(len(row))
        print("  %-5s brain %3.0f %%  %s" % (d, 100 * frac, row))
