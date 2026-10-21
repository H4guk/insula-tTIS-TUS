"""#16 関門: tutorial（Electrode with Nerve Model）で 2000 / 2010 Hz の2つの Source から 10 Hz のうなりが出るかを確かめる。

前提: `Neuronal Stimulation` に Sinusoidal の Source を2つ（2000 Hz・2010 Hz、`AddSource(em, "Overall Field")` で EM につなぐ）、
Duration 110 ms・Titration なしで Run 済み。

注意:
  - `xy.Axis` の単位は**秒**（ms ではない）。
  - `GetComponent(0)` は Source 2つぶんが1次元に並ぶ（2 × 時刻の数）。並び方は stacked（前半＝Source 0）だった。
    念のため stacked / interleaved の両方を作り、なめらかな方を採る。

結果（2026-10-13）: 和の最大は 0〜5 ms で 2.000、45〜55 ms で 0.312（理論 2|cos(2π·5·45ms)| = 0.313）、95〜100 ms で 2.000。
"""
import numpy as np
import matplotlib.pyplot as plt
import s4l_v1.document as document

neuro = document.AllSimulations["Neuronal Stimulation"]
stim = neuro.Results()["Stimulus"]
stim.UpdateAll()
xy = stim["Amplitude"].Data

t = np.asarray(xy.Axis) * 1e3
raw = np.asarray(xy.GetComponent(0))
n = len(t)

stacked = raw.reshape(2, n)
interleaved = raw.reshape(n, 2).T
rough_s = np.abs(np.diff(stacked, axis=1)).mean()
rough_i = np.abs(np.diff(interleaved, axis=1)).mean()
ys = stacked if rough_s < rough_i else interleaved
print("layout:", "stacked" if rough_s < rough_i else "interleaved", rough_s, rough_i)
total = ys.sum(axis=0)

for lo, hi in ((0, 5), (45, 55), (95, 100)):
    m = (t >= lo) & (t <= hi)
    print("%3d-%3d ms | src0 %.3f | src1 %.3f | sum %.3f" % (
        lo, hi, np.abs(ys[0][m]).max(), np.abs(ys[1][m]).max(), np.abs(total[m]).max()))

fig, ax = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
ax[0].plot(t, ys[0], lw=0.3)
ax[0].set_ylabel("src 2000 Hz")
ax[1].plot(t, ys[1], lw=0.3)
ax[1].set_ylabel("src 2010 Hz")
ax[2].plot(t, total, lw=0.3)
ax[2].set_ylabel("sum")
ax[2].set_xlabel("time [ms]")
plt.tight_layout()
plt.show()
