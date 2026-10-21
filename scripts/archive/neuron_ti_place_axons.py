"""#16 ① tTIS の神経レベル比較: 標的と標的外に MRG 軸索を3方向ずつ置く（Sim4Life.lite Python コンソール）。

`neuron_ti_create.py` の後に実行する。

置き方:
  - 場所: 標的＝ROI 中心 (99.1, 295.0, 1562.2)（`define_insula_roi.py` と同じ値）
          標的外＝脳内 TI 最大点 (48.5, 274.5, 1482.5)（ROI 中心から 96.6 mm・標的の 10.7 倍。`docs/comparison-framework.md`）
  - 向き: x・y・z の3方向を1本ずつ。発火は軸索と場の向きの関係で大きく変わり、その場所の線維の向きは分からないため。
  - 型: Motor MRG（哺乳類の有髄軸索の標準）。既定の直径は 20 µm（太い＝発火しやすい側）。長さ 10 mm（節は約 10 個）。
  - 計 6 本。Lite の上限は 10 本（`Light version does not support number of neurons over 10.`）。
    同じ HOC の型の神経は1回の Run に1本しか入らない（2本だと `Failed to write neurons to input file.`）ので HOC は使わない。

この後の GUI 操作:
  `TI_Neuron` の `Neurons` を選ぶ → `New Settings ▾` → Automatic Axon Model Settings を作る →
  Multi Tree の `[Motor MRG Neuron …]` が付いた6本（橙のアイコン）をまとめてドラッグ。
  ただの線（`CreatePolyLine` の結果）は軸索の設定に入らない。`CreateAxonNeurons` は線を残したまま神経を別に作る。

結果（2026-10-13）: `created: 6`、target_x/y/z・offtarget_x/y/z が全て `[Motor MRG Neuron 20.00um] True`。
  Automatic Axon Model Settings に6本入った。
"""
import s4l_v1.model as model
from s4l_v1 import Vec3

sites = {"target": (99.1, 295.0, 1562.2), "offtarget": (48.5, 274.5, 1482.5)}
dirs = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
half = 5.0

lines = []
for s, (cx, cy, cz) in sites.items():
    for d, (dx, dy, dz) in dirs.items():
        ln = model.CreatePolyLine([
            Vec3(cx - half * dx, cy - half * dy, cz - half * dz),
            Vec3(cx + half * dx, cy + half * dy, cz + half * dz),
        ])
        ln.Name = "%s_%s" % (s, d)
        lines.append(ln)

try:
    axons = model.CreateAxonNeurons(lines, model.MotorMrgNeuronProperties())
    print("created:", len(axons))
    for a in axons:
        print("  ", a.Name, model.IsNeuron(a))
except Exception as e:
    print("create error:", repr(e))
