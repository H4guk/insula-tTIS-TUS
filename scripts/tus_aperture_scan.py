# 開口 D を振って、トランスデューサを頭の外に置くのに要る焦点距離 R と、そのときの F#・フレネル数を出す（Sim4Life.lite・読み取りのみ）。#25
# tus_transducer_overlap.py と同じ頭（tTIS_LF1 のボクセル）・同じ軸（焦点→T7）。開口 58 mm で F# 1.21 に戻るかを確かめるため。
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
D = (T7 - FOCUS) / np.linalg.norm(T7 - FOCUS)      # 軸の単位ベクトル（R_OUT で割らない）


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
head = name3 != 'Background'
ix = np.where((cx > FOCUS[0] - 90) & (cx < FOCUS[0] + 90))[0]
iy = np.where((cy > FOCUS[1] - 90) & (cy < FOCUS[1] + 90))[0]
iz = np.where((cz > FOCUS[2] - 90) & (cz < FOCUS[2] + 90))[0]
X, Y, Z = np.meshgrid(cx[ix], cy[iy], cz[iz], indexing='ij')
P = np.stack([X - FOCUS[0], Y - FOCUS[1], Z - FOCUS[2]], axis=-1)
t = P @ D
r = np.sqrt((P ** 2).sum(-1))
perp = np.sqrt(np.maximum(r ** 2 - t ** 2, 0.0))
sub_head = head[np.ix_(ix, iy, iz)]
sub_name = name3[np.ix_(ix, iy, iz)]
LAM = 6.0                                           # 250 kHz の水中の波長 [mm]
R_SCALP = float(np.linalg.norm(T7 - FOCUS))         # T7 の頭皮〜焦点 48.51 mm

print('[grid] tTIS_LF1 %s  頭の組織のセル %d' % (str(name3.shape), int(head.sum())))
print('')
print('  D[mm]  頭の一番外[mm]（組織）        R_IN    R_OUT   F#     N     T7 の頭皮でのビーム径[mm]')
for D_AP in (40, 46, 52, 58, 64, 70):
    a = D_AP / 2.0
    hc = (t > 0) & (perp <= a) & sub_head
    j = int(np.argmax(np.where(hc, r, -1)))
    rmax = float(r.ravel()[j])
    r_in = rmax + 0.5 + GAP
    r_out = r_in + SHELL
    print('  %5d  %6.2f（%-22s）  %6.2f  %6.2f  %4.2f  %4.2f  %5.1f'
          % (D_AP, rmax, sub_name.ravel()[j], r_in, r_out, r_out / D_AP, a * a / (LAM * r_out), D_AP * R_SCALP / r_out))
print('')
print('  N = a^2 / (λ R)。1 前後だと音圧の最大がトランスデューサ側へずれる。旧（R 48.5・D 40）は 1.37')
print('=== 開口の走査 完了（読み取りのみ・保存していない）===')
