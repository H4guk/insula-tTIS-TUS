"""TUS の ROI 平均の音圧 [kPa] を、安全駆動（全体 MI = 1.9）で直接出す（読み取り専用）。

目安の 3 W/cm²（Sharif 2025 [3]）は、出典の Lee 2021（Brain Neurorehabil 14:e4・表5）では
**頭蓋なし（incident）** の ISPPA だった。同じ表の **脳内（in situ）** の音圧は 120〜624 kPa。
脳内どうしで比べるため、ROI 平均を ISPPA ではなく音圧で出す（2026-10-28・#20）。
これまでは ISPPA 0.531 W/cm² から ρc を仮定して約 126〜131 kPa と換算しただけだった。

統合版プロジェクト（TUS_250k を実行済み）の中で、全文を貼って実行する。
"""
import numpy as np, h5py
import s4l_v1.document as document

FOCUS_MM, ROI_R_MM = np.array([99.1, 295.0, 1562.2]), 10.0
BRAIN = ('Cerebrum_grey_matter', 'Cerebrum_white_matter', 'Cerebellum', 'Corpus_callosum', 'Pons',
         'Thalamus', 'Medulla_oblongata', 'Hippocampus', 'Midbrain', 'Hypothalamus', 'Pineal_body',
         'Commissura_posterior')
MI_LIMIT, F_MHZ = 1.9, 0.25
INSITU_LO_KPA = 120.0                    # Lee 2021 表5: ヒトの研究の脳内の音圧の下端（Legon・運動野）
LOWER_WCM2 = 3.0                         # これまでの目安（頭蓋なしの ISPPA）


def tissues(s):
    """各ボクセルの組織名と (rho, c)。submission_code_cell.py と同じ読み方。"""
    def uid(row):
        h = bytes(np.asarray(row, dtype=np.uint8).tolist()).hex()
        return '-'.join((h[0:8], h[8:12], h[12:16], h[16:20], h[20:32]))

    def prop(m, t):
        for k in m.keys():
            ci = m[k].get('_ClassInfo') if hasattr(m[k], 'get') else None
            if ci is not None and ci.attrs.get('_TypeName') == t.encode():
                return float(m[k]['_Object'].attrs['Value'])
        return np.nan

    with h5py.File(s.GetInputFileName(), 'r') as f:
        mm = f['AllMaterialMaps'][list(f['AllMaterialMaps'].keys())[0]]
        mesh = [f['Meshes'][k] for k in f['Meshes'] if 'voxels' in f['Meshes'][k]][0]
        vox, ids = mesh['voxels'][...], mesh['id_map'][...]
        n = int(vox.max()) + 1
        name, rho, c = np.full(n, 'Background', dtype=object), np.full(n, np.nan), np.full(n, np.nan)
        for v in range(min(n, ids.shape[0])):
            u = uid(ids[v])
            if u in mm:
                nm = mm[u].attrs.get('material_name', '?')
                name[v] = (nm.decode() if isinstance(nm, bytes) else str(nm)).split('(')[0].strip()
                rho[v], c[v] = prop(mm[u], 'CMassDensity'), prop(mm[u], 'CSoundSpeed')
    return name[vox], rho[vox], c[vox]


s = [x for x in document.AllSimulations if x.Name == 'TUS_250k'][0]
r = s.Results(); r.UpdateAll()
of = r['Overall Field']; of.Update(0)
pf = of['p(x,y,z,f)']; pf.Update(); pf = pf.Data

g = pf.Grid
ax = [np.asarray([float(v) for v in a]) for a in (g.XAxis, g.YAxis, g.ZAxis)]
cc = [0.5 * (a[:-1] + a[1:]) * 1000.0 for a in ax]
vol = np.diff(ax[0])[:, None, None] * np.diff(ax[1])[None, :, None] * np.diff(ax[2])[None, None, :]
roi = ((cc[0][:, None, None] - FOCUS_MM[0]) ** 2 + (cc[1][None, :, None] - FOCUS_MM[1]) ** 2
       + (cc[2][None, None, :] - FOCUS_MM[2]) ** 2) <= ROI_R_MM ** 2

p3 = np.abs(np.asarray(pf.Field(0))).reshape(vol.shape, order='F')     # 参照駆動（音源 1 MPa）の |p| [Pa]
name3, rho3, c3 = tissues(s)
m = roi & np.isin(name3, BRAIN)

mi_ref = float(np.nanmax(p3)) * 1e-6 / np.sqrt(F_MHZ)                   # 全体最大（頭皮の脂肪）で決まる
k = MI_LIMIT / mi_ref
p_kpa = p3 * k * 1e-3
isppa = (p3 * k) ** 2 / (2.0 * rho3 * c3) * 1e-4

w = vol[m] / vol[m].sum()
p_mean = float((p_kpa[m] * w).sum())
p_max = float(p_kpa[m].max())
frac = float(vol[m & (p_kpa >= INSITU_LO_KPA)].sum() / vol[m].sum())
rc_mean = float((rho3[m] * c3[m] * w).sum())

print('scale: reference MI %.1f -> source %.3f MPa' % (mi_ref, k))
print('ROI cells %d, mean rho*c %.3g' % (int(m.sum()), rc_mean))
print('ROI mean |p| %.1f kPa = %.0f%% of %.0f kPa (in situ lower end)' % (p_mean, 100 * p_mean / INSITU_LO_KPA, INSITU_LO_KPA))
print('ROI max  |p| %.1f kPa' % p_max)
print('ROI fraction >= %.0f kPa: %.1f%%' % (INSITU_LO_KPA, 100 * frac))
print('check: ROI mean ISPPA %.3f W/cm2 (expected 0.531) = %.0f%% of %.0f W/cm2 in amplitude'
      % (float((isppa[m] * w).sum()), 100 * np.sqrt(float((isppa[m] * w).sum()) / LOWER_WCM2), LOWER_WCM2))
