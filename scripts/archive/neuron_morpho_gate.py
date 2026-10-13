"""#16 やり直し・関門: MorphoSONIC の MRG 軸索に超音波（SONIC）と電気刺激をかけて動くか（ローカル Python）。

環境（2026-10-13・macOS arm64・conda Python 3.11）:
  - PySONIC（tjjlemaire/PySONIC 10ed530）＋ MorphoSONIC（tjjlemaire/MorphoSONIC 5d0d264）を `pip install -e --no-deps`
  - NEURON 9.0.2（pip）。MorphoSONIC/nmodl で `nrnivmodl` を実行
    → `arm64/libnrnmech.dylib` ができるが、MorphoSONIC は `arm64/.libs/libnrnmech.so` を探すので symlink を張る
  - pandas は 2.2 未満に下げる（3.x だと PySONIC の `self[...][0] = ...` が Copy-on-Write で黙って効かない）
  - SONIC の lookup `MRGnode_lookups_fs1.00.pkl`（26.6 MB）は Git LFS なので media URL から取り、sha256 b9b9789f… を照合
    lookup の周波数は 20k / 100k / 500k / 1M / 2M / 3M / 4M Hz で、250 kHz は 100k と 500k の間の補間になる（RS も同じ）

結果:
  - MRGFiber(20 µm, 6 節): 節の間隔 1.700 mm・長さ 8.501 mm・36 °C
    Sim4Life の Motor MRG 20 µm も節の間隔は約 1.7 mm（offtarget_x の node[5] が x = 52.296 mm、線の始点 43.5 mm）で一致。
    温度は Sim4Life が 37 °C・MorphoSONIC が 36 °C（MRGnode の lookup は 36 °C で作られている）→ そろえるなら Sim4Life 側を 36 °C にする。
  - 電気（点電源 -1 mA・1 mm 離れ・0.1 ms）: 中央の節で発火 1（0.4 s）
  - 超音波 250 kHz・10 ms・ガウス分布: 100 kPa で 0、300 kPa で 1、600 kPa で 1（1 本 1〜4 s）
  - `IDA initialization failure` の警告が毎回出る（NEURON の DAE ソルバーの初期化）。発火の有無は強さに対して単調で、結果は妥当に見えるが未検証。
"""
import time, logging
import numpy as np
from neuron import h
from PySONIC.utils import logger
from PySONIC.core import PulsedProtocol
from MorphoSONIC.models import MRGFiber
from MorphoSONIC.sources import GaussianAcousticSource, ExtracellularCurrent

logger.setLevel(logging.WARNING)
fiber = MRGFiber(20e-6, nnodes=6, a=32e-9, fs=1.)
print("nnodes", fiber.nnodes, "interL [mm] %.3f" % (fiber.interL * 1e3), "length [mm] %.3f" % (fiber.length * 1e3), "celsius", h.celsius)

def nspikes(data, meta):
    from PySONIC.postpro import detectSpikes
    d = data[fiber.nodeIDs[fiber.nnodes // 2]] if hasattr(data, "keys") else data
    return len(detectSpikes(d)[0])

t0 = time.time()
src = ExtracellularCurrent(x=(0., 1e-3), I=-1.0e-3)
data, meta = fiber.simulate(src, PulsedProtocol(100e-6, 3e-3))
print("estim -1 mA point source 1 mm: spikes at central node =", nspikes(data, meta), "(%.1f s)" % (time.time() - t0))

for A in (100e3, 300e3, 600e3):
    t0 = time.time()
    src = GaussianAcousticSource(0., fiber.length / 4., 250e3, A=A)
    data, meta = fiber.simulate(src, PulsedProtocol(10e-3, 5e-3))
    print("US 250 kHz %.0f kPa 10 ms: spikes =" % (A * 1e-3), nspikes(data, meta), "(%.1f s)" % (time.time() - t0))
