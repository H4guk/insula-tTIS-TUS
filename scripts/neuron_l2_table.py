"""#16 L2 ⑥: 神経レベルの結果の表を作る（手元・Sim4Life 不要）。

2 手法 × 7 本（標的 3・標的外 A 3・標的外 B 1）× 線維 2 種（MRG 16 µm・Sundt 0.8 µm）の発火の倍率を 1 つの表にまとめる。
倍率 = 発火に要る強さ ÷ 標準の安全上限での強さ（1 未満なら安全上限の中で発火する）。
  TUS : MorphoSONIC の titration（250 kHz・100 ms）。閾値の音圧 ÷ 安全駆動での線上の最大音圧
  tTIS: Sim4Life の titration。1 倍 = 合計 2 mA。主はランプ付き（50 ms で上げる・250 ms）、ランプ無し（100 ms）も並べる

使う結果（2000 Hz のままだった 10-17 の MRG・10-18 の Sundt と、10-13 の 1 回目は使わない）:
  results/neuron_tus_titrate_lines_2026-10-15.jsonl
  results/neuron_ti_titration_l2_{mrg16,sundt}_2026-10-19.json         ランプ無し（2000 / 2010 Hz）
  results/neuron_ti_titration_l2_mrg16_ramp_2026-10-19.json            ランプ付き
  results/neuron_ti_titration_l2_sundt_ramp_2026-10-21.json            ランプ付き

まとめの「標的外 ÷ 標的」は、標的外の最小の倍率 ÷ 標的の最小の倍率。1 より大きいほど標的の方が発火しやすい（標的を選べる）。

使い方: python3 scripts/neuron_l2_table.py → results/neuron_l2_table_2026-10-21.md
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
OUT = os.path.join(RES, "neuron_l2_table_2026-10-21.md")

LINES = ["target_x", "target_y", "target_z", "offA_x", "offA_y", "offA_z", "offB_y"]
FIBERS = [("mrg16", "m16", "MRG 16 µm"), ("sundt", "sun", "Sundt 0.8 µm")]
TTIS_FILES = {
    ("mrg16", "noramp"): "neuron_ti_titration_l2_mrg16_2026-10-19.json",
    ("mrg16", "ramp"): "neuron_ti_titration_l2_mrg16_ramp_2026-10-19.json",
    ("sundt", "noramp"): "neuron_ti_titration_l2_sundt_2026-10-19.json",
    ("sundt", "ramp"): "neuron_ti_titration_l2_sundt_ramp_2026-10-21.json",
}


def load_tus():
    out = {}
    with open(os.path.join(RES, "neuron_tus_titrate_lines_2026-10-15.jsonl"), encoding="utf-8") as f:
        for row in f:
            if row.startswith("{"):
                d = json.loads(row)
                out[(d["fiber"], d["line"])] = d["factor"]
    return out


def load_ttis():
    out = {}
    for (fiber, kind), name in TTIS_FILES.items():
        prefix = dict((k, p) for k, p, _ in FIBERS)[fiber] + "_"
        with open(os.path.join(RES, name), encoding="utf-8") as f:
            for n in json.load(f)["neuron_titrations"]:
                line = n["neuron_name"].split()[0][len(prefix):]
                out[(fiber, kind, line)] = (n["titration_factor"], n["time_of_first_spike"] * 1e3)
    return out


def fmt(x):
    if x >= 100:
        return "%.0f" % x
    if x >= 10:
        return "%.1f" % x
    return "%.3g" % x


def ratio(factors):
    tgt = min(v for k, v in factors.items() if k.startswith("target"))
    off = min(v for k, v in factors.items() if k.startswith("off"))
    return tgt, off, off / tgt


tus, ttis = load_tus(), load_ttis()
md = ["# #16 L2 神経レベルの結果（2026-10-21・`scripts/neuron_l2_table.py`）", "",
      "倍率 = 発火に要る強さ ÷ 標準の安全上限での強さ（**1 未満なら安全上限の中で発火する**）。"
      "TUS は MorphoSONIC（250 kHz・100 ms・MI<1.9 の駆動）、tTIS は Sim4Life（合計 2 mA・2000 / 2010 Hz）。", ""]
for fiber, _, label in FIBERS:
    md += ["## %s" % label, "",
           "| 線 | TUS | tTIS ランプ付き | 発火の時刻 [ms] | tTIS ランプ無し | 発火の時刻 [ms] |",
           "|---|---|---|---|---|---|"]
    for line in LINES:
        r, rt = ttis[(fiber, "ramp", line)]
        n, nt = ttis[(fiber, "noramp", line)]
        md.append("| %s | %s | %s | %.1f | %s | %.1f |" % (line, fmt(tus[(fiber, line)]), fmt(r), rt, fmt(n), nt))
    md.append("")

md += ["## まとめ（標的外 ÷ 標的。1 より大きいほど標的を選べる）", "",
       "| 線維 | 手法 | 標的の最小 | 標的外の最小 | 標的外 ÷ 標的 | 安全上限で標的が発火するか |",
       "|---|---|---|---|---|---|"]
for fiber, _, label in FIBERS:
    rows = [("TUS", {l: tus[(fiber, l)] for l in LINES}),
            ("tTIS ランプ付き", {l: ttis[(fiber, "ramp", l)][0] for l in LINES}),
            ("tTIS ランプ無し", {l: ttis[(fiber, "noramp", l)][0] for l in LINES})]
    for method, factors in rows:
        tgt, off, rr = ratio(factors)
        md.append("| %s | %s | %s | %s | %.2f | %s |" % (label, method, fmt(tgt), fmt(off), rr,
                                                        "する" if tgt < 1 else "しない"))
md.append("")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print("\n".join(md))
print("wrote", os.path.relpath(OUT, ROOT))
