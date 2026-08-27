"""工程5 材料σの割り当てと Voxeler への登録（Sim4Life.lite Python コンソール）。

2026-08-03 に判明した根本原因への対処を含む。**σ を付けるだけでは voxeler の対象にならない**。
同じエンティティを **Voxeler 設定にも登録**しないと
`... is not being considered in the voxeling process` → 空ボクセル → 0 unknowns → 全点 NaN になる。

⚠️ 登録するのは **Voxeler だけ**。Grid（AutomaticGridSettings）には登録しない
（登録すると自動グリッドが暴走して `Cell limit exceeded` になる。詳細は工程7 `setup_grid.py`）。

⚠️⚠️ **電極には σ を付けない**（2026-08-03 実機で確定）。材料σと Dirichlet BC を同一ソリッドに
載せると HDF5 が同じ属性を二度書き（`H5A__create(): attribute already exists`）、
`Unable to run simulation` で Run が拒否される（`Input.h5` は出来るが `Input.log` が無い＝
ソルバー起動前で停止）。失うものは無く、Dirichlet を付けた電極は
`will be reassigned to PEC because it constitutes to internal boundary conditions` として
**PEC 扱いになり σ は元々使われない**。電極は **Voxeler 登録 ＋ BC（工程6）**だけでよい。

流れ:
  ① 対象エンティティを確定（頭部組織59 ＋ 電極4 ＝ 63）
  ② 事前ゲート（電極4枚が実在 / タグ無しでグリッド内のものが 0 件）  ← #32 の再発防止
  ② 事前ゲート（続き）: 使う材料が **DB_NAME に全部あるか**を sim を作る前に確認  ← 2026-08-09 追加
  ③ Electro QS Ohmic シミュを作成し**組織59個だけ**に σ を割り当て（材料オブジェクトでリンク）
  ④ Voxeler 設定に**63個すべてを登録**（電極も含む）           ← 2026-08-03 の修正の本体
  ⑤ 事後ゲート（材料59件 / 欠落0 / **σ を DB 格納値と直接照合** / 登録63件）  ← #33 の要件

ペア2 を作るときは SIM_NAME と FREQ だけ変える（tTIS_LF2 / 2010.0）。
本スクリプトは CreateVoxels を実行しない。鉄則は 材料σ → 電極BC（工程6）→ 最後にボクセル化（工程7）。
先に焼くと工程6 の設定追加が `incompatible with this type of simulation` で弾かれる。

出典ノート: Claude/Knowledge/sim4life-material-assignment.md「★★最重要」節
"""
import s4l_v1.document as document
import s4l_v1.model as model
import s4l_v1.simulation.emlf as emlf
import XCoreModeling as xc
import numpy as np

SIM_NAME = 'tTIS_LF2'                  # ペア1 は 'tTIS_LF1'
FREQ = 2010.0                          # ペア1 = T7/P7 で 2000.0。ペア2 = Fp1/Fp2 で 2010.0

# ★2026-08-09: 材料は **DB を明示して材料オブジェクトで渡す**。
#   `LinkMaterialWithDatabase(ms, '材料名')` と名前文字列を渡すと既定の（非 LF）DB を引く。
#   非 LF 系は σ をスカラーで持たず Gabriel 4-Cole-Cole を評価するため、2 kHz では
#   白質 0.064 / 灰白質 0.103 / 皮質骨 0.020 / **乾燥皮膚 0.0002** という低周波外挿値になる。
#   2 kHz は LF DB の想定帯域なので LF 5.0 の固定値を使う（白質 0.348 / 灰白質 0.419 /
#   皮質骨 0.0063 / Skin 0.1483）。判断の経緯は Claude/DailyLogs/2026-08-09.md。
DB_NAME = "IT'IS LF 5.0"

GX, GY, GZ = (4, 202), (162, 352), (1450, 1665)     # 頭部グリッド範囲（工程2 実測）
ELEC = ('Elec_T7', 'Elec_P7', 'Elec_Fp1', 'Elec_Fp2')
SKIP_EXACT = ('Model', 'Grid', 'Bones',             # Bones は EntityGroup（実体なし）
              'GridBox_head',                       # 工程7 のグリッド用補助ブロック（材料もσも持たない）
              'GridBox_TUS',                        # TUS 側のグリッド箱（統合プロジェクトでは同居する）
              'Transducer')                         # ★統合（#36 5-1）用: TUS の音源。tTIS では場に入れない
#   ↑ Transducer / GridBox_TUS は **統合プロジェクトでのみ存在**する。tTIS の電場に参加させないので
#     材料も σ も付けず、Voxeler にも登録しない（登録しなければ電場に存在しない）。2026-08-27 追加。
SKIN_NAMES = ('Skin', 'Ear_skin_left', 'Ear_skin_right')

# skin の上書きは **やめた**（2026-08-09）。0.465 を入れていた唯一の根拠は「DB 値 0.0002 が
# 非物理的（乾燥角質）」だったが、それは非 LF DB を引いていたことによる値で、LF 5.0 では 0.1483。
# また 0.465 は SimNIBS/ROAST の **scalp（皮膚＋脂肪＋筋の合成値）** であり、
# Yoon-sun は Skin / Fat / SAT / Muscle を別エンティティで持つので二重計上になる。
# 上書きに戻すときは数値を入れる（None ＝ DB の値をそのまま使う）。
SIGMA_SKIN = None

N_TISSUE = 59                          # グリッド内の頭部組織（工程5-2 実測）＝σを付ける数
N_TOTAL = N_TISSUE + len(ELEC)         # = 63。Voxeler に登録する数（電極は σ 無しで登録のみ）

# 生体組織として非現実的な値を弾くだけの粗いレンジ（個別の期待値は DB と直接突き合わせる）
SANE_LO, SANE_HI = 1e-3, 3.0
SIGMA_TOL = 0.01                       # sim の σ と DB 格納値の許容相対差


def xyz(v):
    try:    return np.array([float(v[0]), float(v[1]), float(v[2])])
    except: return np.array([float(v.X), float(v.Y), float(v.Z)])


def in_grid(e):
    try:
        bb = xc.GetBoundingBox([e])
    except Exception:
        return False
    lo, hi = xyz(bb[0]), xyz(bb[1])
    return (lo[0] <= GX[1] and hi[0] >= GX[0] and
            lo[1] <= GY[1] and hi[1] >= GY[0] and
            lo[2] <= GZ[1] and hi[2] >= GZ[0])


def base(name):
    """component.Name の接尾辞 '  (Yoon-sun v3.1 Static/Bones)' を落としてエンティティ名に戻す。"""
    return name.split('  (')[0].strip()


def db_sigma(mat):
    """DB の材料オブジェクトから σ を読む。

    `mat.electric_conductivity` はクラス属性の descriptor が返るだけで
    `TypeError: 'property' object is not iterable` になる（2026-08-09 実測）ので
    `AllProperties` から引く。名前は `Name` ではなく `VariableName` に入っている。
    """
    for p in mat.AllProperties:
        nm = str(getattr(p, 'VariableName', None) or getattr(p, 'Description', None))
        if nm == 'electric_conductivity':
            return float(p.Value)
    return None


# ===== ① 対象エンティティの確定 =====
ents = list(model.AllEntities())
elecs = [e for e in ents if e.Name in ELEC]
cands = [e for e in ents
         if e.Name not in SKIP_EXACT
         and e.Name not in ELEC
         and 'Yoon' not in e.Name
         and type(e).__name__ != 'EntityGroup']
model.AutoAssignMaterials(cands)       # 組織名 → ViP 材料名を entity.MaterialName に入れる
head = [e for e in cands if getattr(e, 'MaterialName', None) and in_grid(e)]
targets = head + elecs

# ===== ② 事前ゲート =====
missing_elec = [n for n in ELEC if n not in [e.Name for e in elecs]]
danger = [e for e in cands if not getattr(e, 'MaterialName', None) and in_grid(e)]
print('[pre ] tissues=%d electrodes=%d total=%d (expected %d)'
      % (len(head), len(elecs), len(targets), N_TOTAL))
print('[pre ] missing electrodes:', missing_elec)
print('[pre ] untagged but inside grid:', [e.Name for e in danger])
if missing_elec or danger or len(targets) != N_TOTAL:
    raise SystemExit('[pre ] FAILED — 対象集合が期待どおりでないので中断する')

dup = [s.Name for s in document.AllSimulations if s.Name == SIM_NAME]
if dup:
    raise SystemExit('[pre ] FAILED — 同名 sim が既にある: %s（先に削除するか SIM_NAME を変える）' % SIM_NAME)

# 使う材料が LF DB に全部あるかを **sim を作る前に** 確認する。
# ここで落ちれば副作用ゼロで中断できる（無い材料を既定 DB で補うと今回のバグの再来になる）。
#
# ★表記ゆれを吸収する（2026-08-11）: `e.MaterialName` は `Skull Cortical`（括弧なし）だが
#   DB のキーは `Skull (Cortical)`（括弧つき）で、完全一致では引けない。この2つは別名も持たない
#   ＝純粋な表記ゆれ。そこで **完全一致 → 正規化名 → 別名** の順に探す。
#   ただし**完全一致でなかったものは必ず出力に出す**。黙って曖昧一致させると
#   「もっともらしい別材料に当たっても気づかない」という GH #11 の懸念そのものに戻る。
import s4l_v1.materials as materials
db = materials.database[DB_NAME]
db_all = list(db.AllMaterials)


def norm_name(s):
    return ''.join(ch for ch in str(s).lower() if ch.isalnum())


def resolve_material(nm):
    """材料名を DB の材料オブジェクトに解決する。戻り値 (材料, 解決方法)。"""
    try:
        m = db[nm]
        if m is not None:
            return m, 'exact'
    except Exception:
        pass
    key = norm_name(nm)
    for m in db_all:                    # 正規化名の一致（括弧・記号・大小の違いを吸収）
        if norm_name(m.Name) == key:
            return m, 'normalized'
    for m in db_all:                    # 別名の一致
        try:
            aliases = list(getattr(m, 'Aliases', None) or [])
        except Exception:
            aliases = []
        if any(norm_name(a) == key for a in aliases):
            return m, 'alias'
    return None, None


want = sorted(set(e.MaterialName for e in head))
db_mat, db_sig, absent, fuzzy = {}, {}, [], []
for nm in want:
    m, how = resolve_material(nm)
    s = db_sigma(m) if m is not None else None
    if m is None or s is None:
        absent.append(nm)
        continue
    db_mat[nm], db_sig[nm] = m, s
    if how != 'exact':
        fuzzy.append((nm, m.Name, how, s))
print('[pre ] DB=%s  材料 %d/%d 解決' % (DB_NAME, len(db_mat), len(want)))
for nm, resolved, how, s in fuzzy:
    print('[pre ] 完全一致でない解決: %-22s -> %-22s (%s) sigma=%.6g' % (nm, resolved, how, s))
if absent:
    raise SystemExit('[pre ] FAILED — %s に無い材料: %s' % (DB_NAME, absent))

# ===== ③ シミュ作成とσ割り当て =====
sim = emlf.ElectroQsOhmicSimulation()
sim.Name = SIM_NAME
document.AllSimulations.Add(sim)
sim.SetupSettings.Frequency = FREQ

created = {}
for e in head:
    ms = sim.AddMaterialSettings(e)
    ms.Name = e.MaterialName
    # ★材料**オブジェクト**を渡す。名前文字列だと既定の（非 LF）DB を引く（冒頭の注意を参照）
    sim.LinkMaterialWithDatabase(ms, db_mat[e.MaterialName])
    created[e.Name] = ms
# 電極には材料を作らない（BC と同居させると Run が拒否される。冒頭の注意を参照）
sim.UpdateAllMaterials()

if SIGMA_SKIN is not None:              # 既定は None ＝ DB の値をそのまま使う
    for nm in SKIN_NAMES:
        created[nm].ElectricProps.Conductivity = SIGMA_SKIN
    sim.UpdateAllMaterials()
    print('[sig ] skin 系 %d 件を σ=%g に上書きした' % (len(SKIN_NAMES), SIGMA_SKIN))
else:
    print('[sig ] skin 系は上書きせず DB 値を使う（%s = %.4f S/m）'
          % (DB_NAME, db_sig.get('Skin', float('nan'))))
print('[sig ] created material settings: %d' % len(created))

# ===== ④ Voxeler への登録（2026-08-03 の修正・これが無いと焼かれない）=====
# ★Grid（AutomaticGridSettings）には登録しない。登録すると自動グリッドが解剖メッシュの形状に
#   合わせて自前で細分し、MaxStep と無関係にセル数が爆発して Cell limit exceeded になる。
#   グリッドの刻みは工程7（setup_grid.py）で Global + 頭部 Block の Manual として与える。
vox = [s for s in sim.AllSettings if type(s).__name__ == 'AutomaticVoxelerSettings'][0]
for e in targets:
    sim.Add(vox, [e])
print('[reg ] registered to voxeler: %d' % len(targets))

# ===== ⑤ 事後ゲート =====
fail = []

miss = sorted(set(e.Name for e in head) - set(created.keys()))
print('[post] material settings %d/%d  missing=%s' % (len(created), N_TISSUE, miss))
if len(created) != N_TISSUE or miss:
    fail.append('material settings')

# σ 検算は **リンク先 DB の格納値と直接突き合わせる**（2026-08-09 変更）。
# 期待値をハードコードしていると、別 DB を引いてしまう事故（2026-08-09 に発覚）が
# 「期待値の方を書き換えれば通る」形になり検出できない。DB と比べれば原理的に検出できる。
# ★期待値は **エンティティ名**でキーを張る（2026-08-11 修正）。
#   `LinkMaterialWithDatabase` は **リンク時に MaterialSettings の名前を DB 側の正式名へ
#   書き換える**（`Skull Cancellous` → `Skull (Cancellous)`）。`ms.Name` で `db_sig` を引くと、
#   表記ゆれを吸収した材料でだけ空振りして「σ が読めない」と誤判定する。
exp_by_ent = dict((e.Name, db_sig[e.MaterialName]) for e in head)

ng = []
for ent, ms in sorted(created.items()):
    mat = ms.Name
    exp = exp_by_ent.get(ent)
    try:
        act = float(ms.ElectricProps.Conductivity)
    except Exception:
        act = None
    if SIGMA_SKIN is not None and ent in SKIN_NAMES:
        exp = SIGMA_SKIN                # 意図的な上書きぶんは上書き値と比べる
    if act is None or exp is None:
        ng.append((ent, mat, exp, act, 'σ が読めない'))
        continue
    if abs(act - exp) > max(1e-6, abs(exp) * SIGMA_TOL):
        ng.append((ent, mat, exp, act, 'DB 格納値と不一致'))
    elif mat.lower() != 'air' and not (SANE_LO <= act <= SANE_HI):
        ng.append((ent, mat, exp, act, '生体組織として非現実的'))
print('[post] sigma check NG: %d' % len(ng))
for ent, mat, exp, act, why in ng:
    print('       %-28s -> %-28s DB=%s sim=%s  %s' % (ent, mat, exp, act, why))
if ng:
    fail.append('sigma')

names = set(e.Name for e in targets)
reg = [c for c in sim.AllComponents
       if base(c.Name) in names
       and 'Automatic Voxeler Settings' in c.Settings.keys()]
notreg = sorted(names - set(base(c.Name) for c in reg))
print('[post] registered components %d/%d  not registered=%s' % (len(reg), N_TOTAL, notreg))
if len(reg) != N_TOTAL:
    fail.append('registration')

print('=== 工程5 %s ===' % ('PASS' if not fail else 'FAILED: ' + ', '.join(fail)))
document.Save()
print('saved.')
