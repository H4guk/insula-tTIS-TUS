"""#16 L2 ④: IClamp_Neuron の MRG 16 µm の IClamp の強さを振り直す（Sundt はそのまま）。

1 回目（2026-10-18）: MRG は 0.8〜1.25 倍（1.164〜1.819 nA）のどれも発火しなかった → 1.5・2・3・5・10 倍に広げる。
倍率の基準は MorphoSONIC の閾値 1.455 nA（0.1 ms）。

注意（2026-10-18）: 結果が付いている間は設定に鍵がかかり、Amplitude を代入しても黙って元のままになる
（1 回目はこれで強さが変わらなかった）。先に GUI で Clear Results を押してから実行する。
代入した後に読み直して、入らなかったら NOT SET と出す。
"""
import s4l_v1.document as document

thr = 1.455
new = {"ic_m16_080": 1.5, "ic_m16_090": 2.0, "ic_m16_100": 3.0, "ic_m16_110": 5.0, "ic_m16_125": 10.0}
sim = [s for s in document.AllSimulations if s.Name == "IClamp_Neuron"][0]
for st in sim.AllSettings:
    if type(st).__name__ != "IClampPointProcessSettings":
        continue
    key = st.Name.replace("IClamp ", "")
    if key in new:
        want = round(thr * new[key], 4)
        st.Amplitude = want
        ok = abs(st.Amplitude - want) < 1e-6
        print("%-20s x%-5.2f want %.4f now %.4f nA %s" % (st.Name, new[key], want, st.Amplitude, "" if ok else "NOT SET"))
