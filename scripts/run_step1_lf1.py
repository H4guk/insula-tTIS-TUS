"""Step 1（ペア1 T7-P7）を新規simで一気に組む統合スクリプト（全修正込み・クリーン実行用）。

これまでの全点NaN／incompatible／run拒否は「1つのセッションに壊れたsim・古いGridBox・
run済み状態が溜まって検証を通らなくなる」状態腐りが原因。→ **セッションをリロードして真っさらな
状態でこれ1本を流す**のが確実（壊れたsimに後から足さない）。

前提（この前に実行）:
  1) load_yoonsun.py       # Yoon-sun 読み込み
  2) place_electrodes.py   # Elec_T7/P7/Fp1/Fp2 生成
  そのうえで本スクリプトを貼る。

盛り込んだ修正:
  - 材料名マッチのアンダースコア罠 → [a-z0-9]+ 分割で59組織を取りこぼさない。
  - ★全点NaNの真因 → 駆動電極 Elec_T7/P7 にも材料σを付与（無いとVoxelerが電極を除外しDirichlet=0）。
  - v10: 新規simは document.AllSimulations.Add(sim) で登録。
  - 順序: 材料(組織+電極)→BC→(最後に)グリッド+CreateVoxels。
"""
import re
import s4l_v1
import s4l_v1.model as model
import s4l_v1.document as document
import s4l_v1.simulation.emlf as emlf
import s4l_v1.materials as materials
import XCoreModeling as xc


def V(p): return model.Vec3(*map(float, p))


def xyz(v):
    try:    return float(v[0]), float(v[1]), float(v[2])
    except: return float(v.X), float(v.Y), float(v.Z)


def get_entity(name):
    hit = [e for e in model.AllEntities() if e.Name == name]
    return hit[0] if hit else None


itis = materials.database.ITISLF
db_names = [m.Name for m in itis.AllMaterials]


def get_mat(n):
    for m in itis.AllMaterials:
        if m.Name == n:
            return m
    return None


def words(s):
    return set(re.findall(r'[a-z0-9]+', s.lower()))     # ★ '_' を必ず区切る


def try_match(vip):
    w = words(vip)
    for d in db_names:
        if words(d) == w:
            return d
    return None


MANUAL = {
    'Cerebrum_grey_matter': 'Brain (Grey Matter)', 'Cerebrum_white_matter': 'Brain (White Matter)',
    'Corpus_callosum': 'Brain (White Matter)', 'Dura_mater': 'Dura', 'Artery': 'Blood', 'Vein': 'Blood',
    'SAT': 'SAT (Subcutaneous Fat)', 'Mucosa': 'Mucous Membrane', 'Air_internal': 'Air',
    'Mandible_cortical': 'Skull (Cortical)', 'Mandible_cancellous': 'Skull (Cancellous)',
    'Hyoid_cortical': 'Bone (Cortical)', 'Trachea_wall': 'Trachea', 'Esophagus_wall': 'Esophagus',
    'Lymph_node': 'Lymphnode',
}
for i in range(1, 6):
    MANUAL['Vertebra_cortical_C%d' % i] = 'Bone (Cortical)'
    MANUAL['Vertebra_cancellous_C%d' % i] = 'Bone (Cancellous)'

# grid 内の頭部組織を抽出（電極/グループ/GridBox は除外）
GX, GY, GZ = (4, 202), (162, 352), (1450, 1665)
head = set()
for e in model.AllEntities():
    bb = xc.GetBoundingBox([e])
    if not bb:
        continue
    lo, hi = xyz(bb[0]), xyz(bb[1])
    if hi[2] >= GZ[0] and lo[2] <= GZ[1] and hi[0] >= GX[0] and lo[0] <= GX[1] \
       and hi[1] >= GY[0] and lo[1] <= GY[1]:
        n = e.Name
        if n.startswith('Elec_') or 'Yoon' in n or n in ('Bones', 'Model') or n.startswith('GridBox'):
            continue
        head.add(n)

# 新規 sim + 登録
sim = emlf.ElectroQsOhmicSimulation(); sim.Name = 'tTIS_LF1'
sim.SetupSettings.Frequency = 2000.0
document.AllSimulations.Add(sim)

created = {}
miss = []
for t in sorted(head):
    dbn = try_match(t) or MANUAL.get(t)
    ent, mat = get_entity(t), (get_mat(dbn) if dbn else None)
    if ent is None or mat is None:
        miss.append(t); continue
    ms = sim.AddMaterialSettings(ent); ms.Name = t
    sim.LinkMaterialWithDatabase(ms, mat); created[t] = ms
for nm in ('Skin', 'Ear_skin_left', 'Ear_skin_right'):
    if nm in created:
        created[nm].ElectricProps.Conductivity = 0.465     # 実効頭皮σ
# ★駆動電極にも材料（無いと Voxeler が除外→Dirichlet=0→全点NaN）
for nm in ('Elec_T7', 'Elec_P7'):
    ms = sim.AddMaterialSettings(get_entity(nm)); ms.Name = nm
    ms.ElectricProps.Conductivity = 1.6                    # 食塩水スポンジ相当（簡略化）
    created[nm] = ms
sim.UpdateAllMaterials()
print('材料数:', len(created), '(組織59 + 電極2 = 61 期待) / 未マップ:', miss)

# BC（+1V / 0V）
def add_bc(elec, v, name):
    b = sim.AddBoundarySettings(get_entity(elec)); b.Name = name
    b.BoundaryType = emlf.EnumBoundaryType.kDirichlet     # Deprecated 警告は無害
    b.DirichletValue = v


add_bc('Elec_T7', 1.0, 'BC_T7_pos')
add_bc('Elec_P7', 0.0, 'BC_P7_gnd')

# グリッド → 最後にボクセル化
ggs = sim.GlobalGridSettings; p = ggs.DiscretizationModeProp
p.set(p.findValue('Manual')); ggs.MaxStep = [5.0, 5.0, 5.0]
gb = xc.CreateSolidBlock(V([4, 162, 1450]), V([202, 352, 1665])); gb.Name = 'GridBox_head'
mg = sim.AddManualGridSettings(gb); mg.Name = 'Grid_head_1mm'; mg.MaxStep = [1.0, 1.0, 1.0]
sim.UpdateGrid(); sim.CreateVoxels()
document.Save()
print('組み上げ完了。次:')
print("  sim.RunSimulation(wait=True)")
print("  → Voxeler.log に Elec エラーが無いこと & finite率≈100% を確認")
