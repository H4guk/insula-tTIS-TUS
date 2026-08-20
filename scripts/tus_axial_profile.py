"""T-6b-3 軸方向 |p| プロファイル（Sim4Life.lite Python コンソール・読み取り）。

near-field 最大が物理（頭蓋界面）かモデル起因かを見るため、音源軸（T7→焦点→奥）に沿って
|p| をサンプルする。焦点(48.5mm)・near-field 最大の位置関係が分かる。読み取りのみ。
"""
import numpy as np
import s4l_v1.document as document

SIM_NAME = 'TUS_250k'
FOCUS_MM = np.array([99.1, 295.0, 1562.2])
T7_MM = np.array([94.8, 335.8, 1536.4])
S_START, S_STOP, S_STEP = -5.0, 75.0, 2.0     # T7 を 0 とした軸方向 [mm]


def xyz(v):
    try:    return np.array([float(v[0]), float(v[1]), float(v[2])])
    except: return np.array([float(v.X), float(v.Y), float(v.Z)])


sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

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
mag3 = mag.reshape((nx, ny, nz), order='F')     # T-6b-2 で F と確定

d = FOCUS_MM - T7_MM
R = np.linalg.norm(d)
d = d / R
print('[axis] T7=%s → FOCUS=%s  距離 R=%.1f mm  方向=%s'
      % (np.round(T7_MM, 1), np.round(FOCUS_MM, 1), R, np.round(d, 3)))
print('[axis] s は T7 を 0・焦点は s=%.1f mm' % R)
print('')
print('%-8s %-22s %-12s' % ('s[mm]', 'coord[mm]', '|p|[Pa]'))
print('-' * 46)

best = (-1, 0.0)
prof = []
s = S_START
while s <= S_STOP:
    p = T7_MM + s * d
    i = int(np.argmin(np.abs(cx - p[0])))
    j = int(np.argmin(np.abs(cy - p[1])))
    k = int(np.argmin(np.abs(cz - p[2])))
    val = float(mag3[i, j, k])
    prof.append((s, val))
    mark = ''
    if abs(s - R) < S_STEP / 2:
        mark = '  <- 幾何焦点'
    print('%-8.1f %-22s %-12.4g%s' % (s, np.round(p, 1), val, mark))
    if val > best[1]:
        best = (s, val)
    s += S_STEP

print('')
print('[axis] 軸上の最大: s=%.1f mm（T7から）  |p|=%.4g Pa' % best)
print('[axis] 焦点(s=%.1f)の |p| = %.4g Pa' % (R, dict((round(a, 1), b) for a, b in prof).get(round(R / S_STEP) * S_STEP if False else min(prof, key=lambda t: abs(t[0] - R))[0], float('nan'))))
foc_val = min(prof, key=lambda t: abs(t[0] - R))[1]
print('[axis] 焦点近傍 |p| ≈ %.4g Pa  / 軸上最大 %.4g Pa  比=%.3f'
      % (foc_val, best[1], foc_val / best[1] if best[1] else 0))
print('')
print('=== T-6b-3 完了（軸プロファイル）===')
