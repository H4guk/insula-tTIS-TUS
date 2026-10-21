"""#16 L2 ④: IClamp_Neuron の IClamp と Point Sensor の今の設定を表示する（何も変えない）。

2026-10-18: 振り直し（neuron_iclamp_set_amps.py）の後の Run でも、結果が 1 回目と区画の時刻まで同じだった。
強さが本当に変わったか（MRG 2.18〜14.55 nA になっているか）と、どの区画に付いているかを確かめる。

結果（2026-10-18）: MRG の強さは 1.1640〜1.8188 nA のまま（振り直しが効いていなかった）。PerformTitration False。
結果が付いていて設定に鍵がかかっていたため、代入が黙って無視されたと考えられる。
"""
import s4l_v1.document as document

sim = [s for s in document.AllSimulations if s.Name == "IClamp_Neuron"][0]
for st in sim.AllSettings:
    t = type(st).__name__
    if t == "IClampPointProcessSettings":
        print("%-22s section=%-14s rel=%.2f delay=%.2f dur=%.3f amp=%.4f nA" % (
            st.Name, st.SectionName, st.RelativePosition, st.Delay, st.Duration, st.Amplitude))
    elif t == "SetupSettings":
        print("[setup]", {n: getattr(st, n) for n in dir(st) if "titr" in n.lower() and not n.endswith("Prop")})
