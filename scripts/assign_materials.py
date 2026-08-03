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
  ③ Electro QS Ohmic シミュを作成し**組織59個だけ**に σ を割り当て（DB リンク → skin 0.465 上書き）
  ④ Voxeler 設定に**63個すべてを登録**（電極も含む）           ← 2026-08-03 の修正の本体
  ⑤ 事後ゲート（材料59件 / 欠落0 / σ検算 / 登録63件）          ← #33 の要件

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

SIM_NAME = 'tTIS_LF1'
FREQ = 2000.0                          # ペア1 = T7/P7。ペア2 は 2010.0

GX, GY, GZ = (4, 202), (162, 352), (1450, 1665)     # 頭部グリッド範囲（工程2 実測）
ELEC = ('Elec_T7', 'Elec_P7', 'Elec_Fp1', 'Elec_Fp2')
SKIP_EXACT = ('Model', 'Grid', 'Bones',             # Bones は EntityGroup（実体なし）
              'GridBox_head')                       # 工程7 のグリッド用補助ブロック（材料もσも持たない）
SKIN_NAMES = ('Skin', 'Ear_skin_left', 'Ear_skin_right')

SIGMA_SKIN = 0.465                     # tES 実効頭皮σ（IT'IS LF の 0.0002 は乾燥角質で非物理的）

N_TISSUE = 59                          # グリッド内の頭部組織（工程5-2 実測）＝σを付ける数
N_TOTAL = N_TISSUE + len(ELEC)         # = 63。Voxeler に登録する数（電極は σ 無しで登録のみ）

CHECK = {'Skin': 0.465, 'Skull_cortical': 0.020, 'Skull_cancellous': 0.082,
         'Cerebrospinal_fluid': 2.00, 'Cerebrum_grey_matter': 0.103,
         'Cerebrum_white_matter': 0.064, 'Cerebellum': 0.123, 'Muscle': 0.330}


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

# ===== ③ シミュ作成とσ割り当て =====
sim = emlf.ElectroQsOhmicSimulation()
sim.Name = SIM_NAME
document.AllSimulations.Add(sim)
sim.SetupSettings.Frequency = FREQ

created = {}
for e in head:                          # 組織は IT'IS LF DB から材料名で引く
    ms = sim.AddMaterialSettings(e)
    ms.Name = e.MaterialName
    sim.LinkMaterialWithDatabase(ms, e.MaterialName)
    created[e.Name] = ms
# 電極には材料を作らない（BC と同居させると Run が拒否される。冒頭の注意を参照）
sim.UpdateAllMaterials()

for nm in SKIN_NAMES:                   # DB 値 0.0002 を tES 実効値に上書き
    created[nm].ElectricProps.Conductivity = SIGMA_SKIN
sim.UpdateAllMaterials()
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

ng = []
for nm, exp in sorted(CHECK.items()):
    act = float(created[nm].ElectricProps.Conductivity) if nm in created else None
    if act is None or abs(act - exp) > max(0.005, exp * 0.05):
        ng.append((nm, exp, act))
print('[post] sigma check NG: %d %s' % (len(ng), ng))
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
