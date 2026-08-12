"""prod グリッドの flat 配列の並び順を検証する（読み取り専用）。

なぜ要るか:
  解析側のすべてが「**X-fastest**（flat = x + nx*(y + ny*z) ＝ `reshape(nz, ny, nx)`）」という
  前提に乗っている——`ti_analysis.py` の `sphere_mask`（ROI）・`cell_volumes`（体積重み）、
  `current_scale.py` の面積分。この前提は **2026-07-20 に SAM head で実証したもの**で、
  今回の prod グリッド（228 x 220 x 245）では確認していない。
  **並び順が違えば ROI が別の場所を指し、選択性そのものが無意味になる。**

2通りで確かめる（API と物理の両方から）:
  ① `GetCellCenter` で idx 0 → 1 → 2 → nx → nx*ny の座標を見て、どの軸が先に進むかを直接読む。
  ② **`|E|` が最大になるセルの座標**を出す。駆動電極の縁が最強になるはずなので、
     ペア1 なら T7/P7、ペア2 なら Fp1/Fp2 の近くに落ちる。並び順が違えば無関係な場所に落ちる。
     ——①が API の言い分、②が物理の裏取り。

出典ノート: Claude/Projects/tTIS-field-simulation.md「グリッド解釈を実測で確定」（2026-07-20）
"""
import numpy as np
import s4l_v1.document as document

NAMES = ('tTIS_LF1', 'tTIS_LF2')
E_KEY = 'EM E(x,y,z,f0)'

# 駆動電極の実座標 [mm]（工程4 place_electrodes.py の皮膚投影後の値）
ELEC = {'tTIS_LF1': {'Elec_T7': (94.8, 335.6, 1536.5), 'Elec_P7': (41.7, 329.5, 1546.1)},
        'tTIS_LF2': {'Elec_Fp1': (184.3, 286.8, 1566.1), 'Elec_Fp2': (184.2, 235.5, 1562.4)}}


def get_sim(name):
    hit = [s for s in document.AllSimulations if s.Name == name]
    if len(hit) != 1:
        raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (name, len(hit)))
    return hit[0]


def field_data(sim, key):
    res = sim.Results()
    res.UpdateAll()
    of = res['Overall Field']
    of.Update(0)
    if key not in list(of.keys()):
        print('[err ] %r が無い。利用可能なキー: %s' % (key, list(of.keys())))
        raise SystemExit(1)
    f = of[key]
    f.Update()
    return f.Data


def axes(g):
    a = [np.asarray([float(v) for v in ax], dtype=float) for ax in (g.XAxis, g.YAxis, g.ZAxis)]
    return a[0], a[1], a[2]


name = NAMES[0]
sim = get_sim(name)
fd = field_data(sim, E_KEY)
g = fd.Grid
xa, ya, za = axes(g)
nx, ny, nz = xa.size - 1, ya.size - 1, za.size - 1
xc = 0.5 * (xa[:-1] + xa[1:])
yc = 0.5 * (ya[:-1] + ya[1:])
zc = 0.5 * (za[:-1] + za[1:])
print('[grid] cells: nx=%d ny=%d nz=%d  積=%d  unit=%s' % (nx, ny, nz, nx * ny * nz, g.GetUnit()))
try:
    print('[grid] Dimensions=%s  NumberOfCells=%s' % (list(g.Dimensions), g.NumberOfCells))
except Exception as ex:
    print('[grid] Dimensions/NumberOfCells 取得できず: %r' % (ex,))

# ===== ① GetCellCenter で並び順を直接読む =====
print('')
print('--- ① GetCellCenter の進み方 ---')
probe = [0, 1, 2, nx, nx + 1, nx * ny, nx * ny + 1]
prev = None
for idx in probe:
    try:
        p = g.GetCellCenter(idx)
        v = (float(p[0]), float(p[1]), float(p[2]))
    except Exception as ex:
        print('  idx %-10d 取得できず: %r' % (idx, ex))
        continue
    d = '' if prev is None else '  Δ=(%+.5f, %+.5f, %+.5f)' % tuple(v[i] - prev[i] for i in range(3))
    print('  idx %-10d (%.5f, %.5f, %.5f)%s' % (idx, v[0], v[1], v[2], d))
    prev = v
print('  期待（X-fastest）: idx 0→1 で X のみ進む / idx nx で Y が繰り上がる / idx nx*ny で Z が繰り上がる')

# ===== ② |E| の最大セルが駆動電極の近くか（物理の裏取り）=====
print('')
print('--- ② |E| 最大セルの位置（駆動電極の近くに来るはず）---')
for nm in NAMES:
    s = get_sim(nm)
    d = field_data(s, E_KEY)
    arr = np.asarray(d.Field(0))
    mag = np.sqrt(np.sum(np.abs(arr) ** 2, axis=1))
    mag = np.where(np.isfinite(mag), mag, -1.0)
    k = int(np.argmax(mag))

    # X-fastest 前提で idx → (ix, iy, iz)
    ix = k % nx
    iy = (k // nx) % ny
    iz = k // (nx * ny)
    pos_xf = (xc[ix] * 1000.0, yc[iy] * 1000.0, zc[iz] * 1000.0)

    # 対立仮説: Z-fastest（flat = z + nz*(y + ny*x)）だとどこになるか
    jz = k % nz
    jy = (k // nz) % ny
    jx = k // (nz * ny)
    pos_zf = (xc[jx] * 1000.0, yc[jy] * 1000.0, zc[jz] * 1000.0)

    print('[%s] |E| max = %.4g V/m  at flat idx %d' % (nm, mag[k], k))
    print('       X-fastest 解釈 → (%.1f, %.1f, %.1f) mm' % pos_xf)
    print('       Z-fastest 解釈 → (%.1f, %.1f, %.1f) mm' % pos_zf)
    for ename, ep in sorted(ELEC[nm].items()):
        d_xf = sum((pos_xf[i] - ep[i]) ** 2 for i in range(3)) ** 0.5
        d_zf = sum((pos_zf[i] - ep[i]) ** 2 for i in range(3)) ** 0.5
        print('       %-10s (%.1f, %.1f, %.1f): X-fastest なら %.1f mm / Z-fastest なら %.1f mm'
              % (ename, ep[0], ep[1], ep[2], d_xf, d_zf))
    try:
        c = g.GetCellCenter(k)
        print('       GetCellCenter(%d) = (%.1f, %.1f, %.1f) mm  ← これが正解'
              % (k, float(c[0]) * 1000.0, float(c[1]) * 1000.0, float(c[2]) * 1000.0))
    except Exception as ex:
        print('       GetCellCenter 取得できず: %r' % (ex,))

print('')
print('  判定: ②で「GetCellCenter の座標」と一致する解釈が正しい並び順。')
print('        駆動電極から数 mm〜十数 mm 以内に落ちていれば物理的にも妥当。')
print('')
print('=== 並び順の検証 完了（読み取りのみ・保存していない）===')
