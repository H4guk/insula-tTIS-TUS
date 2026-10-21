"""#16 L2 ④ 実装の突き合わせ（Sim4Life 側）: Titration の代わりに、強さを 5 段に振った IClamp を 1 回の Run で回す準備。

Sim4Life の Titration は外部の Source（電場）が無いと動かない（2026-10-18: "No external source available"）。
そこで、同じ形の軸索を 5 本ずつ作り、IClamp の強さを MorphoSONIC の閾値の 0.8・0.9・1.0・1.1・1.25 倍にする。
どの強さから端まで発火が届くかで、Sim4Life の閾値を ±5〜10% の幅で挟む。電場が無いので、軸索の位置は結果に効かない。

やること（IClamp_Neuron の中・TI_Neuron には触らない）:
  1. 前回の IClamp を外す
  2. MRG 16 µm（ic_m16_080〜125）と Sundt 0.8 µm（ic_sun_080〜125）の軸索を 5 本ずつ作る（形は L2 の m16_・sun_ と同じ）
  3. それぞれの中央（node[3]・section[228]）に IClamp（遅れ 5 ms・0.1 ms）
  4. それぞれの端（node[0]・section[0]）に Point Sensor を置き、膜電位を記録する（中央から端まで発火が届いたかを見る）

結果（2026-10-18）: 前回の IClamp 2 つを外し、10 本を作った（MRG の形は 8 項目とも child・Sundt は 2 項目とも attr）。
IClamp は node[3]（1.1640〜1.8188 nA）・section[228]（0.5720〜0.8937 nA）、Point Sensor は node[0]・section[0] に付いた。
PointSensorSettings の項目: RecordV・RecordIMembrane・RecordEExtracellular・SectionName・RelativePosition・Quantity・Group。

この後 GUI で: 10 本を IClamp_Neuron の軸索設定に入れ（m16_target_x・sun_target_x は外す）、Titration を off にして Run。
"""
import s4l_v1.document as document
import s4l_v1.model as model
import s4l_v1.simulation.neuron as neuron
from s4l_v1 import Vec3

factors = [0.8, 0.9, 1.0, 1.1, 1.25]
fibers = {
    "m16": dict(thr=1.455, center="node[3]", end="node[0]", half=4.5),
    "sun": dict(thr=0.715, center="section[228]", end="section[0]", half=5.0),
}

sim = [s for s in document.AllSimulations if s.Name == "IClamp_Neuron"][0]
for st in list(sim.AllSettings):
    if type(st).__name__ == "IClampPointProcessSettings":
        sim.RemoveSettings(st)
        print("removed:", st.Name)


def try_set(props, k, v):
    try:
        setattr(props, k, v)
        return "attr"
    except Exception:
        pass
    for c in props.Children:
        if str(getattr(c, "Name", "")).replace(" ", "").replace("-", "").lower() == k.lower():
            c.Value = v
            return "child"
    return "no-setter"


def make_props(key):
    if key == "m16":
        p = model.MotorMrgNeuronProperties()
        p.AxonDiameter = 16.0
        want = [("NodeNodeSeparation", 1500.0), ("NodeDiameter", 5.5), ("MYSADiameter", 5.5),
                ("FLUTDiameter", 12.7), ("STINDiameter", 12.7), ("FLUTLength", 60.0),
                ("STINLength", (1500.0 - 1.0 - 2 * 3.0 - 2 * 60.0) / 6), ("NumberOfMyelinLamellae", 150)]
    else:
        p = model.SundtNeuronProperties()
        want = [("AxonDiameter", 0.8), ("SectionLength", 10000.0 / 456)]
    for k, v in want:
        print("[%s props] %-22s %s" % (key, k, try_set(p, k, v)))
    return p


cx, cy, cz = 120.0, 295.0, 1562.2
for row, (key, f) in enumerate(fibers.items()):
    props = make_props(key)
    lines = []
    for i, fac in enumerate(factors):
        y = cy + 2.0 * (5 * row + i)
        ln = model.CreatePolyLine([Vec3(cx - f["half"], y, cz), Vec3(cx + f["half"], y, cz)])
        ln.Name = "ic_%s_%03d" % (key, round(fac * 100))
        lines.append(ln)
    axons = model.CreateAxonNeurons(lines, props)
    print("[%s] created: %d" % (key, len(axons)))
    for ax, fac in zip(axons, factors):
        ic = sim.AddIClampPointProcess(ax)
        ic.Name = "IClamp " + ax.Name.split(" ")[0]
        ic.SectionName = f["center"]
        ic.Delay = 5.0
        ic.Duration = 0.1
        ic.Amplitude = round(f["thr"] * fac, 4)
        try:
            ps = sim.AddPointSensor(ax)
            ps.Name = "End " + ax.Name.split(" ")[0]
            if hasattr(ps, "SectionName"):
                ps.SectionName = f["end"]
            sens = getattr(ps, "SectionName", "?")
        except Exception as e:
            sens = "sensor error %r" % e
        print("  %-48s IClamp %s %.4f nA | sensor %s" % (ax.Name, ic.SectionName, ic.Amplitude, sens))

ps_attrs = [n for n in dir(neuron.PointSensorSettings()) if not n.startswith("_")]
print("[PointSensorSettings attrs]", ps_attrs)
