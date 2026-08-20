"""Phase 4-3 トランスデューサの幾何設計（ローカル実行・Sim4Life 不要）。

集束型（球面キャップ）トランスデューサを想定。幾何焦点＝曲率中心なので、
焦点距離 = 曲率半径 R。焦点を島皮質 ROI 中心（頭皮 T7 近傍から深さ実測 40mm）に置く。

f=250kHz・軟部 c=1500 → λ=6mm。F#=R/D を振って焦点寸法を評価し、
ROI（半径10mm＝径20mm）に側方が収まり、軸方向が過大にならない設計を選ぶ。

焦点寸法の近似（球面集束・弱集束近似）:
  側方 FWHM ~ 1.0 * λ * F#           （lateral）
  軸方向 FWHM ~ 7.0 * λ * F#^2        （axial・葉巻型）
開口 D は側頭部の音響窓（側頭骨は薄いが範囲は限られる）で制限＝現実的に D<=40mm 目安。
"""
import math

F_KHZ = 250
C_SOFT = 1500.0                 # 軟部組織音速 [m/s]
LAMBDA_MM = C_SOFT / (F_KHZ * 1e3) * 1e3   # = 6.0 mm
FOCAL_DEPTH_MM = 40.0           # ROI 中心の深さ（tTIS #37 GH#9 実測 40.0mm）
ROI_DIAM_MM = 20.0              # ROI 径（半径10mm 球）
D_MAX_MM = 40.0                 # 側頭窓で現実的な開口の上限目安

R_MM = FOCAL_DEPTH_MM           # 幾何焦点=曲率中心 → R=焦点距離

print('f=%d kHz  c_soft=%.0f m/s  lambda=%.2f mm' % (F_KHZ, C_SOFT, LAMBDA_MM))
print('焦点深さ=%.0f mm（=曲率半径 R）  ROI 径=%.0f mm  開口上限 D<=%.0f mm'
      % (FOCAL_DEPTH_MM, ROI_DIAM_MM, D_MAX_MM))
print('')
hdr = '%-6s %-8s %-9s %-13s %-13s %-10s'
print(hdr % ('F#', 'D[mm]', 'R[mm]', '側方FWHM[mm]', '軸方向FWHM[mm]', '判定'))
print('-' * 64)

best = None
for f_number in (0.7, 0.8, 1.0, 1.2, 1.5):
    D = R_MM / f_number
    lat = 1.0 * LAMBDA_MM * f_number
    axi = 7.0 * LAMBDA_MM * f_number ** 2
    notes = []
    if D > D_MAX_MM:
        notes.append('D超過(窓)')
    if lat > ROI_DIAM_MM:
        notes.append('側方>ROI')
    # 側方が ROI 径に収まり(<=20mm)・開口が窓内(<=40mm)なら候補
    ok = (D <= D_MAX_MM) and (lat <= ROI_DIAM_MM)
    tag = 'OK' if ok else ('/'.join(notes) if notes else '-')
    print('%-6.1f %-8.1f %-9.1f %-13.1f %-13.1f %-10s'
          % (f_number, D, R_MM, lat, axi, tag))
    # 軸方向をできるだけ小さく（＝F#小＝Dだけ大きく）しつつ窓内に収まる最小 F# を推す
    if ok and (best is None or f_number < best[0]):
        best = (f_number, D, lat, axi)

print('')
if best:
    f_number, D, lat, axi = best
    print('[推奨] F#=%.1f  開口 D=%.1f mm  曲率半径 R=%.1f mm' % (f_number, D, R_MM))
    print('       焦点 側方FWHM~%.1f mm / 軸方向FWHM~%.1f mm' % (lat, axi))
    print('       → 側方は ROI 径 %.0f mm に収まり、開口は側頭窓 %.0f mm 内。'
          % (ROI_DIAM_MM, D_MAX_MM))
    print('       軸方向は葉巻型で長い（TUS 固有）＝ROI を軸方向に貫く形。4-6 で軸ズレ量を定量。')
else:
    print('[推奨] 窓とROIの両制約を満たす F# が無い。D_MAX か焦点深さの前提を見直す。')

print('')
print('[配置] 焦点座標 = ROI 中心 (99.1, 295.0, 1562.2) mm。トランスデューサ面はその点から')
print('       頭皮 T7 側へ R=%.0f mm 離した位置に、面の法線が焦点を向くように置く。' % R_MM)
print('[作成] lec7 の「球→殻→キャップ」Boolean レシピを流用（半径 R の球殻を ROI 中心基準で作り、')
print('       T7 方向の開口 D 分だけ残してキャップ化）。詳細レシピは Sim4life-lec7 ノート。')
