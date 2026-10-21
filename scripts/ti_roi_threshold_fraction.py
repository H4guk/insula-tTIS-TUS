"""GH #19 深部到達②: TI が目安を超える ROI 体積の割合を、目安 3 通りで出す（読み取り専用）。

tTIS_LF1 / tTIS_LF2 を Run 済みのプロジェクト（Phase 2 の tTIS 単独版・統合版のどちらでもよい）で実行する。
**何も書き換えず保存もしない**。

#19 で深部到達の目安を「両手法とも文献の有効範囲の下端」にそろえた:
  tTIS 0.2 V/m（0.2〜0.5 の下端）／ TUS 3 W/cm²（3〜30 の下端・Sharif 2025）。
TUS 側は以前から下端（0.0%）なので出し直し不要。tTIS 側だけ 0.3 V/m（Inoue 2025）で出していたので測り直す。

出すもの（ROI＝球 r=10mm ∩ 材料セル・セル体積で重み付け）:
  - 0.2 V/m（下端・主）／ 0.3 V/m（Inoue 2025・照合用）／ 0.35 V/m（算術中点・幅）を超える割合
  - 検算: ROI 平均 ≈0.2265 V/m・最大 ≈0.3259 V/m・0.3 V/m 超 ≈1.5%（phase2-prod.md）が再現すれば場は同じ

TI と電流スケールの作り方は `ti_analysis.py` と同じ（LOSS_TO_I=2・X-fastest・セル体積重み）。
"""
import numpy as np
import s4l_v1.document as document

NAMES = ('tTIS_LF1', 'tTIS_LF2')       # ペア1 = T7–P7 / ペア2 = Fp1–Fp2
I_TARGET_MA = (0.891, 1.109)           # Inoue 2025 の群レベル最適値
DRIVE_V = 1.0
LOSS_TO_I = 2.0

ROI_CENTER_MM = (99.1, 295.0, 1562.2)
ROI_RADIUS_MM = 10.0

E_KEY = 'EM E(x,y,z,f0)'
LOSS_KEY = 'El. Loss Density(x,y,z,f0)'

THRESHOLDS_VM = (
    (0.2, '下端（#19 の主）'),
    (0.3, 'Inoue 2025（照合用）'),
    (0.35, '算術中点（幅）'),
)
EXPECT = {'mean': 0.2265, 'max': 0.3259, 'frac_0.3': 1.5}


def get_sim(name):
    hit = [s for s in document.AllSimulations if s.Name == name]
    if len(hit) != 1:
        raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (name, len(hit)))
    return hit[0]


def field(sim, key):
    res = sim.Results()
    res.UpdateAll()
    of = res['Overall Field']
    of.Update(0)
    if key not in list(of.keys()):
        print('[err ] %r が無い。利用可能なキー: %s' % (key, list(of.keys())))
        raise SystemExit(1)
    f = of[key]
    f.Update()
    return f.Data


def scalar(a):
    a = np.asarray(a)
    if a.ndim > 1:
        a = a.reshape(a.shape[0], -1)[:, 0]
    return np.real(a).astype(float)


def emag(a):
    return np.sqrt(np.sum(np.abs(np.asarray(a)) ** 2, axis=1))


def axes_of(fd):
    g = fd.Grid
    return [np.asarray([float(v) for v in ax], dtype=float)
            for ax in (g.XAxis, g.YAxis, g.ZAxis)]


def cell_volumes(fd):
    """セル体積を X-fastest flat で返す（グリッド単位 m）。"""
    xa, ya, za = axes_of(fd)
    VX, VY, VZ = np.meshgrid(np.diff(xa), np.diff(ya), np.diff(za), indexing='ij')
    return (VX * VY * VZ).transpose(2, 1, 0).ravel()


def sphere_mask(fd, center_mm, radius_mm):
    """mm 指定の球 ROI を X-fastest flat のブール配列で返す。"""
    xa, ya, za = axes_of(fd)
    xc, yc, zc = (0.5 * (a[:-1] + a[1:]) for a in (xa, ya, za))
    cx, cy, cz = (c / 1000.0 for c in center_mm)
    r = radius_mm / 1000.0
    X, Y, Z = np.meshgrid(xc, yc, zc, indexing='ij')
    d2 = (X - cx) ** 2 + (Y - cy) ** 2 + (Z - cz) ** 2
    return (d2 <= r ** 2).transpose(2, 1, 0).ravel()


# ===== ① 場の読み込みとスケール係数 =====
mags, scales = [], []
fd0 = None
for name, tgt in zip(NAMES, I_TARGET_MA):
    sim = get_sim(name)
    efd = field(sim, E_KEY)
    lfd = field(sim, LOSS_KEY)
    if fd0 is None:
        fd0 = efd
        vol = cell_volumes(efd)
    loss = scalar(lfd.Field(0))
    fin = np.isfinite(loss)
    p = float(np.sum(loss[fin] * vol[fin]))
    s = (tgt * 1e-3) / (LOSS_TO_I * p / DRIVE_V)
    mags.append(emag(efd.Field(0)))
    scales.append(s)
    print('[%s] s=%.6g（%.3f mA に合わせる）' % (name, s, tgt))

# ===== ② TI 包絡と ROI =====
e1 = scales[0] * mags[0]
e2 = scales[1] * mags[1]
material = np.isfinite(e1) & np.isfinite(e2)
ti = np.where(material, 2.0 * np.minimum(np.nan_to_num(e1), np.nan_to_num(e2)), np.nan)
roi = sphere_mask(fd0, ROI_CENTER_MM, ROI_RADIUS_MM) & material
v_roi = float(vol[roi].sum())

mean = float((ti[roi] * vol[roi]).sum() / v_roi)
mx = float(np.nanmax(ti[roi]))
print('')
print('[roi ] セル %d  体積 %.3f mL' % (int(roi.sum()), v_roi * 1e6))
print('[roi ] TI 平均 = %.4f V/m（期待 %.4f）  最大 = %.4f V/m（期待 %.4f）'
      % (mean, EXPECT['mean'], mx, EXPECT['max']))

# ===== ③ 目安を超える ROI 体積の割合 =====
print('')
print('--- TI が目安を超える ROI 体積の割合 ---')
frac = {}
for th, label in THRESHOLDS_VM:
    m = roi & (ti > th)
    frac[th] = 100.0 * float(vol[m].sum()) / v_roi
    print('  %.2f V/m  %-22s %6.1f %%（%d セル）  平均/目安 = %.1f %%'
          % (th, label, frac[th], int(m.sum()), 100.0 * mean / th))

# ===== ④ 検算 =====
ok = (abs(mean - EXPECT['mean']) < 0.002 and abs(mx - EXPECT['max']) < 0.002
      and abs(frac[0.3] - EXPECT['frac_0.3']) < 0.2)
print('')
print('[check] %s — 平均・最大・0.3 V/m 超の割合が phase2-prod.md の値と%s'
      % ('PASS' if ok else 'FAILED', '一致' if ok else '食い違う（場かスケールが違う）'))
print('=== #19 深部到達② 完了（読み取りのみ・保存していない）===')
