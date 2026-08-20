"""Phase 4-2 TUS 駆動周波数とグリッド刻みの検算（ローカル実行・Sim4Life 不要）。

音響グリッドの分解能は「最小波長 lambda_min = c_min/f を >=ppw セルで刻む」で決まる。
頭部の最小音速 c_min（脳・CSF ~1500 m/s）が律速（bone は c 大 = lambda 大なので緩い）。
各 f で必要刻み dx = lambda_min/ppw と、頭部 bbox でのセル数を出し、
Lite の 2000万セル上限に収まる f の上限を判定する。

方針: 島皮質 TUS の実文献帯（250-500 kHz）を狙う。
"""

# 頭部バウンディングボックス（tTIS assign_materials.py の GX/GY/GZ 実測 [mm]）
BBOX_MM = (202 - 4, 352 - 162, 1665 - 1450)   # = (198, 190, 215)

C_MIN = 1500.0     # 脳・CSF の最小音速 [m/s]（律速）= 最小波長を与える
C_MAX = 3514.86    # Bone(Cortical) 最大音速 [m/s]（参考：骨内は波長が長く緩い）

CELL_LIMIT = 20_000_000     # Sim4Life.lite のセル上限（tTIS Phase2 は頭部1mm=12.289 MCells 実績）
FREQS_KHZ = (200, 250, 300, 350, 400, 500)
PPW_GATE = 6       # 最低ライン（>=6 cells/lambda）
PPW_COMFY = 10     # 余裕を見た刻み


def cells_for_dx(dx_mm):
    n = 1.0
    for L in BBOX_MM:
        n *= (L / dx_mm)
    return n


print('頭部 bbox = %.0f x %.0f x %.0f mm  (体積 %.0f cm^3)'
      % (BBOX_MM[0], BBOX_MM[1], BBOX_MM[2], BBOX_MM[0] * BBOX_MM[1] * BBOX_MM[2] / 1000.0))
print('c_min=%.0f m/s（律速）  セル上限=%s' % (C_MIN, format(CELL_LIMIT, ',')))
print('')
hdr = '%-8s %-10s %-12s %-12s %-14s %-14s'
print(hdr % ('f[kHz]', 'lambda[mm]', 'dx@6ppw[mm]', 'dx@10ppw[mm]', 'cells@6ppw', 'cells@10ppw'))
print('-' * 74)

feasible_6, feasible_10 = [], []
for fk in FREQS_KHZ:
    f = fk * 1e3
    lam_mm = C_MIN / f * 1e3           # lambda[mm] = c/f * 1000
    dx6 = lam_mm / PPW_GATE
    dx10 = lam_mm / PPW_COMFY
    c6 = cells_for_dx(dx6)
    c10 = cells_for_dx(dx10)
    tag6 = 'OK' if c6 <= CELL_LIMIT else 'OVER'
    tag10 = 'OK' if c10 <= CELL_LIMIT else 'OVER'
    if c6 <= CELL_LIMIT:
        feasible_6.append(fk)
    if c10 <= CELL_LIMIT:
        feasible_10.append(fk)
    print('%-8d %-10.3f %-12.4f %-12.4f %-14s %-14s'
          % (fk, lam_mm, dx6, dx10,
             '%s(%s)' % (format(int(c6), ','), tag6),
             '%s(%s)' % (format(int(c10), ','), tag10)))

print('')
print('[判定] 6ppw で上限内に収まる f: %s kHz' % feasible_6)
print('[判定] 10ppw で上限内に収まる f: %s kHz' % feasible_10)

# 焦点サイズの目安（F#=1 の球面集束の近似）: 側方 FWHM ~ lambda*F#, 軸方向 ~ 7*lambda*F#^2
print('')
print('[焦点] F#=1 での焦点サイズ目安（軟部組織 c=1500）:')
for fk in FREQS_KHZ:
    lam_mm = C_MIN / (fk * 1e3) * 1e3
    print('   f=%3d kHz  lambda=%.2f mm  側方FWHM~%.1f mm  軸方向~%.1f mm'
          % (fk, lam_mm, lam_mm * 1.0, 7 * lam_mm * 1.0))

print('')
print('[参考] ROI は半径10mm 球。焦点の側方径が ~10-20mm に収まる f が望ましい。')
print('[参考] tTIS Phase2 は頭部1mm で 12.289 MCells 実績 → 1mm 相当が実機で通る目安。')
