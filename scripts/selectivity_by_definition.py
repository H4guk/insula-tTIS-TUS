"""脳の定義を変えたときの選択性（感度解析・GH #17・Sim4Life.lite・読み取りのみ）。2026-10-14。

**統合プロジェクト（tTIS_LF1 / tTIS_LF2 / TUS_250k が同居）で実行する。** 場の作り方は `brain_by_name.py` と同じ（関数をそのまま写した）。

なぜ:
  提出物の感度解析（improve-plan ★1）は「脳の定義を変えても TUS < tTIS の順序は変わらない」を、
  tTIS は σ の帯（WM+GM 0.3758・GM のみ 0.3132・材料全体 1.3200）、TUS は c・ρ の帯（broad 0.1949・GM+WM 0.2017・頭部非水 0.1527）で
  示していた。帯には脳以外が混ざり、しかも手法ごとに定義が違った。
  ここでは定義を **組織の名前で決め、両手法で同じもの** を使う。

定義（どれも Input.h5 の material_name・両手法で同じ）:
  12 組織（主）: 脳実質 12 組織（`brain_by_name.py` と同じ）
  大脳 GM+WM   : Cerebrum_grey_matter・Cerebrum_white_matter
  大脳 GM のみ : Cerebrum_grey_matter
  旧い「材料全体」「頭部非水」は、tTIS と TUS で計算領域の広さが違う（tTIS は首から下も入る）ので同じ定義にできず、外した。

選択性 = （脳 − ROI）の体積重み平均 ÷ ROI の体積重み平均（小さいほど良い）。
  標的レベル（分母）は ROI 全体の平均で、どの定義でも同じ（ROI は 100% 脳 12 組織＝`brain_by_name.py` で確認済み）。
  12 組織の値が `brain_by_name.py` と一致すれば（tTIS 0.3576・TUS 0.1929）、計算は同じ。
判定:
  3 つの定義すべてで TUS < tTIS → 「脳の定義によらず TUS の方が標的に絞れる」をそのまま使う
  どこかで逆転・接近 → 感度解析の書き方を変える
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

DEFS = (
    ('12 組織（主）', BRAIN_TISSUES),
    ('大脳 GM+WM', ('Cerebrum_grey_matter', 'Cerebrum_white_matter')),
    ('大脳 GM のみ', ('Cerebrum_grey_matter',)),
)


def selectivity(f3, names3, roi3, vol3, valid3):
    w = vol3[roi3]
    tgt = float((f3[roi3] * w).sum() / w.sum())
    out = []
    for label, tissues in DEFS:
        m = np.isin(names3, tissues) & valid3
        non = m & ~roi3
        wn = vol3[non]
        out.append((label, float(vol3[m].sum()) * 1e6, float((f3[non] * wn).sum() / wn.sum()) / tgt))
    return tgt, out


t_tgt, t_sel = selectivity(ti3, tname3, tr3, tv3, material.reshape((nx, ny, nz), order='F'))
u_tgt, u_sel = selectivity(p3, uname3, ur3, uv3, np.ones_like(ur3))
print('')
print('[tgt ] 標的レベル（ROI 全体の平均）: tTIS %.4g V/m（期待 0.2265）・TUS %.4g Pa（期待 7.225e+05）' % (t_tgt, u_tgt))
print('')
print('=== 脳の定義を変えたときの選択性（小さいほど良い）===')
print('  %-14s %-12s %-10s %-10s %-14s %s' % ('定義', '体積[mL]', 'tTIS', 'TUS', 'tTIS / TUS', '順序'))
for (lab, vt, st), (_, vu, su) in zip(t_sel, u_sel):
    print('  %-14s %-12s %-10.4f %-10.4f %-14.2f %s'
          % (lab, '%.1f / %.1f' % (vt, vu), st, su, st / su, 'TUS < tTIS' if su < st else '★ 逆転'))
print('')
print('=== 定義別の選択性 完了（読み取りのみ・保存していない）===')
