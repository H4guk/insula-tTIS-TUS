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
  - `sim.CreateVoxels()` は**戻ってきても焼き終わっていない**（実測 13.6 秒）。
    直後にログを読むと空なので「0件」と誤判定する。ログに `Complete Voxel Scene` が出るまで待つ

流れ:
  ① 事前ゲート（sim が1つ・材料と BC が入っている）
  ② AutomaticGridSettings を削除
  ③ グリッド設定（体 BODY_STEP / 頭部 Block に HEAD_STEP）→ UpdateGrid → セル数を確認
  ④ CreateVoxels → Voxeler.log が書き終わるまで待つ
  ⑤ 事後ゲート（not being considered 0 / レポートが組織59件以上）
     ※電極は工程5 で σ を付けないため Voxeler.log にレポートが出るかは未確認。
       電極が焼けているかの最終確認は**工程8 の `Dirichlet points > 0`**（実測 7,120）。

判定に `Voxel Scene Memory Consumption` は使わない（幾何の複雑さの指標であって中身の量ではない）。
**エンティティ単位の `Voxels:` 件数**で判定する。

出典ノート: Claude/Knowledge/sim4life-material-assignment.md
"""
import os
import glob
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

ELEC = ('Elec_T7', 'Elec_P7', 'Elec_Fp1', 'Elec_Fp2')
N_TISSUE = 59                         # σ を持つ頭部組織
N_TOTAL = 63                          # Voxeler 登録数（頭部組織59 + 電極4）
VOXEL_TIMEOUT = 900                   # 秒
# ⚠️ Voxeler.log の `Wall Clock Time`（実測 13.6 秒）は**voxeler の内部計算時間**であって、
#    `CreateVoxels()` を呼んでからログが書き終わるまでの実時間ではない。
#    可視化データの書き出し（0.026 GB）等も挟まり、実測で3分以上かかることがある。
#    2026-08-03 にこれを取り違えて 180 秒に縮め、書き終わる直前で取りこぼした。


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

# ===== ④ ボクセル化（戻り値では完了しないのでログを待つ）=====
# ★ログの更新時刻だけを待つ実装は空振りする（2026-08-03 に 600 秒待たされた。
#   ボクセル化自体は成功していたのに mtime が期待どおり動かなかった）。
#   実行前のスナップショットと突き合わせ、取れなくても**止まらない**ようにする。
def snapshot(d):
    out = {}
    for f in glob.glob(os.path.join(d, '*Voxeler.log')):
        try:
            st = os.stat(f)
            out[f] = (st.st_size, st.st_mtime)
        except OSError:
            pass
    return out


out = os.path.dirname(sim.GetOutputFileName())
before = snapshot(out)
t0 = time.time()
sim.CreateVoxels()
print('[vox ] CreateVoxels returned (まだ焼き終わっていない)')

log, txt = None, ''
last_note = 0.0
while time.time() - t0 < VOXEL_TIMEOUT:
    for f, sig in sorted(snapshot(out).items(), key=lambda kv: kv[1][1]):
        if before.get(f) == sig:
            continue                       # 変化していない＝前回の実行のログ
        body = open(f, encoding='utf-8', errors='replace').read()
        if 'Complete Voxel Scene' in body:
            log, txt = f, body
            break
    if log:
        break
    if time.time() - last_note >= 30:      # 無言で長時間待たない
        last_note = time.time()
        print('[vox ] waiting... %.0f s' % (time.time() - t0))
    time.sleep(2)

if log is None:                            # 諦めるが止めない。Run（工程8）が本当のゲート
    cands = sorted(glob.glob(os.path.join(out, '*Voxeler.log')), key=os.path.getmtime)
    if cands:
        txt = open(cands[-1], encoding='utf-8', errors='replace').read()
    print('[vox ] WARNING: %d 秒待っても新しい Voxeler.log を確認できなかった。'
          '古いログで検証を試みる（結果は参考値）' % VOXEL_TIMEOUT)
else:
    print('[vox ] done in %.1f s: %s' % (time.time() - t0, os.path.basename(log)))

# ===== ⑤ 事後ゲート =====
lines = txt.splitlines()
reports, cur = {}, None
for l in lines:
    s = l.strip()
    if s.startswith('Topological Voxeler Report:'):
        cur = s.split(':', 1)[1].strip()
    elif cur and s.startswith('Voxels:'):
        reports[cur] = s.split(':', 1)[1].strip()
        cur = None
reports.pop('Complete Voxel Scene', None)

empty = sorted(k for k, v in reports.items() if v in ('None', '0'))
notcons = [l.strip() for l in lines if 'not being considered' in l]
pec = [l.strip() for l in lines if 'reassigned to PEC' in l]

print('[post] reports=%d (expected %d)  baked=%d  empty=%d'
      % (len(reports), N_TOTAL, len(reports) - len(empty), len(empty)))
print('[post] not being considered: %d' % len(notcons))
print('[post] electrodes:', dict((e, reports.get(e, '(none)')) for e in ELEC))
if empty:
    print('[post] empty entities:', empty)     # 数mm の構造は 2mm グリッドでは解像できない
for l in pec:
    print('[post]', l)                          # ソリッド BC の電極は PEC 扱いになる

# 期待値は固定値にせず sim から導出する。
# voxeler が処理するのは「σ を持つ組織59」＋「BC を持つ駆動電極」だけ。
# 非駆動ペアは σ も BC も無いので**レポートが出ないのが正常**（2026-08-03 実測）。
driven = sorted(base(c.Name) for c in sim.AllComponents
                if base(c.Name) in ELEC
                and any(k.startswith('BC_') for k in c.Settings.keys()))
expected = N_TISSUE + len(driven)
print('[post] driven electrodes: %s  -> expected reports = %d' % (driven, expected))

fail, warn = [], []
if notcons:
    fail.append('not being considered が %d 件' % len(notcons))
if not reports:
    fail.append('Voxeler.log からレポートを1件も読めない')
elif len(reports) < N_TISSUE:
    fail.append('レポート数 %d（組織 %d を下回る）' % (len(reports), N_TISSUE))
elif len(reports) != expected:
    warn.append('レポート数 %d（期待 %d）' % (len(reports), expected))
for e in driven:                      # 駆動電極が焼けていないと Dirichlet が立たない
    if reports.get(e) in (None, 'None', '0'):
        fail.append('駆動電極 %s が焼けていない' % e)

for w in warn:
    print('[warn]', w)
print('=== 工程7 %s ===' % ('PASS' if not fail else 'FAILED: ' + '; '.join(fail)))
print('    ※電極が焼けているかは工程8 の `Dirichlet points > 0` で最終確認する')
print('    grid:', grid_name)
document.Save()
print('saved.')
