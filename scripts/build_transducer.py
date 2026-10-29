"""工程TUS-1 (4-3) 集束トランスデューサ（球面キャップ）を作成（Sim4Life.lite Python コンソール）。

lec7 の「球→殻→キャップ」Boolean レシピを Python 化。幾何確定値（scripts/plan_transducer.py）:
  f=250kHz / 開口 D=40mm / 焦点=島皮質 ROI 中心。曲率半径 R は下の 2026-10-29 修正を参照（R_OUT 70.53mm・F# 1.76）。
焦点＝球の曲率中心なので、焦点中心の球の凹面が焦点を向く。

T7 の位置は **既存の Elec_T7 エンティティ**（tTIS の左側頭電極＝同じ設置点）の重心から取る。
→ tTIS と物理的に同一の設置点＝#36 比較の「同一条件」を幾何レベルで担保。

★2026-10-29 修正（#25）: 軸は焦点→T7 のまま、殻を頭の外に出した（R_IN = R_IN_CLEAR）。
  それまでは R_OUT = |T7 − F| = 48.5mm で外側の面のてっぺんを頭皮に付けていたので、殻の 40%（1575/3976 セル）が
  皮下脂肪・皮膚・耳・耳下腺に埋まっていた（実際の TUS は頭皮の外に置き、あいだをジェル＝水で埋める）。
  軸が頭の表面に斜めに当たるので、開口の中の頭の一番外は焦点から 65.03mm（耳の皮膚・縁。耳介を除いても 64.99mm）
  ＝ scripts/tus_transducer_overlap.py。殻の内側の面をそれより 0.5mm（ボクセルの半分）＋水 2mm 外に置く。
  あいだは TUS の背景（Water）で埋まる。R_OUT 70.53mm・F# 1.76（開口 40mm のまま）。

流れ:
  ① 事前ゲート（Skin / Elec_T7 が実在・同名 Transducer が無い）
  ② 焦点 F=ROI中心・T7=Elec_T7 重心 → 軸 d=(T7-F)/|T7-F|・距離を実測（T7 の頭皮〜焦点 48.5mm）
  ③ 球 R_OUT（中心 F）と R_IN=R_IN_CLEAR を Subtract → 厚さ3mmの殻（頭の外）
  ④ 軸 d 方向の円柱（半径=開口/2=20mm）で Intersect → T7 側のキャップだけ残す
  ⑤ 'Transducer' にリネーム＋事後検算

geometry を1個作るだけ（不要なら Model ツリーで Transducer を削除すれば戻せる）。
"""
import s4l_v1.document as document
import s4l_v1.model as model
import XCoreModeling as xc
import numpy as np

FOCUS = np.array([99.1, 295.0, 1562.2])   # 島皮質 ROI 中心 [mm]（tTIS と同一 ROI）
# 曲率半径 R: 2026-08-20 は「R = 頭皮(T7)〜焦点の実距離 48.5mm」にしたが、殻の厚さと斜めの軸のため頭に埋まった。
#   2026-10-29 から、殻の内側の面を開口の中の頭の一番外より外に置く（R_IN_CLEAR）。
SHELL = 3.0                                # 殻の厚み [mm]
R_IN_CLEAR = 65.03 + 0.5 + 2.0             # 殻の内側の面 [mm]＝開口の中の頭の一番外＋ボクセルの半分＋水の層（2026-10-29）
APERTURE_D = 40.0                          # 開口径 [mm]（側頭窓の上限で固定）→ F#=R/D は実測で決まる
CAP_R = APERTURE_D / 2.0                   # 円柱半径 = 20mm
T7_NAME = 'Elec_T7'
T7_FALLBACK = np.array([94.8, 335.8, 1536.4])   # Elec_T7 重心の実測（電極削除後はこれを使う・2026-08-20）
NAME = 'Transducer'

FNUM_LO, FNUM_HI = 0.7, 2.0                # F# がこの範囲を外れたら警告（頭の外に出して 1.76）


def V(p):
    return model.Vec3(*map(float, p))


def xyz(v):
    try:
        return np.array([float(v[0]), float(v[1]), float(v[2])])
    except Exception:
        return np.array([float(v.X), float(v.Y), float(v.Z)])


def centroid(ent):
    bb = xc.GetBoundingBox([ent])
    return (xyz(bb[0]) + xyz(bb[1])) / 2.0


# ===== ① 事前ゲート =====
if 'Skin' not in [e.Name for e in model.AllEntities()]:
    raise SystemExit('[pre ] FAILED — Skin が無い（Yoon-sun プロジェクトを開くこと）')

# 既存の Transducer は作り直しのため自動削除（自作エンティティなので安全）。
# ★削除後は必ずリストを取り直す。削除済みハンドルを含む古いリストを回すと
#   e.Name アクセスで RuntimeError: ACIS operation unsuccessful になる（2026-08-20 実測）。
old = [e for e in model.AllEntities() if e.Name == NAME]
for e in old:
    e.Delete()
    print('[pre ] 既存の %r を削除して作り直す' % NAME)
ents = list(model.AllEntities())           # ← 削除後に取り直す

# T7: Elec_T7 があればその重心、無ければ実測フォールバック（電極削除後でも動く）
t7 = [e for e in ents if e.Name == T7_NAME]
if t7:
    T7 = centroid(t7[0])
    print('[pre ] T7 = %s の重心を使用' % T7_NAME)
else:
    T7 = T7_FALLBACK
    print('[pre ] %s が無いので実測フォールバック値を使用' % T7_NAME)

# ===== ② 幾何を実測 → R を頭皮距離に合わせる =====
d = T7 - FOCUS
dist = float(np.linalg.norm(d))
d = d / dist
R_IN = R_IN_CLEAR                          # ★殻を頭の外に置く（T7 は焦点から dist＝48.5mm の頭皮上）
R_OUT = R_IN + SHELL
fnum = R_OUT / APERTURE_D
print('[geo ] 焦点 F   = %s' % np.round(FOCUS, 1))
print('[geo ] T7 重心  = %s' % np.round(T7, 1))
print('[geo ] R=焦点距離=%.1f mm  開口D=%.1f mm  → F#=%.2f  軸 d=%s'
      % (R_OUT, APERTURE_D, fnum, np.round(d, 3)))
if not (FNUM_LO <= fnum <= FNUM_HI):
    print('[geo ] ⚠ WARN — F#=%.2f が想定域 [%.1f,%.1f] 外。開口 D か設置点を見直す'
          % (fnum, FNUM_LO, FNUM_HI))
# 焦点サイズの目安（軟部 c=1500・λ=6mm at 250kHz）
LAM = 6.0
print('[geo ] 焦点目安: 側方FWHM~%.1f mm / 軸方向~%.1f mm' % (LAM * fnum, 7 * LAM * fnum ** 2))

# 凹面（内側の面）のてっぺん＝焦点から d 方向に R_IN。T7 の頭皮より外（あいだは水）
p_face = FOCUS + R_IN * d
print('[geo ] 凹面のてっぺん P_face = %s（T7 の頭皮から %.1f mm 外）' % (np.round(p_face, 1), R_IN - dist))

# ===== ③ 球殻を作る（外球 − 内球）=====
outer = xc.CreateSolidSphere(V(FOCUS), R_OUT)
outer.Name = '_tus_outer'
inner = xc.CreateSolidSphere(V(FOCUS), R_IN)
inner.Name = '_tus_inner'
shell = xc.Subtract([outer, inner])
# Subtract の戻りが Entity か list かは実装依存 → 正規化
shell = shell[0] if isinstance(shell, (list, tuple)) else shell
shell.Name = '_tus_shell'
print('[bld ] 殻を作成: R_out=%.0f - R_in=%.0f (厚 %.0fmm)' % (R_OUT, R_IN, SHELL))

# ===== ④ 円柱で T7 側キャップを切り出す =====
# 軸 d 方向に、殻を確実に貫く長さの円柱（内側は焦点寄り・外側は面より先）
c0 = FOCUS + (R_IN - 5.0) * d      # 殻の内側面より少し手前から
c1 = FOCUS + (R_OUT + 5.0) * d     # 殻の外側面より少し先まで
cyl = xc.CreateSolidCylinder(V(c0), V(c1), CAP_R)
cyl.Name = '_tus_cyl'
cap = xc.Intersect([shell, cyl])
cap = cap[0] if isinstance(cap, (list, tuple)) else cap
cap.Name = NAME
print('[bld ] キャップを切出し: 円柱半径=%.0fmm (開口D=%.0fmm, F#=%.2f)'
      % (CAP_R, APERTURE_D, R_OUT / APERTURE_D))

# ===== ⑤ 事後検算 =====
fail = []
made = [e for e in model.AllEntities() if e.Name == NAME]
if len(made) != 1:
    fail.append('%r が %d 個（1個であること）' % (NAME, len(made)))
else:
    t = made[0]
    bb = xc.GetBoundingBox([t])
    lo, hi = xyz(bb[0]), xyz(bb[1])
    size = hi - lo
    cen = (lo + hi) / 2.0
    print('[post] Transducer bbox size = %s mm' % np.round(size, 1))
    print('[post] Transducer 重心     = %s' % np.round(cen, 1))
    # 開口が概ね D=40mm（軸に直交する2辺が ~40mm 前後）を粗くチェック
    lat = sorted(size)[-2:]            # 大きい方2軸（面内）
    if not (APERTURE_D * 0.6 <= max(lat) <= APERTURE_D * 1.4):
        fail.append('開口寸法が想定外: 面内サイズ %s' % np.round(lat, 1))

# 掃除（残った補助ボディがあれば消す。通常 Boolean が消費している）
for junk in ('_tus_outer', '_tus_inner', '_tus_shell', '_tus_cyl'):
    for e in [e for e in model.AllEntities() if e.Name == junk]:
        try:
            e.Delete()
            print('[post] 補助ボディ %s を削除' % junk)
        except Exception:
            print('[post] ⚠ 補助ボディ %s が残存（手動削除可）' % junk)

print('=== 工程4-3 %s ===' % ('PASS' if not fail else 'FAILED: ' + '; '.join(fail)))
document.Save()
print('saved.')
