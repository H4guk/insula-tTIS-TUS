# TUS の安全駆動を ITRUSST の MItc（軟部組織の in situ の最大負圧。頭蓋骨は除く）で決め直す（Sim4Life.lite・読み取りのみ）。#25
# ITRUSST consensus on biophysical safety（PMC12632700）: MItc は "peak-rarefactional pressure in soft tissues, such as the scalp
# and brain ... but exclude the skull"。tus_safety_drive.py・submission_code_cell.py は骨も含めた全体の最大で k を決めていた。
# 開口 40 mm までは最大が皮下脂肪（軟部組織）だったので同じだったが、開口 64 mm では最大が骨（c 2117・ρ 1178）になった。
# 骨 = material_name が "/Bones)" で終わる組織（Yoon-sun の Bones グループ）。水（背景）と Transducer も除く。
import numpy as np, h5py
import s4l_v1.document as document

FOCUS_MM, ROI_R_MM = np.array([99.1, 295.0, 1562.2]), 10.0
BRAIN = ('Cerebrum_grey_matter', 'Cerebrum_white_matter', 'Cerebellum', 'Corpus_callosum', 'Pons',
         'Thalamus', 'Medulla_oblongata', 'Hippocampus', 'Midbrain', 'Hypothalamus', 'Pineal_body',
         'Commissura_posterior')
MI_LIMIT, F_MHZ, LOWER_KPA = 1.9, 0.25, 120.0


def sim(name):
    return [s for s in document.AllSimulations if s.Name == name][0]


def field(s, key):
    r = s.Results(); r.UpdateAll()
    of = r['Overall Field']; of.Update(0)
    f = of[key]; f.Update()
    return f.Data


def grid(g):
    ax = [np.asarray([float(v) for v in a]) for a in (g.XAxis, g.YAxis, g.ZAxis)]
    c = [0.5 * (a[:-1] + a[1:]) * 1000.0 for a in ax]
    vol = np.diff(ax[0])[:, None, None] * np.diff(ax[1])[None, :, None] * np.diff(ax[2])[None, None, :]
    roi = ((c[0][:, None, None] - FOCUS_MM[0]) ** 2 + (c[1][None, :, None] - FOCUS_MM[1]) ** 2
           + (c[2][None, None, :] - FOCUS_MM[2]) ** 2) <= ROI_R_MM ** 2
    return c, vol, roi


def raw_names(s):
    def uid(row):
        h = bytes(np.asarray(row, dtype=np.uint8).tolist()).hex()
        return '-'.join((h[0:8], h[8:12], h[12:16], h[16:20], h[20:32]))
    with h5py.File(s.GetInputFileName(), 'r') as f:
        mm = f['AllMaterialMaps'][list(f['AllMaterialMaps'].keys())[0]]
        mesh = [f['Meshes'][k] for k in f['Meshes'] if 'voxels' in f['Meshes'][k]][0]
        vox, ids = mesh['voxels'][...], mesh['id_map'][...]
        n = int(vox.max()) + 1
        name = np.full(n, 'Background', dtype=object)
        for v in range(min(n, ids.shape[0])):
            u = uid(ids[v])
            if u in mm:
                nm = mm[u].attrs.get('material_name', '?')
                name[v] = nm.decode() if isinstance(nm, bytes) else str(nm)
    return name[vox]


s = sim('TUS_250k')
pf = field(s, 'p(x,y,z,f)')
c, vol, roi = grid(pf.Grid)
p3 = np.abs(np.asarray(pf.Field(0))).reshape(vol.shape, order='F')
raw = raw_names(s)
short = np.vectorize(lambda n: n.split('(')[0].strip())(raw)
bone = np.vectorize(lambda n: n.rstrip().endswith('/Bones)'))(raw)
other = np.isin(short, ('Background', 'Transducer'))
soft = ~bone & ~other
brain = np.isin(short, BRAIN)


def peak(mask, label):
    q = np.where(mask, p3, -1.0)
    j = np.unravel_index(int(np.argmax(q)), q.shape)
    pm = float(p3[j])
    print('[max ] %-14s %.3f MPa（参照 1 MPa）MI %.2f @ (%.1f, %.1f, %.1f) %s'
          % (label, pm * 1e-6, pm * 1e-6 / np.sqrt(F_MHZ), c[0][j[0]], c[1][j[1]], c[2][j[2]], short[j]))
    return pm


print('[grid] %s  骨のセル %d・軟部組織のセル %d' % (str(p3.shape), int(bone.sum()), int(soft.sum())))
p_all = peak(soft | bone, '全組織（今まで）')
p_bone = peak(bone, '骨だけ')
p_soft = peak(soft, '軟部組織（MItc）')
p_brain = peak(brain, '脳だけ')

# 軟部組織の上位（どこが律速か）
q = np.where(soft, p3, -1.0).ravel()
top = np.argsort(-q)[:5]
print('[top ] 軟部組織の上位 5 セル:')
for t in top:
    j = np.unravel_index(int(t), p3.shape)
    print('       %.3f MPa  %-24s (%.1f, %.1f, %.1f)' % (p3[j] * 1e-6, short[j], c[0][j[0]], c[1][j[1]], c[2][j[2]]))

m = roi & brain
print('')
print('  決め方              MI(参照)  音源[MPa]  ROI 平均[kPa]  120 kPa の  超える割合')
for label, pm in (('全組織（今まで）', p_all), ('軟部組織（MItc）', p_soft)):
    k = MI_LIMIT / (pm * 1e-6 / np.sqrt(F_MHZ))
    pk = p3 * k * 1e-3
    mean = float((pk[m] * vol[m]).sum() / vol[m].sum())
    frac = 100 * float(vol[m & (pk >= LOWER_KPA)].sum() / vol[m].sum())
    print('  %-18s %7.2f  %8.4f  %12.1f  %8.0f %%  %8.1f %%'
          % (label, pm * 1e-6 / np.sqrt(F_MHZ), k, mean, 100 * mean / LOWER_KPA, frac))
print('=== MItc（軟部組織）での安全駆動 完了（読み取りのみ・保存していない）===')
