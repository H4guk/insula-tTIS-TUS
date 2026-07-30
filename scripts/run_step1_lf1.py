"""Step 1（ペア1 T7-P7）を新規simで一気に組んで Run まで通す統合スクリプト（クリーン実行用）。

これまでの全点NaN／incompatible／run拒否は「1つのセッションに壊れたsim・古いGridBox・
run済み状態が溜まって検証を通らなくなる」状態腐りが原因。
→ 最善は**セッションをリロードして真っさらな状態でこれ1本を流す**こと。
   ただしリロードを忘れても死なないよう、本スクリプトは**衝突しない名前を自動で選ぶ**（下記）。

前提（この前に実行）:
  1) load_yoonsun.py       # Yoon-sun 読み込み
  2) place_electrodes.py   # Elec_T7/P7/Fp1/Fp2 生成
  3) preflight_check.py    # セッションの汚れ確認（推奨）
  そのうえで本スクリプトを貼る。

盛り込んだ修正:
  - 材料名マッチのアンダースコア罠 → [a-z0-9]+ 分割で59組織を取りこぼさない（5bfd20b）。
  - ★全点NaNの真因 → 駆動電極 Elec_T7/P7 にも材料σを付与（無いとVoxelerが電極を除外しDirichlet=0）。
  - MANUAL に Ear_cartilage/Ear_skin の4行（9780afd。組織59+電極2=61 が期待値）。
  - v10: 新規simは document.AllSimulations.Add(sim) で登録。
  - 順序: 材料(組織+電極)→BC→(最後に)グリッド+CreateVoxels。
  - ★同名衝突対策（2026-07-30 の Run拒否 `HDF5: attribute already exists` 対策）:
      * sim 名は未使用のものを自動選択（tTIS_LF1 → 使用中なら tTIS_LF1_r2, _r3 …）。
      * GridBox_head は**既にあれば作らず再利用**（作り直しで重複エンティティが増えるのを防ぐ）。
  - ★Run とログ確認まで自動化（往復を減らす）: Run を try/except で回し、成否どちらでも
    dump_logs.py の dump_logs() があれば決定的なログ行を自動表示。E場の finite 率も出す。
"""
import re
import s4l_v1
import s4l_v1.model as model
import s4l_v1.document as document
import s4l_v1.simulation.emlf as emlf
import s4l_v1.materials as materials
import XCoreModeling as xc

RUN = True          # False にすると組み上げまでで止まる（Run は手動）
BASE_NAME = 'tTIS_LF1'
BC_ON_FACE = True   # ★Dirichlet BC を電極ソリッドではなく「外側の面」に付ける（下記）
HEAD_CENTER = (96.5, 258.9, 1566.8)   # 球フィットの中心O（面の内外判定に使う）


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
    'Ear_cartilage_left': 'Cartilage', 'Ear_cartilage_right': 'Cartilage',
    'Ear_skin_left': 'Skin', 'Ear_skin_right': 'Skin',
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

# ---- 新規 sim（★未使用の名前を選ぶ。既存 tTIS_LF1 と結果ファイルの衝突を避ける）----
used = set()
try:
    used = {s.Name for s in document.AllSimulations}
except Exception:
    pass
sim_name = BASE_NAME
k = 1
while sim_name in used:
    k += 1
    sim_name = '%s_r%d' % (BASE_NAME, k)
if sim_name != BASE_NAME:
    print('※ %s は使用中 → 衝突を避けて %s で作る（リロードすれば素の名前に戻る）'
          % (BASE_NAME, sim_name))

sim = emlf.ElectroQsOhmicSimulation(); sim.Name = sim_name
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


# ---- BC（+1V / 0V）----
# ★2026-07-30 の実測: 電極ソリッド(Body)に材料σと Dirichlet BC を**両方**付けると
#   Voxeler.log に `The boundary component 'Elec_T7' is not being considered in the voxeling process.`
#   が出て Run が拒否される（Input.log も生成されない＝ソルバー起動前で停止）。
#   同じエンティティが材料と BC の両方に登録されるため Input.h5 に同じ属性を二度書こうとして
#   `H5A__create(): attribute already exists` も出る。
#   → BC は**別エンティティ＝電極の外側の面**に付ける（BC_ON_FACE=True）。
#      面取得は xc.GetFaces / xc.IsPlanarFace（実機で存在を確認済み・2026-07-30）。
def outer_face(elec_name):
    """電極ソリッドの平面のうち、頭の中心から最も遠い面（＝外側の円板）を返す。"""
    ent = get_entity(elec_name)
    faces = list(xc.GetFaces(ent))
    best, best_d = None, -1.0
    for f in faces:
        try:
            if not xc.IsPlanarFace(f):        # 円筒の側面は除く
                continue
        except Exception:
            pass                              # 判定できない場合は候補に残す
        bb = xc.GetBoundingBox([f])
        if not bb:
            continue
        lo, hi = xyz(bb[0]), xyz(bb[1])
        c = [(lo[i] + hi[i]) / 2.0 for i in range(3)]
        d = sum((c[i] - HEAD_CENTER[i]) ** 2 for i in range(3))
        if d > best_d:
            best, best_d = f, d
    return best, len(faces)


def add_bc(elec, v, name):
    target = get_entity(elec)
    if BC_ON_FACE:
        try:
            f, nf = outer_face(elec)
            if f is not None:
                target = f
                try:    f.Name = elec + '_face_out'
                except Exception: pass
                print('  %s: 面BC を使用（面数 %d / 外側の面を選択）' % (elec, nf))
            else:
                print('  %s: 平面が見つからず → ソリッドBCにフォールバック' % elec)
        except Exception as e:
            print('  %s: 面の取得に失敗(%s) → ソリッドBCにフォールバック' % (elec, type(e).__name__))
    b = sim.AddBoundarySettings(target); b.Name = name
    b.BoundaryType = emlf.EnumBoundaryType.kDirichlet     # Deprecated 警告は無害
    b.DirichletValue = v


print('BC を設定:')
add_bc('Elec_T7', 1.0, 'BC_T7_pos')
add_bc('Elec_P7', 0.0, 'BC_P7_gnd')

# ---- グリッド → 最後にボクセル化 ----
ggs = sim.GlobalGridSettings; p = ggs.DiscretizationModeProp
p.set(p.findValue('Manual')); ggs.MaxStep = [5.0, 5.0, 5.0]
gb = get_entity('GridBox_head')            # ★既にあれば作らない（重複エンティティ防止）
if gb is None:
    gb = xc.CreateSolidBlock(V([4, 162, 1450]), V([202, 352, 1665]))
    gb.Name = 'GridBox_head'
    print('GridBox_head を新規作成')
else:
    print('GridBox_head は既存のものを再利用')
mg = sim.AddManualGridSettings(gb); mg.Name = 'Grid_head_1mm'; mg.MaxStep = [1.0, 1.0, 1.0]
sim.UpdateGrid(); sim.CreateVoxels()
document.Save()
print('組み上げ完了:', sim.Name)

# ---- Run（成否どちらでも証拠ログを出す）----
if RUN:
    ok = False
    try:
        sim.RunSimulation(wait=True)
        ok = True
        print('Run 完了。HasResults:', sim.HasResults())
    except Exception as e:
        print('★Run 拒否/失敗:', type(e).__name__, e)
        print('  → 下のログで "HDF5 / attribute already exists"（同名衝突）か')
        print('    "not being considered"（電極の材料漏れ）か切り分ける。')

    if ok:
        try:
            import numpy as np
            res = sim.Results(); res.UpdateAll()
            of = res['Overall Field']; of.Update()
            ef = of['EM E(x,y,z,f0)']; ef.Update()
            arr = ef.Data.Field(0)
            fin = np.isfinite(np.abs(arr)).all(axis=1)
            print('E場 shape:', arr.shape, '/ finite率: %.1f%%' % (100.0 * fin.mean()))
            if fin.mean() > 0.99:
                mag = np.sqrt(np.sum(np.abs(arr) ** 2, axis=1))
                print('|E| max: %.4g V/m  → ✅ Step1 ペア1 成功。次はペア2(Fp1/Fp2)。' % np.nanmax(mag))
            else:
                print('✗ NaN が残っている → Voxeler.log の "not being considered" を確認')
        except Exception as e:
            print('E場の取得に失敗:', type(e).__name__, e)

    d = globals().get('dump_logs')
    if d:
        d()
    else:
        print('※ ログを見るには dump_logs.py の中身を貼って実行する')

print('次にやること:')
print('  成功  → ペア2: 同じ手順を Elec_Fp1(+1V)/Elec_Fp2(0V) で tTIS_LF2 として組む → ti_analysis.py')
print('  拒否  → リロードして素の名前で1回だけ再試行 → それでも拒否なら')
print('          docs/support-inquiry-draft.md で ZMT サポート/フォーラムへ Input.log 添付で照会')
