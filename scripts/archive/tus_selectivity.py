"""T-6d / 4-6 TUS 選択性（脳マスク＋ROI・|p| 体積重み平均・読み取り専用）。

厳密な脳マスクは Input.h5 の voxels（セル→材料インデックス）から作る。
  voxel値 → id_map[値] の UUID → AllMaterialMaps の材料 → Property(_TypeName=CSoundSpeed / CMassDensity) の _Object.attrs['Value']
★材料ごとに Property の並び順が違うので、固定 index でなく _TypeName で探す（2026-08-25 の修正）。

選択性 = 非標的（脳 − ROI）の |p| 体積重み平均 / 標的（ROI）の平均（小さいほど良い）。
tTIS と同一形式（複数定義併記）。tTIS の選択性は 0.3758（V/m ベース・比なので無次元で TUS と揃う）。
"""
import numpy as np
import h5py
import s4l_v1.document as document

SIM_NAME = 'TUS_250k'
FOCUS_MM = np.array([99.1, 295.0, 1562.2])
ROI_R_MM = 10.0
T7_MM = np.array([94.8, 335.8, 1536.4])
sim = [s for s in document.AllSimulations if s.Name == SIM_NAME][0]

# --- 場 |p| ---
res = sim.Results(); res.UpdateAll()
of = res['Overall Field']; of.Update(0)
pf = of['p(x,y,z,f)']; pf.Update()
data = pf.Data
mag = np.abs(np.asarray(data.Field(0))).ravel()
g = data.Grid
Xm = np.asarray(g.XAxis); Ym = np.asarray(g.YAxis); Zm = np.asarray(g.ZAxis)
cx = 0.5 * (Xm[:-1] + Xm[1:]) * 1000; cy = 0.5 * (Ym[:-1] + Ym[1:]) * 1000; cz = 0.5 * (Zm[:-1] + Zm[1:]) * 1000
nx, ny, nz = cx.size, cy.size, cz.size
mag3 = mag.reshape((nx, ny, nz), order='F')
vol = np.diff(Xm)[:, None, None] * np.diff(Ym)[None, :, None] * np.diff(Zm)[None, None, :]

# --- voxels -> (c, rho)（_TypeName で property を探す）---
path = sim.GetInputFileName()


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


with h5py.File(path, 'r') as f:
    mm = f['AllMaterialMaps'][list(f['AllMaterialMaps'].keys())[0]]
    mesh = None
    for k in f['Meshes']:
        if 'voxels' in f['Meshes'][k]:
            mesh = f['Meshes'][k]; break
    voxels = mesh['voxels'][...]
    id_map = mesh['id_map'][...]
    maxv = int(voxels.max())
    lut_c = np.full(maxv + 1, np.nan); lut_r = np.full(maxv + 1, np.nan)
    for v in np.unique(voxels):
        u = uuid_hex(id_map[v])
        if u in mm:
            lut_c[v] = prop_by_type(mm[u], 'CSoundSpeed')
            lut_r[v] = prop_by_type(mm[u], 'CMassDensity')

n_bad = int(np.sum(~np.isfinite(lut_c[np.unique(voxels)])))
print('[lut ] voxel値 %d 種  c/ρ 取得できない値 %d 種（Transducer 等は c/ρ 無しで正常）'
      % (np.unique(voxels).size, n_bad))
c_grid = lut_c[voxels]; r_grid = lut_r[voxels]

# --- 整合検証: ROI 中心セル ---
ic = int(np.argmin(np.abs(cx - FOCUS_MM[0]))); jc = int(np.argmin(np.abs(cy - FOCUS_MM[1]))); kc = int(np.argmin(np.abs(cz - FOCUS_MM[2])))
print('[chk ] ROI center: c=%.1f rho=%.1f |p|=%.4g Pa (期待 脳 c~1500-1552 / |p|~1.4e6)'
      % (c_grid[ic, jc, kc], r_grid[ic, jc, kc], mag3[ic, jc, kc]))

# --- マスク ---
roi = ((cx[:, None, None] - FOCUS_MM[0]) ** 2 + (cy[None, :, None] - FOCUS_MM[1]) ** 2
       + (cz[None, None, :] - FOCUS_MM[2]) ** 2) <= ROI_R_MM ** 2
brain = (c_grid >= 1490) & (c_grid <= 1560) & (r_grid >= 1035) & (r_grid <= 1058)
gmwm = (((np.abs(c_grid - 1500) < 3) & (np.abs(r_grid - 1044.5) < 3)) |
        ((np.abs(c_grid - 1552.5) < 3) & (np.abs(r_grid - 1041) < 3)))
head = (voxels != 0)


def wmean(m):
    w = vol[m]
    return float((mag3[m] * w).sum() / w.sum()) if w.sum() > 0 else float('nan')


def mL(m):
    return float(vol[m].sum()) * 1e6


tgt = wmean(roi)
print('')
print('[mask] ROI %d (%.2f mL) / 脳broad %d (%.1f mL) / GM+WM %d (%.1f mL) / 頭部非水 %d (%.1f mL)'
      % (int(roi.sum()), mL(roi), int(brain.sum()), mL(brain), int(gmwm.sum()), mL(gmwm), int(head.sum()), mL(head)))
print('[tgt ] ROI |p| 体積重み平均=%.4g  最大=%.4g Pa' % (tgt, float(mag3[roi].max())))
print('')
print('--- 選択性（非標的/標的・小さいほど良い・tTIS=0.3758）---')
for label, m in (('脳broad − ROI', brain & ~roi), ('GM+WM − ROI', gmwm & ~roi), ('頭部非水 − ROI', head & ~roi)):
    nt = wmean(m)
    print('  %-16s 非標的平均=%-10.4g 選択性=%.4f' % (label, nt, nt / tgt))

d = FOCUS_MM - T7_MM; d = d / np.linalg.norm(d)
ph = T7_MM + 15.0 * d
ih = int(np.argmin(np.abs(cx - ph[0]))); jh = int(np.argmin(np.abs(cy - ph[1]))); kh = int(np.argmin(np.abs(cz - ph[2])))
print('')
print('[hot ] near-field 山(s=15): c=%.1f rho=%.1f |p|=%.4g（脳なら選択性悪化=実脳被曝）'
      % (c_grid[ih, jh, kh], r_grid[ih, jh, kh], mag3[ih, jh, kh]))
print('=== 4-6 選択性 完了 ===')
