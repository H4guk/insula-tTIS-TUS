"""④ 頭部組織へ導電率 σ を割り当て（IT'IS LF DB + skin 上書き・Sim4Life.lite）。

lec3 の「σ=0 で no dofs」の罠が Yoon-sun では 326 組織分あるが、
IT'IS の低周波(LF)物性 DB に自動リンクすれば一括で片付く（手打ち不要）。
グリッド内に入る頭部 59 組織だけσを割り当てれば足りる（ボクセル化は Grid 内のみ）。

★skin の罠: IT'IS LF の Skin は σ=0.0002 S/m（乾燥角質）で tES では非物理的
  （電極から電流が頭に入らない）→ tES 標準の実効頭皮 σ 0.465 S/m に上書きする。
⚠️ DatabaseLink は読み取り専用。ElectricProps.Conductivity 直接設定は Update 後も保持されるが、
   ボクセル化/Run 直前に skin σ を再確認すると安全。

出典ノート: Claude/Knowledge/sim4life-material-assignment.md
"""
import s4l_v1.model as model
import s4l_v1.simulation.emlf as emlf
import XCoreModeling as xc
import numpy as np


def xyz(v):
    try:    return np.array([float(v[0]), float(v[1]), float(v[2])])
    except: return np.array([float(v.X), float(v.Y), float(v.Z)])


# ① 組織名→材料を自動タグ付け（電極/ROI/グループは除外）
ents = list(model.AllEntities())
skip = lambda n: (n in ('Model', 'Grid', 'Bones')) or n.startswith('Elec_') \
                 or ('insula' in n.lower()) or ('ROI' in n) or ('Yoon' in n)
tissues = [e for e in ents if not skip(e.Name)]
model.AutoAssignMaterials(tissues)            # entity.MaterialName に材料名が入る

# ② グリッド範囲に入る頭部組織だけに絞る（グリッド外はボクセル化されない）
GX, GY, GZ = (4, 202), (162, 352), (1450, 1665)


def in_grid(e):
    bb = xc.GetBoundingBox([e]); lo, hi = xyz(bb[0]), xyz(bb[1])
    return (lo[0] <= GX[1] and hi[0] >= GX[0] and lo[1] <= GY[1] and hi[1] >= GY[0]
            and lo[2] <= GZ[1] and hi[2] >= GZ[0])


head = [e for e in tissues if getattr(e, 'MaterialName', None) and in_grid(e)]

# ③ Electro QS 作成 → 各組織を DB リンクしてσをロード
sim = emlf.ElectroQsOhmicSimulation(); sim.Name = 'tTIS_LF1'
sim.SetupSettings.Frequency = 2000.0
created = {}
for e in head:
    ms = sim.AddMaterialSettings(e); ms.Name = e.MaterialName
    sim.LinkMaterialWithDatabase(ms, e.MaterialName)
    created[e.Name] = ms
sim.UpdateAllMaterials()

# ④ skin系だけ tES標準の実効頭皮σに上書き（skinの罠）
for nm in ('Skin', 'Ear_skin_left', 'Ear_skin_right'):
    if nm in created:
        created[nm].ElectricProps.Conductivity = 0.465
sim.UpdateAllMaterials()

print('材料割り当て組織数:', len(head))
