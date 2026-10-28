"""5-2/5-3 測り直し: 「標的レベル以上の刺激が及ぶ脳体積」を両手法共通で測る（読み取り専用）。

**統合プロジェクト（tTIS_LF1 / tTIS_LF2 / TUS_250k が同居）で実行する。**

なぜこの指標か:
  5-3b で tTIS は島皮質に「焦点」と呼べる極大を作らないと判明した（脳内 TI 最大は標的から 96.6mm の
  電極側）。よって**ピーク基準の -6dB は tTIS に成立しない**。両手法に共通で成立する問いに変える:

    **標的に与えているのと同じ強さ以上の刺激が、脳の何 mL に及んでいるか。**

  基準は各手法の **ROI 内の体積重み平均**（tTIS: TI [V/m] / TUS: |p| [Pa]）。単位が違っても
  「標的と同じレベル」という無次元の基準なので同じ土俵に乗る。

出すもの（手法ごと）:
  ① 標的レベル = ROI 内の体積重み平均
  ② V_target  = 脳内で「値 >= 標的レベル」の体積 [mL]  ＋ V_target/V_ROI ＋ 脳に占める割合
  ③ V_half    = 同 >= 標的レベル/2（-6dB 相当）の体積
  ④ 連結領域  = ②のうち **ROI と地続き**の部分（離れた高値域＝電極近傍などを分離して数える）
  ⑤ ROI 内割合 = ②のうち ROI 内に入る割合

読み方: 焦点を結ぶ手法なら ② は焦点の周りに限られる。結ばない手法では脳の広範囲に散らばる。
"""
import numpy as np
import s4l_v1.document as document

FOCUS_MM = np.array([99.1, 295.0, 1562.2])
ROI_R_MM = 10.0

# --- tTIS 側 ---
TI_NAMES = ('tTIS_LF1', 'tTIS_LF2')
I_TARGET_MA = (0.891, 1.109)
DRIVE_V = 1.0
LOSS_TO_I = 2.0
E_KEY = 'EM E(x,y,z,f0)'
LOSS_KEY = 'El. Loss Density(x,y,z,f0)'
BRAIN_BAND = (0.33, 0.44)

# --- TUS 側 ---
TUS_NAME = 'TUS_250k'


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


def report(label, unit, f3, brain3, roi3, vol3):
    """共通の集計。f3 は NaN を含まない実数配列（NaN は -1 に潰しておく）。"""
    mL = lambda m: float(vol3[m].sum()) * 1e6
    v_roi = mL(roi3)
    w = vol3[roi3 & brain3]
    tgt = float((f3[roi3 & brain3] * w).sum() / w.sum())
    v_brain = mL(brain3)

    ge = brain3 & (f3 >= tgt)
    ge_half = brain3 & (f3 >= tgt * 0.5)
    comp = connected_from(ge, roi3)

    v_ge, v_half, v_comp = mL(ge), mL(ge_half), mL(comp)
    in_roi = mL(ge & roi3)

    print('')
    print('=== %s ===' % label)
    print('  標的レベル（ROI 内 体積重み平均） : %.4g %s' % (tgt, unit))
    print('  ROI 体積 / 脳体積                 : %.3f mL / %.1f mL' % (v_roi, v_brain))
    print('  ① V_target（脳内 >= 標的レベル）  : **%.1f mL**  ＝ ROI の %.1f 倍 ・ 脳の %.1f %%'
          % (v_ge, v_ge / v_roi, 100.0 * v_ge / v_brain))
    print('  ② V_half（脳内 >= 標的/2・-6dB相当）: %.1f mL  ＝ ROI の %.1f 倍 ・ 脳の %.1f %%'
          % (v_half, v_half / v_roi, 100.0 * v_half / v_brain))
    print('  ③ ①のうち ROI と地続きの連結領域   : **%.1f mL**（①の %.1f %%）'
          % (v_comp, 100.0 * v_comp / v_ge if v_ge > 0 else float('nan')))
    print('  ④ ①のうち ROI 内に入る体積        : %.3f mL（①の %.2f %% / ROI の %.1f %%）'
          % (in_roi, 100.0 * in_roi / v_ge if v_ge > 0 else float('nan'), 100.0 * in_roi / v_roi))
    print('  参考: 脳内 最大 %.4g %s / 標的レベルの %.1f 倍'
          % (float(f3[brain3].max()), unit, float(f3[brain3].max()) / tgt))
    return dict(tgt=tgt, v_roi=v_roi, v_brain=v_brain, v_ge=v_ge, v_half=v_half, v_comp=v_comp)


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
brain_f = np.isfinite(sigma) & (sigma >= BRAIN_BAND[0]) & (sigma <= BRAIN_BAND[1]) & material

nx, ny, nz = xa.size - 1, ya.size - 1, za.size - 1
cx, cy, cz, _ = cells_and_vol(xa, ya, za)
ti3 = ti_f.reshape((nx, ny, nz), order='F')
tb3 = brain_f.reshape((nx, ny, nz), order='F')
tv3 = vol_f.reshape((nx, ny, nz), order='F')
tr3 = roi_mask(cx, cy, cz)
print('[tTIS] grid %d x %d x %d / 脳 %.1f mL（期待 945.1）'
      % (nx, ny, nz, float(tv3[tb3].sum()) * 1e6))
r_ti = report('tTIS（TI 包絡）', 'V/m', ti3, tb3, tr3, tv3)

# ============ TUS ============
import h5py
sim = get_sim(TUS_NAME)
pd = field(sim, 'p(x,y,z,f)')
mag = np.abs(np.asarray(pd.Field(0))).ravel()
xa2, ya2, za2 = axes_mm(pd.Grid)
nx2, ny2, nz2 = xa2.size - 1, ya2.size - 1, za2.size - 1
cx2, cy2, cz2, uv = cells_and_vol(xa2, ya2, za2)
p3 = mag.reshape((nx2, ny2, nz2), order='F')
uv3 = uv


def uuid_hex(row):
    h = bytes(np.asarray(row, dtype=np.uint8).tolist()).hex()
    return '%s-%s-%s-%s-%s' % (h[0:8], h[8:12], h[12:16], h[16:20], h[20:32])


def prop_by_type(mat, typename):
    tn = typename.encode() if isinstance(typename, str) else typename
    for pk in mat.keys():
        grp = mat[pk]
        ci = grp.get('_ClassInfo') if hasattr(grp, 'get') else None
        if ci is not None and ci.attrs.get('_TypeName') == tn:
            try:
                return float(grp['_Object'].attrs['Value'])
            except Exception:
                return np.nan
    return np.nan


with h5py.File(sim.GetInputFileName(), 'r') as f:
    mm = f['AllMaterialMaps'][list(f['AllMaterialMaps'].keys())[0]]
    mesh = None
    for k in f['Meshes']:
        if 'voxels' in f['Meshes'][k]:
            mesh = f['Meshes'][k]; break
    voxels = mesh['voxels'][...]
    id_map = mesh['id_map'][...]
    lut_c = np.full(int(voxels.max()) + 1, np.nan); lut_r = np.full(int(voxels.max()) + 1, np.nan)
    for v in np.unique(voxels):
        u = uuid_hex(id_map[v])
        if u in mm:
            lut_c[v] = prop_by_type(mm[u], 'CSoundSpeed')
            lut_r[v] = prop_by_type(mm[u], 'CMassDensity')

c_grid = lut_c[voxels]; r_grid = lut_r[voxels]
ub3 = (c_grid >= 1490) & (c_grid <= 1560) & (r_grid >= 1035) & (r_grid <= 1058)
ur3 = roi_mask(cx2, cy2, cz2)
print('')
print('[TUS ] grid %d x %d x %d / 脳broad %.1f mL（期待 1091.3）'
      % (nx2, ny2, nz2, float(uv3[ub3].sum()) * 1e6))
r_us = report('TUS（|p|）', 'Pa', p3, ub3, ur3, uv3)

# ============ 比較 ============
print('')
print('=== 比較（標的レベル以上が及ぶ脳体積）===')
print('  %-8s %-14s %-14s %-14s %s' % ('手法', 'V_target[mL]', 'ROI の何倍', '脳の何%', 'うち ROI 地続き[mL]'))
for lab, r in (('tTIS', r_ti), ('TUS', r_us)):
    print('  %-8s %-14.1f %-14.1f %-14.1f %.1f'
          % (lab, r['v_ge'], r['v_ge'] / r['v_roi'], 100.0 * r['v_ge'] / r['v_brain'], r['v_comp']))

ratio = r_ti['v_ge'] / r_us['v_ge'] if r_us['v_ge'] > 0 else float('inf')
print('')
print('[判定] tTIS の V_target は TUS の %.1f 倍' % ratio)
if ratio >= 10:
    print('[判定] **一桁以上大きい ＝「TUS は焦点を結ぶ／tTIS は結ばない」が定量的に確定**')
elif ratio >= 2:
    print('[判定] 数倍の差 ＝ 傾向は同じだが「一桁」とは言えない。表現を「N 倍広い」に調整する')
else:
    print('[判定] 同程度 ＝ 5-3b のプロファイル所見と食い違う。指標の定義から見直す')

print('')
print('=== 5-2/5-3 測り直し 完了（読み取りのみ・保存していない）===')
