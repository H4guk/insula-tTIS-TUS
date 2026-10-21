"""#16 L2 ② の関門: 自作の ProfileAcousticSource が MorphoSONIC の既製の音源と同じ閾値を出すか（ローカル Python）。

確かめること（MRG 16 µm・7 節・250 kHz・10 ms の連続波）:
  (1) 一様: 平らな表（全区画で同じ音圧）  対  GaussianAcousticSource(sigma = 1 m ≒ 一様)
  (2) 非一様: ガウス形の表（sigma = 長さ/4 を 0.25 mm 刻みで標本化）  対  GaussianAcousticSource(sigma = 長さ/4)
判定: 閾値の差が 1% 以内なら通過（titrate の収束幅より十分大きい）。

結果（2026-10-15・MRG 16 µm 7 節 interL 1.500 mm 長さ 9.001 mm）: 通過
  uniform   profile 113.09 kPa / builtin 113.09 kPa（差 +0.000%）
  gaussian  profile 111.68 kPa / builtin 111.74 kPa（差 -0.052%）
  1 件 1 分ほど。"fiber is too short w.r.t stimulus FWHM" の警告は既製のガウス音源が出すもので、比べる目的上は問題ない。
  SUseg の lookup（Sundt 用・11.7 MB・sha256 a4889eba…）も Git LFS の media URL から取り、PySONIC/lookups に置いた。

実行: python -I scripts/archive/neuron_tus_profile_gate.py（scripts/ を sys.path に足して import する）
"""
import os, sys, time, logging
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from PySONIC.utils import logger, gaussian
from PySONIC.core import PulsedProtocol
from MorphoSONIC.models import MRGFiber
from MorphoSONIC.sources import GaussianAcousticSource
from neuron_tus_profile_source import ProfileAcousticSource

logger.setLevel(logging.WARNING)
F = 250e3
pp = PulsedProtocol(10e-3, 5e-3)
fiber = MRGFiber(16e-6, nnodes=7, a=32e-9, fs=1.)
print('MRG 16 um: nnodes %d, interL %.3f mm, length %.3f mm' % (fiber.nnodes, fiber.interL * 1e3, fiber.length * 1e3))
x = np.arange(-20, 21) * 0.25e-3
sig = fiber.length / 4

cases = [
    ('uniform', ProfileAcousticSource(x, np.ones_like(x) * 1e5, F), GaussianAcousticSource(0., 1.0, F)),
    ('gaussian', ProfileAcousticSource(x, gaussian(x, mu=0., sigma=sig, A=1e5), F), GaussianAcousticSource(0., sig, F)),
]
for name, mine, ref in cases:
    t0 = time.time()
    a = fiber.titrate(mine, pp)
    b = fiber.titrate(ref, pp)
    print('%-9s profile %8.2f kPa  builtin %8.2f kPa  diff %+.3f%%  (%.0f s)' % (
        name, a * 1e-3, b * 1e-3, 100 * (a - b) / b, time.time() - t0))
