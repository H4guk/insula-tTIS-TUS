"""③ 電極を座標計算して自動配置（Montage I / 10-20 法・Sim4Life.lite Python コンソール）。

lec6 の教訓「手動の電極配置は精度・再現性が悪い」への解。すべて Python で座標計算 → 生成。

流れ:
  ① 10-20 基準点を取得（nasion / inion / LPA / RPA）
  ② 頭部を球でフィット（中心 O・半径 R）  ← Skin は符号付き距離を返さないので ClosestPosition 方式
  ③ 球面で大円を弧長分割 → T7 / P7 / Fp1 / Fp2 の座標
  ④ 電極中心を実皮膚表面へ投影
  ⑤ 各中心に電極パッド（円板ソリッド）を生成

電極対: ペア1 = T7–P7（左側頭を縦）/ ペア2 = Fp1–Fp2（前頭を横）。
出典ノート: Claude/Knowledge/sim4life-electrode-placement.md ①〜⑤
"""
import s4l_v1.model as model
import XCoreModeling as xc
import numpy as np
import math
import time

skin = [e for e in model.AllEntities() if e.Name == 'Skin'][0]


def closest(P):   # P に最も近い Skin 表面点
    cp = xc.GetEntityPointDistance(skin, model.Vec3(*map(float, P))).ClosestPosition
    try:    return np.array([cp[0], cp[1], cp[2]])
    except: return np.array([cp.X, cp.Y, cp.Z])


def xyz(v):
    try:    return float(v[0]), float(v[1]), float(v[2])
    except: return float(v.X), float(v.Y), float(v.Z)


# ===== ① 10-20 基準点（耳介前点は耳軟骨前縁を皮膚投影）=====
for nm, tag in (('Ear_cartilage_left', 'LPA'), ('Ear_cartilage_right', 'RPA')):
    ent = [e for e in model.AllEntities() if e.Name == nm][0]
    lo, hi = xyz(xc.GetBoundingBox([ent])[0]), xyz(xc.GetBoundingBox([ent])[1])
    sp = closest([hi[0], (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2])
    print(tag, np.round(sp, 1))
# nasion/inion は正中面(Y=260.5)の前後走査で実測済み（下の確定値を使う）。
# nasion は最前点走査では鼻先を拾うので鼻→額の変曲点を採用。

# ===== ② 頭部の球フィット（ClosestPosition 方式）=====
C = np.array([97.0, 260.5, 1562.0])   # 頭内部の中心候補


def fib_dirs(n):                       # フィボナッチ球で方向を均等散布
    ga = math.pi * (3 - math.sqrt(5.0)); out = []
    for i in range(n):
        z = 1 - (i + 0.5) / n * 2; r = math.sqrt(max(0.0, 1 - z * z)); th = ga * i
        out.append(np.array([r * math.cos(th), r * math.sin(th), z]))
    return out


t0 = time.time(); surf = []
for d in fib_dirs(80):
    sp = closest(C + 200.0 * d)        # 頭より十分外側の点の最近傍表面点
    if sp[2] >= 1500.0:                # 頭蓋の丸い部分だけ（顎・首を除外）
        surf.append(sp)
surf = np.unique(np.round(np.array(surf), 1), axis=0)

A = np.c_[2 * surf, np.ones(len(surf))]; b = np.sum(surf ** 2, axis=1)
sol, *_ = np.linalg.lstsq(A, b, rcond=None)      # 線形最小二乗で球フィット
O = sol[:3]; R = math.sqrt(sol[3] + O @ O)
print('中心 O =', np.round(O, 1), ' 半径 R = %.1f' % R, ' 所要 %.0f秒' % (time.time() - t0))
# 実測: O=(96.5, 258.9, 1566.8) / R=91.0mm（残差 mean 4.8 / max 24.6mm）

# ===== ③ 10-20 電極位置（球面で大円を弧長分割）=====
O = np.array([96.5, 258.9, 1566.8]); R = 91.0
Nz = np.array([188.0, 260.5, 1579.0]); Iz = np.array([9.0, 260.5, 1580.0])
LPA = np.array([96.9, 331.3, 1542.1]); RPA = np.array([92.7, 192.0, 1532.4])


def sph(P):                            # 点を頭の球面(中心O・半径R)に乗せる
    u = np.array(P, float) - O; u /= np.linalg.norm(u); return O + R * u


def rot(v, axis, th):                  # Rodrigues 回転
    axis = axis / np.linalg.norm(axis)
    return v * np.cos(th) + np.cross(axis, v) * np.sin(th) + axis * np.dot(axis, v) * (1 - np.cos(th))


def circle3_center(A, B, C):           # 球面上3点を通る円の中心
    A, B, C = sph(A), sph(B), sph(C)
    a2 = np.dot(B - C, B - C); b2 = np.dot(A - C, A - C); c2 = np.dot(A - B, A - B)
    wa = a2 * (b2 + c2 - a2); wb = b2 * (a2 + c2 - b2); wc = c2 * (a2 + b2 - c2)
    return (wa * A + wb * B + wc * C) / (wa + wb + wc)


def arc(A, B, C, fracs):               # A→B→C の弧を A起点で弧長割合分割
    Cc = circle3_center(A, B, C)
    va, vb, vc = sph(A) - Cc, sph(B) - Cc, sph(C) - Cc
    ang = lambda u, v: np.arccos(np.clip(np.dot(u, v) / np.linalg.norm(u) / np.linalg.norm(v), -1, 1))
    total = ang(va, vb) + ang(vb, vc); axis = np.cross(va, vb)
    return [Cc + rot(va, axis, total * f) for f in fracs]


left = arc(Nz, LPA, Iz, [0.1, 0.3, 0.5, 0.7, 0.9])    # Fp1,F7,T7,P7,O1
right = arc(Nz, RPA, Iz, [0.1, 0.3, 0.5, 0.7, 0.9])   # Fp2,F8,T8,P8,O2
elec_sphere = {'T7': left[2], 'P7': left[3], 'Fp1': left[0], 'Fp2': right[0]}
for k, v in elec_sphere.items():
    print('%-4s' % k, np.round(v, 1))

# ===== ④ 電極中心を実皮膚表面へ投影 =====
proj = {}
for k, v in elec_sphere.items():
    sp = closest(v); proj[k] = sp
    print('%-4s → 皮膚(%.1f,%.1f,%.1f) 移動%.1fmm'
          % (k, sp[0], sp[1], sp[2], np.linalg.norm(sp - np.array(v))))

# ===== ⑤ 電極パッドを生成（円板ソリッド・軸は皮膚法線方向）=====
O = np.array([96.5, 258.9, 1566.8])   # 法線の基準


def V(p): return model.Vec3(*map(float, p))


RADIUS = 10.0        # 半径10mm（直径20mm≈Inoue の20mm角と同面積）
D_IN, D_OUT = 1.5, 2.0                 # 皮膚に1.5mmめり込ませ＋外側2mm（接触保証・lec6）
for name, pe in proj.items():
    pe = np.array(pe); n = pe - O; n /= np.linalg.norm(n)   # 皮膚法線（外向き）
    cyl = xc.CreateSolidCylinder(V(pe - n * D_IN), V(pe + n * D_OUT), RADIUS)
    cyl.Name = 'Elec_' + name
    print('作成:', cyl.Name)
