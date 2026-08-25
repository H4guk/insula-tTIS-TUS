"""T-6c 剛体トランスデューサ検証（Sim4Life.lite Python コンソール）。

near-field 優勢が「水トランスデューサ（両面放射）のモデル起因」か「頭蓋物理」かを切り分ける。
Transducer 材料を IsReflector=True（剛体ピストン・前面のみ放射）に変えて再ボクセル化→再Run。

★順序（既知のロック回避）: ClearResults → ResetVoxels → 設定変更 → 再ボクセル化 → Run。
  設定が効いたか読み戻して確認してから、重い CreateVoxels / Run に進む。

判定: 剛体で焦点(s≈48.5)が near-field(s≈15) を上回れば水モデルが主因。
      変わらず near-field 優勢なら頭蓋物理として確定。
"""
import os
import glob
import time
import numpy as np
import s4l_v1.document as document

SIM_NAME = 'TUS_250k'
PERIODS = 40
BAKE_WAIT = 220
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


sim = [s for s in document.AllSimulations if s.Name == SIM_NAME][0]

# 剛体化する材料を特定
ms = [s for s in sim.AllSettings if type(s).__name__ == 'MaterialSettings'
      and 'transducer' in s.Name.lower()]
if not ms:
    raise SystemExit('[pre ] FAILED — Transducer 材料が見つからない')
ms = ms[0]
print('[pre ] material=%s  IsReflector(before)=%s' % (ms.Name, ms.IsReflector))

# ロック解除 → ボクセル解除 → 設定変更
try:
    if sim.HasResults():
        sim.ClearResults(); print('[unlk] cleared results')
except Exception as ex:
    print('[unlk] ClearResults ERR:', ex)
try:
    sim.ResetVoxels(); print('[unlk] ResetVoxels done')
except Exception as ex:
    print('[unlk] ResetVoxels ERR:', ex)

ms.IsReflector = True
sim.SetupSettings.Periods = PERIODS
print('[set ] IsReflector -> %s  Periods -> %s' % (ms.IsReflector, sim.SetupSettings.Periods))
if not bool(ms.IsReflector) or int(sim.SetupSettings.Periods) != PERIODS:
    raise SystemExit('[set ] FAILED — 設定が効いていない（ロック未解除）')

# 再ボクセル化（焼成）
t0 = time.time()
sim.CreateVoxels()
print('[vox ] CreateVoxels returned (async)')
time.sleep(BAKE_WAIT)
document.Save()
print('[vox ] baked+saved in %.0f s' % (time.time() - t0))

# Run
t1 = time.time()
run_ok = False
try:
    sim.RunSimulation(wait=True)
    run_ok = True
    print('[run ] returned after %.1f s' % (time.time() - t1))
except Exception as ex:
    print('[run ] FAILED after %.1f s: %s' % (time.time() - t1, ex))
    read_log_tail()
if not run_ok:
    raise SystemExit('=== 剛体検証: Run 失敗 ===')

# 解析
res = sim.Results(); res.UpdateAll()
of = res['Overall Field']; of.Update(0)
pf = of['p(x,y,z,f)']; pf.Update()
data = pf.Data
mag = np.abs(np.asarray(data.Field(0))).ravel()
g = data.Grid
X = np.asarray(g.XAxis) * 1000.0; Y = np.asarray(g.YAxis) * 1000.0; Z = np.asarray(g.ZAxis) * 1000.0
cx = 0.5 * (X[:-1] + X[1:]); cy = 0.5 * (Y[:-1] + Y[1:]); cz = 0.5 * (Z[:-1] + Z[1:])
nx, ny, nz = cx.size, cy.size, cz.size
mag3 = mag.reshape((nx, ny, nz), order='F')

imax = int(np.argmax(mag))
pk = xyz(g.GetCellCenter(imax)) * 1000.0
print('')
print('[peak] global |p|max=%.4g Pa at %s  (ROI %.1fmm / T7 %.1fmm)'
      % (mag[imax], np.round(pk, 1), np.linalg.norm(pk - FOCUS_MM), np.linalg.norm(pk - T7_MM)))

dx2 = (cx - FOCUS_MM[0]) ** 2; dy2 = (cy - FOCUS_MM[1]) ** 2; dz2 = (cz - FOCUS_MM[2]) ** 2
roi = (dx2[:, None, None] + dy2[None, :, None] + dz2[None, None, :]) <= ROI_R_MM ** 2
rv = mag3[roi]
ic = int(np.argmin(np.abs(cx - FOCUS_MM[0]))); jc = int(np.argmin(np.abs(cy - FOCUS_MM[1]))); kc = int(np.argmin(np.abs(cz - FOCUS_MM[2])))
print('[roi ] center=%.4g  mean=%.4g  max=%.4g Pa  (water-transducer was center1.41e6/mean7.29e5)'
      % (mag3[ic, jc, kc], rv.mean(), rv.max()))

d = FOCUS_MM - T7_MM; R = np.linalg.norm(d); d = d / R
print('')
print('[axis] s=0 at T7, focus at s=%.1f mm' % R)
best = (-1, 0.0); foc = 0.0
s = -3.0
while s <= 75.0:
    p = T7_MM + s * d
    i = int(np.argmin(np.abs(cx - p[0]))); j = int(np.argmin(np.abs(cy - p[1]))); k = int(np.argmin(np.abs(cz - p[2])))
    v = float(mag3[i, j, k])
    mark = ''
    if abs(s - R) < 1.5:
        mark = '  <- focus'; foc = v
    print('  s=%-6.1f |p|=%-12.4g%s' % (s, v, mark))
    if v > best[1]:
        best = (s, v)
    s += 3.0
print('[axis] axial max at s=%.1f mm  |p|=%.4g Pa   focus/axialmax=%.3f'
      % (best[0], best[1], foc / best[1] if best[1] else 0))
print('')
print('[判定] axial max が焦点付近(s≈%.0f)なら水モデル起因・near-field(s≈15)のままなら頭蓋物理' % R)
print('=== T-6c 剛体トランスデューサ検証 完了 ===')
