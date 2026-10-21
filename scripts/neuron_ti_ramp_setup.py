"""#16 L2 ⑤: TI_Neuron の Source 2 つを（PulseType Vectors で）、正弦波 × ランプ（ゆっくり立ち上げて、保って、ゆっくり下げる）の波形に替える。

2010 Hz に直した後の titration（2026-10-19）では、MRG 16 µm の 7 本のうち 4 本が刺激の始まり（1〜7 ms）で発火し、
倍率は 2000 Hz のときと同じだった＝2 kHz の立ち上がりで発火していて、TI の包絡ではない。
Sundt は刺激が終わった直後（101〜104 ms）の発火も多い。ランプで始まりと終わりの急な変化を消し、包絡だけで発火する倍率を出す。

波形: 振幅 × sin(2π f t) × ramp(t)。ramp は 0〜50 ms で 0 → 1、50〜200 ms は 1、200〜250 ms で 1 → 0（直線）。
包絡 |cos(2π·5t)| の山（100・200 ms）と、2 つの場が逆向きの所の山（150 ms）が全振幅のところに入る。
振幅と周波数は今の Sinusoidal の値（AmplitudeSine・FrequencySine）をそのまま使う。点の間隔は 10 µs（2010 Hz の 1 周期に約 50 点）。

使い方: TI_Neuron の Clear Results をしてから実行する（結果が付いていると代入が黙って無視される・2026-10-18）。
代入の後に読み直し、入らなければ NOT SET と出す。Solver の Duration（ms・今 110）を 260 にする。

入れ方（2026-10-19・`archive/neuron_ramp_vector_probe.py`）: TimeVector・ModulationVector は numpy 配列・リストでは
例外なしで黙って入らず、タプルなら入る。Duration は Setup ではなく SolverSettings（Solver）にある。
TimeVector の単位: TimeVectorProp.Unit は 'None'（2026-10-19）。raw の子（TimeVector・InitialTime・DurationP1）の Unit を表示し、
ms / s があればそれに合わせる。どれも無ければ ms で入れる（Solver の Duration は ms・DurationP1 の既定 0.1 は 0.1 ms のパルスと読める）。
単位を間違えると波形が 0.25 ms で終わる（または 250 s になる）ので、Run の前に GUI の Source の波形の表示を確かめる。

1 回目（2026-10-19）: PulseType だけ UserDefined に変わり、波形は 0 点のまま（numpy・リストで入れていた）→ タプルに直した。
3 回目（2026-10-19）: raw の単位は InitialTime・DurationP1 が ms、TimeVector は空文字 → ms で入れた。2 つとも ok・25001 点・250 ms・
max 0.2052 / 0.3316・Solver の Duration 110 → 260。mod@100ms が 0 なのは sin(2π·2000·0.1)＝0 だから（どちらの周波数も 100 ms で周期の整数倍）。

4 回目（2026-10-19）: Run が "Error generating user defined pulse. File  does not exist" で止まった。UserDefined は波形のファイルを
読む種類で、TimeVector・ModulationVector を使うのは Vectors と読める → PulseType を Vectors に替えた。file / path を含む項目も表示する。

元に戻すとき: PulseType を Sinusoidal に戻す（周波数・振幅・半周期 400 / 402 は残っている）。
"""
import numpy as np
import s4l_v1.document as document

T_UP, T_HOLD_END, T_END = 50e-3, 200e-3, 250e-3
DT = 10e-6
SOLVER_DURATION_MS = 260.0

sim = [s for s in document.AllSimulations if s.Name == "TI_Neuron"][0]
srcs = [st for st in sim.AllSettings if type(st).__name__ == "SourceSettings"]
freqs = [float(st.FrequencySine) for st in srcs]
print("[sources]", [(st.Name, str(st.PulseType), f, float(st.AmplitudeSine)) for st, f in zip(srcs, freqs)])
if len(srcs) != 2 or abs(freqs[0] - freqs[1]) < 1.0:
    raise SystemExit("stop: need 2 sources with different FrequencySine, got %r" % freqs)

scales = {"ms": 1e3, "s": 1.0}


def time_unit(st):
    found = {}
    for c in st.raw.Children:
        if c.Name in ("TimeVector", "InitialTime", "DurationP1"):
            found[c.Name] = str(getattr(c, "Unit", None))
    print("[%s raw units] %r" % (st.Name, found))
    for k in ("TimeVector", "InitialTime", "DurationP1"):
        if found.get(k) in scales:
            return found[k]
    return "ms"


units = [time_unit(st) for st in srcs]
print("[TimeVector unit used]", units)

t = np.arange(0.0, T_END + DT / 2, DT)
ramp = np.clip(np.minimum(t / T_UP, (T_END - t) / (T_END - T_HOLD_END)), 0.0, 1.0)
i100 = int(round(100e-3 / DT))

for st, f, u in zip(srcs, freqs, units):
    amp = float(st.AmplitudeSine)
    mod = amp * np.sin(2 * np.pi * f * t) * ramp
    try:
        st.PulseType = st.PulseType.enum.Vectors
    except Exception:
        st.PulseType = st.PulseTypeProp.enum.Vectors
    st.TimeVector = tuple(float(x) for x in t * scales[u])
    st.ModulationVector = tuple(float(x) for x in mod)
    tv = np.asarray(st.TimeVector, dtype=float)
    mv = np.asarray(st.ModulationVector, dtype=float)
    ok = str(st.PulseType).endswith("Vectors") and tv.size == t.size and mv.size == t.size
    print("[%s] %s | PulseType %s | f %.1f Hz | amp %.4f | points %d / %d | t_end %.4g %s | max %.4f | mod@100ms %.4f" % (
        st.Name, "ok" if ok else "NOT SET", st.PulseType, f, amp, tv.size, t.size,
        tv[-1] if tv.size else float("nan"), u, np.abs(mv).max() if mv.size else float("nan"),
        mv[i100] if mv.size > i100 else float("nan")))
    print("[%s file-like items] %r" % (st.Name, {n: getattr(st, n) for n in dir(st)
                                                if not n.startswith("_") and not n.endswith("Prop")
                                                and any(k in n.lower() for k in ("file", "path"))}))

solver = [s for s in sim.AllSettings if type(s).__name__ == "SolverSettings"][0]
before = solver.Duration
solver.Duration = SOLVER_DURATION_MS
print("[solver] Duration %r -> %r | TimeStep %r" % (before, solver.Duration, solver.TimeStep))
