"""T-6b-1 圧力場の非ゼロ確認＋座標 API の調査（Sim4Life.lite Python コンソール・読み取り）。

Run 成功後、p(x,y,z,f) を取り出して ①場が非ゼロ（ソースが鳴っているか）②Data/Grid の
座標 API（軸・配列形状・cell か node か）を確認する。焦点位置・ROI 定量は T-6b-2 で行う。
"""
import numpy as np
import s4l_v1.document as document

SIM_NAME = 'TUS_250k'

sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

res = sim.Results()
res.UpdateAll()
of = res['Overall Field']
of.Update(0)
pf = of['p(x,y,z,f)']
pf.Update()
data = pf.Data
arr = data.Field(0)
arr = np.asarray(arr)
print('[p   ] arr shape=%s dtype=%s' % (arr.shape, arr.dtype))

# 圧力の絶対値（複素なら magnitude）
mag = np.abs(arr)
if mag.ndim > 1:
    mag = mag.reshape(mag.shape[0], -1)[:, 0]
mag = mag.ravel()
fin = np.isfinite(mag)
nz = mag[fin][mag[fin] > 0]
print('[p   ] points=%d finite=%d (%.1f%%) nonzero=%d (%.1f%%)'
      % (mag.size, fin.sum(), 100.0 * fin.sum() / mag.size,
         nz.size, 100.0 * nz.size / max(1, fin.sum())))
if nz.size:
    print('[p   ] |p| max=%.4g  p50=%.4g  p90=%.4g  p99=%.4g (Pa)'
          % (mag[fin].max(), np.percentile(nz, 50), np.percentile(nz, 90), np.percentile(nz, 99)))

# 座標 API の調査
print('')
g = data.Grid
print('[grid] Grid type=%s  attrs=%s' % (type(g).__name__,
      [a for a in dir(g) if not a.startswith('_')][:40]))
for ax in ('XAxis', 'YAxis', 'ZAxis'):
    a = getattr(g, ax, None)
    if a is None:
        print('   %s: なし' % ax)
        continue
    a = np.asarray(a)
    print('   %s: len=%d 範囲 [%.1f .. %.1f]' % (ax, a.size, a.min(), a.max()))

# cell 数 vs node 数の対応を見る（arr の点数がどちらに一致するか）
try:
    nx = np.asarray(g.XAxis).size
    ny = np.asarray(g.YAxis).size
    nz_ = np.asarray(g.ZAxis).size
    print('[grid] axis lens: X=%d Y=%d Z=%d' % (nx, ny, nz_))
    print('[grid] node prod=%d  cell prod=%d  arr points=%d'
          % (nx * ny * nz_, (nx - 1) * (ny - 1) * (nz_ - 1), mag.size))
except Exception as ex:
    print('[grid] axis 取得エラー:', ex)

# Grid に cell-center を返す関数があるか探る
cand = [a for a in dir(g) if any(h in a.lower() for h in ('cell', 'center', 'coord', 'point'))]
print('[grid] center/coord 系メソッド候補: %s' % cand)

print('')
print('=== T-6b-1 完了（非ゼロ確認＋座標API調査・保存なし）===')
