"""5-1g 補助: Transducer の位置を高精度で出す（分離版 / 統合版で比較・読み取り専用）。

統合版の TUS で選択性・ROI 中心 |p| が分離版と数%ずれた。疑っているのは
**トランスデューサの設置点の差**:
  - 分離版: 電極を削除済みだったので `build_transducer.py` の T7_FALLBACK
            = (94.8, 335.8, 1536.4)【**小数1桁に丸めた実測値**】を使った
  - 統合版: `Elec_T7` の実重心を使った（本来の設計）
250kHz は水中 λ≈6mm なので、0.1mm のズレでも位相 6度。焦点の干渉には効く。

**両プロジェクトで流して数値を突き合わせる**。表示はすべて小数4桁。
"""
import numpy as np
import s4l_v1.model as model
import XCoreModeling as xc

T7_FALLBACK = np.array([94.8, 335.8, 1536.4])   # build_transducer.py のハードコード値
FOCUS_MM = np.array([99.1, 295.0, 1562.2])


def xyz(v):
    try:    return np.array([float(v[0]), float(v[1]), float(v[2])])
    except: return np.array([float(v.X), float(v.Y), float(v.Z)])


ents = list(model.AllEntities())


def get(name):
    hit = [e for e in ents if getattr(e, 'Name', '') == name]
    return hit[0] if hit else None


def centroid(e):
    """重心。GetCenterOfMass が無ければ bbox 中心で代用（どちらを使ったか明示する）。"""
    for attr in ('GetCenterOfMass',):
        f = getattr(xc, attr, None)
        if f is not None:
            try:
                return xyz(f(e)), attr
            except Exception:
                pass
    bb = xc.GetBoundingBox([e])
    return 0.5 * (xyz(bb[0]) + xyz(bb[1])), 'bbox中心'


print('=== Transducer の位置（小数4桁）===')
tr = get('Transducer')
if tr is None:
    print('[tr  ] Transducer が無い（tTIS 単体プロジェクトなら正常）')
else:
    bb = xc.GetBoundingBox([tr])
    lo, hi = xyz(bb[0]), xyz(bb[1])
    cen, how = centroid(tr)
    print('[tr  ] bbox lo = [%.4f, %.4f, %.4f]' % tuple(lo))
    print('[tr  ] bbox hi = [%.4f, %.4f, %.4f]' % tuple(hi))
    print('[tr  ] size    = [%.4f, %.4f, %.4f]' % tuple(hi - lo))
    print('[tr  ] 重心(%s) = [%.4f, %.4f, %.4f]' % ((how,) + tuple(cen)))

print('')
print('=== Elec_T7 の位置（統合版のみ存在）===')
et = get('Elec_T7')
if et is None:
    print('[t7  ] Elec_T7 が無い ＝ build_transducer.py は T7_FALLBACK を使ったはず')
    print('[t7  ] FALLBACK = [%.4f, %.4f, %.4f]（小数1桁に丸めた値）' % tuple(T7_FALLBACK))
else:
    bb = xc.GetBoundingBox([et])
    lo, hi = xyz(bb[0]), xyz(bb[1])
    cen, how = centroid(et)
    d = cen - T7_FALLBACK
    print('[t7  ] bbox lo = [%.4f, %.4f, %.4f]' % tuple(lo))
    print('[t7  ] bbox hi = [%.4f, %.4f, %.4f]' % tuple(hi))
    print('[t7  ] 重心(%s) = [%.4f, %.4f, %.4f]' % ((how,) + tuple(cen)))
    print('[t7  ] FALLBACK = [%.4f, %.4f, %.4f]' % tuple(T7_FALLBACK))
    print('[t7  ] **実重心 − FALLBACK = [%+.4f, %+.4f, %+.4f]  距離 %.4f mm**'
          % (d[0], d[1], d[2], float(np.linalg.norm(d))))
    print('       （250kHz・水中 λ≈6mm → %.1f mm のズレは位相 %.1f 度に相当）'
          % (float(np.linalg.norm(d)), 360.0 * float(np.linalg.norm(d)) / 6.0))

print('')
print('=== 焦点距離（設置点 → ROI 中心）===')
src = None
if et is not None:
    src, lab = centroid(et)[0], 'Elec_T7 実重心'
else:
    src, lab = T7_FALLBACK, 'T7_FALLBACK'
print('[geo ] %s → ROI 中心 の距離 = %.4f mm（設計 R=48.5）'
      % (lab, float(np.linalg.norm(FOCUS_MM - src))))
print('[geo ] FALLBACK → ROI 中心 の距離 = %.4f mm'
      % float(np.linalg.norm(FOCUS_MM - T7_FALLBACK)))

print('')
print('=== 5-1g 補助 完了（読み取りのみ）===')
print('    ★ 分離版 TUS プロジェクトでも流し、[tr ] の bbox / 重心を突き合わせること')
