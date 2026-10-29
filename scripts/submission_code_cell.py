# The numbers behind the report, from the submitted Sim4Life project (read-only).
# Run inside the project that holds tTIS_LF1, tTIS_LF2 and TUS_250k (already run).
# Full scripts and history: https://github.com/H4guk/insula-tTIS-TUS (scripts/)
#   tTIS: brain_by_name.py, ti_roi_threshold_fraction.py   TUS: brain_by_name.py, tus_roi_pressure.py
import numpy as np, h5py
import s4l_v1.document as document

FOCUS_MM, ROI_R_MM = np.array([99.1, 295.0, 1562.2]), 10.0       # left insula, 10 mm sphere
BRAIN = ('Cerebrum_grey_matter', 'Cerebrum_white_matter', 'Cerebellum', 'Corpus_callosum', 'Pons',
         'Thalamus', 'Medulla_oblongata', 'Hippocampus', 'Midbrain', 'Hypothalamus', 'Pineal_body',
         'Commissura_posterior')                                   # same twelve tissues for both methods
I_MA = (0.891, 1.109)                    # tTIS currents, 2 mA in total (Inoue 2025)
MI_LIMIT, F_MHZ = 1.9, 0.25              # TUS safety limit and frequency
LOWER_VM, LOWER_KPA = 0.2, 120.0         # lowest effective levels: tTIS [1], TUS in situ [3]


def sim(name):
    return [s for s in document.AllSimulations if s.Name == name][0]


def field(s, key):
    r = s.Results(); r.UpdateAll()
    of = r['Overall Field']; of.Update(0)
    f = of[key]; f.Update()
    return f.Data


def grid(g):
    ax = [np.asarray([float(v) for v in a]) for a in (g.XAxis, g.YAxis, g.ZAxis)]
    c = [0.5 * (a[:-1] + a[1:]) * 1000.0 for a in ax]                       # cell centres [mm]
    vol = np.diff(ax[0])[:, None, None] * np.diff(ax[1])[None, :, None] * np.diff(ax[2])[None, None, :]
    roi = ((c[0][:, None, None] - FOCUS_MM[0]) ** 2 + (c[1][None, :, None] - FOCUS_MM[1]) ** 2
           + (c[2][None, None, :] - FOCUS_MM[2]) ** 2) <= ROI_R_MM ** 2
    return vol, roi


def tissues(s):
    """Tissue name and (rho, c) of every voxel, read from the solver input file."""
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


def contiguous(mask, seed):
    """Part of mask connected (6-neighbour) to seed."""
    comp, n = seed & mask, -1
    while int(comp.sum()) != n:
        n = int(comp.sum()); g = comp.copy()
        for a in range(3):
            g |= np.roll(comp, 1, a) | np.roll(comp, -1, a)
        comp = g & mask
    return comp


def compare(label, f3, brain, roi, vol):
    mL = lambda m: float(vol[m].sum()) * 1e6
    mean = lambda m: float((f3[m] * vol[m]).sum() / vol[m].sum())
    target = mean(roi & brain)                                   # target level = ROI volume mean
    ge = brain & (f3 >= target)
    print('%-5s selectivity %.3f | >= target level %.1f mL (%.1fx ROI), %.0f%% contiguous with ROI'
          % (label, mean(brain & ~roi) / target, mL(ge), mL(ge) / mL(roi),
             100 * mL(contiguous(ge, roi)) / mL(ge)))


# ---- tTIS: each pair was run at 1 V; scale each to its current BEFORE combining,
#      because TI = 2*min(|E1|,|E2|) is non-linear (scaling afterwards gives a different field).
E = []
for name, i_ma in zip(('tTIS_LF1', 'tTIS_LF2'), I_MA):
    s = sim(name)
    e, loss = field(s, 'EM E(x,y,z,f0)'), field(s, 'El. Loss Density(x,y,z,f0)')
    vol, roi = grid(e.Grid)
    vol_f = vol.ravel(order='F')
    p = np.real(np.asarray(loss.Field(0)))
    p = p.reshape(p.shape[0], -1)[:, 0]                          # loss density is a scalar
    i_1v = 2.0 * float(np.nansum(p * vol_f))                    # current drawn at 1 V: P = V*I/2
    E.append(np.sqrt((np.abs(np.asarray(e.Field(0))) ** 2).sum(axis=1)) * (i_ma * 1e-3) / i_1v)
ok = np.isfinite(E[0]) & np.isfinite(E[1])
ti = np.where(ok, 2.0 * np.minimum(np.nan_to_num(E[0]), np.nan_to_num(E[1])), -1.0).reshape(vol.shape, order='F')
name3, _, _ = tissues(sim('tTIS_LF1'))
brain = np.isin(name3, BRAIN) & ok.reshape(vol.shape, order='F')
compare('tTIS', ti, brain, roi, vol)
m = roi & brain
ti_mean = float((ti[m] * vol[m]).sum() / vol[m].sum())
print('      ROI mean %.4f V/m = %.0f%% of %.1f V/m; %.1f%% of the ROI above it'
      % (ti_mean, 100 * ti_mean / LOWER_VM, LOWER_VM, 100 * vol[m & (ti >= LOWER_VM)].sum() / vol[m].sum()))

# ---- TUS: |p| at the 1 MPa reference source; scale so that the global MI is 1.9
s = sim('TUS_250k')
pf = field(s, 'p(x,y,z,f)')
vol, roi = grid(pf.Grid)
p3 = np.abs(np.asarray(pf.Field(0))).reshape(vol.shape, order='F')
name3, _, _ = tissues(s)
brain = np.isin(name3, BRAIN)
compare('TUS', p3, brain, roi, vol)
mi_ref = float(np.nanmax(p3)) * 1e-6 / np.sqrt(F_MHZ)           # set by the scalp fat
k = MI_LIMIT / mi_ref
p_kpa = p3 * k * 1e-3                                           # in situ |p| at the safety drive
m = roi & brain
p_mean = float((p_kpa[m] * vol[m]).sum() / vol[m].sum())
print('      reference MI %.1f -> source %.3f MPa; ROI mean %.1f kPa = %.0f%% of %.0f kPa; %.1f%% of the ROI above it'
      % (mi_ref, k, p_mean, 100 * p_mean / LOWER_KPA, LOWER_KPA, 100 * vol[m & (p_kpa >= LOWER_KPA)].sum() / vol[m].sum()))

# Expected: tTIS selectivity 0.358, 35.9 mL (8.6x), 98%; ROI mean 0.2265 V/m = 113%, 74.5% of the ROI
#           TUS  selectivity 0.193,  7.3 mL (1.7x), 88%; MI 12.2 -> 0.156 MPa; 112.6 kPa = 94%, 41.1% of the ROI
