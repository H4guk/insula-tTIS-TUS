"""#16 L2 ③-2: tTIS 用に、MorphoSONIC と同じ Sundt（無髄）軸索を 7 本置く（Sim4Life.lite Python コンソール）。2026-10-17。

MorphoSONIC 側（`neuron_tus_titrate_lines.py`）: UnmyelinatedFiber(0.8 µm, fiberL = 10 mm) → 456 区画・区画の長さ 21.93 µm。
Sim4Life の SundtNeuronProperties は既定で AxonDiameter 0.8（同じ）・SectionLength 50 µm なので、
区画の長さを 10000 / 456 = 21.93 µm にそろえる（Children の Value で入れる。MRG で属性に入らない値があったため）。
線の長さは 10 mm（中心 ±5 mm）。場所と向きは TUS と同じ 7 本。名前の頭に sun_ を付ける。

Lite の神経は 1 回の Run に 10 本までなので、m16_ の 7 本は Automatic Axon Model Settings から外してから入れる
（m16_ の結果は results/invalid/neuron_ti_titration_l2_mrg16_2026-10-17.json に保存済み。2000 Hz の不具合で無効）。

結果（2026-10-17）: AxonDiameter 0.8・SectionLength 21.9298 とも属性で入った（attr）。created: 7（sun_ の 7 本すべて
  [Unmyelinated Sundt Neuron 0.80um] True）。
"""
import s4l_v1.model as model
from s4l_v1 import Vec3

half = 5.0
lines_def = [
    ("sun_target_x", (99.1, 295.0, 1562.2), (1, 0, 0)),
    ("sun_target_y", (99.1, 295.0, 1562.2), (0, 1, 0)),
    ("sun_target_z", (99.1, 295.0, 1562.2), (0, 0, 1)),
    ("sun_offA_x", (73.5, 266.5, 1512.5), (1, 0, 0)),
    ("sun_offA_y", (73.5, 266.5, 1512.5), (0, 1, 0)),
    ("sun_offA_z", (73.5, 266.5, 1512.5), (0, 0, 1)),
    ("sun_offB_y", (75.5, 264.5, 1509.5), (0, 1, 0)),
]

props = model.SundtNeuronProperties()
want = [("AxonDiameter", 0.8), ("SectionLength", 10000.0 / 456)]

def try_set(k, v):
    try:
        setattr(props, k, v)
        return "attr"
    except Exception:
        pass
    for c in props.Children:
        if getattr(c, "Name", None) == k:
            try:
                c.Value = v
                return "child"
            except Exception as e:
                return "child-fail %r" % e
    return "no-setter"

for k, v in want:
    how = try_set(k, v)
    print("[props] %-14s want %10.4f  now %10.4f  (%s)" % (k, v, getattr(props, k), how))

lines = []
for name, (cx, cy, cz), (dx, dy, dz) in lines_def:
    ln = model.CreatePolyLine([
        Vec3(cx - half * dx, cy - half * dy, cz - half * dz),
        Vec3(cx + half * dx, cy + half * dy, cz + half * dz),
    ])
    ln.Name = name
    lines.append(ln)

try:
    axons = model.CreateAxonNeurons(lines, props)
    print("created:", len(axons))
    for a in axons:
        print("  ", a.Name, model.IsNeuron(a))
except Exception as e:
    print("create error:", repr(e))
