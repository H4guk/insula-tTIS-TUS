# TI_Neuron の 2 つの Source の「開始（InitialTime）」を 0、「長さ（DurationP1）」を 250 ms にする（Sim4Life.lite Python コンソール）。
# 2026-10-29 prod2: neuron_ti_ramp_setup.py で 250 ms のランプ波形を入れたのに、Show Pulse では開始直後の一瞬にしか出ず、
# MRG の発火が 0.4〜0.5 ms に集まった。作ったばかりの Source は InitialTime 0.1 ms・DurationP1 0.1 ms で、
# Vectors の波形がこの枠に押し込まれたと考えている（10-19 はランプ無しの設定を先に入れていたので、この既定値ではなかった）。
# 先に GUI で TI_Neuron の Clear Results を押す（結果が付いていると代入が黙って無視される）。代入の後に読み直して表示する。
import s4l_v1.document as document

# 2026-10-29 改訂: 1 回目は 4 つとも NOT SET（Run の結果が付いて鍵がかかっていた）。属性で入らなければ raw の子の Value でも入れる。
# PulseType が Vectors でなければ止める（1 回目は Sinusoidal に戻っていた＝ neuron_ti_ramp_setup.py を流し直す）。

WANT = {"InitialTime": 0.0, "DurationP1": 250.0}       # ms

sim = [s for s in document.AllSimulations if s.Name == "TI_Neuron"][0]
srcs = [st for st in sim.AllSettings if type(st).__name__ == "SourceSettings"]
bad = [st.Name for st in srcs if not str(st.PulseType).endswith("Vectors")]
if bad:
    raise SystemExit("stop: PulseType が Vectors でない %r（Clear Results の後に neuron_ti_ramp_setup.py を流し直してから、これを流す）" % bad)
for st in srcs:
    for name, want in WANT.items():
        child = [c for c in st.raw.Children if c.Name == name]
        before = getattr(st, name, None)
        how = "attr"
        try:
            setattr(st, name, want)
        except Exception:
            pass
        now = getattr(st, name, None)
        if (now is None or abs(float(now) - want) > 1e-9) and child:
            how = "child"
            try:
                child[0].Value = want
            except Exception as e:
                print("[%s] %s child error %r" % (st.Name, name, e))
            now = child[0].Value
        unit = str(getattr(child[0], "Unit", "")) if child else "?"
        ok = now is not None and abs(float(now) - want) < 1e-9
        print("[%s] %-11s %r -> %r %s（%s）%s" % (st.Name, name, before, now, unit, how, "" if ok else "NOT SET"))
    print("[%s] PulseType %s | TimeVector %d 点・最後 %.4g" % (
        st.Name, st.PulseType, len(st.TimeVector), st.TimeVector[-1] if len(st.TimeVector) else float("nan")))
print("=== この後 GUI の Show Pulse で、2 つの波形が 0〜250 ms に広がっているかを見る ===")
