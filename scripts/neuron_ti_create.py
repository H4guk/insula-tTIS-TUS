"""#16 ① tTIS の神経レベル比較: Neuron シミュレーションを作り、2ペアの場をつなぐ（Sim4Life.lite Python コンソール）。

統合版プロジェクト（`docs/reproduce-integrated.md`）で `tTIS_LF1`・`tTIS_LF2` を Run 済みの前提。

やること:
  Neuron シミュレーション `TI_Neuron` を作り、`AddSource` で
  Source 1 ← `tTIS_LF1` の Overall Field、Source 2 ← `tTIS_LF2` の Overall Field をつなぐ。
  tutorial と違い、ペアごとに別の場をつなぐ（うなりの深さが場所ごとに変わる＝TI の本体）。

波形（2000 / 2010 Hz の Sinusoidal）と振幅（電流のスケール）は GUI の Source 設定で別に入れる。
**Source Settings 1 の周波数が 2010 Hz になっているかを必ず確かめる**（2026-10-18: 2000 Hz のままで、TI ではなく 2 kHz の刺激になっていた・docs/phase6-neuron.md §6）。

API の注意（2026-10-13 に確認）:
  - Source は `sim.AddSource(em_sim, "Overall Field")` で EM とつながる（GUI のドラッグではつながらない）。
  - 神経の設定は `sim.Add(設定, [エンティティ])` だと型によらず `incompatible with this type of simulation`
    で失敗する。神経は GUI のドラッグで設定に入れる（`archive/neuron_ti_place_axons.py`）。

結果（2026-10-13）: `created: Simulation | TI_Neuron` / `source linked: tTIS_LF1` / `source linked: tTIS_LF2`
"""
import s4l_v1.document as document
import s4l_v1.simulation.neuron as neuron

lf1 = document.AllSimulations["tTIS_LF1"]
lf2 = document.AllSimulations["tTIS_LF2"]

try:
    sim = neuron.Simulation()
    sim.Name = "TI_Neuron"
    document.AllSimulations.Add(sim)
    print("created:", type(sim).__name__, "|", sim.Name)
except Exception as e:
    print("create error:", repr(e))
    sim = None

if sim is not None:
    for em in (lf1, lf2):
        try:
            sim.AddSource(em, "Overall Field")
            print("source linked:", em.Name)
        except Exception as e:
            print("source error:", em.Name, repr(e))
