"""T-5b ボクセル化の判定（Sim4Life.lite Python コンソール）。

tTIS の verify_voxels.py の音響版。T-5a（tus_setup_grid.py）が**終了したあと**に別実行する
（実行中のスクリプトからは自分が焼いた Voxeler.log が見えない・tTIS で確定した鉄則）。

判定に Voxel Scene Memory は使わず、エンティティ単位の `Voxels:` 件数で見る。
期待＝59組織＋Transducer（音源面）。Transducer が焼けていないと音を出せない。

流れ:
  ① Voxeler.log を UUID 一致で特定
  ② エンティティ単位の Voxels 件数を読む
  ③ not being considered=0 / レポート数 / Transducer が焼けている を判定
"""
import os
import glob
import time
import s4l_v1.document as document

SIM_NAME = 'TUS_250k'
TRANSDUCER = 'Transducer'
N_TISSUE = 59
MAX_AGE = 1800


def base(name):
    return name.split('  (')[0].strip()


sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

# ===== ① ログ特定（UUID 一致・全バージョンの結果ディレクトリ横断）=====
out = sim.GetOutputFileName()
uid = os.path.basename(out).split('_Output')[0]
root = os.path.dirname(os.path.dirname(out))
cands = glob.glob(os.path.join(root, '*_Results', uid + '_Voxeler.log'))
if not cands:
    raise SystemExit('[log ] FAILED — %s の Voxeler.log が無い（T-5a を実行したか）' % uid[:8])

log = max(cands, key=os.path.getmtime)
age = time.time() - os.path.getmtime(log)
txt = open(log, encoding='utf-8', errors='replace').read()
print('[log ] %s  (%d B, %.0f s前)' % (os.path.basename(log), len(txt), age))
if age > MAX_AGE:
    print('[warn] ログが %.0f 分前。今回の焼成か確認' % (age / 60.0))
if 'Complete Voxel Scene' not in txt:
    raise SystemExit('[log ] FAILED — 焼成未完（Complete Voxel Scene が無い）')

# ===== ② エンティティ単位の内訳 =====
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
wall = [l.strip() for l in lines if 'Wall Clock Time' in l]

# ★Transducer は Source 割当（材料なし）なので材料ボクセルレポートを出さない（2026-08-20）。
#   ボクセル化されたかは「not being considered に出ていないこと」で判定し、
#   音源が実際に効くかは T-6 の場（非ゼロ音圧・焦点位置）で確認する。
print('[post] reports=%d (tissues %d)  baked=%d  empty=%d'
      % (len(reports), N_TISSUE, len(reports) - len(empty), len(empty)))
print('[post] not being considered: %d' % len(notcons))
print('[post] Transducer material report: %s（Source は材料なし＝レポート無しが正常）'
      % reports.get(TRANSDUCER, '(none)'))
if empty:
    print('[post] empty entities:', empty)     # 数mm の構造は 1mm グリッドで解像できないことがある
for l in notcons[:10]:
    print('[post] NC:', l)
for l in wall:
    print('[post]', l)

fail, warn = [], []
if notcons:
    fail.append('not being considered が %d 件（Transducer 含む何かが未ボクセル化）' % len(notcons))
if not reports:
    fail.append('レポートを1件も読めない')
elif len(reports) < N_TISSUE - 2:      # 極薄構造の空きは数件まで許容
    fail.append('レポート数 %d（組織 %d に対し不足）' % (len(reports), N_TISSUE))
if TRANSDUCER in [l.split()[0] for l in notcons]:  # 明示的に無視されたら失敗
    fail.append('Transducer が not being considered に出た')

for w in warn:
    print('[warn]', w)
print('=== T-5b %s ===' % ('PASS' if not fail else 'FAILED: ' + '; '.join(fail)))
print('    ※音源が効くかは T-6 の場（有限音圧率・焦点位置）でも確認する')
