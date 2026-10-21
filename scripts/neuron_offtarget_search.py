"""#16 再開: tTIS の「標的外」を、軸索（MRG・長さ 10 mm）が脳に収まる点の中から選び直す（Sim4Life.lite・読み取りのみ）。2026-10-15。

**統合プロジェクト（tTIS_LF1 / tTIS_LF2 / TUS_250k が同居）で実行する。** 場と脳 12 組織の作り方は `brain_by_name.py` と同じ
（`archive/ti_brain_max_boundary_check.py` から関数を写した）。

なぜ:
  脳内の TI 最大（延髄の表面 (72.5, 276.5, 1511.5)・標的の 4.59 倍）と、その内側の候補 (72.5, 275.5, 1511.5) には、
  どの向き・長さでも軸索の線が脳に収まらなかった（`archive/neuron_offtarget_line_fit.py`。10 mm で脳 22〜66%）。
  電場は脳脊髄液との境で強くなりやすいので、「TI が一番高いセル」はどうしても脳の端になる。
  そこで標的外を「**10 mm の線が脳に収まる点のうち TI が一番高い所**」と定義し直す（本人の判断: 神経は両手法とも MRG のまま）。

やること:
  脳 12 組織のセルを TI の高い順に見て、ROI 中心から 20 mm 以上離れたものについて、
  長さ 10 mm の線（0.25 mm 刻み 41 点）が脳に入る割合を 13 方向（26 近傍の向きの半分）で調べる。
  出すもの:
    (A) x・y・z の3方向すべてで脳 95% 以上の点のうち TI 最大（標的と同じ置き方ができる点）
    (B) どれか1方向で脳 100% の点のうち TI 最大（その向きも出す）
    参考: 上位の候補 10 個（倍率・位置・組織・ROI からの距離・3方向の脳の割合）

結果（2026-10-15）: s1/s2 0.619856・標的レベル 0.2265 V/m（記録どおり）。上位 10 候補はすべて延髄（4.13〜4.59 倍・ROI から 60〜65 mm）で、
  3方向とも収まるものは無い。
  (A) 3方向とも脳 95% 以上: **2.50 倍 @ (73.5, 266.5, 1512.5)・延髄・ROI から 62.8 mm**（TI 順位 548・x 95% y 100% z 95%）
  (B) 1方向で脳 100%: **4.16 倍 @ (75.5, 264.5, 1509.5)・延髄・65.3 mm**（TI 順位 7・向き y）
"""
import numpy as np
import h5py
import s4l_v1.document as document

FOCUS_MM = np.array([99.1, 295.0, 1562.2])
ROI_R_MM = 10.0

TI_NAMES = ('tTIS_LF1', 'tTIS_LF2')
I_TARGET_MA = (0.891, 1.109)
DRIVE_V = 1.0
LOSS_TO_I = 2.0
E_KEY = 'EM E(x,y,z,f0)'
LOSS_KEY = 'El. Loss Density(x,y,z,f0)'
BRAIN_BAND = (0.33, 0.44)

BRAIN_TISSUES = (
    'Cerebrum_grey_matter', 'Cerebrum_white_matter', 'Cerebellum', 'Corpus_callosum', 'Pons', 'Thalamus',
    'Medulla_oblongata', 'Hippocampus', 'Midbrain', 'Hypothalamus', 'Pineal_body', 'Commissura_posterior',
)


def get_sim(name):
    hit = [s for s in document.AllSimulations if s.Name == name]
    if len(hit) != 1:
        raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (name, len(hit)))
    return hit[0]


def field(sim, key):
    res = sim.Results(); res.UpdateAll()
    of = res['Overall Field']; of.Update(0)
    f = of[key]; f.Update()
    return f.Data


def scalar(a):
    a = np.asarray(a)
    if a.ndim > 1:
        a = a.reshape(a.shape[0], -1)[:, 0]
    return np.real(a).astype(float)


def emag(a):
    return np.sqrt(np.sum(np.abs(np.asarray(a)) ** 2, axis=1))


def axes_mm(g):
    xa = np.asarray([float(v) for v in g.XAxis])
    ya = np.asarray([float(v) for v in g.YAxis])
    za = np.asarray([float(v) for v in g.ZAxis])
    return xa, ya, za


def cells_and_vol(xa, ya, za):
    cx = 0.5 * (xa[:-1] + xa[1:]) * 1000.0
    cy = 0.5 * (ya[:-1] + ya[1:]) * 1000.0
    cz = 0.5 * (za[:-1] + za[1:]) * 1000.0
    vol = (np.diff(xa)[:, None, None] * np.diff(ya)[None, :, None] * np.diff(za)[None, None, :])
    return cx, cy, cz, vol


def roi_mask(cx, cy, cz):
    return ((cx[:, None, None] - FOCUS_MM[0]) ** 2 + (cy[None, :, None] - FOCUS_MM[1]) ** 2
            + (cz[None, None, :] - FOCUS_MM[2]) ** 2) <= ROI_R_MM ** 2


def connected_from(mask, seeds):
    """mask のうち seeds(bool) と 6近傍で地続きの部分。bbox に切って反復膨張。"""
    if not mask.any() or not (mask & seeds).any():
        return np.zeros_like(mask)
    idx = np.array(np.nonzero(mask))
    lo = idx.min(axis=1); hi = idx.max(axis=1) + 1
    sl = tuple(slice(lo[a], hi[a]) for a in range(3))
    sub = mask[sl]
    comp = (seeds & mask)[sl].copy()
    n_prev = -1
    while int(comp.sum()) != n_prev:
        n_prev = int(comp.sum())
        nxt = comp.copy()
        nxt[1:, :, :] |= comp[:-1, :, :]; nxt[:-1, :, :] |= comp[1:, :, :]
        nxt[:, 1:, :] |= comp[:, :-1, :]; nxt[:, :-1, :] |= comp[:, 1:, :]
        nxt[:, :, 1:] |= comp[:, :, :-1]; nxt[:, :, :-1] |= comp[:, :, 1:]
        comp = nxt & sub
    full = np.zeros_like(mask)
    full[sl] = comp
    return full




def uuid_hex(row):
    h = bytes(np.asarray(row, dtype=np.uint8).tolist()).hex()
    return '%s-%s-%s-%s-%s' % (h[0:8], h[8:12], h[12:16], h[16:20], h[20:32])


def text(v):
    return v.decode(errors='replace') if isinstance(v, bytes) else str(v)


def prop_by_type(mat, typename):
    tn = typename.encode()
    for pk in mat.keys():
        grp = mat[pk]
        ci = grp.get('_ClassInfo') if hasattr(grp, 'get') else None
        if ci is not None and ci.attrs.get('_TypeName') == tn:
            try:
                return float(grp['_Object'].attrs['Value'])
            except Exception:
                return np.nan
    return np.nan


def voxel_names(sim, want_acoustic=False):
    """ボクセルごとの組織名の配列（名前の短縮形＝括弧の前）と、TUS 用に c・ρ。"""
    with h5py.File(sim.GetInputFileName(), 'r') as f:
        mm = f['AllMaterialMaps'][list(f['AllMaterialMaps'].keys())[0]]
        mesh = None
        for k in f['Meshes']:
            if 'voxels' in f['Meshes'][k]:
                mesh = f['Meshes'][k]; break
        voxels = mesh['voxels'][...]
        id_map = mesh['id_map'][...]
        n = int(voxels.max()) + 1
        names = np.array(['Background'] * n, dtype=object)
        lut_c = np.full(n, np.nan); lut_r = np.full(n, np.nan)
        for v in range(min(n, id_map.shape[0])):
            u = uuid_hex(id_map[v])
            if u in mm:
                names[v] = text(mm[u].attrs.get('material_name', '?')).split('(')[0].strip()
                if want_acoustic:
                    lut_c[v] = prop_by_type(mm[u], 'CSoundSpeed')
                    lut_r[v] = prop_by_type(mm[u], 'CMassDensity')
    return voxels, names, lut_c, lut_r


# ============ tTIS ============
mags, scales = [], []
fd0 = None
for name, tgt_ma in zip(TI_NAMES, I_TARGET_MA):
    sim = get_sim(name)
    efd = field(sim, E_KEY); lfd = field(sim, LOSS_KEY)
    if fd0 is None:
        fd0 = efd
        xa, ya, za = axes_mm(fd0.Grid)
        VX, VY, VZ = np.meshgrid(np.diff(xa), np.diff(ya), np.diff(za), indexing='ij')
        vol_f = (VX * VY * VZ).transpose(2, 1, 0).ravel()
        loss0, mag0 = scalar(lfd.Field(0)), emag(efd.Field(0))
    mag = emag(efd.Field(0)); loss = scalar(lfd.Field(0))
    fin = np.isfinite(loss)
    i_1v = LOSS_TO_I * float(np.sum(loss[fin] * vol_f[fin])) / DRIVE_V
    mags.append(mag); scales.append((tgt_ma * 1e-3) / i_1v)
print('[tTIS] s1/s2 = %.6g （期待 0.6199）' % (scales[0] / scales[1]))
e1 = scales[0] * mags[0]; e2 = scales[1] * mags[1]
material = np.isfinite(e1) & np.isfinite(e2)
ti_f = np.where(material, 2.0 * np.minimum(np.nan_to_num(e1), np.nan_to_num(e2)), -1.0)
sigma = np.full(mag0.shape, np.nan)
ok = np.isfinite(mag0) & np.isfinite(loss0) & (mag0 > 0)
sigma[ok] = 2.0 * loss0[ok] / (mag0[ok] ** 2)
old_f = np.isfinite(sigma) & (sigma >= BRAIN_BAND[0]) & (sigma <= BRAIN_BAND[1]) & material

nx, ny, nz = xa.size - 1, ya.size - 1, za.size - 1
cx, cy, cz, _ = cells_and_vol(xa, ya, za)
ti3 = ti_f.reshape((nx, ny, nz), order='F')
tv3 = vol_f.reshape((nx, ny, nz), order='F')
tr3 = roi_mask(cx, cy, cz)
told3 = old_f.reshape((nx, ny, nz), order='F')
vox, nm, _, _ = voxel_names(get_sim(TI_NAMES[0]))
if vox.shape != ti3.shape:
    raise SystemExit('[tTIS] FAILED — voxels %s と場 %s の形が違う' % (vox.shape, ti3.shape))
tname3 = nm[vox]
tnew3 = np.isin(tname3, BRAIN_TISSUES) & material.reshape((nx, ny, nz), order='F')

brain = tnew3
w = tv3[tr3 & brain]
tgt = float((ti3[tr3 & brain] * w).sum() / w.sum())
print('[tTIS] 標的レベル %.4g V/m（期待 0.2265）' % tgt)



FIT = 0.95
LEN = 10.0
STEP = 0.25
MIN_DIST = 20.0
N_TRY = 20000

dirs13 = []
for a in (-1, 0, 1):
    for b in (-1, 0, 1):
        for c in (-1, 0, 1):
            v = np.array([a, b, c], float)
            if np.linalg.norm(v) == 0:
                continue
            v = v / np.linalg.norm(v)
            if not any(np.allclose(v, u) or np.allclose(v, -u) for u in dirs13):
                dirs13.append(v)
AXES = {'x': np.array([1.0, 0, 0]), 'y': np.array([0, 1.0, 0]), 'z': np.array([0, 0, 1.0])}
s = np.arange(-LEN / 2, LEN / 2 + 1e-9, STEP)


def idx_of(ax, v):
    return int(np.argmin(np.abs(ax - v)))


def frac_brain(p, u):
    n_in = 0
    for t in s:
        q = p + t * u
        if not (cx[0] <= q[0] <= cx[-1] and cy[0] <= q[1] <= cy[-1] and cz[0] <= q[2] <= cz[-1]):
            continue
        if brain[idx_of(cx, q[0]), idx_of(cy, q[1]), idx_of(cz, q[2])]:
            n_in += 1
    return n_in / float(s.size)


ti_b = np.where(brain, ti3, -1.0)
order = np.argsort(ti_b, axis=None)[::-1]
best_a = best_b = None
rows = []
for n, flat in enumerate(order[:N_TRY]):
    i, j, k = np.unravel_index(int(flat), ti3.shape)
    if ti_b[i, j, k] <= 0:
        break
    p = np.array([cx[i], cy[j], cz[k]])
    dist = float(np.linalg.norm(p - FOCUS_MM))
    if dist < MIN_DIST:
        continue
    fx = {d: frac_brain(p, u) for d, u in AXES.items()}
    if len(rows) < 10:
        rows.append((ti3[i, j, k] / tgt, p, tname3[i, j, k], dist, fx))
    if best_a is None and min(fx.values()) >= FIT:
        best_a = (ti3[i, j, k] / tgt, p, tname3[i, j, k], dist, fx, n)
    if best_b is None:
        for u in dirs13:
            if frac_brain(p, u) >= 0.999:
                best_b = (ti3[i, j, k] / tgt, p, tname3[i, j, k], dist, u, n)
                break
    if best_a is not None and best_b is not None:
        break

print('')
print('[top ] 上位の候補（ROI から %.0f mm 以上）' % MIN_DIST)
for r, p, nm_, d, fx in rows:
    print('  %5.2f 倍 @ (%.1f, %.1f, %.1f) %-22s %5.1f mm  脳の割合 x %3.0f%% y %3.0f%% z %3.0f%%'
          % (r, p[0], p[1], p[2], nm_, d, 100 * fx['x'], 100 * fx['y'], 100 * fx['z']))
print('')
if best_a:
    r, p, nm_, d, fx, n = best_a
    print('(A) 3方向とも脳 %.0f%% 以上: %.2f 倍 @ (%.1f, %.1f, %.1f) %s ・ ROI から %.1f mm ・ TI 順位 %d ・ x %.0f%% y %.0f%% z %.0f%%'
          % (100 * FIT, r, p[0], p[1], p[2], nm_, d, n + 1, 100 * fx['x'], 100 * fx['y'], 100 * fx['z']))
else:
    print('(A) 上位 %d セルの中に該当なし' % N_TRY)
if best_b:
    r, p, nm_, d, u, n = best_b
    print('(B) 1方向で脳 100%%: %.2f 倍 @ (%.1f, %.1f, %.1f) %s ・ ROI から %.1f mm ・ TI 順位 %d ・ 向き (%.2f, %.2f, %.2f)'
          % (r, p[0], p[1], p[2], nm_, d, n + 1, u[0], u[1], u[2]))
else:
    print('(B) 上位 %d セルの中に該当なし' % N_TRY)
print('')
print('=== 標的外の選び直し 完了（読み取りのみ・保存していない）===')
