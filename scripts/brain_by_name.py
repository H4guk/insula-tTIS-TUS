"""脳を「組織の名前」で定義し直して、tTIS と TUS の場のレベルの数値を出し直す（Sim4Life.lite・読み取りのみ）。2026-10-13。

**統合プロジェクト（tTIS_LF1 / tTIS_LF2 / TUS_250k が同居）で実行する。**

なぜ:
  旧い脳の定義は手法ごとに違い、どちらも脳以外が混ざっていた。
    tTIS: σ 0.33〜0.44 S/m（945 mL）。腱・靭帯・水晶体・気管が混ざり、小脳・橋・視床が抜けていた。
          「脳内 TI 最大 (48.5, 274.5, 1482.5)・標的の 10.7 倍」は腱・靭帯だった（`archive/neuron_offtarget_tissue_probe.py`）。
    TUS : c 1490〜1560・ρ 1035〜1058（1091 mL）。食道・唾液腺・下垂体なども帯に入る。
  新しい定義は、Input.h5 の `material_name` で決めた **脳実質 12 組織**（`archive/list_tissues.py`、約 1041.5 mL）を
  両手法で共通に使う。

出すもの（手法ごと・新旧の脳で並べる）:
  標的レベル（ROI 内の体積重み平均）・選択性（脳 − ROI の平均 ÷ ROI の平均、小さいほど良い）・
  V_target（脳内で標的レベル以上の体積）・V_half（標的レベルの半分以上）・ROI と地続きの部分・
  脳内最大（値・標的の何倍・位置・ROI 中心からの距離・その組織名）
旧い脳の数値が記録（tTIS 945.1 mL・選択性 0.3758・脳内最大 10.7 倍 / TUS 1091.3 mL）と一致すれば、場の計算は前と同じで、違いは脳の定義だけだと言える。
「ROI のうち脳」が 100% 近くなら、ボクセル（組織名）と場の並びが合っている（ずれていれば ROI＝白質の塊から外れて下がる）。
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
TUS_NAME = 'TUS_250k'

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


def report(label, unit, f3, brain3, roi3, vol3, cx, cy, cz, name3):
    mL = lambda m: float(vol3[m].sum()) * 1e6
    v_roi = mL(roi3)
    w = vol3[roi3 & brain3]
    tgt = float((f3[roi3 & brain3] * w).sum() / w.sum())
    non = brain3 & ~roi3
    wn = vol3[non]
    sel = float((f3[non] * wn).sum() / wn.sum()) / tgt
    v_brain = mL(brain3)
    ge = brain3 & (f3 >= tgt)
    ge_half = brain3 & (f3 >= tgt * 0.5)
    comp = connected_from(ge, roi3)
    v_ge, v_half, v_comp = mL(ge), mL(ge_half), mL(comp)
    mi = np.unravel_index(int(np.argmax(np.where(brain3, f3, -1.0))), f3.shape)
    mx = float(f3[mi])
    pos = np.array([cx[mi[0]], cy[mi[1]], cz[mi[2]]])
    dist = float(np.linalg.norm(pos - FOCUS_MM))
    print('  [%s] 脳 %.1f mL ・ ROI のうち脳 %.1f %% ・ 標的レベル %.4g %s ・ **選択性 %.4f**'
          % (label, v_brain, 100.0 * mL(roi3 & brain3) / v_roi, tgt, unit, sel))
    print('      V_target %.1f mL（ROI の %.1f 倍・脳の %.2f %%）・V_half %.1f mL・ROI と地続き %.1f mL（%.1f %%）'
          % (v_ge, v_ge / v_roi, 100.0 * v_ge / v_brain, v_half, v_comp,
             100.0 * v_comp / v_ge if v_ge > 0 else float('nan')))
    print('      脳内最大 %.4g %s ＝ 標的の **%.2f 倍** @ (%.1f, %.1f, %.1f) ・ ROI 中心から %.1f mm ・ 組織 %s'
          % (mx, unit, mx / tgt, pos[0], pos[1], pos[2], dist, name3[mi]))
    return dict(tgt=tgt, sel=sel, v_ge=v_ge, v_roi=v_roi, v_brain=v_brain, v_comp=v_comp, ratio=mx / tgt, pos=pos)


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
print('')
print('=== tTIS（TI 包絡・合計 2 mA）===')
print('  旧い脳（σ 帯）の中身: ' + ', '.join('%s %.1f' % (k, float(tv3[told3 & (tname3 == k)].sum()) * 1e6)
                                     for k in sorted(set(tname3[told3]))))
t_old = report('旧 σ 帯', 'V/m', ti3, told3, tr3, tv3, cx, cy, cz, tname3)
t_new = report('新 12 組織', 'V/m', ti3, tnew3, tr3, tv3, cx, cy, cz, tname3)

# ============ TUS ============
sim = get_sim(TUS_NAME)
pd = field(sim, 'p(x,y,z,f)')
mag = np.abs(np.asarray(pd.Field(0))).ravel()
xa2, ya2, za2 = axes_mm(pd.Grid)
nx2, ny2, nz2 = xa2.size - 1, ya2.size - 1, za2.size - 1
cx2, cy2, cz2, uv3 = cells_and_vol(xa2, ya2, za2)
p3 = mag.reshape((nx2, ny2, nz2), order='F')
ur3 = roi_mask(cx2, cy2, cz2)
vox2, nm2, lc, lr = voxel_names(sim, want_acoustic=True)
if vox2.shape != p3.shape:
    raise SystemExit('[TUS ] FAILED — voxels %s と場 %s の形が違う' % (vox2.shape, p3.shape))
uname3 = nm2[vox2]
c_grid = lc[vox2]; r_grid = lr[vox2]
uold3 = (c_grid >= 1490) & (c_grid <= 1560) & (r_grid >= 1035) & (r_grid <= 1058)
unew3 = np.isin(uname3, BRAIN_TISSUES)
print('')
print('=== TUS（|p|・音源 1 MPa の参照駆動。比なので駆動によらない）===')
print('  旧い脳（c・ρ 帯）の中身: ' + ', '.join('%s %.1f' % (k, float(uv3[uold3 & (uname3 == k)].sum()) * 1e6)
                                         for k in sorted(set(uname3[uold3]))))
u_old = report('旧 c・ρ 帯', 'Pa', p3, uold3, ur3, uv3, cx2, cy2, cz2, uname3)
u_new = report('新 12 組織', 'Pa', p3, unew3, ur3, uv3, cx2, cy2, cz2, uname3)

# ============ 比較（新しい脳）============
print('')
print('=== 比較（新 12 組織・両手法で同じ脳）===')
print('  %-6s %-10s %-14s %-12s %-16s %s' % ('手法', '選択性', 'V_target[mL]', 'ROI の何倍', '脳内最大/標的', 'ROI 中心からの距離[mm]'))
for lab, r in (('tTIS', t_new), ('TUS', u_new)):
    print('  %-6s %-10.4f %-14.1f %-12.1f %-16.2f %.1f'
          % (lab, r['sel'], r['v_ge'], r['v_ge'] / r['v_roi'], r['ratio'], float(np.linalg.norm(r['pos'] - FOCUS_MM))))
print('')
print('=== 脳を名前で定義し直した再計算 完了（読み取りのみ・保存していない）===')
