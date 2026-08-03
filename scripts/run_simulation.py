"""工程8・9 Run と結果検証（Sim4Life.lite Python コンソール）。

工程5（`assign_materials.py`）→ 工程6（`setup_boundary.py`）→ 工程7（`setup_grid.py`）が
済んだ sim を実行し、**解が実際に入ったか**まで確認する。
Run が通っただけでは不十分で、2026-07-22〜07-29 は「Run は通るが全点 NaN」だった。

流れ:
  ① 事前ゲート（材料・BC・Voxeler 登録が揃っている）
  ② RunSimulation → Input.log が書かれるまで待つ
  ③ 工程8 の判定: `Degree of freedoms` 行で unknowns > 0 かつ Dirichlet points > 0
  ④ 工程9 の判定: E 場を取り出して有限値・非ゼロ率を確認

★finite 率の読み方（2026-08-03 訂正）:
  全身を囲む箱グリッドでは**材料の無いセル（空気）が NaN になる**ので、
  全点に対する finite 率は 26% 程度が正常。判定は次の2つで行う:
    (a) 材料領域（finite な点）の**非ゼロ率が ≈100%**
    (b) NaN の数がソルバーの `unused` とほぼ一致する（＝解けなかったのではなく材料が無い）

出典ノート: Claude/Knowledge/sim4life-material-assignment.md
           Claude/Knowledge/sim4life-electrode-placement.md
"""
import os
import re
import glob
import time
import numpy as np
import s4l_v1.document as document

SIM_NAME = 'tTIS_LF1'                 # ペア2 は 'tTIS_LF2'

N_TISSUE = 59
LOG_TIMEOUT = 900                     # 秒
NONZERO_MIN = 99.0                    # 材料領域の非ゼロ率の下限（%）
UNUSED_TOL = 0.01                     # NaN 数と unused の許容相対差


def base(name):
    return name.split('  (')[0].strip()


# ===== ① 事前ゲート =====
sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

n_mat = sum(1 for s in sim.AllSettings if type(s).__name__ == 'MaterialSettings')
n_bc = sum(1 for s in sim.AllSettings if type(s).__name__ == 'BoundarySettings')
n_reg = sum(1 for c in sim.AllComponents if 'Automatic Voxeler Settings' in c.Settings.keys())
print('[pre ] materials=%d  boundaries=%d  voxeler-registered=%d' % (n_mat, n_bc, n_reg))
if n_mat < N_TISSUE or n_bc < 3:
    raise SystemExit('[pre ] FAILED — 工程5/6 が済んでいない')
print('[pre ] grid:', sim.GlobalGridSettings.Name)

# ===== ② Run =====
# ★既に結果を持つ sim をそのまま再実行すると `Unable to run simulation` で拒否される
#   （同じ Output.h5 に二度書こうとするため。2026-08-03 実測）。先に結果を消す。
try:
    if sim.HasResults():
        sim.ClearResults()
        print('[run ] 既存の結果を ClearResults で削除した')
except Exception as err:
    print('[run ] ClearResults ERR:', err)

out = os.path.dirname(sim.GetOutputFileName())
t0 = time.time()
try:
    sim.RunSimulation(wait=True)
    print('[run ] returned after %.1f s' % (time.time() - t0))
except Exception as err:
    raise SystemExit('[run ] FAILED — %s' % err)
try:
    print('[run ] HasResults:', sim.HasResults())
except Exception as err:
    print('[run ] HasResults ERR:', err)

log, txt = None, ''
while time.time() - t0 < LOG_TIMEOUT:
    for f in sorted(glob.glob(os.path.join(out, '*Input.log')), key=os.path.getmtime):
        if os.path.getmtime(f) >= t0:
            body = open(f, encoding='utf-8', errors='replace').read()
            if 'Degree of freedoms' in body:
                log, txt = f, body
                break
    if log:
        break
    time.sleep(2)
if log is None:
    raise SystemExit('[run ] FAILED — Input.log に Degree of freedoms が出ない'
                     '（ソルバー起動前で停止している可能性）')
print('[run ] log:', os.path.basename(log))

# ===== ③ 工程8 の判定 =====
m = re.search(r'Degree of freedoms:\s*(\d+) total,\s*(\d+) unknowns,\s*(\d+) Dirichlet points'
              r'(?:,\s*(\d+) collapsed points)?(?:,\s*(\d+) unused)?', txt)
if not m:
    raise SystemExit('[run ] FAILED — Degree of freedoms 行を解釈できない')
total, unknowns, dirichlet = int(m.group(1)), int(m.group(2)), int(m.group(3))
unused = int(m.group(5)) if m.group(5) else None
print('[dof ] total=%d unknowns=%d dirichlet=%d unused=%s'
      % (total, unknowns, dirichlet, unused))

fail = []
if unknowns <= 0:
    fail.append('unknowns=0（ボクセル化されていない）')
if dirichlet <= 0:
    fail.append('Dirichlet points=0（BC が効いていない）')
for l in txt.splitlines():
    s = l.strip()
    if 'lossy' in s or 'no used degrees' in s:
        print('[dof ] WARN:', s)

if fail:
    print('=== 工程8 FAILED: %s ===' % '; '.join(fail))
    raise SystemExit(1)
print('=== 工程8 PASS ===')

# ===== ④ 工程9 の判定 =====
res = sim.Results()
res.UpdateAll()
of = res['Overall Field']
of.Update(0)
ef = of['EM E(x,y,z,f0)']
ef.Update()                           # AlgorithmOutput.Update() は引数を取らない（of.Update(0) とは別物）
arr = ef.Data.Field(0)

mag = np.sqrt(np.sum(np.abs(arr) ** 2, axis=1))
fin = np.isfinite(mag)
n_nan = int(mag.size - fin.sum())
m_fin = mag[fin]
nz = m_fin[m_fin > 0]
nz_pct = 100.0 * nz.size / max(1, m_fin.size)

print('[field] points=%d finite=%d (%.2f %%) NaN=%d'
      % (mag.size, fin.sum(), 100.0 * fin.sum() / mag.size, n_nan))
print('[field] 材料領域の非ゼロ率: %.2f %%' % nz_pct)
if nz.size:
    print('[field] |E| max=%.4g  p50=%.4g  p90=%.4g  p99=%.4g'
          % (m_fin.max(), np.percentile(nz, 50), np.percentile(nz, 90), np.percentile(nz, 99)))

fail = []
if nz_pct < NONZERO_MIN:
    fail.append('材料領域の非ゼロ率 %.2f %% < %.1f %%' % (nz_pct, NONZERO_MIN))
if unused is not None:
    rel = abs(n_nan - unused) / float(max(1, unused))
    print('[field] NaN=%d vs solver unused=%d (相対差 %.4f)' % (n_nan, unused, rel))
    if rel > UNUSED_TOL:
        fail.append('NaN 数が unused と一致しない（相対差 %.4f）' % rel)

print('=== 工程9 %s ===' % ('PASS' if not fail else 'FAILED: ' + '; '.join(fail)))
document.Save()
print('saved.')
