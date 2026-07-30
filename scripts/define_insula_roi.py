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

妥当性の判定基準（ノートが定めたもの）:
  MNI ±38, 0, 0 相当・**頭皮から 3–4cm 深**

確定値（2026-07-21）: 中心 (99.1, 295.0, 1562.2) / 半径 10mm ★左半球
出典ノート: Claude/Knowledge/sim4life-yoonsun-implementation.md §4 / docs/phase1-dev.md 工程3
"""
import s4l_v1.model as model
import XCoreModeling as xc

RECORDED = (99.1, 295.0, 1562.2)      # 2026-07-21 に確定した値（再計算結果と突き合わせる）
RADIUS = 10.0                          # mm
MNI_OFFSET = 38.0                      # MNI の島皮質 y オフセット
MNI_BRAIN_WIDTH = 140.0                # MNI 標準脳幅
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

# ---- ② 妥当性の検証（判定基準＝頭皮から 3–4cm 深・脳内にあること）----
print('\n--- 妥当性の検証（ROI 中心からの符号付き距離・負＝内部）---')
for nm in ('Skin', 'Skull_cortical', 'Cerebrum_grey_matter', 'Cerebrum_white_matter'):
    d = dist_from(nm, RECORDED)
    print('  %-24s %+.1f mm' % (nm, d) if d is not None else '  %-24s なし' % nm)

skin_d = dist_from('Skin', RECORDED)
print('\n判定:')
print('  頭皮からの深さ %.1f mm → 基準 30–40mm: %s' % (skin_d, 'OK' if 30 <= skin_d <= 40 else '★基準外'))
print('  ※ Yoon-sun は小さめの頭（脳幅 %.0fmm・MNI の %.2f倍）なので換算 %.0f–%.0f mm 相当'
      % (brain_w, brain_w / MNI_BRAIN_WIDTH,
         30 * brain_w / MNI_BRAIN_WIDTH, 40 * brain_w / MNI_BRAIN_WIDTH))
print('  ※ Skin は薄い"層"なので、頭の内部の点は「層の外側」＝正の距離になる（内外判定には使えない）')

wm_d = dist_from('Cerebrum_white_matter', RECORDED)
print('  白質の内部にあるか（負なら内部）: %+.1f mm → %s' % (wm_d, 'OK' if wm_d < 0 else '★脳外'))

inside_grid = all(lo <= c - RADIUS and c + RADIUS <= hi
                  for c, (lo, hi) in zip(RECORDED, (GX, GY, GZ)))
print('  ROI 球が頭部グリッド範囲に収まるか: %s' % inside_grid)

print('\n→ 解析で使う ROI: sphere_mask(%.1f/1000, %.1f/1000, %.1f/1000, %.3f)  ※単位 m'
      % (RECORDED[0], RECORDED[1], RECORDED[2], RADIUS / 1000.0))
print('   （ti_analysis.py の sphere_mask はグリッド座標＝m なので mm を 1000 で割る）')
