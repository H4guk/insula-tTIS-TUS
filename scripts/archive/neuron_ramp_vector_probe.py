"""#16 L2 ⑤: UserDefined の TimeVector・ModulationVector に値を入れる方法を探す（TI_Neuron の Source Settings だけを触る）。

2026-10-19: `neuron_ti_ramp_setup.py` で PulseType は UserDefined に変わったが、TimeVector・ModulationVector は
numpy 配列でもリストでも 0 点のまま（例外は出ずに黙って入らない）。Setup に Duration の項目も無かった。

やること:
  1. TimeVector の今の値の型と、TimeVectorProp の属性を表示する
  2. 3 点だけの短い配列で、入れ方を順に試し、入ったかを読み直す
     （そのまま代入・float32・タプル・Prop.Value・Prop.SetValue・raw の子）
  3. sim.AllSettings の各設定の中で duration / time を含む項目を表示する（Solver の Duration の場所を探す）

結果（2026-10-19）: TimeVector は list、TimeVectorProp は QuantitySequence（Unit・Value・set などがある）。
入ったのはタプルの代入だけ（size 3）。numpy float64・float32・Prop.Value は例外なしで 0 のまま。SetValue は無い。
raw の子 TimeVector・ModulationVector は PropertyRealVector。Duration は SolverSettings（Solver）にあり 110.0（ms）・TimeStep 0.0025。
Source Settings には DurationP1・DurationP2（0.1）・InitialTime（0.0）もある。この probe で Source Settings の TimeVector に 3 点が入ったまま。
"""
import numpy as np
import s4l_v1.document as document

sim = [s for s in document.AllSimulations if s.Name == "TI_Neuron"][0]
st = [s for s in sim.AllSettings if type(s).__name__ == "SourceSettings"][0]
print("[source]", st.Name, st.PulseType)

v = st.TimeVector
print("[TimeVector] type %s | repr %r" % (type(v).__name__, v))
p = getattr(st, "TimeVectorProp", None)
print("[TimeVectorProp] type %s" % type(p).__name__)
if p is not None:
    print("[TimeVectorProp attrs]", [n for n in dir(p) if not n.startswith("_")])

t3 = np.array([0.0, 1e-3, 2e-3])


def size_now():
    try:
        return np.asarray(st.TimeVector, dtype=float).size
    except Exception as e:
        return "read error %r" % e


trials = [
    ("attr float64", lambda: setattr(st, "TimeVector", t3)),
    ("attr float32", lambda: setattr(st, "TimeVector", t3.astype(np.float32))),
    ("attr tuple", lambda: setattr(st, "TimeVector", tuple(t3.tolist()))),
    ("Prop.Value", lambda: setattr(p, "Value", t3)),
    ("Prop.SetValue", lambda: p.SetValue(t3)),
]
for name, fn in trials:
    try:
        fn()
        print("[try %-14s] no error | size %s" % (name, size_now()))
    except Exception as e:
        print("[try %-14s] error %r" % (name, e))

raw = getattr(st, "raw", None)
if raw is not None:
    for c in raw.Children:
        if "time" in str(c.Name).lower() or "modulation" in str(c.Name).lower():
            print("[raw child] %s | type %s | attrs %s" % (
                c.Name, type(c).__name__, [n for n in dir(c) if not n.startswith("_")][:40]))

for s in sim.AllSettings:
    items = [n for n in dir(s) if not n.startswith("_") and not n.endswith("Prop")
             and any(k in n.lower() for k in ("duration", "time"))]
    if items:
        vals = []
        for n in items:
            try:
                vals.append("%s=%r" % (n, getattr(s, n)))
            except Exception as e:
                vals.append("%s=<%s>" % (n, e))
        print("[%s | %s] %s" % (type(s).__name__, s.Name, " ".join(vals)[:300]))
