"""5-3b tTIS の焦点の有無を切り分ける（局所極大＋ROI 貫通プロファイル・読み取り専用）。

5-3 で「脳内 TI 最大は標的から 96.6mm の電極側」と分かり、**グローバルピーク基準の -6dB が
tTIS では成立しない**ことが判明した。そこで測り直しの前に、より基本的な問いを片付ける:

  **島皮質に「焦点」と呼べる局所極大があるのか、それとも電極側へ向かう裾の途中なのか。**

2つの見方を突き合わせる:
  ① ROI 中心 ±40mm の箱の中で、脳マスク内の **26近傍すべてより大きいセル（局所極大）** を列挙し、
     標的にどれだけ近いものがあるかを見る（グローバル最大が電極側にあるのは既知なので箱に限定）。
  ② ROI 中心を通る **X / Y / Z 3方向の TI プロファイル**（±40mm）を出し、標的の位置に山があるか、
     一方向へ単調に増えているだけかを目で見る。

場の作り方・並び順は ti_focus_size.py / ti_analysis.py と同一。
脳マスクは 2026-10-14（GH #17）に σ 0.33〜0.44 の帯から、Input.h5 の material_name で決めた脳実質 12 組織
（`brain_by_name.py` と同一）に替えた。旧い帯は腱・靭帯・気管・水晶体が混ざり、小脳・橋・視床が抜けていた。
"""
import numpy as np
import h5py
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
BOX_MM = 40.0          # ROI 中心まわりの探索箱（半幅）
PROF_MM = 40.0         # プロファイルの片側長
TOP_N = 12             # 列挙する局所極大の数
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


def voxel_names(sim):
    """ボクセルの id の配列と、id ごとの組織名（括弧の前）。brain_by_name.py と同一。"""
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
        for v in range(min(n, id_map.shape[0])):
            h = bytes(np.asarray(id_map[v], dtype=np.uint8).tolist()).hex()
            u = '%s-%s-%s-%s-%s' % (h[0:8], h[8:12], h[12:16], h[16:20], h[20:32])
            if u in mm:
                nm = mm[u].attrs.get('material_name', '?')
                names[v] = (nm.decode(errors='replace') if isinstance(nm, bytes) else str(nm)).split('(')[0].strip()
    return voxels, names


# ===== 場（ti_focus_size.py と同一手順）=====
mags, scales = [], []
fd0 = None
for name, tgt in zip(NAMES, I_TARGET_MA):
    sim = get_sim(name)
    efd = field(sim, E_KEY); lfd = field(sim, LOSS_KEY)
    if fd0 is None:
        fd0 = efd
        g = fd0.Grid
        xa = np.asarray([float(v) for v in g.XAxis])
        ya = np.asarray([float(v) for v in g.YAxis])
        za = np.asarray([float(v) for v in g.ZAxis])
        VX, VY, VZ = np.meshgrid(np.diff(xa), np.diff(ya), np.diff(za), indexing='ij')
        vol_f = (VX * VY * VZ).transpose(2, 1, 0).ravel()
        loss0, mag0 = scalar(lfd.Field(0)), emag(efd.Field(0))
    mag = emag(efd.Field(0)); loss = scalar(lfd.Field(0))
    fin = np.isfinite(loss)
    i_1v = LOSS_TO_I * float(np.sum(loss[fin] * vol_f[fin])) / DRIVE_V
    mags.append(mag); scales.append((tgt * 1e-3) / i_1v)
print('[scale] s1=%.6g s2=%.6g  s1/s2=%.6g （Phase2 0.2056/0.3316=0.6200）'
      % (scales[0], scales[1], scales[0] / scales[1]))

e1 = scales[0] * mags[0]; e2 = scales[1] * mags[1]
material = np.isfinite(e1) & np.isfinite(e2)
ti_f = np.where(material, 2.0 * np.minimum(np.nan_to_num(e1), np.nan_to_num(e2)), np.nan)

sigma = np.full(mag0.shape, np.nan)
ok = np.isfinite(mag0) & np.isfinite(loss0) & (mag0 > 0)
sigma[ok] = 2.0 * loss0[ok] / (mag0[ok] ** 2)
brain_f = np.isfinite(sigma) & (sigma >= BRAIN_BAND[0]) & (sigma <= BRAIN_BAND[1]) & material

nx, ny, nz = xa.size - 1, ya.size - 1, za.size - 1
cx = 0.5 * (xa[:-1] + xa[1:]) * 1000.0
cy = 0.5 * (ya[:-1] + ya[1:]) * 1000.0
cz = 0.5 * (za[:-1] + za[1:]) * 1000.0
ti3 = ti_f.reshape((nx, ny, nz), order='F')
old3 = brain_f.reshape((nx, ny, nz), order='F')
vox, nm = voxel_names(get_sim(NAMES[0]))
if vox.shape != ti3.shape:
    raise SystemExit('[pre ] FAILED — voxels %s と場 %s の形が違う' % (vox.shape, ti3.shape))
brain3 = np.isin(nm[vox], BRAIN_TISSUES) & material.reshape((nx, ny, nz), order='F')
vol3 = vol_f.reshape((nx, ny, nz), order='F')
tin = np.nan_to_num(ti3, nan=-1.0)

ic = int(np.argmin(np.abs(cx - FOCUS_MM[0])))
jc = int(np.argmin(np.abs(cy - FOCUS_MM[1])))
kc = int(np.argmin(np.abs(cz - FOCUS_MM[2])))
print('[chk ] ROI center TI=%.4f V/m σ=%.4f / 脳（12 組織）%.1f mL ／ 旧い σ 帯 %.1f mL （期待 0.2229 / 0.3480 / 1041.5 / 945.1）'
      % (ti3[ic, jc, kc], sigma[ic + nx * (jc + ny * kc)], float(vol3[brain3].sum()) * 1e6,
         float(vol3[old3].sum()) * 1e6))

# ===== ① ROI 周辺 ±40mm の箱で局所極大（26近傍）=====
i0, i1 = int(np.searchsorted(cx, FOCUS_MM[0] - BOX_MM)), int(np.searchsorted(cx, FOCUS_MM[0] + BOX_MM))
j0, j1 = int(np.searchsorted(cy, FOCUS_MM[1] - BOX_MM)), int(np.searchsorted(cy, FOCUS_MM[1] + BOX_MM))
k0, k1 = int(np.searchsorted(cz, FOCUS_MM[2] - BOX_MM)), int(np.searchsorted(cz, FOCUS_MM[2] + BOX_MM))
sub = tin[i0:i1, j0:j1, k0:k1]
subb = brain3[i0:i1, j0:j1, k0:k1]
print('')
print('[box ] ROI 中心 ±%.0fmm = %d x %d x %d cells（脳セル %d）'
      % (BOX_MM, sub.shape[0], sub.shape[1], sub.shape[2], int(subb.sum())))

ismax = np.ones_like(sub, dtype=bool)
for di in (-1, 0, 1):
    for dj in (-1, 0, 1):
        for dk in (-1, 0, 1):
            if di == 0 and dj == 0 and dk == 0:
                continue
            sh = np.roll(np.roll(np.roll(sub, di, 0), dj, 1), dk, 2)
            ismax &= (sub >= sh)
ismax[0, :, :] = False; ismax[-1, :, :] = False        # 箱の縁は判定不能
ismax[:, 0, :] = False; ismax[:, -1, :] = False
ismax[:, :, 0] = False; ismax[:, :, -1] = False
ismax &= subb & (sub > 0)

ii, jj, kk = np.nonzero(ismax)
if ii.size == 0:
    print('[max ] 箱の中に脳内局所極大が 1つも無い ＝ 島皮質周辺は単調な裾')
else:
    pts = np.stack([cx[ii + i0], cy[jj + j0], cz[kk + k0]], axis=1)
    val = sub[ii, jj, kk]
    dist = np.linalg.norm(pts - FOCUS_MM, axis=1)
    order = np.argsort(-val)[:TOP_N]
    print('[max ] 脳内局所極大 %d 個。TI 降順 上位%d（ROI 中心 %s）:' % (ii.size, min(TOP_N, ii.size), np.round(FOCUS_MM, 1)))
    print('       %-10s %-28s %-10s %s' % ('TI[V/m]', '座標[mm]', 'ROIまで', 'ROI内?'))
    for t in order:
        print('       %-10.4f %-28s %-10.1f %s'
              % (val[t], str(np.round(pts[t], 1)), dist[t], 'YES' if dist[t] <= ROI_R_MM else ''))
    n_in = int(np.sum(dist <= ROI_R_MM))
    near = int(np.argmin(dist))
    print('[max ] ROI(r=10mm) 内の局所極大 %d 個 / 最も近い極大は %.1f mm（TI=%.4f）'
          % (n_in, dist[near], val[near]))

# ROI 内の最大セルが局所極大かどうか
roi3 = ((cx[:, None, None] - FOCUS_MM[0]) ** 2 + (cy[None, :, None] - FOCUS_MM[1]) ** 2
        + (cz[None, None, :] - FOCUS_MM[2]) ** 2) <= ROI_R_MM ** 2
rm = np.where(roi3 & brain3, tin, -1.0)
ri = np.unravel_index(int(np.argmax(rm)), rm.shape)
nb = tin[max(ri[0] - 1, 0):ri[0] + 2, max(ri[1] - 1, 0):ri[1] + 2, max(ri[2] - 1, 0):ri[2] + 2]
print('[roi ] ROI 内の TI 最大 %.4f V/m at (%.1f,%.1f,%.1f) — 26近傍の最大は %.4f → %s'
      % (tin[ri], cx[ri[0]], cy[ri[1]], cz[ri[2]], nb.max(),
         '局所極大（山の頂）' if nb.max() <= tin[ri] else '局所極大でない（斜面の途中）'))

# ===== ② ROI 中心を通る 3方向プロファイル =====
print('')
print('=== ROI 中心を通る TI プロファイル（±%.0fmm・バーは各方向の最大で正規化）===' % PROF_MM)
for axname, carr, idx in (('X', cx, 0), ('Y', cy, 1), ('Z', cz, 2)):
    off = np.arange(-PROF_MM, PROF_MM + 1, 2.0)
    vals, sig = [], []
    for o in off:
        p = FOCUS_MM.copy(); p[idx] += o
        a = int(np.argmin(np.abs(cx - p[0]))); b = int(np.argmin(np.abs(cy - p[1]))); c = int(np.argmin(np.abs(cz - p[2])))
        vals.append(tin[a, b, c]); sig.append(brain3[a, b, c])
    vals = np.array(vals)
    vmax = vals.max() if vals.max() > 0 else 1.0
    print('')
    print('--- %s 方向（+ は %s 増加・脳外は . 印）---' % (axname, axname))
    for o, v, s in zip(off, vals, sig):
        bar = '#' * int(round(40.0 * max(v, 0) / vmax))
        mark = ' ' if s else '.'
        here = ' <= ROI 中心' if abs(o) < 1e-6 else ''
        print('  %+6.1f mm %s %8.4f |%-40s|%s' % (o, mark, v, bar, here))
    print('  この方向の最大 %.4f V/m at %+.1f mm' % (vals.max(), off[int(np.argmax(vals))]))

print('')
print('[判定材料] ROI 中心 TI=%.4f / 脳内グローバル最大 TI=%.4f（延髄・標的から 60.2mm）'
      % (ti3[ic, jc, kc], float(np.max(np.where(brain3, tin, -1.0)))))
print('=== 5-3b 完了（読み取りのみ・保存していない）===')
