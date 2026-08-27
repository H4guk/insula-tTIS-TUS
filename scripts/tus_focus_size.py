"""5-2 TUS 焦点サイズの実測（-6dB 焦点領域・Sim4Life.lite Python コンソール・読み取り専用）。

設計値（側方 7.3mm / 軸 61.7mm・F#=1.21 の解析見積り）を、実際の場から測った値に置き換える。

手順:
  ① 圧力場 |p| と、Input.h5 の voxels→(c, ρ) から作る厳密な脳マスク（tus_selectivity.py と同一定義）
  ② 脳内の |p| ピークを探す（頭皮 near-field の山を除外するため脳内に限定）
  ③ 閾値 = 0.5 * ピーク（-6dB・振幅半分＝強度 1/4。音響の FWHM 相当の標準境界）
  ④ ピークを種にした連結領域（6近傍）を切り出す＝焦点。離れた副極大は数えない
  ⑤ 領域のセル中心を ビーム軸 u=(ROI中心 - T7)/|..| と直交2軸 v,w に射影して
     軸長・側方径（-6dB 全幅）を出す。体積は cell 体積の総和
  ⑥ 頭部全域版（脳マスクなし）も出し、焦点が頭皮の山と連結していないかを確認する

出力の読み方は docs/comparison-framework.md §3 の軸 A（焦点サイズ）に入る。
"""
import numpy as np
import h5py
import s4l_v1.document as document

SIM_NAME = 'TUS_250k'
FOCUS_MM = np.array([99.1, 295.0, 1562.2])    # ROI 中心 [mm]（tTIS と同一）
ROI_R_MM = 10.0
T7_MM = np.array([94.8, 335.8, 1536.4])       # 頭皮 T7（source 面付近）
DB = -6.0                                      # 焦点の境界 [dB]

sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

# --- ① 場 ---
res = sim.Results(); res.UpdateAll()
of = res['Overall Field']; of.Update(0)
pf = of['p(x,y,z,f)']; pf.Update()
data = pf.Data
mag = np.abs(np.asarray(data.Field(0))).ravel()
g = data.Grid
Xm = np.asarray(g.XAxis); Ym = np.asarray(g.YAxis); Zm = np.asarray(g.ZAxis)
cx = 0.5 * (Xm[:-1] + Xm[1:]) * 1000.0
cy = 0.5 * (Ym[:-1] + Ym[1:]) * 1000.0
cz = 0.5 * (Zm[:-1] + Zm[1:]) * 1000.0
nx, ny, nz = cx.size, cy.size, cz.size
mag3 = mag.reshape((nx, ny, nz), order='F')
vol = (np.diff(Xm)[:, None, None] * np.diff(Ym)[None, :, None] * np.diff(Zm)[None, None, :])
print('[grid] cells %d x %d x %d = %d' % (nx, ny, nz, nx * ny * nz))

# --- ① 脳マスク（voxels -> c, rho）---
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

c_grid = lut_c[voxels]; r_grid = lut_r[voxels]
brain = (c_grid >= 1490) & (c_grid <= 1560) & (r_grid >= 1035) & (r_grid <= 1058)
head = (voxels != 0)

# 整合検証（4-6 と同じ数字が出るか）
ic = int(np.argmin(np.abs(cx - FOCUS_MM[0])))
jc = int(np.argmin(np.abs(cy - FOCUS_MM[1])))
kc = int(np.argmin(np.abs(cz - FOCUS_MM[2])))
print('[chk ] ROI center: c=%.1f rho=%.1f |p|=%.4g Pa (期待 c~1500-1552 / |p|~1.4e6)'
      % (c_grid[ic, jc, kc], r_grid[ic, jc, kc], mag3[ic, jc, kc]))
print('[chk ] 脳マスク %d cells (%.1f mL)' % (int(brain.sum()), float(vol[brain].sum()) * 1e6))

# --- ② 脳内ピーク ---
mb = np.where(brain, mag3, -1.0)
pk_idx = np.unravel_index(int(np.argmax(mb)), mb.shape)
pk_val = float(mag3[pk_idx])
pk_mm = np.array([cx[pk_idx[0]], cy[pk_idx[1]], cz[pk_idx[2]]])
print('')
print('[peak] 脳内 |p|max = %.4g Pa at (%.1f, %.1f, %.1f) mm' % ((pk_val,) + tuple(pk_mm)))
print('[peak] ROI 中心まで %.1f mm / 全体 |p|max = %.4g Pa（頭皮込み）'
      % (np.linalg.norm(pk_mm - FOCUS_MM), float(mag3.max())))

# --- ③ 閾値 ---
thr = pk_val * (10.0 ** (DB / 20.0))
print('[thr ] %.1f dB → |p| >= %.4g Pa (= %.3f x peak)' % (DB, thr, 10.0 ** (DB / 20.0)))

# --- ④ 連結領域（6近傍・種はピーク・scipy 無しでも動く反復膨張）---
u = FOCUS_MM - T7_MM; u = u / np.linalg.norm(u)
tmp = np.array([1.0, 0.0, 0.0])
if abs(np.dot(tmp, u)) > 0.9:
    tmp = np.array([0.0, 0.0, 1.0])
v = np.cross(u, tmp); v = v / np.linalg.norm(v)
w = np.cross(u, v)


def connected(mask, seed):
    """mask 内で seed を含む 6近傍連結成分（bbox に切って反復膨張）。"""
    idx = np.array(np.nonzero(mask))
    lo = idx.min(axis=1); hi = idx.max(axis=1) + 1
    sl = tuple(slice(lo[a], hi[a]) for a in range(3))
    sub = mask[sl]
    comp = np.zeros_like(sub)
    comp[tuple(np.array(seed) - lo)] = True
    n_prev = 0
    it = 0
    while True:
        nxt = comp.copy()
        nxt[1:, :, :] |= comp[:-1, :, :]; nxt[:-1, :, :] |= comp[1:, :, :]
        nxt[:, 1:, :] |= comp[:, :-1, :]; nxt[:, :-1, :] |= comp[:, 1:, :]
        nxt[:, :, 1:] |= comp[:, :, :-1]; nxt[:, :, :-1] |= comp[:, :, 1:]
        nxt &= sub
        n = int(nxt.sum())
        it += 1
        if n == n_prev:
            break
        comp = nxt; n_prev = n
    full = np.zeros_like(mask)
    full[sl] = comp
    return full, it


def report(label, mask6):
    comp, it = connected(mask6, pk_idx)
    n = int(comp.sum())
    v_mm3 = float(vol[comp].sum()) * 1e9
    ii, jj, kk = np.nonzero(comp)
    pts = np.stack([cx[ii], cy[jj], cz[kk]], axis=1) - pk_mm
    su = pts.dot(u); sv = pts.dot(v); sw = pts.dot(w)
    d_eq = 2.0 * (3.0 * v_mm3 / (4.0 * np.pi)) ** (1.0 / 3.0)
    in_roi = np.linalg.norm(pts + pk_mm - FOCUS_MM, axis=1) <= ROI_R_MM
    print('')
    print('--- %s ---' % label)
    print('  -6dB cells   : %d (連結・膨張%d回) / 閾値超え全体 %d' % (n, it, int(mask6.sum())))
    print('  -6dB 体積    : %.1f mm^3 (%.4f mL)  等価球径 %.1f mm' % (v_mm3, v_mm3 * 1e-3, d_eq))
    print('  軸方向 長さ  : %.1f mm  (u 方向 %.1f 〜 %.1f・設計 61.7)' % (su.max() - su.min(), su.min(), su.max()))
    print('  側方 径 v    : %.1f mm  (設計 7.3)' % (sv.max() - sv.min()))
    print('  側方 径 w    : %.1f mm  (設計 7.3)' % (sw.max() - sw.min()))
    print('  bbox XYZ     : %.1f x %.1f x %.1f mm'
          % (cx[ii].ptp() if n > 1 else 0.0, cy[jj].ptp() if n > 1 else 0.0, cz[kk].ptp() if n > 1 else 0.0))
    print('  ROI(r=10mm) 内に入る割合 : %.1f %% (%d/%d cells)'
          % (100.0 * in_roi.mean(), int(in_roi.sum()), n))
    return comp, v_mm3, su.max() - su.min(), max(sv.max() - sv.min(), sw.max() - sw.min())


comp_b, vb, lenb, latb = report('脳内 -6dB 焦点（脳マスク内で連結）', brain & (mag3 >= thr))
comp_h, vh, lenh, lath = report('頭部全域 -6dB 焦点（脳マスクなし・連結）', head & (mag3 >= thr))

# --- ⑥ 頭皮の山と連結しているか ---
print('')
d = FOCUS_MM - T7_MM; dn = d / np.linalg.norm(d)
scalp = T7_MM + 15.0 * dn
i2 = int(np.argmin(np.abs(cx - scalp[0]))); j2 = int(np.argmin(np.abs(cy - scalp[1]))); k2 = int(np.argmin(np.abs(cz - scalp[2])))
print('[sep ] near-field 山(s=15mm) |p|=%.4g Pa / 焦点 -6dB 閾値 %.4g Pa' % (mag3[i2, j2, k2], thr))
print('[sep ] 頭皮の山は焦点の連結領域に%s' % ('含まれる（分離できていない）' if comp_h[i2, j2, k2] else '含まれない（分離している）'))
if vh > vb * 1.5:
    print('[sep ] 頭部全域版が脳内版の %.1f 倍 ＝ -6dB 領域が脳外へ大きくはみ出している' % (vh / vb))
else:
    print('[sep ] 頭部全域版 ≈ 脳内版 ＝ -6dB 焦点はほぼ脳内に収まる')

# --- 判定 ---
print('')
print('[判定] 脳内 -6dB: 側方 %.1f mm / 軸 %.1f mm / %.1f mm^3' % (latb, lenb, vb))
if latb <= 2 * ROI_R_MM:
    print('[判定] 側方径は ROI 直径 %.0f mm 以内 ＝ 島皮質の幅には収まる' % (2 * ROI_R_MM))
else:
    print('[判定] 側方径が ROI 直径 %.0f mm を超える ＝ 隣接領域へ及ぶ（選択性の数字と突き合わせ）' % (2 * ROI_R_MM))
if lenb > 2 * ROI_R_MM:
    print('[判定] 軸方向は ROI 直径を超える ＝ 葉巻型・味覚ゾーンより軸に長い（tTIS との差の主張点）')
else:
    print('[判定] 軸方向も ROI 内に収まる ＝ 想定より鋭い焦点（設計値と乖離・要確認）')

print('')
print('=== 5-2 TUS 焦点サイズ 完了 ===')
