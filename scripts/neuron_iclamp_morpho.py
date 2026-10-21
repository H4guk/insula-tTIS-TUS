"""#16 L2 ④ 実装の突き合わせ（MorphoSONIC 側・ローカル）: 軸索の中央に細胞内電流（IClamp）を流し、発火の閾値を求める。

Sim4Life 側（Point Processes の IClamp）と同じ条件で閾値を比べ、2つの実装の軸索が同じように発火するかを確かめる。
電極の場や音圧を介さないので、違いが出ればそれは軸索の実装（形・チャネル・温度）の違い。

条件: 中央の区画（MRG は node3・Sundt は中央の区画）・パルス 0.1 ms と 1 ms・後の観察 30 ms
発火の判定は MorphoSONIC の標準（両端の節で spike＝端まで伝わった）。

環境: ~/envs/insula-sonic（scripts/archive/neuron_morpho_gate.py の docstring）
使い方: ~/envs/insula-sonic/bin/python scripts/neuron_iclamp_morpho.py

結果（2026-10-18・36 °C）:
  mrg16  node3（67 区画）   0.1 ms: 1.455 nA   1 ms: 0.2825 nA
  sundt  node228（456 区画） 0.1 ms: 0.715 nA   1 ms: 0.1175 nA
"""
import json, time, logging
from neuron import h
from PySONIC.utils import logger
from PySONIC.core import PulsedProtocol
from MorphoSONIC.models import MRGFiber, UnmyelinatedFiber
from MorphoSONIC.sources import IntracellularCurrent

logger.setLevel(logging.WARNING)

fibers = {
    "mrg16": lambda: MRGFiber(16e-6, nnodes=7, a=32e-9, fs=1.),
    "sundt": lambda: UnmyelinatedFiber(0.8e-6, fiberL=10e-3, a=32e-9, fs=1.),
}

for name, make in fibers.items():
    fiber = make()
    sec = fiber.central_ID
    for tstim in (0.1e-3, 1e-3):
        t0 = time.time()
        Ithr = fiber.titrate(IntracellularCurrent(sec, mode="anode"), PulsedProtocol(tstim, 30e-3))
        print(json.dumps({"fiber": name, "sec": sec, "nsec": len(fiber.seclist), "celsius": h.celsius,
                          "tstim_ms": tstim * 1e3, "Ithr_nA": round(Ithr * 1e9, 4), "sec_run": round(time.time() - t0, 1)}),
              flush=True)
