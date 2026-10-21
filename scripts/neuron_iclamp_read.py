"""#16 L2 ④ 実装の突き合わせ（Sim4Life 側）: IClamp_Neuron の結果を読み、どの強さで端まで発火が届いたかを出す。

Sim4Life が自動で付ける Action Potential Sensor（区画ごとの spike 時刻の JSON）を使う。
Point Sensor の v は FloatXYData で GetComponentArray が無いので使わない（2026-10-18）。
神経ごとに、spike した区画の数・刺激した区画（最初に spike した区画）の時刻・端（node[0] / section[0]）の時刻を表示する。
"""
import json
import s4l_v1.document as document

sim = document.AllSimulations["IClamp_Neuron"]
res = sim.Results()
res["Action Potential Sensor"].UpdateAll()
raw = res["Action Potential Sensor"]["Action Potential"].Data.DataJson
for n in json.loads(raw)["neuron_action_potentials"]:
    sp = n["spiking_times_per_section"]
    if not sp:
        print("%-46s no spike" % n["neuron_name"])
        continue
    first = min(sp, key=lambda k: sp[k][0])
    end = "node[0]" if "node[0]" in sp else "section[0]"
    t_end = sp[end][0] * 1e3 if end in sp else float("nan")
    print("%-46s spiking sections %4d | first %s %.3f ms | end %s %.3f ms" % (
        n["neuron_name"], len(sp), first, sp[first][0] * 1e3, end, t_end))
