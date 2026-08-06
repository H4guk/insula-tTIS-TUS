"""工程7-b ボクセル化の判定（Sim4Life.lite Python コンソール）。

`setup_grid.py`（工程7-a）が**終了したあと**に、別スクリプトとして実行する。

★分けている理由（2026-08-06 実測・GH Issue #12）:
  **実行中のスクリプトからは、自分が焼いた `Voxeler.log` は見えない。**
  ファイルが現れるのはスクリプトが終了したあとで、実行中は何秒待っても・何回 `document.Save()` を
  呼んでも現れない（焼成は 13.89 秒で終わっているのに、97/154/211/269/326 秒の Save では出ず、
  スクリプト終了時に書かれた）。2026-08-03 の「Save のときに書き出される」という説明は誤り。
  → 待ちループは原理的に成立しないので、焼成（7-a）と判定（7-b）を分ける。

判定に `Voxel Scene Memory Consumption` は使わない（幾何の複雑さの指標であって中身の量ではない）。
**エンティティ単位の `Voxels:` 件数**で判定する。

期待値は固定値で持たず sim から導出する。voxeler が処理するのは
「σ を持つ組織59」＋「BC を持つ駆動電極」だけで、非駆動ペアはレポートが出ないのが正常。

出典ノート: Claude/Knowledge/sim4life-material-assignment.md
"""
import os
import glob
import time
import s4l_v1.document as document

SIM_NAME = 'tTIS_LF1'
ELEC = ('Elec_T7', 'Elec_P7', 'Elec_Fp1', 'Elec_Fp2')
N_TISSUE = 59                         # σ を持つ頭部組織
MAX_AGE = 1800                        # 秒。これより古いログは「前回の実行のもの」として警告する


def base(name):
    return name.split('  (')[0].strip()


sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

# ===== ① ログの特定（UUID 一致・全バージョンの結果ディレクトリを横断）=====
# ログは sim ごとに UUID 付きの別ファイル。UUID は .smash のバージョンをまたいで使い回されるので、
# 「最新のログ」を拾うと別 sim のものを読む（2026-08-06 実測: v4/v5 が同一 UUID）。
out = sim.GetOutputFileName()
uid = os.path.basename(out).split('_Output')[0]
root = os.path.dirname(os.path.dirname(out))
cands = glob.glob(os.path.join(root, '*_Results', uid + '_Voxeler.log'))
if not cands:
    raise SystemExit('[log ] FAILED — %s の Voxeler.log が無い（工程7-a を実行したか？）' % uid[:8])

log = max(cands, key=os.path.getmtime)
age = time.time() - os.path.getmtime(log)
txt = open(log, encoding='utf-8', errors='replace').read()
print('[log ] %s  (%d B, %.0f s前)' % (os.path.basename(log), len(txt), age))
if age > MAX_AGE:
    print('[warn] ログが %.0f 分前のもの。今回の焼成の結果か確認すること' % (age / 60.0))
if 'Complete Voxel Scene' not in txt:
    raise SystemExit('[log ] FAILED — 焼成が完了していない（Complete Voxel Scene が無い）')

# ===== ② エンティティ単位の内訳を読む =====
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
wall = [l.strip() for l in lines if 'Wall Clock Time' in l]

# 期待値は sim から導出する（駆動電極 = BC_ キーを持つ電極）
driven = sorted(base(c.Name) for c in sim.AllComponents
                if base(c.Name) in ELEC
                and any(k.startswith('BC_') for k in c.Settings.keys()))
expected = N_TISSUE + len(driven)

print('[post] reports=%d (expected %d)  baked=%d  empty=%d'
      % (len(reports), expected, len(reports) - len(empty), len(empty)))
print('[post] not being considered: %d' % len(notcons))
print('[post] driven electrodes: %s' % driven)
print('[post] electrodes:', dict((e, reports.get(e, '(none)')) for e in ELEC))
if empty:
    print('[post] empty entities:', empty)      # 数mm の構造は 2mm グリッドでは解像できない
for l in pec + wall:
    print('[post]', l)

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
print('    ※電極が焼けているかは工程8 の `Dirichlet points > 0` でも確認できる')
