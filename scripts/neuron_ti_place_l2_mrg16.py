"""#16 L2 ③-1: tTIS 用に、MorphoSONIC と同じ形の MRG 16 µm 軸索を 7 本置く（Sim4Life.lite Python コンソール）。2026-10-16。

形は MorphoSONIC の MRGFiber(16 µm)（McIntyre 2002 の表）に合わせて直接入れる。
Sim4Life の既定（直径からの式）とは最大 3% 違う（`scripts/archive/neuron_ti_props_probe2.py`）ので、
実装の突き合わせ（L2 ④）で形の違いが混ざらないよう、形は同じにする。
  NodeNodeSeparation 1500・NodeDiameter 5.5・MYSADiameter 5.5・FLUT/STINDiameter 12.7・FLUTLength 60・
  STINLength 228.8333・NumberOfMyelinLamellae 150（MYSALength 3・NodeLength 1・InternodeCount 6 は既定のまま）
線の長さは 9.0 mm（中心 ±4.5 mm）。間隔 1.5 mm で節が 7 個、両端と中心に節が来て、MorphoSONIC の 7 節（-4.5〜+4.5 mm）と同じ位置になる。
場所と向きは TUS と同じ 7 本（標的 target・標的外 offA x/y/z・offB y）。名前の頭に m16_ を付けて、旧い軸索と区別する。

2026-10-17 改訂: 1 回目は `props.NodeNodeSeparation = 1500.0` で "property … has no setter"（AxonDiameter は入った）。
  そこで、属性で入らない値は Children（XCore.PropertyReal）の Value で入れてみて、入ったかを 1 行ずつ表示する。
  節の間隔が 1500 に入らなかった場合も 7 節が線に収まるよう、線の半分の長さを「3 × 実際の間隔」にする。

結果（2026-10-17・2 回目）: 8 個の値はすべて Children の Value で入った（now = want・入れ方 child）。
  half = 4.5000 mm、created: 7（m16_target_x/y/z・m16_offA_x/y/z・m16_offB_y がすべて [Motor MRG Neuron 16.00um] True）。

この後の GUI 操作は、手順を別に伝える（旧い 6 本を設定から外し、この 7 本を入れて Run）。
"""
import s4l_v1.model as model
from s4l_v1 import Vec3

lines_def = [
    ("m16_target_x", (99.1, 295.0, 1562.2), (1, 0, 0)),
    ("m16_target_y", (99.1, 295.0, 1562.2), (0, 1, 0)),
    ("m16_target_z", (99.1, 295.0, 1562.2), (0, 0, 1)),
    ("m16_offA_x", (73.5, 266.5, 1512.5), (1, 0, 0)),
    ("m16_offA_y", (73.5, 266.5, 1512.5), (0, 1, 0)),
    ("m16_offA_z", (73.5, 266.5, 1512.5), (0, 0, 1)),
    ("m16_offB_y", (75.5, 264.5, 1509.5), (0, 1, 0)),
]

want = [
    ("NodeNodeSeparation", 1500.0),
    ("NodeDiameter", 5.5),
    ("MYSADiameter", 5.5),
    ("FLUTDiameter", 12.7),
    ("STINDiameter", 12.7),
    ("FLUTLength", 60.0),
    ("STINLength", (1500.0 - 1.0 - 2 * 3.0 - 2 * 60.0) / 6),
    ("NumberOfMyelinLamellae", 150),
]

props = model.MotorMrgNeuronProperties()
props.AxonDiameter = 16.0

def try_set(k, v):
    try:
        setattr(props, k, v)
        return "attr"
    except Exception:
        pass
    for c in props.Children:
        tags = [str(getattr(c, a, "")) for a in ("Name", "Description")]
        if any(t.replace(" ", "").replace("-", "").lower() == k.lower() for t in tags):
            try:
                c.Value = v
                return "child"
            except Exception as e:
                return "child-fail %r" % e
    return "no-setter"

for k, v in want:
    how = try_set(k, v)
    print("[props] %-24s want %10.4f  now %10.4f  (%s)" % (k, v, getattr(props, k), how))
print("[props] %-24s %.4f" % ("AxonDiameter", props.AxonDiameter))
print("[props] %-24s %.4f" % ("InternodeCount", props.InternodeCount))
for c in props.Children:
    print("[child] %r %r %r" % (getattr(c, "Name", None), getattr(c, "Description", None), getattr(c, "Value", None)))

half = 3 * props.NodeNodeSeparation / 1000.0
print("[line] half = %.4f mm (7 nodes at -3..+3 separations)" % half)

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
