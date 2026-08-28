"""Figure 1: 両手法の場スライスを島皮質断面で並置（**Sim4Life の Python コンソールで実行**）。

`probe_slice_export.py` で matplotlib 3.9.2 が使えると確認したので、Sim4Life 側で直接 PNG を作る。
出力: /home/smu/work/workspace/fig1_field_slices.png （+ .svg）  ← ブラウザからダウンロードする

設計:
  断面   : **X = 99.50mm の YZ 平面**（要求 99.1 の最近傍セル）。ビーム軸 (-0.089,0.842,-0.532) は
           X 成分がほぼゼロなのでこの面がビーム経路をほぼ含み、T7 電極（X=94.8）も近い。
  ★正規化: 両パネルとも「**標的レベル（ROI 内の体積重み平均）の何倍か**」にする。
           単位の違う場（V/m と Pa）が**同じ無次元スケール**で並び、カラーバーを共通にできる。
           **1.0 の等値線 = 標的と同じ強さの境界** ＝ Figure 2（reach volume）の 50.5 / 8.7 mL に対応。
  色     : 手法ごとの sequential（tTIS=blue / TUS=orange）。more-is-darker。vmax=4 で線形。
  重ねる : ROI 円（r=10mm・破線）／1.0 の等値線／脳の輪郭（薄いグレー）

配色は make_figures.py（Fig.2/3）と同じ定数を使い、3枚で見た目を揃える。
"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import h5py
import s4l_v1.document as document

OUT_DIR = '/home/smu/work/workspace'
SLICE_X_MM = 99.1
FOCUS_MM = np.array([99.1, 295.0, 1562.2])
ROI_R_MM = 10.0
Y_RANGE = (248.0, 362.0)
Z_RANGE = (1498.0, 1622.0)
VMAX = 4.0                      # 標的レベルの何倍まで色を割り当てるか
# ★表示範囲は両パネルで揃える。tTIS は空気中に電場が無い（材料外は NaN）が
#   TUS は背景が水なので値が続く——揃えないと非対称に見える（2026-08-28 修正）
XLIM = (250.0, 348.0)

TI_NAMES = ('tTIS_LF1', 'tTIS_LF2')
I_TARGET_MA = (0.891, 1.109)
LOSS_TO_I = 2.0
DRIVE_V = 1.0
E_KEY = 'EM E(x,y,z,f0)'
LOSS_KEY = 'El. Loss Density(x,y,z,f0)'
BRAIN_BAND = (0.33, 0.44)
TUS_NAME = 'TUS_250k'

SURFACE = '#fcfcfb'; INK = '#0b0b0b'; INK2 = '#52514e'; MUTED = '#8a8983'
TTIS = '#2a78d6'; TUS = '#eb6834'


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
    xa = np.asarray([float(v) for v in g.XAxis]) * 1000.0
    ya = np.asarray([float(v) for v in g.YAxis]) * 1000.0
    za = np.asarray([float(v) for v in g.ZAxis]) * 1000.0
    return xa, ya, za


def cells(xa, ya, za):
    return (0.5 * (xa[:-1] + xa[1:]), 0.5 * (ya[:-1] + ya[1:]), 0.5 * (za[:-1] + za[1:]))


def vol_of(xa, ya, za):
    return (np.diff(xa)[:, None, None] * np.diff(ya)[None, :, None] * np.diff(za)[None, None, :]) * 1e-9


def roi_mask(cx, cy, cz):
    return ((cx[:, None, None] - FOCUS_MM[0]) ** 2 + (cy[None, :, None] - FOCUS_MM[1]) ** 2
            + (cz[None, None, :] - FOCUS_MM[2]) ** 2) <= ROI_R_MM ** 2


# ============ tTIS: TI 包絡（スケール込み）と σ 脳マスク ============
mags, scales, fd0 = [], [], None
for name, tgt in zip(TI_NAMES, I_TARGET_MA):
    sim = get_sim(name)
    efd = field(sim, E_KEY); lfd = field(sim, LOSS_KEY)
    if fd0 is None:
        fd0 = efd
        xa, ya, za = axes_mm(fd0.Grid)
        VX, VY, VZ = np.meshgrid(np.diff(xa), np.diff(ya), np.diff(za), indexing='ij')
        vol_f = (VX * VY * VZ).transpose(2, 1, 0).ravel() * 1e-9
        loss0, mag0 = scalar(lfd.Field(0)), emag(efd.Field(0))
    mag = emag(efd.Field(0)); loss = scalar(lfd.Field(0))
    fin = np.isfinite(loss)
    i_1v = LOSS_TO_I * float(np.sum(loss[fin] * vol_f[fin])) / DRIVE_V
    mags.append(mag); scales.append((tgt * 1e-3) / i_1v)

e1 = scales[0] * mags[0]; e2 = scales[1] * mags[1]
material = np.isfinite(e1) & np.isfinite(e2)
ti_f = np.where(material, 2.0 * np.minimum(np.nan_to_num(e1), np.nan_to_num(e2)), np.nan)
sigma = np.full(mag0.shape, np.nan)
ok = np.isfinite(mag0) & np.isfinite(loss0) & (mag0 > 0)
sigma[ok] = 2.0 * loss0[ok] / (mag0[ok] ** 2)
brain_f = np.isfinite(sigma) & (sigma >= BRAIN_BAND[0]) & (sigma <= BRAIN_BAND[1]) & material

nx, ny, nz = xa.size - 1, ya.size - 1, za.size - 1
tcx, tcy, tcz = cells(xa, ya, za)
ti3 = ti_f.reshape((nx, ny, nz), order='F')
tb3 = brain_f.reshape((nx, ny, nz), order='F')
tv3 = vol_f.reshape((nx, ny, nz), order='F')
tr3 = roi_mask(tcx, tcy, tcz)
m = tr3 & tb3
ti_ref = float((np.nan_to_num(ti3)[m] * tv3[m]).sum() / tv3[m].sum())
print('[tTIS] 標的レベル（ROI 体積重み平均 TI）= %.4f V/m （期待 0.2265）' % ti_ref)

# ============ TUS: |p| と (c,rho) 脳マスク ============
sim = get_sim(TUS_NAME)
pd = field(sim, 'p(x,y,z,f)')
pmag = np.abs(np.asarray(pd.Field(0))).ravel()
xa2, ya2, za2 = axes_mm(pd.Grid)
nx2, ny2, nz2 = xa2.size - 1, ya2.size - 1, za2.size - 1
ucx, ucy, ucz = cells(xa2, ya2, za2)
p3 = pmag.reshape((nx2, ny2, nz2), order='F')
uv3 = vol_of(xa2, ya2, za2)


def uuid_hex(row):
    h = bytes(np.asarray(row, dtype=np.uint8).tolist()).hex()
    return '%s-%s-%s-%s-%s' % (h[0:8], h[8:12], h[12:16], h[16:20], h[20:32])


def prop_by_type(mat, tn):
    tnb = tn.encode() if isinstance(tn, str) else tn
    for pk in mat.keys():
        grp = mat[pk]
        ci = grp.get('_ClassInfo') if hasattr(grp, 'get') else None
        if ci is not None and ci.attrs.get('_TypeName') == tnb:
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
    voxels = mesh['voxels'][...]; id_map = mesh['id_map'][...]
    lut_c = np.full(int(voxels.max()) + 1, np.nan); lut_r = np.full(int(voxels.max()) + 1, np.nan)
    for v in np.unique(voxels):
        u = uuid_hex(id_map[v])
        if u in mm:
            lut_c[v] = prop_by_type(mm[u], 'CSoundSpeed')
            lut_r[v] = prop_by_type(mm[u], 'CMassDensity')

c3 = lut_c[voxels]; r3 = lut_r[voxels]
ub3 = (c3 >= 1490) & (c3 <= 1560) & (r3 >= 1035) & (r3 <= 1058)
ur3 = roi_mask(ucx, ucy, ucz)
mu = ur3 & ub3
p_ref = float((p3[mu] * uv3[mu]).sum() / uv3[mu].sum())
print('[TUS ] 標的レベル（ROI 体積重み平均 |p|）= %.4g Pa （期待 7.2e5）' % p_ref)

# ============ 断面を切る ============
def slab(c3d, cx, cy, cz, brain3):
    i = int(np.argmin(np.abs(cx - SLICE_X_MM)))
    js = np.where((cy >= Y_RANGE[0]) & (cy <= Y_RANGE[1]))[0]
    ks = np.where((cz >= Z_RANGE[0]) & (cz <= Z_RANGE[1]))[0]
    sl = c3d[i][np.ix_(js, ks)]
    br = brain3[i][np.ix_(js, ks)]
    return sl, br, cy[js], cz[ks], cx[i]


ti_sl, ti_br, ti_y, ti_z, x_used_t = slab(np.nan_to_num(ti3), tcx, tcy, tcz, tb3)
p_sl, p_br, p_y, p_z, x_used_u = slab(p3, ucx, ucy, ucz, ub3)
print('[slice] X=%.2f (tTIS) / %.2f (TUS) mm  断面 %s / %s'
      % (x_used_t, x_used_u, ti_sl.shape, p_sl.shape))

ti_n = ti_sl / ti_ref          # 標的レベルの何倍か
p_n = p_sl / p_ref

# ============ 描画 ============
def ramp(hex_hi):
    return LinearSegmentedColormap.from_list('r', [SURFACE, hex_hi], N=256)


plt.rcParams.update({'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
                     'savefig.facecolor': SURFACE, 'font.family': 'DejaVu Sans',
                     'font.size': 10, 'text.color': INK, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2})

fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), sharey=True)
panels = [('tTIS  (TI envelope)', ti_n, ti_br, ti_y, ti_z, TTIS),
          ('TUS  (|p|)', p_n, p_br, p_y, p_z, TUS)]

for ax, (title, dat, br, yv, zv, col) in zip(axes, panels):
    ext = [yv[0], yv[-1], zv[0], zv[-1]]
    im = ax.imshow(dat.T, origin='lower', extent=ext, aspect='equal',
                   cmap=ramp(col), vmin=0, vmax=VMAX, interpolation='nearest')
    # ★脳の外を薄くして脳内を主役にする（頭皮 near-field は文脈として残す）
    veil = np.zeros(br.T.shape + (4,))
    veil[..., :3] = 1.0
    veil[..., 3] = np.where(br.T, 0.0, 0.55)
    ax.imshow(veil, origin='lower', extent=ext, aspect='equal', interpolation='nearest')
    # 脳の輪郭
    ax.contour(yv, zv, br.T.astype(float), levels=[0.5], colors=[MUTED],
               linewidths=0.9)
    # 標的レベル（1.0）の等値線
    ax.contour(yv, zv, dat.T, levels=[1.0], colors=[INK], linewidths=1.4)
    # ROI 円
    th = np.linspace(0, 2 * np.pi, 200)
    ax.plot(FOCUS_MM[1] + ROI_R_MM * np.cos(th), FOCUS_MM[2] + ROI_R_MM * np.sin(th),
            color=INK, linestyle='--', linewidth=1.6)
    ax.set_title(title, loc='left', fontsize=12, color=INK, pad=8)
    ax.set_xlabel('Y [mm]', labelpad=6)
    ax.set_xlim(*XLIM)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)
    ax.spines['left'].set_color(MUTED); ax.spines['bottom'].set_color(MUTED)

axes[0].set_ylabel('Z [mm]')
cb = fig.colorbar(im, ax=axes, fraction=0.035, pad=0.02, extend='max')
cb.set_label('field strength / target level   (1.0 = ROI mean)', color=INK2)
cb.outline.set_edgecolor(MUTED)
fig.suptitle('Field on the insula plane (X = %.1f mm):  TUS forms a focus, tTIS does not'
             % x_used_t, x=0.02, ha='left', fontsize=13, color=INK)
fig.subplots_adjust(bottom=0.18)
fig.text(0.02, 0.03,
         'dashed circle = ROI (r = 10 mm) · black line = target level (1.0) · '
         'grey line = brain outline · area outside the brain is dimmed',
         fontsize=9, color=INK2)

for ext in ('png', 'svg'):
    path = os.path.join(OUT_DIR, 'fig1_field_slices.%s' % ext)
    fig.savefig(path, dpi=200, bbox_inches='tight')
    print('[out ] %s' % path)
plt.close(fig)
print('')
print('=== Figure 1 生成 完了 — workspace からダウンロードしてください ===')
