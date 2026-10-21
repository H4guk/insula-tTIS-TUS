"""#16 ② TUS の神経レベル比較: 2か所の音圧で PySONIC の神経が発火するか（ローカル Python）。

PySONIC（Lemaire, Neufeld, Kuster, Micera 2019, J Neural Eng・tjjlemaire/PySONIC 10ed530）を使う。
lookup テーブルは Git LFS なので、clone の後に別途ダウンロードしてある前提。

設定:
  - 神経: 大脳皮質の regular spiking（RS）点神経、ソノフォア半径 32 nm、膜の被覆率 fs = 1
  - 刺激: 250 kHz（`TUS_250k` と同じ）、100 ms の連続波（tTIS の刺激 100 ms とそろえる）、開始 10 ms・後 50 ms
  - 音圧: `neuron_tus_site_pressure.py` の安全駆動（MI<1.9・k = 0.1558）での値
      標的   205.33 kPa（まわり 3×3×3 で 151.72〜235.29）
      標的外   6.09 kPa（同 1.18〜16.77）
  - 閾値: PySONIC の titrate（二分探索）で発火に要る音圧を出し、「閾値 ÷ その場所の音圧」を倍率とする
    （tTIS の titration_factor と同じ意味。1 未満なら安全駆動で発火する）

実行: python scripts/neuron_tus_pysonic.py
"""
import logging
import numpy as np
from PySONIC.utils import logger
from PySONIC.neurons import getPointNeuron
from PySONIC.core import NeuronalBilayerSonophore, AcousticDrive
from PySONIC.core.protocols import PulsedProtocol
from PySONIC.postpro import detectSpikes

logger.setLevel(logging.WARNING)

F_HZ = 250e3
SITES_KPA = {
    "target": (205.33, 151.72, 235.29),
    "offtarget": (6.09, 1.18, 16.77),
}

nbls = NeuronalBilayerSonophore(32e-9, getPointNeuron("RS"))
lkp = nbls.getLookup()
print("lookup A (kPa): %.1f .. %.1f" % (lkp.refs["A"].min() * 1e-3, lkp.refs["A"].max() * 1e-3))
pp = PulsedProtocol(100e-3, 50e-3, tstart=10e-3)

thr = nbls.titrate(AcousticDrive(F_HZ), pp)
thr_kpa = np.nan if thr is None or np.isnan(thr) else thr * 1e-3
print("threshold (250 kHz, 100 ms CW): %.2f kPa" % thr_kpa)
print("")
print("%-10s %10s %8s %10s" % ("site", "A [kPa]", "spikes", "factor"))
for site, amps in SITES_KPA.items():
    for tag, a in zip(("cell", "min", "max"), amps):
        data, meta = nbls.simulate(AcousticDrive(F_HZ, a * 1e3), pp)
        ispikes, _ = detectSpikes(data)
        print("%-10s %10.2f %8d %10.3f  (%s)" % (site, a, len(ispikes), thr_kpa / a, tag))
