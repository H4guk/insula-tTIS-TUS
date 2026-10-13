"""tTIS の脳内 TI 最大（延髄 1 セル・4.59 倍）が脳の端で跳ねた値かを確かめる（GH #17 チェックリスト 1・Sim4Life.lite・読み取りのみ）。2026-10-13。

**統合プロジェクト（tTIS_LF1 / tTIS_LF2 / TUS_250k が同居）で実行する。** 場と脳 12 組織の作り方は `brain_by_name.py` と同じ（関数をそのまま写した）。

なぜ:
  `brain_by_name.py` で、脳 12 組織の中の TI 最大は 1.04 V/m＝標的の 4.59 倍 @ (72.5, 276.5, 1511.5)・延髄・ROI から 60.2 mm。
  これは 1 セルの値で、延髄は脳の端（脳脊髄液・脊髄との境）にある。電極に近い境界のセルだけが突出しているなら、
  「脳内最大 4.59 倍」は脳の端の 1 セルの値で、#16 の標的外の点にも使えない。

出すもの:
  ① 最大点のまわり 5×5×5 の TI（標的の何倍）と、脳かどうか・組織の内訳
  ② 脳内の TI 上位 20 セル: 倍率・位置・ROI からの距離・組織・6 近傍のうち脳でないセル数（0＝脳の内側）
  ③ 1 セルに頼らない最大: 脳内の上位 0.1 %・1 % の値、「6 近傍がすべて脳」の内側セルだけの最大（値・位置・組織）
判定:
  まわりもなだらかに高く、内側セルの最大も 4.59 倍に近い → 本物の最大（4.59 倍・延髄を使う）
  1 セルだけ突出し、上位が境界（6 近傍に脳でないセル）に固まる → 境界の値。内側の最大か上位パーセンタイルで言い直す
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


def nonbrain_nbrs(i, j, k):
    out = []
    for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        a, b, c = i + d[0], j + d[1], k + d[2]
        if not brain[a, b, c]:
            out.append(tname3[a, b, c])
    return out


def where(i, j, k):
    pos = np.array([cx[i], cy[j], cz[k]])
    return pos, float(np.linalg.norm(pos - FOCUS_MM))


# ① 最大点のまわり 5×5×5
mi = np.unravel_index(int(np.argmax(np.where(brain, ti3, -1.0))), ti3.shape)
pos, dist = where(*mi)
print('')
print('=== ① 最大点 (%.1f, %.1f, %.1f)・%.2f 倍・%s のまわり 5×5×5（数値＝標的の何倍、* ＝脳 12 組織）==='
      % (pos[0], pos[1], pos[2], ti3[mi] / tgt, tname3[mi]))
for dk in range(-2, 3):
    print('  z = %.1f' % cz[mi[2] + dk])
    for dj in range(-2, 3):
        row = []
        for di in range(-2, 3):
            a, b, c = mi[0] + di, mi[1] + dj, mi[2] + dk
            row.append('%5.2f%s' % (ti3[a, b, c] / tgt, '*' if brain[a, b, c] else ' '))
        print('    y = %.1f  ' % cy[mi[1] + dj] + ' '.join(row))
sl = tuple(slice(m - 2, m + 3) for m in mi)
nb, bb = tname3[sl], brain[sl]
print('  組織の内訳: ' + ', '.join('%s %d' % (k, int((nb == k).sum())) for k in sorted(set(nb.ravel()))))
print('  脳セル %d / 125 ・ 脳セルの倍率 最小 %.2f ・ 中央 %.2f ・ 最大 %.2f'
      % (int(bb.sum()), (ti3[sl][bb] / tgt).min(), np.median(ti3[sl][bb] / tgt), (ti3[sl][bb] / tgt).max()))
print('  最大点の 6 近傍で脳でないもの: %s' % (', '.join(nonbrain_nbrs(*mi)) or 'なし（内側）'))

# ② 脳内の上位 20 セル
vals = np.where(brain, ti3, -1.0).ravel()
top = np.argsort(vals)[::-1][:20]
print('')
print('=== ② 脳内の TI 上位 20 セル ===')
print('  %-3s %-6s %-22s %-8s %-22s %s' % ('#', '倍率', '位置 [mm]', '距離', '組織', '6 近傍の非脳'))
for r, f in enumerate(top, 1):
    i, j, k = np.unravel_index(int(f), ti3.shape)
    p, d = where(i, j, k)
    nn = nonbrain_nbrs(i, j, k)
    print('  %-3d %-6.2f (%6.1f, %6.1f, %6.1f) %-8.1f %-22s %d %s'
          % (r, ti3[i, j, k] / tgt, p[0], p[1], p[2], d, tname3[i, j, k], len(nn),
             ('(' + ', '.join(sorted(set(nn))) + ')') if nn else ''))

# ③ 1 セルに頼らない最大
bv = ti3[brain]; bw = tv3[brain]
order = np.argsort(bv)[::-1]
cumw = np.cumsum(bw[order]) / bw.sum()
print('')
print('=== ③ 1 セルに頼らない最大 ===')
for q in (0.001, 0.01):
    v = float(bv[order][np.searchsorted(cumw, q)])
    print('  脳の体積の上位 %.1f %% の境の値: %.4g V/m ＝ 標的の %.2f 倍' % (100 * q, v, v / tgt))
inner = brain.copy()
inner[1:, :, :] &= brain[:-1, :, :]; inner[:-1, :, :] &= brain[1:, :, :]
inner[:, 1:, :] &= brain[:, :-1, :]; inner[:, :-1, :] &= brain[:, 1:, :]
inner[:, :, 1:] &= brain[:, :, :-1]; inner[:, :, :-1] &= brain[:, :, 1:]
ii = np.unravel_index(int(np.argmax(np.where(inner, ti3, -1.0))), ti3.shape)
p, d = where(*ii)
print('  内側セル（6 近傍がすべて脳）だけの最大: %.4g V/m ＝ 標的の %.2f 倍 @ (%.1f, %.1f, %.1f) ・ ROI から %.1f mm ・ %s'
      % (ti3[ii], ti3[ii] / tgt, p[0], p[1], p[2], d, tname3[ii]))
print('  内側セルは脳の %.1f %%（体積）' % (100.0 * float(tv3[inner].sum()) / float(tv3[brain].sum())))
print('')
print('=== 延髄の最大値の確認 完了（読み取りのみ・保存していない）===')
