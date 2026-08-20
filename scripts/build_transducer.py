"""工程TUS-1 (4-3) 集束トランスデューサ（球面キャップ）を作成（Sim4Life.lite Python コンソール）。

lec7 の「球→殻→キャップ」Boolean レシピを Python 化。幾何確定値（scripts/plan_transducer.py）:
  f=250kHz / 曲率半径 R=40mm / 開口 D=40mm(F#=1.0) / 焦点=島皮質 ROI 中心。
焦点＝球の曲率中心なので、焦点中心の球（R=40）の凹面が焦点を向く。

T7 の位置は **既存の Elec_T7 エンティティ**（tTIS の左側頭電極＝同じ設置点）の重心から取る。
→ tTIS と物理的に同一の設置点＝#36 比較の「同一条件」を幾何レベルで担保。

流れ:
  ① 事前ゲート（Skin / Elec_T7 が実在・同名 Transducer が無い）
  ② 焦点 F=ROI中心・T7=Elec_T7 重心 → 軸 d=(T7-F)/|T7-F|・距離を実測（設計 R=40 と照合）
  ③ 球 R_OUT=40（中心 F）と R_IN=37 を Subtract → 厚さ3mmの殻
  ④ 軸 d 方向の円柱（半径=開口/2=20mm）で Intersect → T7 側のキャップだけ残す
  ⑤ 'Transducer' にリネーム＋事後検算

geometry を1個作るだけ（不要なら Model ツリーで Transducer を削除すれば戻せる）。
"""
import s4l_v1.document as document
import s4l_v1.model as model
import XCoreModeling as xc
import numpy as np

FOCUS = np.array([99.1, 295.0, 1562.2])   # 島皮質 ROI 中心 [mm]（tTIS と同一 ROI）
# ★曲率半径 R = 焦点距離 = 頭皮(T7)〜焦点の実距離に合わせる（2026-08-20 修正）。
#   R を固定40mm にすると椀の面が頭皮より内側に埋没する（T7 は焦点から実測 48.5mm）。
#   焦点を ROI 中心に正しく当てるため R は実測距離に追従させる。
SHELL = 3.0                                # 殻の厚み [mm]
APERTURE_D = 40.0                          # 開口径 [mm]（側頭窓の上限で固定）→ F#=R/D は実測で決まる
CAP_R = APERTURE_D / 2.0                   # 円柱半径 = 20mm
T7_NAME = 'Elec_T7'
T7_FALLBACK = np.array([94.8, 335.8, 1536.4])   # Elec_T7 重心の実測（電極削除後はこれを使う・2026-08-20）
NAME = 'Transducer'

FNUM_LO, FNUM_HI = 0.7, 1.6                # F# がこの範囲を外れたら警告


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
R_OUT = dist                               # ★焦点距離＝頭皮〜焦点の実距離
R_IN = R_OUT - SHELL
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

# 面の中心（凹面のてっぺん）＝焦点から d 方向に R_OUT ＝ 頭皮上に乗る
p_face = FOCUS + R_OUT * d
print('[geo ] キャップ面のてっぺん P_face = %s（頭皮上）' % np.round(p_face, 1))

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
