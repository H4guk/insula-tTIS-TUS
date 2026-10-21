"""#16 ① tTIS の神経レベル比較: `TI_Neuron` の Titration の結果を読む（Sim4Life.lite Python コンソール・読み取りのみ）。

`neuron_ti_create.py` → `neuron_ti_place_axons.py` → GUI で Source / Solver / Setup を設定 → センサー追加 → Run の後に実行する。

設定（2026-10-13）:
  - Source 1 ← tTIS_LF1: Sinusoidal 2000 Hz・振幅 0.2056・半周期 400・開始 0
  - Source 2 ← tTIS_LF2: Sinusoidal 2010 Hz・振幅 0.3316・半周期 402・開始 0
    （振幅＝Inoue 2025 の 0.891 / 1.109 mA ÷ 1 V 駆動時の 4.334 / 3.344 mA。`current_scale.py` の I = 2P/V）
  - Solver: Duration 110 ms・Time Step 0.0025 ms
  - Setup: Perform Titration on・NEURON・収束 1%・Threshold
  - センサー: `sim.AddOverallLineSensor()`

読み方:
  - `res["Titration Sensor"]["Titration"].Data.DataJson` に神経ごとの titration_factor（1 倍＝合計 2 mA）。1 未満なら 2 mA で発火する。
  - `.keys()` は DEPRECATED（`.DataSimpleDataCollection.Keys()` を使う）。`.Value` は無い。
  - 位置は m 単位（0.0485 = 48.5 mm）、時刻は s 単位。

結果（2026-10-13・計算 10分32秒）:
  offtarget  x 45.5 / y 15.0 / z 6.375  （最小 6.375）
  target     x 32.25 / y 47.75 / z 128.0（最小 32.25）
"""
import json
import s4l_v1.document as document

sim = document.AllSimulations["TI_Neuron"]
res = sim.Results()
for k in ("Titration Sensor", "Action Potential Sensor"):
    res[k].UpdateAll()

tit = json.loads(res["Titration Sensor"]["Titration"].Data.DataJson)
print("%-42s %10s %12s %s" % ("neuron", "factor", "t_first[ms]", "where"))
for n in tit["neuron_titrations"]:
    print("%-42s %10.4g %12.3f %s %s" % (
        n["neuron_name"], n["titration_factor"], n["time_of_first_spike"] * 1e3,
        n["location_of_first_spike"], [round(p * 1e3, 2) for p in n["position_of_first_spike"]]))

for site in ("target", "offtarget"):
    fs = [n["titration_factor"] for n in tit["neuron_titrations"] if n["neuron_name"].startswith(site + "_")]
    print("%-10s min factor = %.4g  (fires at 2 mA: %s)" % (site, min(fs), min(fs) < 1))

print(res["Titration Sensor"]["Titration"].Data.DataJson)
