"""5-3 tTIS 焦点サイズの実測（TI 包絡の -6dB 領域・Sim4Life.lite Python コンソール・読み取り専用）。

TUS 側 `tus_focus_size.py`（5-2）の tTIS 版。比較のため体積・等価球径・ROI ズレは同じ定義で出す。

tTIS 固有の事情（TUS 版から変えた3点）:
  ① 場を合成する — TI = 2·min(s1|E1|, s2|E2|)。**電流スケール s1/s2 を省略できない**
     （min が非線形なのでスケールで分布の形が変わる）。ti_analysis.py と同じ手順で
     `El. Loss Density` の体積積分 P から I=2P/V を出し、Inoue の 0.891/1.109 mA に合わせる。
  ② 脳マスクは σ = 2·loss/|E|^2 の帯（0.33–0.44 = WM 0.348 + GM 0.4191・Phase2 で 945mL）。
  ③ ビーム軸が無い（2ペアの干渉で焦点が決まる）ので、-6dB 領域の**主軸（PCA）**に沿って
     3方向の全幅を出す。体積・等価球径は TUS とそのまま比較できる。

グリッドは非一様（体 5mm ＋ 頭部 1mm）なので体積重み必須。並び順は X-fastest（Phase2 で検証済み）。
"""
import numpy as np
import s4l_v1.document as document

NAMES = ('tTIS_LF1', 'tTIS_LF2')
I_TARGET_MA = (0.891, 1.109)
DRIVE_V = 1.0
LOSS_TO_I = 2.0
E_KEY = 'EM E(x,y,z,f0)'
LOSS_KEY = 'El. Loss Density(x,y,z,f0)'

FOCUS_MM = np.array([99.1, 295.0, 1562.2])
ROI_R_MM = 10.0
BRAIN_BAND = (0.33, 0.44)
DB = -6.0


def get_sim(name):
    hit = [s for s in document.AllSimulations if s.Name == name]
    if len(hit) != 1:
        raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (name, len(hit)))
    return hit[0]


def field(sim, key):
    res = sim.Results(); res.UpdateAll()
    of = res['Overall Field']; of.Update(0)
    if key not in list(of.keys()):
        print('[err ] %r が無い。利用可能: %s' % (key, list(of.keys())))
        raise SystemExit(1)
    f = of[key]; f.Update()
    return f.Data


def scalar(a):
    a = np.asarray(a)
    if a.ndim > 1:
        a = a.reshape(a.shape[0], -1)[:, 0]
    return np.real(a).astype(float)


def emag(a):
    return np.sqrt(np.sum(np.abs(np.asarray(a)) ** 2, axis=1))


# ===== ① TI 包絡（スケール込み）=====
mags, scales = [], []
fd0 = None
for name, tgt in zip(NAMES, I_TARGET_MA):
    sim = get_sim(name)
    efd = field(sim, E_KEY)
    lfd = field(sim, LOSS_KEY)
    if fd0 is None:
        fd0 = efd
        g = fd0.Grid
        xa = np.asarray([float(v) for v in g.XAxis])
        ya = np.asarray([float(v) for v in g.YAxis])
        za = np.asarray([float(v) for v in g.ZAxis])
        VX, VY, VZ = np.meshgrid(np.diff(xa), np.diff(ya), np.diff(za), indexing='ij')
        vol_f = (VX * VY * VZ).transpose(2, 1, 0).ravel()   # X-fastest flat
        loss0, mag0 = scalar(lfd.Field(0)), emag(efd.Field(0))
    mag = emag(efd.Field(0))
    loss = scalar(lfd.Field(0))
    fin = np.isfinite(loss)
    p = float(np.sum(loss[fin] * vol_f[fin]))
    i_1v = LOSS_TO_I * p / DRIVE_V
    s = (tgt * 1e-3) / i_1v
    mags.append(mag); scales.append(s)
    print('[%s] P=%.6g W  I_1V=%.4f mA  → s=%.6g' % (name, p, i_1v * 1e3, s))
print('[scale] s1/s2 = %.6g （Phase2 実測 0.2056/0.3316 = 0.6200 と一致するか）'
      % (scales[0] / scales[1]))

e1 = scales[0] * mags[0]
e2 = scales[1] * mags[1]
material = np.isfinite(e1) & np.isfinite(e2)
ti_f = np.where(material, 2.0 * np.minimum(np.nan_to_num(e1), np.nan_to_num(e2)), np.nan)

# ===== ② σ から脳マスク =====
sigma = np.full(mag0.shape, np.nan)
ok = np.isfinite(mag0) & np.isfinite(loss0) & (mag0 > 0)
sigma[ok] = 2.0 * loss0[ok] / (mag0[ok] ** 2)
brain_f = np.isfinite(sigma) & (sigma >= BRAIN_BAND[0]) & (sigma <= BRAIN_BAND[1]) & material

# ===== 3D 化（X-fastest flat → (nx,ny,nz)）=====
nx, ny, nz = xa.size - 1, ya.size - 1, za.size - 1
cx = 0.5 * (xa[:-1] + xa[1:]) * 1000.0
cy = 0.5 * (ya[:-1] + ya[1:]) * 1000.0
cz = 0.5 * (za[:-1] + za[1:]) * 1000.0
print('[grid] cells %d x %d x %d = %d (arr %d)' % (nx, ny, nz, nx * ny * nz, ti_f.size))

ti3 = ti_f.reshape((nx, ny, nz), order='F')
brain3 = brain_f.reshape((nx, ny, nz), order='F')
vol3 = vol_f.reshape((nx, ny, nz), order='F')

# 並び順の検証（ROI 中心セルで flat と 3D が一致するか）
ic = int(np.argmin(np.abs(cx - FOCUS_MM[0])))
jc = int(np.argmin(np.abs(cy - FOCUS_MM[1])))
kc = int(np.argmin(np.abs(cz - FOCUS_MM[2])))
flat_c = ic + nx * (jc + ny * kc)
print('[chk ] ROI center 3D=%.4f / flat=%.4f V/m  σ=%.4f （一致すれば並び順 OK・期待 σ~0.348=WM）'
      % (ti3[ic, jc, kc], ti_f[flat_c], sigma[flat_c]))
print('[chk ] 脳マスク %d cells (%.1f mL)  ※Phase2 は 945 mL' % (int(brain3.sum()), float(vol3[brain3].sum()) * 1e6))

# ===== ③ 脳内ピークと -6dB =====
tin = np.nan_to_num(ti3, nan=-1.0)
tb = np.where(brain3, tin, -1.0)
pk_idx = np.unravel_index(int(np.argmax(tb)), tb.shape)
pk_val = float(ti3[pk_idx])
pk_mm = np.array([cx[pk_idx[0]], cy[pk_idx[1]], cz[pk_idx[2]]])
print('')
print('[peak] 脳内 TI max = %.4f V/m at (%.1f, %.1f, %.1f) mm' % ((pk_val,) + tuple(pk_mm)))
print('[peak] ROI 中心まで %.1f mm / ROI 中心の TI = %.4f V/m（Phase2 平均 0.2265）'
      % (np.linalg.norm(pk_mm - FOCUS_MM), ti3[ic, jc, kc]))
print('[peak] 材料全体の TI max = %.4f V/m（電極縁を含む）' % float(np.nanmax(ti_f)))

thr = pk_val * (10.0 ** (DB / 20.0))
print('[thr ] %.1f dB → TI >= %.4f V/m' % (DB, thr))


def connected(mask, seed):
    idx = np.array(np.nonzero(mask))
    lo = idx.min(axis=1); hi = idx.max(axis=1) + 1
    sl = tuple(slice(lo[a], hi[a]) for a in range(3))
    sub = mask[sl]
    comp = np.zeros_like(sub)
    comp[tuple(np.array(seed) - lo)] = True
    n_prev = 0; it = 0
    while True:
        nxt = comp.copy()
        nxt[1:, :, :] |= comp[:-1, :, :]; nxt[:-1, :, :] |= comp[1:, :, :]
        nxt[:, 1:, :] |= comp[:, :-1, :]; nxt[:, :-1, :] |= comp[:, 1:, :]
        nxt[:, :, 1:] |= comp[:, :, :-1]; nxt[:, :, :-1] |= comp[:, :, 1:]
        nxt &= sub
        n = int(nxt.sum()); it += 1
        if n == n_prev:
            break
        comp = nxt; n_prev = n
    full = np.zeros_like(mask)
    full[sl] = comp
    return full, it


def report(label, mask6):
    comp, it = connected(mask6, pk_idx)
    n = int(comp.sum())
    v_mm3 = float(vol3[comp].sum()) * 1e9
    ii, jj, kk = np.nonzero(comp)
    pts = np.stack([cx[ii], cy[jj], cz[kk]], axis=1)
    w = vol3[comp]
    ctr = (pts * w[:, None]).sum(axis=0) / w.sum()
    d = pts - ctr
    cov = (d * w[:, None]).T.dot(d) / w.sum()
    val, vec = np.linalg.eigh(cov)
    ax = vec[:, ::-1]                      # 主軸（分散の大きい順）
    proj = d.dot(ax)
    L = proj.max(axis=0) - proj.min(axis=0)
    d_eq = 2.0 * (3.0 * v_mm3 / (4.0 * np.pi)) ** (1.0 / 3.0)
    in_roi = np.linalg.norm(pts - FOCUS_MM, axis=1) <= ROI_R_MM
    print('')
    print('--- %s ---' % label)
    print('  -6dB cells   : %d (連結・膨張%d回) / 閾値超え全体 %d' % (n, it, int(mask6.sum())))
    print('  -6dB 体積    : %.1f mm^3 (%.4f mL)  等価球径 %.1f mm  ※TUS 2576/2.576/17.0'
          % (v_mm3, v_mm3 * 1e-3, d_eq))
    print('  主軸 全幅    : L1=%.1f  L2=%.1f  L3=%.1f mm （TUS: 軸49.7 / 側方16.6・11.2）'
          % (L[0], L[1], L[2]))
    print('  重心         : (%.1f, %.1f, %.1f) mm  ROI 中心まで %.1f mm'
          % (ctr[0], ctr[1], ctr[2], np.linalg.norm(ctr - FOCUS_MM)))
    print('  bbox XYZ     : %.1f x %.1f x %.1f mm'
          % (cx[ii].ptp() if n > 1 else 0.0, cy[jj].ptp() if n > 1 else 0.0, cz[kk].ptp() if n > 1 else 0.0))
    print('  ROI(r=10mm) 内に入る割合 : %.1f %% (%d/%d cells)  ※TUS 41.9%%'
          % (100.0 * in_roi.mean(), int(in_roi.sum()), n))
    return v_mm3, L


vb, Lb = report('脳内 -6dB 焦点（脳マスク内で連結）', brain3 & (tin >= thr))
vh, Lh = report('材料全体 -6dB 焦点（脳マスクなし・連結）', np.isfinite(ti3) & (tin >= thr))

# ===== 判定 =====
print('')
print('[判定] tTIS 脳内 -6dB: %.1f mm^3 (%.3f mL) / 主軸 %.1f×%.1f×%.1f mm' % (vb, vb * 1e-3, Lb[0], Lb[1], Lb[2]))
if vb > 2576.0 * 1.3:
    print('[判定] TUS(2576 mm^3) より %.1f 倍大きい ＝ 絶対サイズでも TUS が小さい'
          '→ 結論の芯①「焦点性は TUS 優位」を復活できる' % (vb / 2576.0))
elif vb < 2576.0 / 1.3:
    print('[判定] TUS(2576 mm^3) より %.1f 倍小さい ＝ 絶対サイズでは tTIS が小さい'
          '→ ①は書き換え（TUS の優位は選択性という比の量に限る）' % (2576.0 / vb))
else:
    print('[判定] TUS(2576 mm^3) と同程度 ＝ 焦点サイズでは差がつかない'
          '→ ①は「選択性という比の量に限る」に書き換え')
if vh > vb * 1.5:
    print('[判定] 材料全体版が脳内版の %.1f 倍 ＝ -6dB 領域が脳外（頭皮・電極側）へ大きく広がる' % (vh / vb))
else:
    print('[判定] 材料全体版 ≈ 脳内版 ＝ -6dB 領域はほぼ脳内に収まる')

print('')
print('=== 5-3 tTIS 焦点サイズ 完了（読み取りのみ・保存していない）===')
