"""#16 L2 ②: Sim4Life の音圧を MorphoSONIC の軸索に区画ごとに与える音源（ローカル Python）。

MorphoSONIC（tjjlemaire/MorphoSONIC 5d0d264）にある音源は、ガウス分布・平面振動子・1 区画だけで、
任意の音圧分布を与えるものが無い。そこで GaussianAcousticSource と同じ形（AbstractAcousticSource を継承し、
computeDistributedAmps で区画ごとの振幅を返す）で、線に沿った音圧の表から振幅を決める音源を作った。

  - 音圧の表: `neuron_tus_line_pressure2.py` の出力（線の中心を 0 として -5〜+5 mm・0.25 mm 刻み・安全駆動 k 倍後）
  - 形: 表を最大値で割った相対分布 rel(x)。区画の中心の x で線形補間する（表の外は端の値）
  - 強さ: xvar = A は「表の最大値の位置での音圧」。titrate は A を二分探索するので、
    閾値 A_thr ÷ 表の最大値 が倍率（tTIS の titration_factor と同じ意味。1 未満なら安全駆動で発火）
"""
import numpy as np
from MorphoSONIC.sources import AbstractAcousticSource


class ProfileAcousticSource(AbstractAcousticSource):

    def __init__(self, x, p, f, A=None):
        ''' Constructor.

            :param x: positions along the fiber, centered on the fiber center (m)
            :param p: pressure amplitudes at x (Pa)
            :param f: US frequency (Hz)
            :param A: pressure at the profile maximum (Pa)
        '''
        self.x = np.asarray(x, dtype=float)
        self.p = np.asarray(p, dtype=float)
        self.pmax = float(self.p.max())
        AbstractAcousticSource.__init__(self, f, A=A)

    def copy(self):
        return self.__class__(self.x, self.p, self.f, A=self.A)

    def __repr__(self):
        return f'ProfileAcousticSource(f={self.f * 1e-3:.0f}kHz, A={self.A})'

    def getField(self, xq):
        return self.A * np.interp(xq, self.x, self.p / self.pmax)

    def computeDistributedAmps(self, fiber):
        return {k: self.getField(v) for k, v in fiber.getXCoords().items()}

    def computeSourceAmp(self, fiber, A):
        return A
