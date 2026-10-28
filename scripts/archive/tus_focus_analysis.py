"""T-6b-2 焦点位置と ROI 定量（Sim4Life.lite Python コンソール・読み取り）。

圧力場 p(x,y,z,f) から:
  ① |p| 最大点の座標（GetCellCenter で厳密に）→ ROI 中心との距離
  ② ROI（半径10mm 球）内の平均・最大・中央値 |p|
  ③ 焦点が ROI に結ぶか（max が ROI 内か・source 面か）の判定材料
グリッドはメートル単位・cell ベース。ROI 中心は tTIS と同一。
"""
import numpy as np
import s4l_v1.document as document

SIM_NAME = 'TUS_250k'
FOCUS_MM = np.array([99.1, 295.0, 1562.2])    # ROI 中心 [mm]（tTIS と同一）
ROI_R_MM = 10.0
T7_MM = np.array([94.8, 335.8, 1536.4])       # 参考: 頭皮 T7（source 面付近）


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

# 軸（メートル→mm）と cell 中心
X = np.asarray(g.XAxis) * 1000.0
Y = np.asarray(g.YAxis) * 1000.0
Z = np.asarray(g.ZAxis) * 1000.0
cx = 0.5 * (X[:-1] + X[1:])
cy = 0.5 * (Y[:-1] + Y[1:])
cz = 0.5 * (Z[:-1] + Z[1:])
nx, ny, nz = cx.size, cy.size, cz.size
print('[grid] cells %d x %d x %d = %d (arr %d)' % (nx, ny, nz, nx * ny * nz, mag.size))

# ① |p| 最大点（GetCellCenter で厳密座標）
imax = int(np.argmax(mag))
pk = xyz(g.GetCellCenter(imax)) * 1000.0
d_focus = np.linalg.norm(pk - FOCUS_MM)
d_t7 = np.linalg.norm(pk - T7_MM)
print('[peak] |p|max=%.4g Pa  at %s mm' % (mag[imax], np.round(pk, 1)))
print('[peak] ROI中心まで %.1f mm / T7(source面)まで %.1f mm' % (d_focus, d_t7))

# 並び順を GetCellCenter と突き合わせて確定（C か F）
i = int(np.argmin(np.abs(cx - pk[0])))
j = int(np.argmin(np.abs(cy - pk[1])))
k = int(np.argmin(np.abs(cz - pk[2])))
order = None
for od in ('C', 'F'):
    if np.ravel_multi_index((i, j, k), (nx, ny, nz), order=od) == imax:
        order = od
        break
print('[grid] argmax ijk=(%d,%d,%d) 並び順=%s' % (i, j, k, order))
if order is None:
    order = 'F'
    print('[grid] 並び順を特定できず F と仮定（要注意）')

mag3 = mag.reshape((nx, ny, nz), order=order)

# ② ROI（半径10mm 球）内の統計
dx2 = (cx - FOCUS_MM[0]) ** 2
dy2 = (cy - FOCUS_MM[1]) ** 2
dz2 = (cz - FOCUS_MM[2]) ** 2
d2 = dx2[:, None, None] + dy2[None, :, None] + dz2[None, None, :]
roi = d2 <= ROI_R_MM ** 2
roi_vals = mag3[roi]
print('[roi ] cells=%d  mean=%.4g  max=%.4g  p50=%.4g (Pa)'
      % (roi_vals.size, roi_vals.mean(), roi_vals.max(), np.percentile(roi_vals, 50)))

# ROI 中心セルの値
ic = int(np.argmin(np.abs(cx - FOCUS_MM[0])))
jc = int(np.argmin(np.abs(cy - FOCUS_MM[1])))
kc = int(np.argmin(np.abs(cz - FOCUS_MM[2])))
print('[roi ] ROI中心セル |p|=%.4g Pa  at (%.1f,%.1f,%.1f)'
      % (mag3[ic, jc, kc], cx[ic], cy[jc], cz[kc]))

# ③ 判定材料: max が ROI 内か
print('')
if d_focus <= ROI_R_MM:
    print('[判定] |p|最大点は ROI 内（%.1fmm）＝焦点が島皮質に結んでいる' % d_focus)
elif d_t7 < d_focus:
    print('[判定] |p|最大点は T7(source面)寄り（focusまで%.1f/ T7まで%.1f）＝near-field か焦点ズレの疑い'
          % (d_focus, d_t7))
else:
    print('[判定] |p|最大点は ROI 外（%.1fmm）＝焦点ズレ（頭蓋収差の可能性）' % d_focus)
print('[参考] ROImax/全体max = %.3f' % (roi_vals.max() / mag[imax]))

print('')
print('=== T-6b-2 完了（焦点位置・ROI 定量）===')
