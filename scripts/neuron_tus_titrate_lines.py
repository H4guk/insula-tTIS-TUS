"""#16 L2 ②: 7 本の線 × 2 種類の線維で、TUS の発火に要る倍率を出す（ローカル Python・MorphoSONIC）。

入力: results/neuron_tus_line_pressure2_2026-10-15.txt（`neuron_tus_line_pressure2.py` の出力。安全駆動 k = 0.1558 後の |p| [kPa]、
      線の中心を 0 として -5〜+5 mm・0.25 mm 刻み・41 点）
音源: `neuron_tus_profile_source.ProfileAcousticSource`（関門は scripts/archive/neuron_tus_profile_gate.py で通過）
線維（軸索の中心を線の中心に置き、線の向きに沿わせる）:
  - mrg16: MRGFiber 16 µm・7 節（間隔 1.500 mm・長さ 9.0 mm、±4.5 mm で表の範囲に収まる）
  - sundt: UnmyelinatedFiber（Sundt 2015）0.8 µm・長さ 10 mm
  どちらもソノフォア半径 32 nm・被覆率 fs = 1
刺激: 250 kHz・100 ms の連続波・その後 50 ms（tTIS と同じ 100 ms）
倍率 = titrate の閾値 A_thr ÷ 線上の最大音圧。1 未満なら安全駆動で発火する。lookup の上限 600 kPa を超えると閾値は nan。

実行: python scripts/neuron_tus_titrate_lines.py <fiber> <line>   （1 件ずつ・1 行の JSON を出す）
"""
import os, sys, json, time, logging
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySONIC.utils import logger
from PySONIC.core import PulsedProtocol
from MorphoSONIC.models import MRGFiber, UnmyelinatedFiber
from neuron_tus_profile_source import ProfileAcousticSource

logger.setLevel(logging.ERROR)
F = 250e3
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = os.path.join(ROOT, 'results', 'neuron_tus_line_pressure2_2026-10-15.txt')


def load_lines(path):
    lines = {}
    for row in open(path):
        parts = row.split()
        if len(parts) > 2 and parts[1] == "p" and not row.startswith("#"):
            lines[parts[0]] = np.array([float(v) for v in parts[2:]]) * 1e3
    return lines


def make_fiber(kind):
    if kind == 'mrg16':
        return MRGFiber(16e-6, nnodes=7, a=32e-9, fs=1.)
    if kind == 'sundt':
        return UnmyelinatedFiber(0.8e-6, fiberL=10e-3, a=32e-9, fs=1.)
    raise ValueError(kind)


if __name__ == '__main__':
    kind, name = sys.argv[1], sys.argv[2]
    p = load_lines(SRC)[name]
    x = np.linspace(-5e-3, 5e-3, p.size)
    fiber = make_fiber(kind)
    t0 = time.time()
    thr = fiber.titrate(ProfileAcousticSource(x, p, F), PulsedProtocol(100e-3, 50e-3))
    thr = float('nan') if thr is None else float(thr)
    print(json.dumps({'fiber': kind, 'line': name, 'pmax_kPa': round(p.max() * 1e-3, 3),
                      'thr_kPa': round(thr * 1e-3, 3), 'factor': round(thr / p.max(), 4),
                      'nsec': sum(len(v) for v in fiber.sections.values()),
                      'sec': round(time.time() - t0, 1)}), flush=True)
