"""TUS 安全駆動の再測（MI<1.9 での焦点線量・読み取り専用）。

`phase4-tus.md` 4-4a の値（音源 0.148MPa → 焦点 0.30MPa・ISPPA 2.9 W/cm²）は
**2026-08-25 の分離版**で出したもので、統合版では取り直していない。
MI は**頭皮の1点（皮下脂肪の最大値）**で決まる量なので、5-1g の知見
「単一セルの値は 6〜7% 動く」がそのまま効く。⇒ 統合版で再測する。

計算式（4-4a の再構成。実装スクリプトが残っていないため `phase4-tus.md` の記述から復元）:
  MI   = p_neg[MPa] / sqrt(f[MHz])       f=0.25MHz なので **MI = 2 × p[MPa]**
         （定常正弦波なので |p| = 振幅 = |p_neg|）
  k    = 1.9 / MI_ref                     参照1MPa 駆動の全体最大 MI を 1.9 に落とすスケール
  ISPPA= p^2 / (2 ρ c)                    ρ, c は**その場所の局所値**
  有効域: ISPPA 3–30 W/cm²（Sharif et al. 2025 / 一次 Lee 2021・Rabut 2020）

**式の検算**: 分離版の記録（頭皮最大 6.404MPa → MI 12.8 / 音源 0.148MPa / 焦点 0.30MPa）を
この式で再現できるかを出力に併記する。再現できなければ式の復元が違う。
"""
import numpy as np
import h5py
import s4l_v1.document as document

SIM_NAME = 'TUS_250k'
FREQ_MHZ = 0.25
MI_LIMIT = 1.9                      # FDA / ITRUSST
FOCUS_MM = np.array([99.1, 295.0, 1562.2])
ROI_R_MM = 10.0
EFF_LO, EFF_HI = 3.0, 30.0          # ISPPA の有効域 [W/cm^2]

# 分離版（2026-08-25・4-4a）の記録値。式の検算と統合版との比較に使う
REF = dict(scalp_mpa=6.404, mi_ref=12.8, src_mpa=0.148, focus_mpa=0.30, isppa=2.9)


def mi(p_pa):
    return (p_pa * 1e-6) / np.sqrt(FREQ_MHZ)


sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

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
p3 = mag.reshape((nx, ny, nz), order='F')
vol = (np.diff(Xm)[:, None, None] * np.diff(Ym)[None, :, None] * np.diff(Zm)[None, None, :])


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
    lut_c = np.full(int(voxels.max()) + 1, np.nan)
    lut_r = np.full(int(voxels.max()) + 1, np.nan)
    for v in np.unique(voxels):
        u = uuid_hex(id_map[v])
        if u in mm:
            lut_c[v] = prop_by_type(mm[u], 'CSoundSpeed')
            lut_r[v] = prop_by_type(mm[u], 'CMassDensity')

c3 = lut_c[voxels]; r3 = lut_r[voxels]
brain = (c3 >= 1490) & (c3 <= 1560) & (r3 >= 1035) & (r3 <= 1058)
roi = ((cx[:, None, None] - FOCUS_MM[0]) ** 2 + (cy[None, :, None] - FOCUS_MM[1]) ** 2
       + (cz[None, None, :] - FOCUS_MM[2]) ** 2) <= ROI_R_MM ** 2

print('[grid] %d x %d x %d = %d cells' % (nx, ny, nz, nx * ny * nz))

# ===== ① 参照駆動（音源 1MPa）での全体最大＝MI の律速点 =====
gi = np.unravel_index(int(np.argmax(p3)), p3.shape)
g_p = float(p3[gi])
g_mm = np.array([cx[gi[0]], cy[gi[1]], cz[gi[2]]])
g_c, g_r = float(c3[gi]), float(r3[gi])
print('')
print('[ref ] 参照駆動（音源 1 MPa）')
print('  全体最大 |p| = %.4g Pa = %.3f MPa  at (%.1f, %.1f, %.1f)'
      % (g_p, g_p * 1e-6, g_mm[0], g_mm[1], g_mm[2]))
print('  その場所の材料: c=%.1f m/s  rho=%.1f kg/m^3  %s'
      % (g_c, g_r, '（脳内）' if brain[gi] else '（脳外＝頭皮側のはず）'))
print('  MI(参照) = %.2f    ※分離版の記録 %.1f（頭皮 %.3f MPa）'
      % (mi(g_p), REF['mi_ref'], REF['scalp_mpa']))

# ===== ② MI<1.9 に落とすスケール =====
k = MI_LIMIT / mi(g_p)
print('')
print('[safe] MI を %.1f に落とすスケール k = %.5f  → **音源 %.4f MPa**（記録 %.3f MPa）'
      % (MI_LIMIT, k, k, REF['src_mpa']))

# ===== ③ その駆動での標的線量 =====
bi = np.unravel_index(int(np.argmax(np.where(brain, p3, -1.0))), p3.shape)
b_p = float(p3[bi]) * k
b_c, b_r = float(c3[bi]), float(r3[bi])

w = vol[roi & brain]
roi_mean = float((p3[roi & brain] * w).sum() / w.sum()) * k
ri = np.unravel_index(int(np.argmax(np.where(roi & brain, p3, -1.0))), p3.shape)
roi_max = float(p3[ri]) * k
r_c, r_r = float(c3[ri]), float(r3[ri])


def isppa(p_pa, rho, c):
    return p_pa ** 2 / (2.0 * rho * c) * 1e-4      # W/m^2 → W/cm^2


# ★ISPPA は p^2 に比例するので (平均p)^2 != 平均(p^2)。
#   ROI の代表値は**セルごとに ISPPA を出してから体積平均**を取る（2026-08-28 修正）。
isppa_map = (p3 * k) ** 2 / (2.0 * r3 * c3) * 1e-4     # [W/cm^2] 局所 rho,c を使用
m = roi & brain
wv = vol[m]
isppa_mean = float((isppa_map[m] * wv).sum() / wv.sum())
isppa_max = float(isppa_map[m].max())

print('')
print('[dose] MI<%.1f 駆動での標的線量' % MI_LIMIT)
print('  脳内ピーク   |p| = %.4f MPa  MI = %.3f  ISPPA = %.2f W/cm^2  （記録 焦点 %.2f MPa）'
      % (b_p * 1e-6, mi(b_p), isppa(b_p, b_r, b_c), REF['focus_mpa']))
print('  ROI 内 最大  |p| = %.4f MPa  MI = %.3f  **ISPPA = %.2f W/cm^2**  （記録 %.1f）'
      % (roi_max * 1e-6, mi(roi_max), isppa_max, REF['isppa']))
print('  ROI 体積平均 |p| = %.4f MPa  MI = %.3f  **ISPPA = %.3f W/cm^2**'
      % (roi_mean * 1e-6, mi(roi_mean), isppa_mean))
print('     ※参考: 平均 |p| から計算すると %.3f（p^2 の非線形性で**過小評価**になるので使わない）'
      % isppa(roi_mean, r_r, r_c))
print('  （ISPPA は局所 rho*c を使用: ROI max で rho=%.1f c=%.1f）' % (r_r, r_c))

# ===== ④ ROI のうち有効域に入る体積割合（tTIS の「閾値超え 1.5%」に対応）=====
v_roi = float(wv.sum())
frac = float(vol[m & (isppa_map >= EFF_LO)].sum()) / v_roi
print('')
print('[frac] **ROI のうち ISPPA >= %.0f W/cm^2 の体積割合 = %.1f %%**' % (EFF_LO, 100.0 * frac))
print('       ※tTIS の対応値＝「TI が閾値 0.3 V/m を超える ROI 体積割合 = 1.5 %」')
print('')
print('[sym ] **統計量を揃えた比較**（tTIS / TUS）')
print('  ROI 平均 / 基準 : tTIS 0.2265/0.3 = 75.5 %%   TUS %.3f/%.0f = %.1f %%'
      % (isppa_mean, EFF_LO, 100.0 * isppa_mean / EFF_LO))
print('  ROI 最大 / 基準 : tTIS 0.3259/0.3 = 108.6 %%  TUS %.2f/%.0f = %.1f %%'
      % (isppa_max, EFF_LO, 100.0 * isppa_max / EFF_LO))
print('  基準超えの ROI 体積割合 : tTIS 1.5 %%   TUS %.1f %%' % (100.0 * frac))

# ===== ⑤ 有効域との照合 =====
val = isppa_max
print('')
print('[lit ] TUS 神経調節の有効域 ISPPA %.0f–%.0f W/cm^2（Sharif 2025）' % (EFF_LO, EFF_HI))
if val < EFF_LO:
    print('[判定] ROI max %.2f は**下端 %.0f を下回る**（%.0f%%）＝安全上限では有効域に届かない'
          % (val, EFF_LO, 100.0 * val / EFF_LO))
else:
    print('[判定] ROI max %.2f は有効域に入る（下端の %.2f 倍）' % (val, val / EFF_LO))

print('')
print('[chk ] 式の検算: 参照 MI %.2f（記録 %.1f）/ 音源 %.4f（記録 %.3f）/ ISPPA %.2f（記録 %.1f）'
      % (mi(g_p), REF['mi_ref'], k, REF['src_mpa'], val, REF['isppa']))
print('       ★ 記録と桁・傾向が合えば式の復元は正しい。数%のズレは統合版と分離版の差（5-1g）。')
print('')
print('=== TUS 安全駆動の再測 完了（読み取りのみ・保存していない）===')
