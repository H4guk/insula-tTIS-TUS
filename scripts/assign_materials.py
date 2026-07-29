"""④ 頭部組織へ導電率 σ を割り当て（IT'IS LF DB 自動リンク・Sim4Life.lite）。

lec3 の「σ=0 で no dofs」の罠が Yoon-sun では 326 組織分あるが、
IT'IS の低周波(LF)物性 DB に自動リンクすれば一括で片付く（手打ち不要）。
グリッド内に入る頭部 59 組織だけσを割り当てれば足りる（ボクセル化は Grid 内のみ）。

方式（★実機で通した確定版・2026-07-23）:
  ① グリッド範囲にかかる組織を抽出（電極 / グループ / Model は除外）
  ② ViP 組織名 → ITISLF 材料名 の対応表を作る
     - 語順・括弧を無視した集合一致で自動マッチ（Cerebrum_grey_matter→Brain (Grey Matter) 等）
     - 自動で取れないものは手動対応表 MANUAL で補う
  ③ 各組織で AddMaterialSettings(ent単体) → LinkMaterialWithDatabase(ms, mat_object)
     ※ LinkMaterialWithDatabase の第2引数は Material オブジェクト（materials.database.ITISLF から取得）。
     ※ AddMaterialSettings は entity 単体を渡す（リスト [ent] ではない）。
  ④ skin 系だけ σ=0.465 に上書き（IT'IS の乾燥皮膚値は tES で非物理的・下記）。

出典ノート: Claude/Knowledge/sim4life-material-assignment.md（確立版・σ検算表・skin上書き）
           Claude/Knowledge/sim4life-yoonsun-implementation.md §6.5（対応表）

⚠️ 未解決（2026-07-23 時点）: この方式で 59 組織を割り当てても、実機の Run が
   `no used dofs / no lossy dielectrics` で全点 NaN になる事象が発生している。
   原因は「保存忘れによる状態喪失で不整合になった状態」か「DB リンクが σ を実際に
   セットしていない仕様」か切り分けできていない。次回クリーンな新規プロジェクトで再現確認する。
   → 再発したら σ を直接設定する方式（ElectricProps.Conductivity）へ切替を検討（未検証）。
"""
import s4l_v1.model as model
import s4l_v1.simulation.emlf as emlf
import s4l_v1.materials as materials
import XCoreModeling as xc
import re


def get_entity(name):
    hit = [e for e in model.AllEntities() if e.Name == name]
    return hit[0] if hit else None


def xyz(v):
    try:    return float(v[0]), float(v[1]), float(v[2])
    except: return float(v.X), float(v.Y), float(v.Z)


# ① IT'IS 低周波(LF)物性 DB
itis = materials.database.ITISLF
db_names = [m.Name for m in itis.AllMaterials]


def get_mat(db_name):
    for m in itis.AllMaterials:
        if m.Name == db_name:
            return m
    return None


# ② グリッド範囲（頭部 envelope + マージン）にかかる組織を抽出
GX, GY, GZ = (4, 202), (162, 352), (1450, 1665)
head = set()
for e in model.AllEntities():
    bb = xc.GetBoundingBox([e])
    if not bb:
        continue
    lo, hi = xyz(bb[0]), xyz(bb[1])
    if hi[2] >= GZ[0] and lo[2] <= GZ[1] and hi[0] >= GX[0] and lo[0] <= GX[1] \
       and hi[1] >= GY[0] and lo[1] <= GY[1]:
        if e.Name.startswith('Elec_') or 'Yoon' in e.Name \
           or e.Name in ('Bones', 'Model', 'GridBox_head'):
            continue
        head.add(e.Name)


# ③ ViP 組織名 → ITISLF 材料名 の対応表
def _words(s):
    # ★アンダースコアで必ず区切る: \w は '_' を単語文字扱いにするため
    #   'Cerebrospinal_fluid' が1トークンになり DB 'Cerebrospinal Fluid'(2語) と一致しない。
    #   [a-z0-9]+ で切ると _ / 空白 / 括弧 / バックスラッシュ すべてが区切りになる。
    return set(re.findall(r'[a-z0-9]+', s.lower()))


def try_match(vip):
    """語順・括弧・アンダースコアを無視した集合一致で DB 材料名を探す。"""
    vw = _words(vip)
    for db in db_names:
        if _words(db) == vw:
            return db
    return None


# 自動マッチしないものの手動対応表
MANUAL = {
    'Cerebrum_grey_matter':  'Brain (Grey Matter)',
    'Cerebrum_white_matter': 'Brain (White Matter)',
    'Corpus_callosum':       'Brain (White Matter)',
    'Dura_mater':            'Dura',
    'Artery':                'Blood',
    'Vein':                  'Blood',
    'SAT':                   'SAT (Subcutaneous Fat)',
    'Ear_cartilage_left':    'Cartilage',
    'Ear_cartilage_right':   'Cartilage',
    'Ear_skin_left':         'Skin',
    'Ear_skin_right':        'Skin',
    'Mucosa':                'Mucous Membrane',
    'Air_internal':          'Air',
    'Mandible_cortical':     'Skull (Cortical)',
    'Mandible_cancellous':   'Skull (Cancellous)',
    'Hyoid_cortical':        'Bone (Cortical)',
    'Trachea_wall':          'Trachea',
    'Esophagus_wall':        'Esophagus',
    'Lymph_node':            'Lymphnode',
}
for i in range(1, 6):
    MANUAL['Vertebra_cortical_C%d' % i]   = 'Bone (Cortical)'
    MANUAL['Vertebra_cancellous_C%d' % i] = 'Bone (Cancellous)'

full_map = {}
for t in head:
    m = try_match(t) or MANUAL.get(t)
    if m:
        full_map[t] = m

# ④ Electro QS 作成 → 各組織を DB リンクしてσをロード
sim = emlf.ElectroQsOhmicSimulation()
sim.Name = 'tTIS_LF1'
sim.SetupSettings.Frequency = 2000.0

ok = 0
created = {}                                       # 組織名 → MaterialSettings（skin 上書き用）
for vip, db_name in full_map.items():
    ent, mat = get_entity(vip), get_mat(db_name)
    if ent is None or mat is None:
        continue
    ms = sim.AddMaterialSettings(ent)              # ★entity 単体（リストではない）
    ms.Name = vip
    sim.LinkMaterialWithDatabase(ms, mat)         # ★第2引数は Material オブジェクト
    created[vip] = ms
    ok += 1
sim.UpdateAllMaterials()

# ⑤ skin 系だけ tES 標準の実効頭皮 σ に上書き（★sim4life-material-assignment.md・2026-07-23 実機確立）
#   IT'IS LF の Skin は σ=0.0002 S/m（乾燥角質の実測値）で、tES/tTIS では非物理的
#   （電極から電流が頭皮に入らない）。tES はゲル/スポンジで角質層をバイパスする前提なので、
#   実効頭皮 σ=0.465 S/m（SimNIBS/ROAST 標準）へ上書きする。Ear_skin も同様。
#   ⚠️ DatabaseLink は読取専用だが ElectricProps.Conductivity は直接上書きでき、
#      UpdateAllMaterials() 後も保持される（実機確認）。ボクセル化/Run 直前に skin σ を再確認すると安全。
SKIN_OVERRIDE = 0.465
overridden = []
for nm in ('Skin', 'Ear_skin_left', 'Ear_skin_right'):
    if nm in created:
        created[nm].ElectricProps.Conductivity = SKIN_OVERRIDE
        overridden.append(nm)
sim.UpdateAllMaterials()

print('材料割り当て組織数:', ok)
print('sim.AllComponents:', len(list(sim.AllComponents)))
print('skin σ 上書き:', overridden, '→', SKIN_OVERRIDE, 'S/m')
# ⚠️ Run 前に SolverLog で "used dofs" が 0 でないか確認すること（全点 NaN の早期検知）。
# ⚠️ σ検算（sim4life-material-assignment.md）: skin 0.465 / 皮質骨 ~0.020 / CSF ~2.0 /
#    灰白 ~0.103 / 白質 ~0.064。ボクセル化前にこのレンジに収まるか確認すると安全。
