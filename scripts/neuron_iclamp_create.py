"""#16 L2 ④ 実装の突き合わせ（Sim4Life 側）: IClamp だけで刺激する Neuron シミュレーション `IClamp_Neuron` を作る。

TI_Neuron には触らない。電場の Source はつながない（細胞内電流だけで発火させる）。
軸索は m16_target_x と sun_target_x の 2 本（MorphoSONIC の `scripts/neuron_iclamp_morpho.py` と同じ形）。

やること:
  1. `IClamp_Neuron` を作る（既にあればそれを使う）
  2. 2 本の軸索それぞれに `AddIClampPointProcess(軸索)` で IClamp を 1 つ足す
     遅れ 5 ms・長さ 0.1 ms・強さは MorphoSONIC の閾値（MRG 1.455 nA・Sundt 0.715 nA）
  3. IClamp の「区画の名前」の選択肢を表示し、中央の区画（MRG は node[3]・Sundt は 456 区画の中央）に合わせる

API の注意（2026-10-18）: IClampPointProcessSettings は Amplitude（nA）・Delay（ms）・Duration（ms）・
RelativePosition（0〜1）・SectionName（選択肢）を持つ。Children は無い（raw.Children にある）。

結果（2026-10-18）: `created: IClamp_Neuron`。2 本とも IClamp が付き、SectionName は文字列でそのまま入った
（m16_target_x → node[3]・sun_target_x → section[228]・rel 0.5・遅れ 5 ms・0.1 ms・1.455 / 0.715 nA）。
選択肢の一覧は SectionNameProp から取れなかった（options=0）が、設定には効いている。
Run（Titration on）は "Error executing titration procedure: No external source available" で失敗。
Titration は電場の Source が無いと動かない → `neuron_iclamp_sweep_setup.py`（強さを 5 段に振る）に切り替えた。
ログで分かったこと: Sim4Life の MRG 16 µm の形は MorphoSONIC と一致（間隔 1500・節 5.5・FLUT 60 / 12.7・STIN 228.83 / 12.7・150 枚）、
発火の判定は "Depolarization threshold 60.0"（mV の上昇幅と思われる）。
"""
import s4l_v1.document as document
import s4l_v1.model as model
import s4l_v1.simulation.neuron as neuron

targets = [("m16_target_x", 1.455, "node[3]"), ("sun_target_x", 0.715, "section[228]")]

sims = [s for s in document.AllSimulations if s.Name == "IClamp_Neuron"]
if sims:
    sim = sims[0]
    print("found:", sim.Name)
else:
    sim = neuron.Simulation()
    sim.Name = "IClamp_Neuron"
    document.AllSimulations.Add(sim)
    print("created:", sim.Name)

ents = {e.Name: e for e in model.AllEntities() if model.IsNeuron(e)}
for prefix, amp, want_sec in targets:
    hits = [n for n in ents if n.startswith(prefix + " ")]
    if not hits:
        print("[%s] neuron not found" % prefix)
        continue
    ent = ents[hits[0]]
    try:
        ic = sim.AddIClampPointProcess(ent)
    except Exception as e:
        print("[%s] add error: %r" % (prefix, e))
        continue
    ic.Name = "IClamp " + prefix
    ic.Delay = 5.0
    ic.Duration = 0.1
    ic.Amplitude = amp
    p = ic.SectionNameProp
    opts = []
    for k in ("Enum", "Options", "Values"):
        if hasattr(p, k):
            try:
                opts = list(getattr(p, k))
                break
            except Exception:
                pass
    print("[%s] neuron=%s options=%d first=%s last=%s" % (prefix, hits[0], len(opts), opts[:3], opts[-3:]))
    if not opts:
        print("[%s] SectionNameProp attrs: %s" % (prefix, [n for n in dir(p) if not n.startswith("_")]))
    try:
        ic.SectionName = want_sec
    except Exception as e:
        print("[%s] SectionName set error: %r" % (prefix, e))
    print("[%s] section=%s rel=%s delay=%s dur=%s amp=%s" % (
        prefix, ic.SectionName, ic.RelativePosition, ic.Delay, ic.Duration, ic.Amplitude))
