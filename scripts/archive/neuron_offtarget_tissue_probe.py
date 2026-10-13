"""#16 やり直し: tTIS の「標的外（脳内 TI 最大点）」が本当に脳の中かを確かめる（Sim4Life.lite・読み取りのみ）。

きっかけ（2026-10-13）: `neuron_tus_line_pressure.py` で、標的外 (48.5, 274.5, 1482.5) を通る 10 mm の線3本が
41 点すべて「脳でも脳脊髄液でもない（O）」と出た。
tTIS の脳マスクは σ 0.33〜0.44 S/m の帯（`reach_volume.py`・`ti_local_maxima.py`）で、
この帯には `Tendon\\Ligament`（0.3676）・`Eye (Lens)`（0.3453）・`Trachea`（0.3420）も入る（`phase2-prod.md`）。
標的外の点がこれらの組織に当たっていないかを、`TUS_250k` のボクセルの (c, ρ) から組織名を逆引きして確かめる。

出力: 標的外の点と、そのまわり ±2 セルに含まれる組織ごとのセル数。比較のため標的（ROI 中心）も出す。

結果（2026-10-13）:
  標的   (99.5, 294.5, 1562.5): Brain (White Matter)。まわり 125 セルすべて白質。
  標的外 (48.5, 274.5, 1482.5): **Tendon\\Ligament**。まわり 125 セルは Muscle/Tongue 48・Fat 29・Bone (Cortical) 26・
         Tendon\\Ligament 21・Bone (Cancellous) 1。脳は 0 セル。
  ⇒ tTIS の「脳内 TI 最大点」は脳ではなく、ROI より 80 mm 下（首・顎のあたり）の腱・靭帯だった。
"""
import numpy as np
import h5py
import s4l_v1.document as document

SIM_NAME = "TUS_250k"
SITES = {"target": (99.1, 295.0, 1562.2), "offtarget": (48.5, 274.5, 1482.5)}
TABLE = {
    "Blood": (1049.75, 1578.18), "Bone (Cancellous)": (1178.33, 2117.53), "Bone (Cortical)": (1908, 3514.86),
    "Brain (Grey Matter)": (1044.5, 1500), "Brain (White Matter)": (1041, 1552.5), "Cartilage": (1099.5, 1639.6),
    "Cerebellum": (1045, 1537), "Cerebrospinal Fluid": (1007, 1504.5), "Dura": (1174, 1500),
    "Esophagus": (1040, 1500), "Eye (Cornea)": (1061.65, 1565.77), "Eye (Lens)": (1075.5, 1643.32),
    "Eye (Sclera)": (1032, 1630.4), "Eye (Vitreous Humor)": (1004.5, 1525.84), "Fat": (911, 1440.19),
    "Hypophysis": (1053, 1500), "Lymphnode": (1035, 1586), "Medulla/Midbrain/Pons": (1045.5, 1546.32),
    "Mucous Membrane": (1102, 1620.68), "Muscle/Tongue": (1090.4, 1588.43), "Nerve": (1075, 1629.5),
    "SAT (Subcutaneous Fat)": (911, 1477), "Salivary Gland": (1048, 1559.5), "Skin": (1109, 1624),
    "Skull (Cancellous)": (1178.33, 2117.53), "Skull (Cortical)": (1908, 2813.69), "Spinal Cord": (1075, 1542),
    "Tendon\\Ligament": (1142, 1750), "Tooth": (2180, 4565.88), "Trachea": (1080, 1639.6),
}


def name_of(r, c):
    if not np.isfinite(r) or not np.isfinite(c):
        return "(none)"
    best = min(TABLE.items(), key=lambda kv: abs(kv[1][0] - r) / 1000 + abs(kv[1][1] - c) / 1500)
    return "%s (rho %.1f c %.1f)" % (best[0], r, c)


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


sim = document.AllSimulations[SIM_NAME]
res = sim.Results()
res.UpdateAll()
of = res["Overall Field"]
of.Update(0)
pf = of["p(x,y,z,f)"]
pf.Update()
g = pf.Data.Grid
cx = 0.5 * (np.asarray(g.XAxis)[:-1] + np.asarray(g.XAxis)[1:]) * 1000.0
cy = 0.5 * (np.asarray(g.YAxis)[:-1] + np.asarray(g.YAxis)[1:]) * 1000.0
cz = 0.5 * (np.asarray(g.ZAxis)[:-1] + np.asarray(g.ZAxis)[1:]) * 1000.0

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
print("[grid] voxels %s  cells %d x %d x %d" % (c3.shape, cx.size, cy.size, cz.size))

for site, (x, y, z) in SITES.items():
    i = int(np.argmin(np.abs(cx - x)))
    j = int(np.argmin(np.abs(cy - y)))
    l = int(np.argmin(np.abs(cz - z)))
    print("")
    print("[%s] cell (%.1f, %.1f, %.1f): %s" % (site, cx[i], cy[j], cz[l], name_of(r3[i, j, l], c3[i, j, l])))
    counts = {}
    for a in range(i - 2, i + 3):
        for b in range(j - 2, j + 3):
            for c in range(l - 2, l + 3):
                nm = name_of(r3[a, b, c], c3[a, b, c])
                counts[nm] = counts.get(nm, 0) + 1
    for nm, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print("   %3d / 125  %s" % (n, nm))
