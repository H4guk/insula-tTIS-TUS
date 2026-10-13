"""#16 関門: Sim4Life.lite の神経の本数上限を確かめる（tutorial の `Neuronal Stimulation` で実行）。

手順（2026-10-13）:
  1. 本ファイルで、`axon_test`（HOC 神経の中心を通る 5 mm の線）の横に 0.2 mm ずつずらした線を 10 本作り、SENN 軸索にする。
     `axon_test` 自体は事前に `model.CreateAxonNeuron(line, model.SennNeuronProperties())` で軸索にしておく。
  2. GUI で `Neurons` を選ぶ → `New Settings ▾` → Automatic Axon Model Settings → 11 本をドラッグ（HOC 1本と合わせて 12 本）。
  3. Duration 1 ms で Run。

結果: `[ERROR] Light version does not support number of neurons over 10.` → 入力ファイルを書けず計算は始まらない。上限は 10 本。

途中で分かったこと:
  - 同じ HOC の型（L5_TTPC2_cADpyr232）を `Clone()` で2本にすると、上の文言なしで `Failed to write neurons to input file.`。
    1本ずつなら通り、HOC 1本＋SENN 1本も通る ⇒ 本数ではなく同じ HOC の型の重複が原因。
  - `sim.Add(HocNeuronSettings or AutomaticAxonNeuronSettings, [entity])` は `incompatible with this type of simulation`。
    神経は GUI のドラッグで設定に入れる。
  - ただの線は軸索の設定に入らない。`CreateAxonNeuron(s)` で神経のエンティティにしてから入れる。
"""
import s4l_v1.model as model
from s4l_v1 import Vec3

base = [e for e in model.AllEntities() if e.Name.startswith("axon_test")][0]
p0, p1 = model.GetBoundingBox([base])
cx = (p0[0] + p1[0]) / 2
cy = (p0[1] + p1[1]) / 2
cz = (p0[2] + p1[2]) / 2

lines = []
for i in range(1, 11):
    ln = model.CreatePolyLine([Vec3(cx - 2.5, cy + 0.2 * i, cz), Vec3(cx + 2.5, cy + 0.2 * i, cz)])
    ln.Name = "axon_%02d" % i
    lines.append(ln)

try:
    axons = model.CreateAxonNeurons(lines, model.SennNeuronProperties())
    print("created:", len(axons))
    for a in axons:
        print("  ", a.Name, model.IsNeuron(a))
except Exception as e:
    print("create error:", repr(e))
