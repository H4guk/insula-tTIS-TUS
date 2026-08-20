"""T-5a グリッド設定 → ボクセル化（焼成のみ・Sim4Life.lite Python コンソール）。

tTIS の setup_grid.py の音響版。TUS_250k に対しグリッドを与えて焼く。
判定は verify_voxels 相当（T-5b）を**このスクリプトが終わってから**別に実行する
（実行中のスクリプトからは自分が焼いた Voxeler.log が見えない・tTIS で確定した鉄則）。

★グリッド箱は頭部＋トランスデューサを内包する（ソース面を 1mm で刻むため）:
  tTIS 頭部箱 ∪ Transducer の実 bbox ＋余白 PAD（水結合層・境界用）。
★AutomaticGridSettings は使わない（自動細分でセル爆発＝tTIS の教訓）。
  Global Manual 5mm（周辺は粗く）＋ 箱に Manual 1mm。
★250kHz/1mm は脳(c=1500)で 6セル/λ ＝ 数値分散のフロア。UpdateGrid のセル数と Invalid を必ず確認。

流れ:
  ① 事前ゲート（sim・材料59+・Source・Voxeler 登録60）
  ② AutomaticGridSettings 削除
  ③ 箱を作成（頭部∪Transducer＋PAD）→ Global 5mm・箱 1mm → UpdateGrid → セル数確認
  ④ CreateVoxels → BAKE_WAIT 待つ → Save
"""
import time
import numpy as np
import s4l_v1.document as document
import s4l_v1.model as model
import XCoreModeling as xc

SIM_NAME = 'TUS_250k'
BOX_NAME = 'GridBox_TUS'
HEAD_BOX = ((4, 162, 1450), (202, 352, 1665))     # tTIS 頭部範囲
TRANSDUCER = 'Transducer'
PAD = 10.0                             # 箱の余白 [mm]（水結合層・境界）

BODY_STEP = 5.0                        # 周辺（粗くてよい）
HEAD_STEP = 1.0                        # 1mm（250kHz で 6セル/λ）
RESOLUTION = 1.0
CELL_LIMIT = 20_000_000
N_TISSUE = 59
N_REG = 60                             # 59組織 + Transducer
BAKE_WAIT = 200                        # 秒（焼成＋保存の見込み）


def V(p):
    return model.Vec3(*map(float, p))


def xyz(v):
    try:    return np.array([float(v[0]), float(v[1]), float(v[2])])
    except: return np.array([float(v.X), float(v.Y), float(v.Z)])


def base(name):
    return name.split('  (')[0].strip()


# ===== ① 事前ゲート =====
sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

n_mat = sum(1 for s in sim.AllSettings if type(s).__name__ == 'MaterialSettings')
n_src = sum(1 for s in sim.AllSettings if type(s).__name__ == 'SourceSettings')
n_reg = sum(1 for c in sim.AllComponents if 'Automatic Voxeler Settings' in c.Settings.keys())
print('[pre ] materials=%d  sources=%d  voxeler-registered=%d' % (n_mat, n_src, n_reg))
if n_mat < N_TISSUE:
    raise SystemExit('[pre ] FAILED — T-2 未完（材料 %d）' % n_mat)
if n_src < 1:
    raise SystemExit('[pre ] FAILED — T-3 未完（Source %d）' % n_src)
if n_reg < N_REG:
    raise SystemExit('[pre ] FAILED — Voxeler 登録 %d < %d' % (n_reg, N_REG))

# ===== ② AutomaticGridSettings 削除 =====
for s in [s for s in sim.AllSettings if type(s).__name__ == 'AutomaticGridSettings']:
    sim.RemoveSettings(s)
    print('[grid] removed AutomaticGridSettings:', s.Name)

# ===== ③ 箱（頭部 ∪ Transducer ＋ PAD）=====
tr = [e for e in model.AllEntities() if e.Name == TRANSDUCER]
if len(tr) != 1:
    raise SystemExit('[grid] FAILED — %r が %d 個' % (TRANSDUCER, len(tr)))
tb = xc.GetBoundingBox([tr[0]])
tlo, thi = xyz(tb[0]), xyz(tb[1])
hlo = np.array(HEAD_BOX[0], float)
hhi = np.array(HEAD_BOX[1], float)
lo = np.minimum(hlo, tlo) - PAD
hi = np.maximum(hhi, thi) + PAD
size = hi - lo
print('[grid] Transducer bbox: %s .. %s' % (np.round(tlo, 1), np.round(thi, 1)))
print('[grid] 箱 %s .. %s  size=%s mm' % (np.round(lo, 1), np.round(hi, 1), np.round(size, 1)))
est = np.prod(size / HEAD_STEP)
print('[grid] 1mm での概算セル数（箱のみ）: %s' % format(int(est), ','))

# Global grid（周辺 5mm）
ggs = sim.GlobalGridSettings
p = ggs.DiscretizationModeProp
p.set(p.findValue('Manual'))
ggs.MaxStep = [BODY_STEP] * 3
ggs.Resolution = [RESOLUTION] * 3

# 箱の作成（既存は掃除して作り直す）
for e in [e for e in model.AllEntities() if e.Name == BOX_NAME]:
    e.Delete()
box = xc.CreateSolidBlock(V(lo), V(hi))
box.Name = BOX_NAME
print('[grid] created', BOX_NAME)

# 箱に Manual 1mm（重複掃除→無ければ作成→紐付け確認）
mans = [s for s in sim.AllSettings if type(s).__name__ == 'ManualGridSettings']
for s in mans[1:]:
    sim.RemoveSettings(s)
mans = [s for s in sim.AllSettings if type(s).__name__ == 'ManualGridSettings']
mg = mans[0] if mans else sim.AddManualGridSettings(box)
if not [c for c in sim.AllComponents if base(c.Name) == BOX_NAME]:
    sim.Add(mg, [box])
    print('[grid] bound %s to manual grid' % BOX_NAME)
mg.Name = 'Grid_TUS_%gmm' % HEAD_STEP
mg.MaxStep = [HEAD_STEP] * 3

sim.UpdateGrid()
grid_name = ggs.Name
print('[grid] body=%gmm head=%gmm -> %s' % (BODY_STEP, HEAD_STEP, grid_name))
if 'Invalid' in grid_name:
    raise SystemExit('[grid] FAILED — グリッドが計算できない（範囲か刻みを見直す）')

# ===== ④ ボクセル化（焼成のみ）=====
t0 = time.time()
sim.CreateVoxels()
print('[vox ] CreateVoxels returned（非同期）')
time.sleep(BAKE_WAIT)
document.Save()
print('[vox ] baked+saved in %.0f s' % (time.time() - t0))
print('    grid:', grid_name)
print('=== T-5a（焼成）完了 ===')
print('    次: このスクリプトが終わってから T-5b（verify）を実行して判定する')
