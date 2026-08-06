"""工程7 グリッド設定 → ボクセル化（Sim4Life.lite Python コンソール）。

工程5（`assign_materials.py`）・工程6（`setup_boundary.py`）が済んだ sim に対して実行する。

**AutomaticGridSettings は使わない**（2026-08-03 確定）。
`sim.Add(grd, [e])` で63個を自動グリッドに登録すると、自動グリッドが解剖メッシュの形状に合わせて
自前で細分するため、グローバルの `MaxStep` と無関係にグリッド線が爆発して
`Cell limit exceeded` になる（グローバル 50mm・頭部 20mm まで粗くしても失敗した）。
`AutomaticGridSettings` を丸ごと削除すると通る。刻みは
**GlobalGridSettings（体）＋ 頭部を囲む Block への ManualGridSettings（頭）**で与える。

★API が成否も完了も戻り値で教えてくれない点に注意（2026-08-03 実測）:
  - `sim.UpdateGrid()` は**失敗しても例外を投げない**。判定は `GlobalGridSettings.Name` を見る
    （`Grid (Invalid)` / `Grid 125 x 121 x 134 = 2.027 MCells`）
  - `sim.CreateVoxels()` は**戻ってきても焼き終わっていない**（実測 13.9 秒）

★★ 検証は別スクリプト `verify_voxels.py` で行う（2026-08-06 確定・GH Issue #12）:
  **実行中のスクリプトからは、自分が焼いた `Voxeler.log` は見えない。**
  ファイルが現れるのは**スクリプトが終了したあと**で、実行中に何秒待っても・何回 `document.Save()` を
  呼んでも現れない（2026-08-06 実測: 焼成は 13.89 秒で完了しているのに、97 / 154 / 211 / 269 / 326 秒の
  時点の Save では出ず、スクリプト終了時に書かれた）。2026-08-03 の「Save のときに書き出される」は誤り。
  → **同一スクリプト内で待つ設計は原理的に成立しない**ので、焼成と検証を分ける。

流れ（このスクリプト＝工程7-a）:
  ① 事前ゲート（sim が1つ・材料と BC が入っている）
  ② AutomaticGridSettings を削除
  ③ グリッド設定（体 BODY_STEP / 頭部 Block に HEAD_STEP）→ UpdateGrid → セル数を確認
  ④ CreateVoxels → 焼成ぶんだけ待つ（BAKE_WAIT）→ document.Save() → 終了
  ⑤ 判定は `verify_voxels.py`（工程7-b）を**このスクリプトが終わってから**実行する

判定に `Voxel Scene Memory Consumption` は使わない（幾何の複雑さの指標であって中身の量ではない）。
**エンティティ単位の `Voxels:` 件数**で判定する。

出典ノート: Claude/Knowledge/sim4life-material-assignment.md
"""
import time
import s4l_v1.document as document
import s4l_v1.model as model
import XCoreModeling as xc

SIM_NAME = 'tTIS_LF1'
BOX_NAME = 'GridBox_head'
HEAD_BOX = ((4, 162, 1450), (202, 352, 1665))     # 工程2 実測の頭部グリッド範囲

BODY_STEP = 5.0                       # 体（電流の帰り道。粗くてよい）
HEAD_STEP = 2.0                       # dev は 2mm。prod（#37）で 1.0 に上げる
RESOLUTION = 2.0                      # 既定 0.0625mm は細かすぎる

N_TISSUE = 59                         # σ を持つ頭部組織
N_TOTAL = 63                          # Voxeler 登録数（頭部組織59 + 電極4）
BAKE_WAIT = 40                        # 秒。焼成の実測は 13.9 秒（dev 2.027 MCells）。prod では伸ばす


def V(p):
    return model.Vec3(*map(float, p))


def base(name):
    return name.split('  (')[0].strip()


# ===== ① 事前ゲート =====
sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

# 材料は「頭部組織59 ＋ 既定の Air」で 60 になる（電極には σ を付けないので 63 にはならない）。
# BC は「駆動2 ＋ 既定の Boundary Settings」で 3。
n_mat = sum(1 for s in sim.AllSettings if type(s).__name__ == 'MaterialSettings')
n_bc = sum(1 for s in sim.AllSettings if type(s).__name__ == 'BoundarySettings')
n_reg = sum(1 for c in sim.AllComponents if 'Automatic Voxeler Settings' in c.Settings.keys())
print('[pre ] materials=%d  boundaries=%d  voxeler-registered=%d' % (n_mat, n_bc, n_reg))
if n_mat < N_TISSUE:
    raise SystemExit('[pre ] FAILED — 工程5 が済んでいない（材料 %d < %d）' % (n_mat, N_TISSUE))
if n_bc < 3:
    raise SystemExit('[pre ] FAILED — 工程6 が済んでいない（BC %d < 3）' % n_bc)
if n_reg < N_TOTAL:
    raise SystemExit('[pre ] FAILED — Voxeler 登録が %d 件（期待 %d）' % (n_reg, N_TOTAL))

# ===== ② AutomaticGridSettings を削除（これが Cell limit exceeded の原因）=====
for s in [s for s in sim.AllSettings if type(s).__name__ == 'AutomaticGridSettings']:
    sim.RemoveSettings(s)
    print('[grid] removed AutomaticGridSettings:', s.Name)

# ===== ③ グリッド設定 =====
ggs = sim.GlobalGridSettings
p = ggs.DiscretizationModeProp
p.set(p.findValue('Manual'))          # enum は findValue → set が正解パターン
ggs.MaxStep = [BODY_STEP] * 3
ggs.Resolution = [RESOLUTION] * 3

hit = [e for e in model.AllEntities() if e.Name == BOX_NAME]
box = hit[0] if hit else None
if box is None:
    box = xc.CreateSolidBlock(V(HEAD_BOX[0]), V(HEAD_BOX[1]))
    box.Name = BOX_NAME
    print('[grid] created', BOX_NAME)
else:
    print('[grid] reuse', BOX_NAME)

mans = [s for s in sim.AllSettings if type(s).__name__ == 'ManualGridSettings']
for s in mans[1:]:                    # 二重実行で増えた分を掃除（同名で複数できる）
    sim.RemoveSettings(s)
    print('[grid] removed duplicate ManualGridSettings:', s.Name)
mans = [s for s in sim.AllSettings if type(s).__name__ == 'ManualGridSettings']
mg = mans[0] if mans else sim.AddManualGridSettings(box)

box_keys = [sorted(c.Settings.keys()) for c in sim.AllComponents
            if base(c.Name) == BOX_NAME]
if not box_keys:                      # 設定削除で紐付けが外れることがある
    sim.Add(mg, [box])
    print('[grid] re-bound %s to manual grid settings' % BOX_NAME)

mg.Name = 'Grid_head_%gmm' % HEAD_STEP
mg.MaxStep = [HEAD_STEP] * 3

sim.UpdateGrid()
grid_name = ggs.Name
print('[grid] body=%gmm head=%gmm -> %s' % (BODY_STEP, HEAD_STEP, grid_name))
if 'Invalid' in grid_name:
    raise SystemExit('[grid] FAILED — グリッドが計算できない（刻みを粗くするか範囲を見直す）')

# ===== ④ ボクセル化（焼成のみ。判定は verify_voxels.py）=====
# ★★ 実行中のスクリプトからは、自分が焼いた Voxeler.log は見えない（2026-08-06 実測）。
#    焼成は 13.9 秒で終わっているのに、97/154/211/269/326 秒の時点で document.Save() を
#    呼んでもファイルは現れず、スクリプト終了時に書かれた。よってここでは待たず、
#    焼成ぶんだけ寝てから保存して抜ける。判定は verify_voxels.py（工程7-b）で行う。
t0 = time.time()
sim.CreateVoxels()
print('[vox ] CreateVoxels returned (非同期。焼成の実測は約14秒)')

time.sleep(BAKE_WAIT)
document.Save()
print('[vox ] baked+saved in %.0f s' % (time.time() - t0))
print('    grid:', grid_name)
print('=== 工程7-a（焼成）完了 ===')
print('    次: このスクリプトが終わってから verify_voxels.py を実行して判定する')
