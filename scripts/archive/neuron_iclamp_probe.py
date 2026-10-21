"""#16 L2 ④ 下調べ（Sim4Life 側）: 神経シミュレーションに IClamp（Point Process）を Python で置く方法を探す。

TI_Neuron には触らない（読むだけ）。s4l_v1.simulation.neuron の中で Point / Clamp / Stimul / Source を名前に含むものと、
TI_Neuron の Point Processes まわりの属性を表示する。

結果（2026-10-18）: 使える。neuron に IClampPointProcessSettings、シミュレーションに AddIClampPointProcess がある
（ほか VClamp・ExpSyn・Exp2Syn・AlphaSynapse の Point Process、PointSensorSettings・LineSensorSettings）。
TI_Neuron の設定: Setup / Neurons / Automatic Axon Model Settings / Sources（Source Settings ×2）/ Point Processes /
Network Connections / Sensors（Overall Line Sensor Settings）/ Solver。
"""
import s4l_v1.document as document
import s4l_v1.simulation.neuron as neuron

for n in sorted(dir(neuron)):
    if any(k in n.lower() for k in ("point", "clamp", "stimul", "source", "sensor", "titration")):
        print("[neuron]", n)

sim = [s for s in document.AllSimulations if s.Name == "TI_Neuron"][0]
for n in sorted(dir(sim)):
    if not n.startswith("_") and any(k in n.lower() for k in ("point", "add", "source", "setting", "create")):
        print("[sim]", n)
print("[sim] AllSettings:", [type(s).__name__ + ":" + s.Name for s in sim.AllSettings])
