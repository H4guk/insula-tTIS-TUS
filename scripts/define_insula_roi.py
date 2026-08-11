"""工程3 島皮質 ROI の定義と検証（Sim4Life.lite Python コンソール）。

工程2（`detect_coordinate_system.py`）から分離した。工程2は「座標系とランドマークを確定させる」担当で、
本ファイルは「その結果から ROI を決め、妥当かどうかを確かめる」担当。

ROI の決め方:
  MNI 座標の左島皮質 (−38, 0, 0) を Yoon-sun に移す。
  - 左右 : 正中（耳の中点）から **MNI 38mm を脳幅で補正した量** だけ左（+Y）へ寄せる
           補正 = Yoon-sun の脳幅 / MNI 標準 140mm（実測 127/140 = 0.91）→ 約 34.5mm
  - 前後・高さ : MNI では insula は AC（前交連）と同じ y,z なので **AC と同じ X, Z** を使う
  - 半径 : 10mm の球（粗ROI）

粗ROI にする理由:
  Yoon-sun は**島皮質を独立した組織として持たない**（軸位断で GM の帯が1本しか出ないことを 2026-07-21 に確認）。
  組織ベースの精密 ROI は作れないので球で切る。tTIS/TUS で同一 ROI を使う限り比較の公平性は保たれる。

妥当性の判定基準:
  MNI ±38, 0, 0 相当・**頭皮から 40mm 深**（2026-08-11 に「3–4cm」の幅を 40mm へ一本化・GH #9）

★深さの測り方（2026-08-11・GH #9 の本体）:
  従来の 25.0mm は `GetEntityPointDistance` の**最近傍面までの距離**で、これは
  「頭皮からの深さ」とは別物になりうる。左側頭の頭皮は T7 の実測で Y=335.6、ROI は Y=295.0 だから
  **外側の頭皮までは約 40mm** あるはずで、25.0mm と合わない。本命は**外耳道**——
  ROI の高さ（Z=1562.2）は耳の高さで、外耳道の皮膚は頭の内側へ 20〜25mm 入り込むため、
  `Skin` メッシュがそれを含んでいれば最近傍面は外耳道の壁になる。
  そこで深さを**2通りで測って区別する**:
    (a) 最近傍面までの距離 ＋ **その最近傍点の座標**（どこを拾っているかが分かる）
    (b) **外側の頭皮までの距離**（ROI の外側に置いた点から `ClosestPosition` で頭皮に落とす）
  ROI を動かして深さを稼ぐ案は採らない。15mm 内側へ寄せると正中から 19.5mm ＝ MNI |x|≈21mm で
  **大脳基底核の領域になり、標的が島皮質でなくなる**ため。

確定値（2026-07-21）: 中心 (99.1, 295.0, 1562.2) / 半径 10mm ★左半球
出典ノート: Claude/Knowledge/sim4life-yoonsun-implementation.md §4 / docs/phase1-dev.md 工程3
"""
import s4l_v1.model as model
import XCoreModeling as xc

RECORDED = (99.1, 295.0, 1562.2)      # 2026-07-21 に確定した値（再計算結果と突き合わせる）
RADIUS = 10.0                          # mm
MNI_OFFSET = 38.0                      # MNI の島皮質 y オフセット
MNI_BRAIN_WIDTH = 140.0                # MNI 標準脳幅
DEPTH_CRITERION = 40.0                # mm。頭皮からの深さの基準（2026-08-11 確定・GH #9）
DEPTH_TOL = 5.0                       # mm。基準からの許容幅（粗ROIなので mm 精度は求めない）
PROBE_OUT = 150.0                     # mm。外側の頭皮を拾うために ROI の +Y 側へ置く探査点の距離
GX, GY, GZ = (4, 202), (162, 352), (1450, 1665)   # 頭部グリッド範囲（工程7で使う）


def xyz(v):
    try:    return float(v[0]), float(v[1]), float(v[2])
    except: return float(v.X), float(v.Y), float(v.Z)


ents = list(model.AllEntities())


def center_of(name):
    hit = [e for e in ents if e.Name == name]
    if not hit:
        return None
    bb = xc.GetBoundingBox(hit)
    if not bb:
        return None
    lo, hi = xyz(bb[0]), xyz(bb[1])
    return tuple((lo[i] + hi[i]) / 2 for i in range(3)), lo, hi


def dist_from(name, p):
    """p から name への符号付き距離（負＝その組織の内部）。"""
    hit = [e for e in ents if e.Name == name]
    if not hit:
        return None
    r = xc.GetEntityPointDistance(hit[0], model.Vec3(*map(float, p)))
    return float(r.Distance)


def closest_on(name, p):
    """p に最も近い name 表面上の点を (距離, (x, y, z)) で返す。"""
    hit = [e for e in ents if e.Name == name]
    if not hit:
        return None, None
    r = xc.GetEntityPointDistance(hit[0], model.Vec3(*map(float, p)))
    return float(r.Distance), xyz(r.ClosestPosition)


def norm(a, b):
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


# ---- ① ランドマークから ROI 中心を計算する ----
ac = center_of('Commissura_anterior')
el = center_of('Ear_cartilage_left')
er = center_of('Ear_cartilage_right')
gm = center_of('Cerebrum_grey_matter')

mid_y = (el[0][1] + er[0][1]) / 2.0                      # 正中 = 耳の中点
brain_w = gm[2][1] - gm[1][1]                            # 脳の左右幅
offset = MNI_OFFSET * brain_w / MNI_BRAIN_WIDTH          # スケール補正した左右オフセット
roi = (ac[0][0], mid_y + offset, ac[0][2])               # 左半球（+Y=左）

print('正中 Y（耳の中点）      = %.1f' % mid_y)
print('脳幅                    = %.1f mm → 補正係数 %.3f' % (brain_w, brain_w / MNI_BRAIN_WIDTH))
print('左右オフセット          = %.1f mm（MNI 38mm を補正）' % offset)
print('計算した左島皮質 ROI    = (%.1f, %.1f, %.1f) r=%.0fmm' % (roi[0], roi[1], roi[2], RADIUS))
print('記録値（2026-07-21）    = (%.1f, %.1f, %.1f)' % RECORDED)
print('記録値とのずれ          = (%.1f, %.1f, %.1f) mm'
      % tuple(roi[i] - RECORDED[i] for i in range(3)))

# ---- ② 妥当性の検証（判定基準＝頭皮から 40mm 深・脳内にあること）----
print('\n--- 妥当性の検証（ROI 中心からの符号付き距離・負＝内部）---')
for nm in ('Skin', 'Skull_cortical', 'Cerebrum_grey_matter', 'Cerebrum_white_matter'):
    d = dist_from(nm, RECORDED)
    print('  %-24s %+.1f mm' % (nm, d) if d is not None else '  %-24s なし' % nm)

# ---- ③ 深さを2通りで測って区別する（2026-08-11・GH #9）----
# (a) 最近傍面までの距離。**どこを拾っているか**が分かるよう最近傍点の座標も出す。
#     外耳道の壁を拾っていれば、その点は ROI より内側（Y が小さい）か耳道の奥に来る。
# (b) 外側の頭皮までの距離。ROI の +Y 側（左の外）に置いた探査点から頭皮へ落とす。
print('\n--- 深さの測り方の区別（GH #9）---')
near_d, near_p = closest_on('Skin', RECORDED)
print('(a) 最近傍の皮膚面まで      %.1f mm  最近傍点 (%.1f, %.1f, %.1f)'
      % (near_d, near_p[0], near_p[1], near_p[2]))
print('    ROI からの向き          ΔX %+.1f  ΔY %+.1f  ΔZ %+.1f'
      % tuple(near_p[i] - RECORDED[i] for i in range(3)))

probe = (RECORDED[0], RECORDED[1] + PROBE_OUT, RECORDED[2])       # 頭の外（左側）
out_d, out_p = closest_on('Skin', probe)
lateral = norm(RECORDED, out_p)
print('(b) 外側の頭皮まで          %.1f mm  頭皮点 (%.1f, %.1f, %.1f)'
      % (lateral, out_p[0], out_p[1], out_p[2]))

print('\n判定（基準 %.0f mm ± %.0f）:' % (DEPTH_CRITERION, DEPTH_TOL))
for label, val in (('(a) 最近傍面', near_d), ('(b) 外側の頭皮', lateral)):
    ok = abs(val - DEPTH_CRITERION) <= DEPTH_TOL
    print('  %-16s %.1f mm → %s' % (label, val, 'OK' if ok else '★基準外'))
print('  ※ (a) と (b) が大きく食い違う場合、(a) は外耳道など内側へ入り込む皮膚面を拾っている。')
print('     その場合「頭皮からの深さ」として採用するのは (b)。')
print('  ※ Yoon-sun は小さめの頭（脳幅 %.0fmm・MNI の %.2f倍）なので、'
      'MNI 換算では %.0f mm 相当' % (brain_w, brain_w / MNI_BRAIN_WIDTH,
                                    DEPTH_CRITERION * MNI_BRAIN_WIDTH / brain_w))
print('  ※ Skin は薄い"層"なので、頭の内部の点は「層の外側」＝正の距離になる（内外判定には使えない）')

wm_d = dist_from('Cerebrum_white_matter', RECORDED)
print('  白質の内部にあるか（負なら内部）: %+.1f mm → %s' % (wm_d, 'OK' if wm_d < 0 else '★脳外'))

inside_grid = all(lo <= c - RADIUS and c + RADIUS <= hi
                  for c, (lo, hi) in zip(RECORDED, (GX, GY, GZ)))
print('  ROI 球が頭部グリッド範囲に収まるか: %s' % inside_grid)

print('\n→ 解析で使う ROI: sphere_mask(%.1f/1000, %.1f/1000, %.1f/1000, %.3f)  ※単位 m'
      % (RECORDED[0], RECORDED[1], RECORDED[2], RADIUS / 1000.0))
print('   （ti_analysis.py の sphere_mask はグリッド座標＝m なので mm を 1000 で割る）')
