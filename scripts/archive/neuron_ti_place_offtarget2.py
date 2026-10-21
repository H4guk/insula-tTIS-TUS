"""#16 再開 3/5: 選び直した標的外に MRG 軸索を置く（Sim4Life.lite Python コンソール）。2026-10-15。

`neuron_offtarget_search.py` の結果:
  (A) 2.50 倍 @ (73.5, 266.5, 1512.5)・延髄 — x・y・z の 10 mm の線がすべて脳 95% 以上 → 標的と同じ3方向で置く（offA_x/y/z）
  (B) 4.16 倍 @ (75.5, 264.5, 1509.5)・延髄 — y 方向の 10 mm だけ脳 100% → y の1本だけ置く（offB_y）
旧い標的外 offtarget_x/y/z（腱・靭帯 (48.5, 274.5, 1482.5)）は使わない。標的の target_x/y/z はそのまま。
合計は 標的 3＋(A) 3＋(B) 1＝7 本（Lite の上限 10 本以内）。

型・長さは `neuron_ti_place_axons.py` と同じ（Motor MRG・既定の直径 20 µm・10 mm）。
この後の GUI 操作: TI_Neuron の Clear Results → Automatic Axon Model Settings から offtarget_x/y/z を外す →
Multi Tree の `[Motor MRG Neuron …]` が付いた offA_x/y/z・offB_y をドラッグ → 7 本になったら Run。
"""
import s4l_v1.model as model
from s4l_v1 import Vec3

half = 5.0
lines_def = [
    ("offA_x", (73.5, 266.5, 1512.5), (1, 0, 0)),
    ("offA_y", (73.5, 266.5, 1512.5), (0, 1, 0)),
    ("offA_z", (73.5, 266.5, 1512.5), (0, 0, 1)),
    ("offB_y", (75.5, 264.5, 1509.5), (0, 1, 0)),
]

lines = []
for name, (cx, cy, cz), (dx, dy, dz) in lines_def:
    ln = model.CreatePolyLine([
        Vec3(cx - half * dx, cy - half * dy, cz - half * dz),
        Vec3(cx + half * dx, cy + half * dy, cz + half * dz),
    ])
    ln.Name = name
    lines.append(ln)

try:
    axons = model.CreateAxonNeurons(lines, model.MotorMrgNeuronProperties())
    print("created:", len(axons))
    for a in axons:
        print("  ", a.Name, model.IsNeuron(a))
except Exception as e:
    print("create error:", repr(e))
