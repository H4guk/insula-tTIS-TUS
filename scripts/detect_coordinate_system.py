"""② 座標系・ランドマーク・島皮質 ROI の検出（Sim4Life.lite Python コンソール）。

座標ラベル(X/Y/Z)を鵜呑みにせず、寸法・組織名・組織間の位置関係という
"座標系に依らない事実" から軸の意味を逆算する（別モデルでも通用させるため）。

実測結果(Yoon-sun・単位 mm・原点は足元):
  X=前後(+X=前) / Y=左右(+Y=左・正中≈260.5) / Z=上下(頭頂1661)
  ★ +Y=左 の取り違え厳禁（電極は左・ROI は右で全実験が無意味になる）
  AC-PC 傾き 3.18° → 回転補正不要
  左島皮質 ROI: 中心 (99.1, 295.0, 1562.2) / 半径 10mm の球

出典ノート: Claude/Knowledge/sim4life-yoonsun-implementation.md §3
"""
import s4l_v1.model as model
import XCoreModeling as xc
import math


def xyz(v):
    try:    return float(v[0]), float(v[1]), float(v[2])
    except: return float(v.X), float(v.Y), float(v.Z)


ents = list(model.AllEntities())


def bbox(name):
    hit = [e for e in ents if e.Name == name]
    if not hit: return None
    bb = xc.GetBoundingBox(hit)
    if not bb: return None
    lo, hi = xyz(bb[0]), xyz(bb[1])
    return lo, hi, tuple((lo[i] + hi[i]) / 2 for i in range(3))


# ① 軸の意味（脳の寸法で判定）
whole = xc.GetBoundingBox(ents); wlo, whi = xyz(whole[0]), xyz(whole[1])
gm = bbox('Cerebrum_grey_matter')
for i, ax in enumerate(['X', 'Y', 'Z']):
    print('%s: 全身 %.1f→%.1f  脳幅 %.1f' % (ax, wlo[i], whi[i], gm[1][i] - gm[0][i]))

# ② 左右の向き（耳で確定・★+Y=左）
el, er = bbox('Ear_cartilage_left'), bbox('Ear_cartilage_right')
print('Ear_left Y %.1f / Ear_right Y %.1f → +Y=%s'
      % (el[2][1], er[2][1], '左' if el[2][1] > er[2][1] else '右'))
mid_y = (el[2][1] + er[2][1]) / 2
print('正中 Y（耳の中点）= %.1f' % mid_y)

# ③ 前後の向き（眼で確定・★+X=前）＋ランドマーク
for name in ('Commissura_anterior', 'Commissura_posterior', 'Eye_lens', 'Hippocampus'):
    b = bbox(name)
    if b: print('%-22s = (%.1f, %.1f, %.1f)' % (name, *b[2]))
ac, eye = bbox('Commissura_anterior'), bbox('Eye_lens')
print('眼X %.1f > AC X %.1f → +X=前' % (eye[2][0], ac[2][0]))

# ④ 頭の傾き（AC-PC線）
pc = bbox('Commissura_posterior')
dx, dz = ac[2][0] - pc[2][0], ac[2][2] - pc[2][2]
print('AC-PC 距離 %.2fmm / 傾き %.2f度（0なら補正不要）'
      % (math.hypot(dx, dz), math.degrees(math.atan2(dz, dx))))

# ⑤ 頭部範囲（Z>=1450 の組織）
head = []
for e in ents:
    bb = xc.GetBoundingBox([e])
    if bb and xyz(bb[0])[2] >= 1450.0:
        head.append((xyz(bb[0]), xyz(bb[1])))
x0 = min(h[0][0] for h in head); x1 = max(h[1][0] for h in head)
y0 = min(h[0][1] for h in head); y1 = max(h[1][1] for h in head)
z0 = min(h[0][2] for h in head); z1 = max(h[1][2] for h in head)
print('頭部 X %.1f→%.1f / Y %.1f→%.1f / Z %.1f→%.1f' % (x0, x1, y0, y1, z0, z1))

# ⑥ 島皮質 ROI（MNI±38 を脳幅で補正）
brain_w = gm[1][1] - gm[0][1]; off = 38.0 * brain_w / 140.0
print('左島皮質 (%.1f, %.1f, %.1f) r=10mm ★本番' % (ac[2][0], mid_y + off, ac[2][2]))
print('右島皮質 (%.1f, %.1f, %.1f) r=10mm'        % (ac[2][0], mid_y - off, ac[2][2]))
