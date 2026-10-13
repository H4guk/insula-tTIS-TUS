"""脳を「組織の名前」で定義し直す 2番: 両手法の組織名とボクセルの体積を一覧にする（Sim4Life.lite・読み取りのみ）。2026-10-13。

`probe_material_names.py` で、Input.h5 の材料グループの属性 `material_name` に Yoon-sun の組織名があると分かった。
ここでは `tTIS_LF1` と `TUS_250k` のそれぞれで、全組織の名前・セル数・体積 [mL] を出す。
この一覧から「脳」に含める組織を決める（次の手）。

結果（2026-10-13）: tTIS 59 ラベル・TUS 60 ラベル（TUS は Transducer が1つ多い）。頭部は両方とも 1 mm のセルで、
脳の組織のセル数はほぼ同じ（例 Cerebrum_grey_matter 527068 / 527068、Cerebrum_white_matter 367592 / 367588）。

決めた「脳」（脳実質 12 組織。両手法で同じ名前の集合を使う）:
  Cerebrum_grey_matter 527.07 / Cerebrum_white_matter 367.59 / Cerebellum 110.05 / Corpus_callosum 12.79 /
  Pons 8.19 / Thalamus 7.87 / Medulla_oblongata 3.28 / Hippocampus 2.06 / Midbrain 1.95 / Hypothalamus 0.62 /
  Pineal_body 0.04 / Commissura_posterior 0.00  [mL]  → 合計 約 1041.5 mL（tTIS 1041520 セル・TUS 1041521 セル）
外したもの: Hypophysis（下垂体・脳実質の外）、Spinal_cord、Nerve、Cerebrospinal_fluid、Dura_mater。
旧定義との差: tTIS の σ 帯は 945 mL、TUS の GM+WM は 918 mL だった。
"""
import numpy as np
import h5py
import s4l_v1.document as document


def uuid_hex(row):
    hx = bytes(np.asarray(row, dtype=np.uint8).tolist()).hex()
    return "%s-%s-%s-%s-%s" % (hx[0:8], hx[8:12], hx[12:16], hx[16:20], hx[20:32])


def text(v):
    return v.decode(errors="replace") if isinstance(v, bytes) else str(v)


for name in ("tTIS_LF1", "TUS_250k"):
    sim = document.AllSimulations[name]
    with h5py.File(sim.GetInputFileName(), "r") as f:
        mm = f["AllMaterialMaps"][list(f["AllMaterialMaps"].keys())[0]]
        mesh = None
        for key in f["Meshes"]:
            if "voxels" in f["Meshes"][key]:
                mesh = f["Meshes"][key]
                break
        voxels = mesh["voxels"][...]
        id_map = mesh["id_map"][...]
        ax = [np.asarray(mesh[a][...]) for a in ("axis_x", "axis_y", "axis_z")]
        names = {}
        for v in range(id_map.shape[0]):
            u = uuid_hex(id_map[v])
            names[v] = text(mm[u].attrs.get("material_name", "?")) if u in mm else "(not in map: %s)" % u
    dx, dy, dz = [np.diff(a) for a in ax]
    vol = dx[:, None, None] * dy[None, :, None] * dz[None, None, :]
    if vol.shape != voxels.shape:
        print("[warn] vol %s != voxels %s" % (vol.shape, voxels.shape))
    labels, inv = np.unique(voxels, return_inverse=True)
    vsum = np.bincount(inv.ravel(), weights=vol.ravel())
    csum = np.bincount(inv.ravel())
    print("")
    print("######## %s  grid %s  labels %d" % (name, voxels.shape, labels.size))
    rows = sorted(zip(labels, csum, vsum), key=lambda r: names.get(int(r[0]), "?"))
    for lab, n, v in rows:
        print("%4d  %9d cells  %9.2f mL  %s" % (lab, n, v * 1e6, names.get(int(lab), "?")))
