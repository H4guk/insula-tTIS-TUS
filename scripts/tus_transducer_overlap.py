# TUS のトランスデューサが頭に食い込んでいないかを確かめ、頭の外に出すのに要る焦点距離 R を測る（Sim4Life.lite・読み取りのみ）。#25
# 頭の形は tTIS_LF1 のボクセル（Transducer を登録していないので、組織だけの頭）を使う。tTIS_LF1 を Run した後に流す。
# 殻は build_transducer.py と同じ: 焦点 F 中心、厚さ 3 mm、軸 d = (T7 - F)/|T7 - F| の半径 20 mm の円柱で切り出し。
# 結果（2026-10-29・prod）: 旧い殻（R_OUT = |T7 - F| = 48.51 mm）は 3976 セルのうち 1575（40%）が頭の組織と重なっていた
#   （SAT 770・Skin 391・耳 305・唾液腺 94）。開口の中の頭の一番外は 65.03 mm → build_transducer.py の R_IN_CLEAR = 67.53 mm。
import numpy as np, h5py
import s4l_v1.document as document

FOCUS = np.array([99.1, 295.0, 1562.2])
T7 = np.array([94.7869, 335.8444, 1536.3872])     # Elec_T7 の重心（probe_transducer_pose.py・prod と旧で同じ）
SHELL, CAP_R = 3.0, 20.0
GAP = 2.0                                          # 頭皮と殻の内側の面のあいだにとる水の厚さ [mm]（提案値）

R_IN = 65.03 + 0.5 + GAP                           # build_transducer.py の R_IN_CLEAR と同じ
R_OUT = R_IN + SHELL
D = (T7 - FOCUS) / R_OUT


def sim(name):
    return [s for s in document.AllSimulations if s.Name == name][0]


def centres(s, key):
    r = s.Results(); r.UpdateAll()
    of = r['Overall Field']; of.Update(0)
    f = of[key]; f.Update()
    g = f.Data.Grid
    ax = [np.asarray([float(v) for v in a]) for a in (g.XAxis, g.YAxis, g.ZAxis)]
    return [0.5 * (a[:-1] + a[1:]) * 1000.0 for a in ax]                    # [mm]


def names(s):
    def uid(row):
        h = bytes(np.asarray(row, dtype=np.uint8).tolist()).hex()
        return '-'.join((h[0:8], h[8:12], h[12:16], h[16:20], h[20:32]))
    with h5py.File(s.GetInputFileName(), 'r') as f:
        mm = f['AllMaterialMaps'][list(f['AllMaterialMaps'].keys())[0]]
        mesh = [f['Meshes'][k] for k in f['Meshes'] if 'voxels' in f['Meshes'][k]][0]
        vox, ids = mesh['voxels'][...], mesh['id_map'][...]
        n = int(vox.max()) + 1
        name = np.full(n, 'Background', dtype=object)
        for v in range(min(n, ids.shape[0])):
            u = uid(ids[v])
            if u in mm:
                nm = mm[u].attrs.get('material_name', '?')
                name[v] = (nm.decode() if isinstance(nm, bytes) else str(nm)).split('(')[0].strip()
    return name[vox]


s = sim('tTIS_LF1')
cx, cy, cz = centres(s, 'EM E(x,y,z,f0)')
name3 = names(s)
head = name3 != 'Background'                       # 電極はボクセル 0 なので組織だけになる
print('[grid] tTIS_LF1 %s  頭の組織のセル %d' % (str(name3.shape), int(head.sum())))

# 円柱（開口）の中だけ見る: 軸方向 t > 0（T7 側）、軸からの距離 <= CAP_R
ix = np.where((cx > FOCUS[0] - 70) & (cx < FOCUS[0] + 70))[0]
iy = np.where((cy > FOCUS[1] - 70) & (cy < FOCUS[1] + 70))[0]
iz = np.where((cz > FOCUS[2] - 70) & (cz < FOCUS[2] + 70))[0]
X, Y, Z = np.meshgrid(cx[ix], cy[iy], cz[iz], indexing='ij')
P = np.stack([X - FOCUS[0], Y - FOCUS[1], Z - FOCUS[2]], axis=-1)
t = P @ D
perp = np.sqrt(np.maximum((P ** 2).sum(-1) - t ** 2, 0.0))
r = np.sqrt((P ** 2).sum(-1))
sub_head = head[np.ix_(ix, iy, iz)]
sub_name = name3[np.ix_(ix, iy, iz)]
cyl = (t > 0) & (perp <= CAP_R)

# (1) 今の殻と頭の重なり（組織ごと）
over = cyl & (r >= R_IN) & (r <= R_OUT) & sub_head
shell_all = cyl & (r >= R_IN) & (r <= R_OUT)
print('')
print('=== (1) 殻（R %.2f〜%.2f mm）と頭の重なり ===' % (R_IN, R_OUT))
print('[over] 殻のセル %d のうち頭の組織と重なる %d（%.0f %%）'
      % (int(shell_all.sum()), int(over.sum()), 100.0 * over.sum() / max(shell_all.sum(), 1)))
u, c = np.unique(sub_name[over], return_counts=True)
for k in np.argsort(-c):
    print('       %-28s %5d' % (u[k], c[k]))

# (2) 開口の中で、頭の一番外の点（焦点からの距離）。殻の内側の面はこれより外に要る
print('')
print('=== (2) 開口（半径 %.0f mm）の中の頭の一番外 ===' % CAP_R)
hc = cyl & sub_head
rr, nn, pp = r[hc], sub_name[hc], perp[hc]
for label, m in (('すべての組織', np.ones(rr.shape, bool)),
                 ('耳介を除く', np.array([not str(n).startswith('Ear_') for n in nn]))):
    j = int(np.argmax(np.where(m, rr, -1)))
    print('[max ] %-10s 焦点から %.2f mm（%s・軸から %.1f mm）' % (label, rr[j], nn[j], pp[j]))

# 軸からの距離ごとの頭の一番外（どこが効いているか）
print('[ring] 軸からの距離ごとの一番外 [mm]:')
for a, b in ((0, 5), (5, 10), (10, 15), (15, 20)):
    m = (pp >= a) & (pp < b) if b < 20 else (pp >= a) & (pp <= b)
    if m.any():
        j = int(np.argmax(np.where(m, rr, -1)))
        print('       %2d〜%2d mm: %.2f（%s）' % (a, b, rr[j], nn[j]))

# (3) 頭の外に出すのに要る R
rmax = float(rr.max())
print('')
print('=== (3) 置き直しの目安（水の層 GAP %.1f mm・ボクセル 1 mm の半分を足す）===' % GAP)
need_in = rmax + 0.5 + GAP
print('[R   ] 殻の内側の面 R_IN >= %.2f mm → R_OUT = %.2f mm（今 %.2f）・F# = %.2f（今 %.2f、開口 40 mm のまま）'
      % (need_in, need_in + SHELL, R_OUT, (need_in + SHELL) / 40.0, R_OUT / 40.0))
print('=== 食い込みの確かめ %s（読み取りのみ・保存していない）===' % ('PASS' if int(over.sum()) == 0 else 'FAILED: 殻が頭の組織と %d セル重なる' % int(over.sum())))
