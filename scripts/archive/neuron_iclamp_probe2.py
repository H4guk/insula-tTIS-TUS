"""#16 L2 ④ 下調べ 2（Sim4Life 側）: AddIClampPointProcess の引数と、IClamp の設定項目（位置・遅れ・長さ・強さ）を調べる。

TI_Neuron には何も足さない（読むだけ）。関数の説明文と、IClampPointProcessSettings の属性・Children を表示する。

結果（2026-10-18）: AddIClampPointProcess(entity_or_simcomponent) → IClampPointProcessSettings（docstring は無い）。
設定は Amplitude（nA）・Delay（ms）・Duration（ms）・RelativePosition（既定 0.5）・SectionName（選択肢・既定 None）。
`ic.Children` は無く AttributeError で止まった（中身は raw.Children）ので、Titration の項目までは見ていない。
"""
import inspect
import s4l_v1.document as document
import s4l_v1.simulation.neuron as neuron

sim = [s for s in document.AllSimulations if s.Name == "TI_Neuron"][0]
f = sim.AddIClampPointProcess
print("[doc AddIClampPointProcess]", f.__doc__)
try:
    print("[sig]", inspect.signature(f))
except Exception as e:
    print("[sig] n/a", e)

ic = neuron.IClampPointProcessSettings()
for n in sorted(dir(ic)):
    if n.startswith("_"):
        continue
    try:
        v = getattr(ic, n)
    except Exception as e:
        v = "<%s>" % e
    if not callable(v):
        print("[attr]", n, "=", v)
for c in ic.Children:
    try:
        print("[child]", c.Name, "=", getattr(c, "Value", None), getattr(c, "Unit", ""))
    except Exception as e:
        print("[child] ?", e)

for n in sorted(dir(sim.SolverSettings)):
    if "titr" in n.lower():
        print("[solver]", n, "=", getattr(sim.SolverSettings, n))
