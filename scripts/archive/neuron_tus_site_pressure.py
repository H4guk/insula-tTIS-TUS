"""#16 ② TUS の神経レベル比較: 標的と標的外の音圧を取り出す（Sim4Life.lite Python コンソール・読み取りのみ）。

tTIS（`neuron_ti_*.py`）と同じ2か所の |p| を、MI<1.9 の安全駆動にスケールして出す。この値を PySONIC に入れる。

  - 標的   = ROI 中心 (99.1, 295.0, 1562.2)
  - 標的外 = tTIS の脳内 TI 最大点 (48.5, 274.5, 1482.5)（ROI 中心から 96.6 mm）

スケール（`tus_safety_drive.py` と同じ式）:
  `TUS_250k` は音源 1 MPa の参照駆動。MI = p[MPa]/sqrt(f[MHz]) の全体最大（頭皮の皮下脂肪）を 1.9 に落とす k を掛ける。
  統合版の記録は k = 0.1558（音源 0.156 MPa、2026-08-28）。

値はその点を含むセル（最近傍）と、まわり 3×3×3 セルの最大・最小も出す（1 セルの値は数 % 動くため）。
"""
import numpy as np
import s4l_v1.document as document

SIM_NAME = "TUS_250k"
FREQ_MHZ = 0.25
MI_LIMIT = 1.9
SITES = {"target": (99.1, 295.0, 1562.2), "offtarget": (48.5, 274.5, 1482.5)}

sim = document.AllSimulations[SIM_NAME]
res = sim.Results()
res.UpdateAll()
of = res["Overall Field"]
of.Update(0)
pf = of["p(x,y,z,f)"]
pf.Update()
data = pf.Data
mag = np.abs(np.asarray(data.Field(0))).ravel()
g = data.Grid
Xm = np.asarray(g.XAxis)
Ym = np.asarray(g.YAxis)
Zm = np.asarray(g.ZAxis)
cx = 0.5 * (Xm[:-1] + Xm[1:]) * 1000.0
cy = 0.5 * (Ym[:-1] + Ym[1:]) * 1000.0
cz = 0.5 * (Zm[:-1] + Zm[1:]) * 1000.0
p3 = mag.reshape((cx.size, cy.size, cz.size), order="F")

gmax = float(p3.max())
k = MI_LIMIT / ((gmax * 1e-6) / np.sqrt(FREQ_MHZ))
print("[grid] %d x %d x %d" % p3.shape)
print("[ref ] global max |p| = %.4f MPa  -> k = %.5f (record 0.1558)" % (gmax * 1e-6, k))
print("")
print("%-10s %-24s %12s %12s %22s" % ("site", "cell center [mm]", "ref [kPa]", "safe [kPa]", "safe 3x3x3 min-max"))
for name, (x, y, z) in SITES.items():
    i = int(np.argmin(np.abs(cx - x)))
    j = int(np.argmin(np.abs(cy - y)))
    l = int(np.argmin(np.abs(cz - z)))
    p = float(p3[i, j, l])
    blk = p3[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2, max(l - 1, 0):l + 2] * k
    print("%-10s (%6.1f, %6.1f, %7.1f) %12.2f %12.2f %10.2f - %.2f" % (
        name, cx[i], cy[j], cz[l], p * 1e-3, p * k * 1e-3, blk.min() * 1e-3, blk.max() * 1e-3))
