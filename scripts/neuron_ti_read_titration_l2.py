"""#16 L2 ③: `TI_Neuron` の Titration の結果を読む（Sim4Life.lite Python コンソール・読み取りのみ）。2026-10-17。

`archive/neuron_ti_read_titration.py`（10/13）は神経の名前が target_ / offtarget_ で始まる前提で地点ごとの最小を出していたので、
L2 の名前（m16_… ・ sun_…）でも読めるように、まとめの行を除いて全部の神経を出すだけにした。
倍率 titration_factor は 1 倍 = 合計 2 mA。1 未満なら 2 mA で発火する。位置は mm、時刻は ms に直して出す。
最後の行の JSON をそのまま results/ に保存する。
"""
import json
import s4l_v1.document as document

sim = document.AllSimulations["TI_Neuron"]
res = sim.Results()
for k in ("Titration Sensor", "Action Potential Sensor"):
    res[k].UpdateAll()

raw = res["Titration Sensor"]["Titration"].Data.DataJson
tit = json.loads(raw)
print("%-42s %10s %12s %s" % ("neuron", "factor", "t_first[ms]", "where"))
for n in tit["neuron_titrations"]:
    print("%-42s %10.4g %12.3f %s %s" % (
        n["neuron_name"], n["titration_factor"], n["time_of_first_spike"] * 1e3,
        n["location_of_first_spike"], [round(p * 1e3, 2) for p in n["position_of_first_spike"]]))
print(raw)
