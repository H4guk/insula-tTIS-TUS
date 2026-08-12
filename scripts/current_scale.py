"""項目5（GH #7 Phase 2）1V 駆動時の電流を求めてスケール係数を出す（読み取り専用）。

工程8・9（`run_simulation.py`）で両ペアを Run 済みの前提。**何も書き換えず保存もしない**。

なぜ要るか:
  BC は 1V の Dirichlet で駆動しているので、E 場の絶対値は「1V を掛けたとき」の値でしかない。
  Inoue 2025 の **I₁ = 0.891 mA / I₂ = 1.109 mA** に合わせるには、各ペアの
  **1V 駆動時の電流 I_1V** を知って `s = I_target / I_1V` を掛ける必要がある。

★スケールを飛ばして選択性だけ出すことはできない:
  TI 包絡は `2·min(s₁|E1|, s₂|E2|)` で **min が非線形**なので、s₁/s₂ が変わると分布の形が変わる。
  一様なスケールなら比は不変だが、2ペアで別の係数を掛けるので不変にならない。

必要なものは2段に分かれる:
  (1) **相対スケール** s₁:s₂ ← 電流比 I₁:I₂ ＝ 損失比 P₁:P₂。**係数の規約に依存しない**。
  (2) **絶対値**（mA → V/m・活性化閾値 0.3 V/m の判定）← 損失から電流を出す係数を確定させる必要がある。

係数の規約（振幅 or RMS）の判別方法:
  電力と電流の関係は規約で 2倍変わる（`I = P/V` か `I = 2P/V`）。どちらが正しいかは
  **頭部インピーダンス Z = V/I が tES で妥当な範囲（おおむね 1〜10 kΩ）に入るか**で判別できる
  ——取り違えると2倍ずれるので、境界に近くなければ判定できる。両方が範囲内なら絶対値は保留し、
  相対スケールだけを使って選択性を出す（選択性は絶対値に依存しない）。

出典ノート: Claude/Projects/tTIS-field-simulation.md / docs/phase2-prod.md
"""
import numpy as np
import s4l_v1.document as document

NAMES = ('tTIS_LF1', 'tTIS_LF2')
I_TARGET_MA = (0.891, 1.109)          # Inoue 2025 の群レベル最適値（制約 I₁+I₂ = 2 mA）
DRIVE_V = 1.0                          # 工程6 の Dirichlet 電位差
LOSS_KEY = 'El. Loss Density(x,y,z,f0)'
Z_PLAUSIBLE = (1e3, 1e4)              # Ω。tES の頭部インピーダンスの妥当域


def get_sim(name):
    hit = [s for s in document.AllSimulations if s.Name == name]
    if len(hit) != 1:
        raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (name, len(hit)))
    return hit[0]


def get_field(sim, key):
    """Overall Field から指定キーの場データを取る。無ければ利用可能なキーを出して中断。"""
    res = sim.Results()
    res.UpdateAll()
    of = res['Overall Field']
    of.Update(0)
    keys = list(of.keys())
    if key not in keys:
        print('[err ] %r が無い。利用可能なキー:' % key)
        for k in keys:
            print('       %s' % k)
        raise SystemExit('[err ] LOSS_KEY を上のどれかに書き換える')
    f = of[key]
    f.Update()
    return f.Data


def cell_volumes(fd):
    """各セルの体積 dx*dy*dz を X-fastest の flat で返す（グリッド単位は m）。"""
    g = fd.Grid

    def dax(a):
        v = np.asarray([float(x) for x in a], dtype=float)
        return np.diff(v)

    dx, dy, dz = dax(g.XAxis), dax(g.YAxis), dax(g.ZAxis)
    VX, VY, VZ = np.meshgrid(dx, dy, dz, indexing='ij')      # (nx, ny, nz)
    return (VX * VY * VZ).transpose(2, 1, 0).ravel()         # → flat（X-fastest）


def flat(arr):
    a = np.asarray(arr)
    if a.ndim > 1:
        a = a.reshape(a.shape[0], -1)
        a = a[:, 0] if a.shape[1] == 1 else np.sqrt(np.sum(np.abs(a) ** 2, axis=1))
    return np.real(a).astype(float)


# ===== 各ペアの損失積分 =====
power = {}
for name in NAMES:
    sim = get_sim(name)
    fd = get_field(sim, LOSS_KEY)
    loss = flat(fd.Field(0))            # W/m^3（想定）
    vol = cell_volumes(fd)
    print('[%s] cells: loss=%d vol=%d  unit=%s'
          % (name, loss.size, vol.size, fd.Grid.GetUnit()))
    if loss.size != vol.size:
        raise SystemExit('[err ] セル数が一致しない（グリッド解釈が違う）')

    fin = np.isfinite(loss)
    p = float(np.sum(loss[fin] * vol[fin]))
    power[name] = p
    print('[%s] 有限セル %d / %d  総オーム損失 P = %.6g W'
          % (name, int(fin.sum()), loss.size, p))
    print('[%s] loss density: max=%.4g  p99=%.4g W/m^3'
          % (name, loss[fin].max(), np.percentile(loss[fin], 99)))

p1, p2 = power[NAMES[0]], power[NAMES[1]]

# ===== 規約2通りで電流とインピーダンスを出す =====
print('')
print('--- 1V 駆動時の電流とインピーダンス（規約2通り）---')
print('%-28s %-14s %-14s %-14s' % ('規約', 'I1 [mA]', 'I2 [mA]', 'Z1 / Z2 [kΩ]'))
cands = (('P = ½VI （振幅）  I = 2P/V', 2.0),
         ('P = VI  （実効値）I = P/V ', 1.0))
ok = []
for label, k in cands:
    i1, i2 = k * p1 / DRIVE_V, k * p2 / DRIVE_V          # A
    z1, z2 = DRIVE_V / i1, DRIVE_V / i2                  # Ω
    inside = (Z_PLAUSIBLE[0] <= z1 <= Z_PLAUSIBLE[1] and
              Z_PLAUSIBLE[0] <= z2 <= Z_PLAUSIBLE[1])
    print('%-28s %-14.4g %-14.4g %.3f / %.3f  %s'
          % (label, i1 * 1e3, i2 * 1e3, z1 / 1e3, z2 / 1e3,
             '← 妥当域' if inside else ''))
    if inside:
        ok.append((label, k, i1, i2))

# ===== スケール係数 =====
print('')
print('--- スケール係数 ---')
print('相対スケール（規約に依存しない）: P1/P2 = %.6g  → I1/I2 = %.6g' % (p1 / p2, p1 / p2))
rel = (I_TARGET_MA[0] / I_TARGET_MA[1]) * (p2 / p1)
print('  s1/s2 = (I1_target/I2_target)·(P2/P1) = %.6g' % rel)
print('  ※ TI = 2·min(s1|E1|, s2|E2|) は s1/s2 に依存する（min が非線形）')

for label, k, i1, i2 in ok:
    s1 = (I_TARGET_MA[0] * 1e-3) / i1
    s2 = (I_TARGET_MA[1] * 1e-3) / i2
    print('  [%s] s1 = %.6g  s2 = %.6g  (s1/s2 = %.6g)' % (label, s1, s2, s1 / s2))

if not ok:
    print('  ※どちらの規約も %.0f〜%.0f Ω に入らないが、これは判定基準が不適切だったため。' % Z_PLAUSIBLE)
    print('    実測の tES インピーダンス（1〜10 kΩ）は**電極–ゲル–皮膚の接触インピーダンス**が')
    print('    大半を占めるが、本モデルは PEC 円板を皮膚に埋め込んでおり接触抵抗ゼロ・')
    print('    skin も LF の 0.1483 S/m（乾燥角質層を持たない）＝**体積伝導だけの抵抗**なので、')
    print('    数百 Ω は妥当。→ 規約は下の面積分で直接決める。')
elif len(ok) > 1:
    print('  ★両方の規約が妥当域に入った。絶対値は下の面積分で決める。')

# ===== 電流を J の面積分で直接求める（規約の仮定を要しない）=====
# 電極間を分断する平面を通る J·n の総和は、定義上そのまま電極電流。
# 電流連続性から**面をどこに置いても同じ値**になるはずなので、3枚で測って一致を確認する
# ＝グリッド解釈（X-fastest の reshape）の検算も同時に行える。
print('')
print('--- 電流の直接測定（J の面積分）---')
J_KEY = 'J(x,y,z,f0)'
# (sim, 法線軸, 分断面の位置[mm]) — 電極の実座標の間に取る
#   ペア1: T7 X=94.8 / P7 X=41.7 → X で分断
#   ペア2: Fp1 Y=286.8 / Fp2 Y=235.5 → Y で分断
PLANES = {NAMES[0]: ('x', (55.0, 68.0, 82.0)),
          NAMES[1]: ('y', (250.0, 260.0, 270.0))}

current = {}
for name in NAMES:
    sim = get_sim(name)
    res = sim.Results()
    res.UpdateAll()
    of = res['Overall Field']
    of.Update(0)
    keys = list(of.keys())
    if J_KEY not in keys:
        print('[%s] %r が無い。利用可能なキー: %s' % (name, J_KEY, keys))
        raise SystemExit('[err ] J_KEY を上のどれかに書き換える')
    jf = of[J_KEY]
    jf.Update()
    fd = jf.Data

    g = fd.Grid

    def axis(a):
        return np.asarray([float(v) for v in a], dtype=float)

    xa, ya, za = axis(g.XAxis), axis(g.YAxis), axis(g.ZAxis)
    nx, ny, nz = xa.size - 1, ya.size - 1, za.size - 1
    xc, yc, zc = 0.5 * (xa[:-1] + xa[1:]), 0.5 * (ya[:-1] + ya[1:]), 0.5 * (za[:-1] + za[1:])
    dx, dy, dz = np.diff(xa), np.diff(ya), np.diff(za)

    arr = np.asarray(fd.Field(0))
    if arr.shape[0] != nx * ny * nz:
        raise SystemExit('[err ] J のセル数 %d がグリッド %d と合わない' % (arr.shape[0], nx * ny * nz))
    # flat = x + nx*(y + ny*z) → (nz, ny, nx, 3)
    J = arr.reshape(nz, ny, nx, 3)
    J = np.where(np.isfinite(J), J, 0.0)          # 空気（NaN）は電流なし

    ax, positions = PLANES[name]
    vals = []
    for pos_mm in positions:
        p = pos_mm / 1000.0                        # グリッドは m
        if ax == 'x':
            i = int(np.argmin(np.abs(xc - p)))
            w = np.outer(dz, dy)                   # (nz, ny)
            flux = np.sum(J[:, :, i, 0] * w)
        else:
            i = int(np.argmin(np.abs(yc - p)))
            w = np.outer(dz, dx)                   # (nz, nx)
            flux = np.sum(J[:, i, :, 1] * w)
        vals.append(complex(flux))
        print('[%s] %s=%.1fmm (idx %d): I = %.6g mA  (実部 %.6g / 虚部 %.3g)'
              % (name, ax.upper(), pos_mm, i, abs(flux) * 1e3,
                 flux.real * 1e3, flux.imag * 1e3))

    mags = np.array([abs(v) for v in vals])
    spread = (mags.max() - mags.min()) / max(1e-30, mags.mean())
    i_mean = float(mags.mean())
    current[name] = i_mean
    print('[%s] 3面の平均 I = %.6g mA  ばらつき %.2f %%  → %s'
          % (name, i_mean * 1e3, spread * 100.0,
             'OK（面に依存しない＝連続性を満たす）' if spread < 0.05 else '★ばらつきが大きい'))

# ===== 規約の確定とスケール係数 =====
print('')
print('--- 面積分から決めたスケール係数 ---')
for name, i_v, p_v, tgt in zip(NAMES, [current[n] for n in NAMES],
                               [power[n] for n in NAMES], I_TARGET_MA):
    ratio = p_v / (DRIVE_V * i_v)
    s = (tgt * 1e-3) / i_v
    print('[%s] I_1V = %.6g mA  Z = %.1f Ω  P/(V·I) = %.4f  → s = %.6g（%.3f mA に合わせる）'
          % (name, i_v * 1e3, DRIVE_V / i_v, ratio, s, tgt))
print('  ※ P/(V·I) が 0.5 なら損失密度は σ|E|²/2（振幅規約）・1.0 なら σ|E|²')
s_ratio = ((I_TARGET_MA[0] * 1e-3) / current[NAMES[0]]) / \
          ((I_TARGET_MA[1] * 1e-3) / current[NAMES[1]])
print('  s1/s2 = %.6g（損失比から出した %.6g と一致するはず）' % (s_ratio, rel))


# ===== 面積分のプロファイル（2026-08-12 追加）=====
# 3面で 20〜24% ばらつき、しかも**単調増加**した（T7 に近い面ほど大きい）。
# `P/(V·I)` もペア間で一致しない（0.726 vs 0.776）＝**面積分側の系統誤差**。
# 仮説の判別:
#   (A) 接地された外側境界（BC 一覧の 'Boundary Settings': 0.0）へ電流が漏れている
#       → **電極対を分断しない面でもゼロでない流束**が出る。勾配は連続的。
#   (B) セル中心 J を面に補間した離散化誤差
#       → 対の外側は**ほぼゼロ**、内側の中央は平坦で、電極の直近だけ跳ねる。
print('')
print('--- 面積分のプロファイル（対の外側も含めてスキャン）---')
# (法線軸, 開始, 終了, 刻み[mm], 電極位置[mm])
SCAN = {NAMES[0]: ('x', 10.0, 140.0, 10.0, {'P7': 41.7, 'T7': 94.8}),
        NAMES[1]: ('y', 200.0, 330.0, 10.0, {'Fp2': 235.5, 'Fp1': 286.8})}

for name in NAMES:
    sim = get_sim(name)
    res = sim.Results()
    res.UpdateAll()
    of = res['Overall Field']
    of.Update(0)
    jf = of[J_KEY]
    jf.Update()
    fd = jf.Data
    g = fd.Grid
    xa = np.asarray([float(v) for v in g.XAxis], dtype=float)
    ya = np.asarray([float(v) for v in g.YAxis], dtype=float)
    za = np.asarray([float(v) for v in g.ZAxis], dtype=float)
    nx, ny, nz = xa.size - 1, ya.size - 1, za.size - 1
    xc, yc = 0.5 * (xa[:-1] + xa[1:]), 0.5 * (ya[:-1] + ya[1:])
    dx, dy, dz = np.diff(xa), np.diff(ya), np.diff(za)
    J = np.asarray(fd.Field(0)).reshape(nz, ny, nx, 3)
    J = np.where(np.isfinite(J), J, 0.0)

    ax, lo, hi, step, elec = SCAN[name]
    print('[%s] 電極位置: %s' % (name, ', '.join('%s=%.1f' % kv for kv in sorted(elec.items(),
                                                                              key=lambda t: t[1]))))
    print('[%s] %-8s %-14s %s' % (name, ax.upper() + ' [mm]', 'I [mA]', '対を分断するか'))
    inner = sorted(elec.values())
    for pos_mm in np.arange(lo, hi + 1e-9, step):
        p = pos_mm / 1000.0
        if ax == 'x':
            i = int(np.argmin(np.abs(xc - p)))
            flux = np.sum(J[:, :, i, 0] * np.outer(dz, dy))
        else:
            i = int(np.argmin(np.abs(yc - p)))
            flux = np.sum(J[:, i, :, 1] * np.outer(dz, dx))
        sep = inner[0] < pos_mm < inner[1]
        print('[%s] %-8.1f %-14.6g %s' % (name, pos_mm, abs(complex(flux)) * 1e3,
                                         '分断' if sep else '—（外側）'))

print('')
print('  判定: 外側でもゼロでない流束が出るなら (A) 境界への漏れ。')
print('        外側がほぼゼロで内側の中央が平坦なら (B) 離散化誤差 → 中央付近の値を採用する。')

print('')
print('=== 項目5 完了（読み取りのみ・保存していない）===')
