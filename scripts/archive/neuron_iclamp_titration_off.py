"""#16 L2 ④: IClamp_Neuron の Titration を off にする（Setup の "Perform titration"）。

2026-10-18: GUI で off にしたつもりでも、ログの Setup が "Perform titration: 1" のままで、
"No external source available" で失敗した。Setup の中の titration を含む項目を表示し、False にする。
"""
import s4l_v1.document as document

sim = [s for s in document.AllSimulations if s.Name == "IClamp_Neuron"][0]
setup = sim.SetupSettings
hits = [n for n in dir(setup) if "titr" in n.lower() and not n.endswith("Prop")]
print("[setup] titration items:", hits)
for n in hits:
    v = getattr(setup, n)
    if isinstance(v, bool):
        setattr(setup, n, False)
    print("[setup] %s: %r -> %r" % (n, v, getattr(setup, n)))
print("[setup] all:", [n for n in dir(setup) if not n.startswith("_") and not n.endswith("Prop")])
