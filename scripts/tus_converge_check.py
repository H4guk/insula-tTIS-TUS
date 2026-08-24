"""T-6b-4 収束確認: Periods を増やして再 Run し焦点圧が上がるか見る（Sim4Life.lite）。

Periods=10 では焦点(48.5mm=約8周期)が定常未達の疑い。Periods を増やして再 Run し、
焦点圧・ROI 平均・軸プロファイルが Periods=10（焦点1.26/ROI平均0.68 MPa・軸上最大 s=15）から
どう変わるかを見る。上がれば収束が主因、変わらなければ頭蓋物理 or 水トランスデューサモデル。

Periods はソルバー時間の設定（幾何ではない）ので ResetVoxels 不要。Run 失敗でもログ末尾を出す。
"""
import os
import glob
import time
import numpy as np
import s4l_v1.document as document

SIM_NAME = 'TUS_250k'
PERIODS = 40
FOCUS_MM = np.array([99.1, 295.0, 1562.2])
T7_MM = np.array([94.8, 335.8, 1536.4])
ROI_R_MM = 10.0


def xyz(v):
    try:    return np.array([float(v[0]), float(v[1]), float(v[2])])
    except: return np.array([float(v.X), float(v.Y), float(v.Z)])


def read_log_tail():
    out = sim.GetOutputFileName()
    uid = os.path.basename(out).split('_Output')[0]
    root = os.path.dirname(os.path.dirname(out))
    logs = glob.glob(os.path.join(root, '*_Results', uid + '_Input.log')) \
        or glob.glob(os.path.join(root, '*_Results', '*_Input.log'))
    if not logs:
        print('[log ] no Input.log'); return
    lg = max(logs, key=os.path.getmtime)
    for l in open(lg, encoding='utf-8', errors='replace').read().splitlines()[-15:]:
        print('   |', l)


sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED - sim count %d' % len(sims))
sim = sims[0]

# ★順序が肝: Setup 変更は HasResults 中はロックされ黙って無視される（2026-08-25 実測）。
#   先に ClearResults でロックを外してから Periods を設定する。
old = sim.SetupSettings.Periods
try:
    if sim.HasResults():
        sim.ClearResults()
        print('[run ] cleared results')
except Exception as ex:
    print('[run ] ClearResults ERR:', ex)
sim.SetupSettings.Periods = PERIODS
print('[set ] Periods %s -> %s' % (old, sim.SetupSettings.Periods))
if int(sim.SetupSettings.Periods) != PERIODS:
    raise SystemExit('[set ] FAILED — Periods を %d に設定できなかった（ロック未解除）' % PERIODS)

t0 = time.time()
run_ok = False
try:
    sim.RunSimulation(wait=True)
    run_ok = True
    print('[run ] returned after %.1f s' % (time.time() - t0))
except Exception as ex:
    print('[run ] FAILED after %.1f s: %s' % (time.time() - t0, ex))
    read_log_tail()

if not run_ok:
    raise SystemExit('=== 収束確認: Run 失敗（上のログ末尾を確認）===')

# ---- 場を取り出す ----
res = sim.Results(); res.UpdateAll()
of = res['Overall Field']; of.Update(0)
pf = of['p(x,y,z,f)']; pf.Update()
data = pf.Data
mag = np.abs(np.asarray(data.Field(0))).ravel()
g = data.Grid
X = np.asarray(g.XAxis) * 1000.0
Y = np.asarray(g.YAxis) * 1000.0
Z = np.asarray(g.ZAxis) * 1000.0
cx = 0.5 * (X[:-1] + X[1:]); cy = 0.5 * (Y[:-1] + Y[1:]); cz = 0.5 * (Z[:-1] + Z[1:])
nx, ny, nz = cx.size, cy.size, cz.size
mag3 = mag.reshape((nx, ny, nz), order='F')

# 全体最大
imax = int(np.argmax(mag))
pk = xyz(g.GetCellCenter(imax)) * 1000.0
print('')
print('[peak] global |p|max=%.4g Pa at %s  (ROI %.1fmm / T7 %.1fmm)'
      % (mag[imax], np.round(pk, 1), np.linalg.norm(pk - FOCUS_MM), np.linalg.norm(pk - T7_MM)))

# ROI 統計
dx2 = (cx - FOCUS_MM[0]) ** 2; dy2 = (cy - FOCUS_MM[1]) ** 2; dz2 = (cz - FOCUS_MM[2]) ** 2
roi = (dx2[:, None, None] + dy2[None, :, None] + dz2[None, None, :]) <= ROI_R_MM ** 2
rv = mag3[roi]
ic = int(np.argmin(np.abs(cx - FOCUS_MM[0]))); jc = int(np.argmin(np.abs(cy - FOCUS_MM[1]))); kc = int(np.argmin(np.abs(cz - FOCUS_MM[2])))
print('[roi ] center=%.4g  mean=%.4g  max=%.4g Pa  (Periods=10 は center1.26e6/mean6.78e5)'
      % (mag3[ic, jc, kc], rv.mean(), rv.max()))

# 軸プロファイル（3mm 刻み）
d = FOCUS_MM - T7_MM; R = np.linalg.norm(d); d = d / R
print('')
print('[axis] s=0 at T7, focus at s=%.1f mm' % R)
best = (-1, 0.0)
s = -3.0
while s <= 75.0:
    p = T7_MM + s * d
    i = int(np.argmin(np.abs(cx - p[0]))); j = int(np.argmin(np.abs(cy - p[1]))); k = int(np.argmin(np.abs(cz - p[2])))
    v = float(mag3[i, j, k])
    mark = '  <- focus' if abs(s - R) < 1.5 else ''
    print('  s=%-6.1f |p|=%-12.4g%s' % (s, v, mark))
    if v > best[1]:
        best = (s, v)
    s += 3.0
print('[axis] axial max at s=%.1f mm  |p|=%.4g Pa' % best)
print('')
print('=== 収束確認 完了（Periods=%d）===' % PERIODS)
