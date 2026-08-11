"""工程6 電極に Dirichlet BC（±電位）を付ける（Sim4Life.lite Python コンソール）。

工程5（`assign_materials.py`）で σ と Voxeler/Grid 登録が済んだ sim に対して実行する。

**BC は電極ソリッド本体に付ける**（2026-08-03 確定）。
2026-07-30 には「材料σと BC を同一ソリッドに付けると弾かれる」と判断して面（Face）へ移したが、
その観測はボクセル化が壊れていた期間のもので、Run 拒否はボクセル化の段で起きていた。
根本原因（Voxeler/Grid への登録漏れ）を直したうえで測り直したところ、
ソリッドへの BC は材料σ・Grid・Voxeler と併存して正しく紐付く（コンポーネントが4キーになる）。

逆に **面（Face）への BC は使えない**。`sim.AddBoundarySettings(face)` は恒久的な紐付けを作らず、
**常に最後の1つだけ**が単一の無名コンポーネントに載り、それ以前の BC は設定だけ残って孤児になる。
設定は `AllSettings` から読めてしまうため「付いているのに効いていない」形の罠になる（2026-08-03 実測）。

流れ:
  ① 対象 sim を取得し、既存 BC が無いことを確認（孤児 BC が残った sim には流さない）
  ② 駆動ペアの2枚に Dirichlet を付ける（+1V / 0V）
  ③ ゲート（駆動2枚が BC を保持 / 非駆動に BC が無い / 材料と Voxeler 登録が生きている）

1V 駆動でよい。電場は線形なので Inoue の 0.891/1.109 mA へのスケールは計算後に行う。
両方 0V だと電位差ゼロで電流が流れない（lec6 の罠）。

ペア2 を作るときは SIM_NAME と DRIVE を差し替える（tTIS_LF2 / Fp1 +1V / Fp2 0V）。
本スクリプトは CreateVoxels を実行しない。ボクセル化は全設定を終えた後の工程7 で行う。

出典ノート: Claude/Knowledge/sim4life-electrode-placement.md ⑥
"""
import s4l_v1.document as document
import s4l_v1.model as model
import s4l_v1.simulation.emlf as emlf

SIM_NAME = 'tTIS_LF2'                            # ペア1 は 'tTIS_LF1'
DRIVE = (('Elec_Fp1', 1.0, 'BC_Fp1_pos'),        # ペア2。ペア1 は Elec_T7 / Elec_P7
         ('Elec_Fp2', 0.0, 'BC_Fp2_gnd'))
ALL_ELEC = ('Elec_T7', 'Elec_P7', 'Elec_Fp1', 'Elec_Fp2')

DEFAULT_BC_NAME = 'Boundary Settings'            # sim 作成時から在る既定の BC（駆動には使わない）


def base(name):
    """component.Name の接尾辞 '  (Yoon-sun v3.1 Static/Bones)' を落としてエンティティ名に戻す。"""
    return name.split('  (')[0].strip()


# ===== ① 対象 sim の取得と事前ゲート =====
sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個（1個であること）' % (SIM_NAME, len(sims)))
sim = sims[0]

existing = [s.Name for s in sim.AllSettings
            if type(s).__name__ == 'BoundarySettings' and s.Name != DEFAULT_BC_NAME]
print('[pre ] sim=%s  existing BC settings=%s' % (sim.Name, existing))
if existing:
    raise SystemExit('[pre ] FAILED — 既に BC がある。孤児が混ざるので sim を作り直すこと')

# ===== ② Dirichlet BC を電極ソリッドに付ける =====
for nm, volt, bcname in DRIVE:
    ent = [e for e in model.AllEntities() if e.Name == nm][0]
    bc = sim.AddBoundarySettings(ent)
    bc.Name = bcname
    bc.BoundaryType = emlf.EnumBoundaryType.kDirichlet     # Deprecated 警告が出るが動く
    bc.DirichletValue = volt
    print('[bc  ] %-10s -> %-12s %.1f V' % (nm, bcname, volt))

# ===== ③ 事後ゲート =====
fail = []
driven = dict((nm, bcname) for nm, _, bcname in DRIVE)
seen = {}
for c in sim.AllComponents:
    nm = base(c.Name)
    if nm in ALL_ELEC:
        seen[nm] = sorted(c.Settings.keys())

for nm in ALL_ELEC:
    keys = seen.get(nm)
    print('[post] %-10s %s' % (nm, keys))
    if keys is None:
        fail.append('%s: コンポーネントが無い' % nm)
        continue
    has_bc = driven[nm] in keys if nm in driven else any(k.startswith('BC_') for k in keys)
    if nm in driven and not has_bc:
        fail.append('%s: BC が紐付いていない' % nm)
    if nm not in driven and has_bc:
        fail.append('%s: 非駆動なのに BC が付いている' % nm)
    # Grid（AutomaticGridSettings）には登録しない構成なので 'Automatic' キーは現れない。
    # 見るのは Voxeler 登録だけ（2026-08-03）。
    if 'Automatic Voxeler Settings' not in keys:
        fail.append('%s: Voxeler 登録が消えている' % nm)

vals = dict((s.Name, getattr(s, 'DirichletValue', None)) for s in sim.AllSettings
            if type(s).__name__ == 'BoundarySettings')
print('[post] boundary settings:', vals)
for nm, volt, bcname in DRIVE:
    if vals.get(bcname) != volt:
        fail.append('%s: 電位が %s（期待 %s）' % (bcname, vals.get(bcname), volt))
if len(vals) != len(DRIVE) + 1:
    fail.append('BC 設定の数が %d（期待 %d = 駆動%d + 既定1）'
                % (len(vals), len(DRIVE) + 1, len(DRIVE)))

print('=== 工程6 %s ===' % ('PASS' if not fail else 'FAILED: ' + '; '.join(fail)))
document.Save()
print('saved.')
