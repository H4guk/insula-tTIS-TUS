"""項目6（GH #7 Phase 2）TI 包絡 → 島皮質 ROI 定量 → 選択性（読み取り専用）。

工程8・9 で両ペアを Run 済みの前提。**何も書き換えず保存もしない**。

TI = `2·min(s₁|E1|, s₂|E2|)`（Grossman の等方近似）。
選択性 = **非標的領域の平均 EFE / 標的（ROI）の平均 EFE**（小さいほど良い）→ Inoue 2025 の **≈0.40** と照合。

--- 2026-08-12 に確定した前提（すべて実測で裏を取ってある）---

**① 電流スケール（項目5）**
  BC は 1V 駆動なので、Inoue の I₁=0.891 / I₂=1.109 mA に合わせる係数が要る。
  `El. Loss Density` を体積積分した P から `I = 2P/V` で求める。
  係数 2 は**σ を逆算して既知値と照合して確定**した——`σ = 2·loss/|E|²` が
  既知の σ（白質 0.3480・灰白質 0.4191・Skin 0.1483・皮質骨 0.006447・CSF 1.8790）を
  有効セルの 61.1% で再現し、`σ = loss/|E|²` は 12.1% しか再現しなかった。
  ＝ `loss = σ|E|²/2` → `P = ½VI`。実測 I₁=4.334 mA / I₂=3.344 mA → s₁=0.2056 / s₂=0.3316。
  ★**スケールを省略できない**: TI は `2·min(s₁|E1|, s₂|E2|)` で **min が非線形**なので、
    s₁/s₂ が変われば分布の形が変わる（一様なスケールなら選択性は不変だが、
    2ペアで別の係数を掛けるので不変にならない）。

**② 並び順**
  flat = x + nx*(y + ny*z)（**X-fastest** ＝ `reshape(nz, ny, nx)`）を prod グリッドで検証済み。
  `GetCellCenter` の進み方と、`|E|` 最大セルが駆動電極の縁（T7 から 11.3mm / Fp1 から 7.2mm）に
  来ることの両方で確認した。

**③ 非標的領域は「脳組織のうち ROI 外」**
  旧実装は `~roi`（ROI 外の**全セル**）で、**空気（NaN）も体も含む**ため平均が NaN になり、
  Inoue の定義（皮質表面頂点）ともかけ離れていた。σ マップから脳を切り出す:
  `σ ∈ [0.33, 0.44]` ＝ 白質 0.348 ＋ 灰白質 0.4191 で **945 mL**（Yoon-sun は小柄な26歳女性・
  大脳の GM+WM のみなので妥当）。定義の違いで選択性は動くので**複数の定義で出して併記する**。

**④ グリッドは非一様（graded）**
  体 5mm ＋ 頭部 1mm なので、ROI 内平均は**セル体積で重み付け**しないと歪む。

出典ノート: Claude/DailyLogs/2026-08-12.md / docs/phase2-prod.md
"""
import numpy as np
import s4l_v1.document as document

NAMES = ('tTIS_LF1', 'tTIS_LF2')       # ペア1 = T7–P7 / ペア2 = Fp1–Fp2
I_TARGET_MA = (0.891, 1.109)           # Inoue 2025 の群レベル最適値
DRIVE_V = 1.0
LOSS_TO_I = 2.0                        # I = LOSS_TO_I · P / V（2026-08-12 に σ 照合で確定）

ROI_CENTER_MM = (99.1, 295.0, 1562.2)  # 左島皮質（工程3・深さ 40.0mm を 2026-08-11 に確認）
ROI_RADIUS_MM = 10.0

E_KEY = 'EM E(x,y,z,f0)'
LOSS_KEY = 'El. Loss Density(x,y,z,f0)'

ACTIVATION_VM = 0.3                    # 活性化閾値（有効範囲 0.2–0.5 V/m の中点・Inoue 2025）
BRAIN_BAND = (0.33, 0.44)              # σ [S/m]: 白質 0.348 ＋ 灰白質 0.4191
GM_BAND = (0.407, 0.432)               # 灰白質のみ（0.4191 ± 3%）
REF_SELECTIVITY = 0.40                 # Inoue 2025 Montage I


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


def wmean(f, m, vol):
    v = vol[m]
    return float((f[m] * v).sum() / v.sum()) if v.sum() > 0 else float('nan')


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
        loss0, mag0 = scalar(lfd.Field(0)), emag(efd.Field(0))

    mag = emag(efd.Field(0))
    loss = scalar(lfd.Field(0))
    fin = np.isfinite(loss)
    p = float(np.sum(loss[fin] * vol[fin]))
    i_1v = LOSS_TO_I * p / DRIVE_V
    s = (tgt * 1e-3) / i_1v
    mags.append(mag)
    scales.append(s)
    print('[%s] P=%.6g W  I_1V=%.4f mA  → s=%.6g（%.3f mA に合わせる）'
          % (name, p, i_1v * 1e3, s, tgt))
print('[scale] s1/s2 = %.6g' % (scales[0] / scales[1]))

# ===== ② TI 包絡 =====
e1 = scales[0] * mags[0]
e2 = scales[1] * mags[1]
material = np.isfinite(e1) & np.isfinite(e2)
ti = np.where(material, 2.0 * np.minimum(np.nan_to_num(e1), np.nan_to_num(e2)), np.nan)
print('[ti  ] 材料セル %d / %d  TI: max=%.4g  p50=%.4g  p99=%.4g V/m'
      % (int(material.sum()), material.size, np.nanmax(ti),
         np.nanpercentile(ti[material], 50), np.nanpercentile(ti[material], 99)))
print('[ti  ] スケール後の |E|: ペア1 max=%.4g / ペア2 max=%.4g V/m'
      % (np.nanmax(e1), np.nanmax(e2)))

# ===== ③ σ マップと領域マスク =====
sigma = np.full(mag0.shape, np.nan)
ok = np.isfinite(mag0) & np.isfinite(loss0) & (mag0 > 0)
sigma[ok] = 2.0 * loss0[ok] / (mag0[ok] ** 2)

roi = sphere_mask(fd0, ROI_CENTER_MM, ROI_RADIUS_MM) & material
brain = np.isfinite(sigma) & (sigma >= BRAIN_BAND[0]) & (sigma <= BRAIN_BAND[1]) & material
gm = np.isfinite(sigma) & (sigma >= GM_BAND[0]) & (sigma <= GM_BAND[1]) & material

print('')
print('[mask] ROI          セル %-8d 体積 %8.3f mL（球の理論値 %.3f mL）'
      % (int(roi.sum()), float(vol[roi].sum()) * 1e6,
         4.0 / 3.0 * np.pi * (ROI_RADIUS_MM / 10.0) ** 3))
print('[mask] 脳(WM+GM)    セル %-8d 体積 %8.1f mL' % (int(brain.sum()), float(vol[brain].sum()) * 1e6))
print('[mask] 灰白質のみ    セル %-8d 体積 %8.1f mL' % (int(gm.sum()), float(vol[gm].sum()) * 1e6))
print('[mask] 材料全体      セル %-8d 体積 %8.1f mL'
      % (int(material.sum()), float(vol[material].sum()) * 1e6))
roi_sigma = sigma[roi]
roi_sigma = roi_sigma[np.isfinite(roi_sigma)]
if roi_sigma.size:
    print('[mask] ROI 内の σ: 中央値 %.4f（白質 0.3480 ならモデル上 WM ラベル）' % np.median(roi_sigma))

# ===== ④ ROI 定量と選択性 =====
ti_roi = wmean(ti, roi, vol)
print('')
print('--- 標的（ROI）---')
print('  TI 体積重み平均 = %.4f V/m   最大 = %.4f V/m' % (ti_roi, float(np.nanmax(ti[roi]))))
print('  ペア1 |E| 平均 = %.4f / ペア2 |E| 平均 = %.4f V/m'
      % (wmean(e1, roi, vol), wmean(e2, roi, vol)))
print('  閾値 %.1f V/m 超の ROI 体積割合 = %.1f %%'
      % (ACTIVATION_VM,
         100.0 * float(vol[roi & (ti > ACTIVATION_VM)].sum()) / float(vol[roi].sum())))

print('')
print('--- 選択性（非標的平均 / 標的平均・小さいほど良い）---')
print('  %-28s %-14s %-14s %s' % ('非標的の定義', '非標的平均', '選択性', '≈%.2f との比' % REF_SELECTIVITY))
for label, m in (('脳(WM+GM) − ROI', brain & ~roi),
                 ('灰白質のみ − ROI', gm & ~roi),
                 ('材料全体 − ROI（頭+体）', material & ~roi)):
    nt = wmean(ti, m, vol)
    sel = nt / ti_roi
    print('  %-28s %-14.4f %-14.4f %.2f×' % (label, nt, sel, sel / REF_SELECTIVITY))

print('')
print('  ※ Inoue 2025 の非標的は皮質表面頂点（FreeSurfer）で、我々は球 ROI ＋ σ による組織帯。')
print('     頭部モデル・ソルバー・電極モデルも異なるため**完全一致は求めず桁と傾向で照合**する。')
print('')
print('=== 項目6 完了（読み取りのみ・保存していない）===')
