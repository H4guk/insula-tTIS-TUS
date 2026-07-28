"""tTIS 本番シミュレーションのパラメータ集約（Montage I / 材料 / BC / グリッド / ROI）。

出典: Yoon-sun 実測（2026-07-21）＋ Inoue 2025 (arXiv:2510.23290) Montage I。
座標は Yoon-sun モデル座標系（単位 mm・原点は足元・+X=前 / +Y=左 / +Z=上）。
scripts/ 各段はこの値を参照する（現状はスクリプトにもハードコードされているため、
リファクタ時の単一の真実として本ファイルを使う）。
"""

# ---- 座標系・ランドマーク（Yoon-sun 実測 2026-07-21）----
AC = (99.1, 259.9, 1562.2)          # 前交連（MNI 原点相当）
MIDLINE_Y = 260.5                    # 正中 Y（両耳の中点）
LANDMARKS = {
    "Nz":  (188.0, 260.5, 1579.0),   # nasion（鼻→額の変曲点。簡易法）
    "Iz":  (9.0,   260.5, 1580.0),   # inion（後端 X 極小）
    "LPA": (96.9,  331.3, 1542.1),   # 左耳介前点
    "RPA": (92.7,  192.0, 1532.4),   # 右耳介前点
}

# ---- 頭部の球フィット（電極を10-20で置くための近似球）----
HEAD_SPHERE_CENTER = (96.5, 258.9, 1566.8)
HEAD_SPHERE_RADIUS = 91.0            # mm

# ---- 島皮質 ROI（粗ROI・球）----
# MNI ±38mm を Yoon-sun 脳幅で補正（127/140=0.91 → ±34.5mm）。左島皮質が標的。
INSULA_ROI_LEFT = {"center_mm": (99.1, 295.0, 1562.2), "radius_mm": 10.0}

# ---- Montage I（Inoue 2025・島皮質狙い最頻・focality 最良）----
# 電極中心の最終座標（実皮膚表面へ投影後）。
ELECTRODES = {
    "T7":  (94.8,  335.6, 1536.5),   # 左側頭（耳の上）
    "P7":  (41.7,  329.5, 1546.1),   # 左後側頭
    "Fp1": (184.3, 286.8, 1566.1),   # 左前頭極
    "Fp2": (184.2, 235.5, 1562.4),   # 右前頭極
}
PAIR1 = ("T7", "P7")                 # 2000 Hz 相当
PAIR2 = ("Fp1", "Fp2")               # 2010 Hz 相当
CURRENT_MA = {"I1": 0.891, "I2": 1.109}   # 群レベル最適（I1+I2 = 2 mA）

# 電極パッド（円板ソリッド）
ELECTRODE_RADIUS_MM = 10.0           # 直径 20mm ≈ Inoue の 20mm 角と同面積
ELECTRODE_DEPTH_IN_MM = 1.5          # 皮膚へのめり込み（接触保証）
ELECTRODE_DEPTH_OUT_MM = 2.0         # 外側の厚み

# ---- 駆動周波数（TI は 2 つの近接周波数で差の包絡線を作る）----
FREQ_PAIR1_HZ = 2000.0
FREQ_PAIR2_HZ = 2010.0

# ---- グリッド（頭部だけ精細・体は粗く）----
GRID_BOX_MIN = (4.0, 162.0, 1450.0)  # 頭部 envelope + 10mm マージン
GRID_BOX_MAX = (202.0, 352.0, 1665.0)
GRID_STEP_HEAD_MM = 1.0
GRID_STEP_BODY_MM = 5.0

# ---- 材料 σ（IT'IS LF DB 自動リンク・assign_materials.py 参照）----
# ⚠️ 未検証の候補メモ（実機では未適用）:
#   tES 文献では実効頭皮 σ に 0.465 S/m（SimNIBS/ROAST 標準）を使うことがある。
#   ただし Yoon-sun 実機でこの上書きが必要か・値が妥当かは未確認。
#   現状のスクリプトは DB リンクした σ をそのまま使う（上書きしない）。
#   材料σが効かない（no lossy dielectrics）問題の解決とは別軸なので、実機確定後に判断する。
# SKIN_CONDUCTIVITY_OVERRIDE = 0.465   # S/m（候補・未適用）
# SKIN_ENTITIES = ("Skin", "Ear_skin_left", "Ear_skin_right")

# ---- 照合先（先行研究 Inoue 2025）----
SELECTIVITY_REFERENCE = 0.40         # 非標的平均 / 標的平均（Montage I ≈0.40）
ACTIVATION_THRESHOLD_VM = 0.3        # 活性化閾値 V/m（0.2–0.5 の中点）
