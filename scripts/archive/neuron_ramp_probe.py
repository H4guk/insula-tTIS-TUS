"""#16 L2 ⑤ 下調べ: TI_Neuron の Source の波形に「ランプ（ゆっくり立ち上げる）」をかける手段があるかを調べる（読むだけ）。

TI_Neuron の Source Settings 2 つの、今の値（波形の種類・周波数・振幅など）と、波形の種類の選択肢を表示する。
選択肢に User Defined（任意波形）や包絡・ランプの項目があれば、それでランプをかける。

結果（2026-10-18）:
  - PulseType の選択肢: Monopolar / Bipolar / Sinusoidal / UserDefined / Vectors。UserDefined には TimeVector と
    ModulationVector（今は空）がある → 任意の波形（正弦波 × ランプ）を入れられる見込み。
  - ★ Source Settings（AmplitudeSine 0.2056）も Source Settings 1（0.3316）も FrequencySine = 2000.0 だった。
    半周期の数は 400 と 402。docs/phase6-neuron.md §2-1 の「2000 / 2010 Hz」と違い、2 つ目が 2010 Hz になっていない。
    このままだと 2 つの Source は同じ 2000 Hz で、10 Hz のうなり（TI の包絡）が出ない。
"""
import s4l_v1.document as document

sim = [s for s in document.AllSimulations if s.Name == "TI_Neuron"][0]
for st in sim.AllSettings:
    if type(st).__name__ != "SourceSettings":
        continue
    print("=== %s" % st.Name)
    for n in sorted(dir(st)):
        if n.startswith("_") or n.endswith("Prop") or n in ("raw",):
            continue
        try:
            v = getattr(st, n)
        except Exception as e:
            v = "<%s>" % e
        if callable(v):
            continue
        print("  %-32s %r" % (n, v))
        p = getattr(st, n + "Prop", None)
        en = getattr(p, "enum", None) if p is not None else None
        if en is not None:
            try:
                print("  %-32s options: %s" % ("", [str(x) for x in en]))
            except Exception:
                print("  %-32s enum: %r" % ("", en))
    raw = getattr(st, "raw", None)
    if raw is not None:
        print("  raw.Children:", [c.Name for c in raw.Children])
