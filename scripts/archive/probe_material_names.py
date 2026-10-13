"""脳を「組織の名前」で定義し直すための調査（Sim4Life.lite・読み取りのみ）。2026-10-13。

背景: tTIS の脳（σ 0.33〜0.44）にも TUS の脳（c・ρ の帯）にも脳以外の組織が混ざり、範囲も手法で違った
（tTIS の「脳内最大点」は腱・靭帯だった。`neuron_offtarget_tissue_probe.py`）。
両手法で同じ「脳」にするため、各ボクセルの組織名を Input.h5 から取れるかを調べる。

やること: `tTIS_LF1` と `TUS_250k` の Input.h5 で、
  - 材料マップ（AllMaterialMaps）の1つ目の材料グループの中身（属性・子の型・文字列の属性）を出す
  - Meshes の voxels を持つメッシュの中身（キー・形・属性）を出す
名前がどこに入っているかが分かれば、次でボクセル → 組織名の表を作る。

結果（2026-10-13）: 材料グループの属性 `material_name` に Yoon-sun の組織名が入っている
（例 `Hyoid_cortical  (Yoon-sun v3.1 Static/Bones)`）。材料の数は tTIS_LF1 62・TUS_250k 61。
voxels → id_map → uuid → material_name でボクセルごとの組織名が引ける。グリッドは tTIS 228×220×245・TUS 220×212×237。
"""
import numpy as np
import h5py
import s4l_v1.document as document


def show_attrs(obj, indent):
    for ak, av in obj.attrs.items():
        v = av
        if isinstance(v, bytes):
            v = v.decode(errors="replace")
        if isinstance(v, np.ndarray) and v.dtype.kind in "SO":
            v = [x.decode(errors="replace") if isinstance(x, bytes) else x for x in v.ravel()[:5]]
        s = str(v)
        print("%s@%s = %s" % (indent, ak, s[:120]))


def walk(g, indent, depth):
    show_attrs(g, indent)
    if depth == 0 or not hasattr(g, "keys"):
        return
    for k in list(g.keys())[:12]:
        obj = g[k]
        if isinstance(obj, h5py.Dataset):
            print("%s%s  dataset %s %s" % (indent, k, obj.shape, obj.dtype))
            show_attrs(obj, indent + "  ")
        else:
            print("%s%s/" % (indent, k))
            walk(obj, indent + "  ", depth - 1)


for name in ("tTIS_LF1", "TUS_250k"):
    sim = document.AllSimulations[name]
    print("")
    print("########", name, sim.GetInputFileName())
    with h5py.File(sim.GetInputFileName(), "r") as f:
        print("top keys:", list(f.keys()))
        maps = f["AllMaterialMaps"]
        mk = list(maps.keys())[0]
        print("material maps:", list(maps.keys()), "-> using", mk)
        mm = maps[mk]
        uu = list(mm.keys())
        print("materials in map:", len(uu))
        print("--- first material group:", uu[0])
        walk(mm[uu[0]], "  ", 3)
        for key in f["Meshes"]:
            if "voxels" in f["Meshes"][key]:
                print("--- mesh with voxels:", key)
                walk(f["Meshes"][key], "  ", 1)
                break
