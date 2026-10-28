"""σ マップを逆算して規約を確定し、組織マスクを得る（読み取り専用）。

2つの目的を1回で果たす。

**目的1: 損失密度の規約を確定する（項目5 の残件）**
  `El. Loss Density` と `|E|` から σ を逆算できる。規約は2通り:
      loss = σ|E|²/2  →  σ = 2·loss/|E|²
      loss = σ|E|²    →  σ =   loss/|E|²
  **σ の真値は監査で全部分かっている**（白質 0.3480 / 灰白質 0.4191 / Skin 0.1483 /
  皮質骨 0.006447 / CSF 1.8790 …）ので、**どちらの式が既知の値を再現するかで規約が決まる**。
  推定ではなく照合。規約が決まれば `I = kP/V` の k も決まり、電流の絶対値が出せる。

**目的2: 組織マスクを得る（項目6 の前提）**
  現在の `ti_analysis.py` は非標的領域を `~roi`（ROI 外の全セル）としており、
  **空気（NaN）も体も含む**ので平均が NaN になる。σ マップがあれば
  「脳組織のうち ROI 外」を正しく切り出せる。
  ※ Yoon-sun は島皮質を独立組織として持たないので ROI は球のままだが、
    **非標的領域の定義は選択性の値を直接動かす**ので、ここは厳密にやる必要がある。

副産物: σ の頻出値が既知の材料と一致すれば、**材料の割り当てが場に正しく反映されている**
ことの独立な確認になる（工程5 のゲートは設定値を見ているだけで、場は見ていない）。

出典ノート: Claude/Projects/tTIS-field-simulation.md「Step 0 ②は空振り＋代替を発見」（2026-07-20）
"""
import numpy as np
import s4l_v1.document as document

SIM_NAME = 'tTIS_LF1'                  # σ は両ペア共通なので片方でよい
E_KEY = 'EM E(x,y,z,f0)'
LOSS_KEY = 'El. Loss Density(x,y,z,f0)'

# 監査（2026-08-11）で確定した IT'IS LF 5.0 の σ [S/m]
KNOWN = {'Skull (Cortical)': 0.006447, 'Nerve/Spinal cord': 0.029893,
         'Fat / SAT': 0.042269, 'Skull (Cancellous) ': 0.099750,
         'Skin': 0.148297, 'Cartilage/Larynx': 0.174946,
         'Brain (White Matter)': 0.347954, 'Tendon': 0.384652,
         'Brain (Grey Matter)': 0.419055, 'Muscle/Mucosa': 0.461008,
         'Dura': 0.500917, 'Blood': 0.700002, 'Cerebrospinal Fluid': 1.878999}
TOL = 0.03                             # 相対許容差（3%）で「一致」とみなす


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


sim = get_sim(SIM_NAME)
efd = field(sim, E_KEY)
lfd = field(sim, LOSS_KEY)

e = np.asarray(efd.Field(0))
mag2 = np.sum(np.abs(e) ** 2, axis=1)                  # |E|^2
loss = np.asarray(lfd.Field(0))
if loss.ndim > 1:
    loss = loss.reshape(loss.shape[0], -1)[:, 0]
loss = np.real(loss).astype(float)

good = np.isfinite(mag2) & np.isfinite(loss) & (mag2 > 0)
print('[pre ] 有効セル %d / %d' % (int(good.sum()), mag2.size))

g = efd.Grid
dx = np.diff(np.asarray([float(v) for v in g.XAxis], dtype=float))
dy = np.diff(np.asarray([float(v) for v in g.YAxis], dtype=float))
dz = np.diff(np.asarray([float(v) for v in g.ZAxis], dtype=float))
VX, VY, VZ = np.meshgrid(dx, dy, dz, indexing='ij')
vol = (VX * VY * VZ).transpose(2, 1, 0).ravel()        # X-fastest（2026-08-12 検証済み）

# ===== 規約2通りで σ を逆算し、既知の値との一致数を数える =====
print('')
print('--- 規約の照合（既知の σ を再現するのはどちらか）---')
best = None
for label, k in (('σ = 2·loss/|E|²  （loss = σ|E|²/2）', 2.0),
                 ('σ =   loss/|E|²  （loss = σ|E|²）', 1.0)):
    sig = np.full(mag2.shape, np.nan)
    sig[good] = k * loss[good] / mag2[good]
    hit_total = 0
    detail = []
    for nm, val in sorted(KNOWN.items(), key=lambda t: t[1]):
        n = int(np.sum(np.abs(sig - val) <= val * TOL))
        hit_total += n
        if n:
            detail.append('%s:%d' % (nm.split()[0], n))
    frac = 100.0 * hit_total / max(1, int(good.sum()))
    print('  %s → 既知値に一致 %d セル（有効セルの %.1f %%）' % (label, hit_total, frac))
    print('     内訳: %s' % (', '.join(detail) if detail else 'なし'))
    if best is None or hit_total > best[2]:
        best = (label, k, hit_total, sig)

label, k_best, _, sigma = best
print('  → 採用: %s' % label)
print('     ＝ P と I の関係は %s' % ('P = ½VI（振幅規約）→ I = 2P/V' if k_best == 2.0
                                     else 'P = VI → I = P/V'))

# ===== σ の頻出値（材料の棚卸し）=====
print('')
print('--- σ の頻出値（体積の大きい順・材料の割り当てが場に反映されているかの確認）---')
s = sigma[np.isfinite(sigma)]
v = vol[np.isfinite(sigma)]
r = np.round(s, 4)
uniq, inv = np.unique(r, return_inverse=True)
vsum = np.bincount(inv, weights=v)
csum = np.bincount(inv)
order = np.argsort(-vsum)[:20]
print('  %-12s %-12s %-14s %s' % ('σ [S/m]', 'セル数', '体積 [mL]', '一致する材料'))
for i in order:
    val = uniq[i]
    name = '—'
    for nm, kv in KNOWN.items():
        if abs(val - kv) <= max(1e-4, kv * TOL):
            name = nm
            break
    print('  %-12.4f %-12d %-14.2f %s' % (val, int(csum[i]), vsum[i] * 1e6, name))

# ===== 脳組織マスクの候補 =====
print('')
print('--- 脳組織マスクの候補（非標的領域の定義に使う）---')
BRAIN = {'白質のみ (0.348)': (0.3480 * (1 - TOL), 0.3480 * (1 + TOL)),
         '灰白質のみ (0.419)': (0.4191 * (1 - TOL), 0.4191 * (1 + TOL)),
         '白質+灰白質 (0.33-0.44)': (0.33, 0.44),
         '脳らしい帯 (0.10-0.50)': (0.10, 0.50)}
for nm, (lo, hi) in BRAIN.items():
    m = np.isfinite(sigma) & (sigma >= lo) & (sigma <= hi)
    print('  %-26s セル %-10d 体積 %.1f mL' % (nm, int(m.sum()), float(vol[m].sum()) * 1e6))
print('  ※ 参考: 成人の脳容積は約 1200〜1400 mL（Yoon-sun は小柄なので下寄りの想定）')

print('')
print('=== σ マップ 完了（読み取りのみ・保存していない）===')
