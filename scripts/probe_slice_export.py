"""Figure 1 の下ごしらえ: 場スライスの取り出し方を確認する（統合プロジェクト・読み取り専用）。

Figure 1 = **両手法の場スライスを島皮質断面で並置**（tTIS の TI 包絡 / TUS の |p|）。
断面は **X = 99.1mm の YZ 平面**——ビーム軸 (-0.089, 0.842, -0.532) は X 成分がほぼゼロなので
この面がビーム経路をほぼ含み、T7 電極（X=94.8）も近い。tTIS の「電極から島皮質への裾」と
TUS の焦点を同じ面で見せられる。

このスクリプトは**描画の前に環境を確かめる**だけ:
  ① matplotlib が使えるか（使えるなら Sim4Life 側で PNG を作れる）
  ② 書き込めるディレクトリはどこか
  ③ 断面の大きさ（何セル × 何セル）と値の範囲
  ④ 使えない場合に備え、**粗くサンプリングした断面を base64 で吐く**選択肢の見積り

結果を見てから、PNG 生成版か数値エクスポート版のどちらを作るか決める。
"""
import os
import sys
import numpy as np
import s4l_v1.document as document

SLICE_X_MM = 99.1
FOCUS_MM = np.array([99.1, 295.0, 1562.2])

print('[env ] python %s' % sys.version.split()[0])
for mod in ('matplotlib', 'PIL', 'scipy', 'h5py'):
    try:
        m = __import__(mod)
        print('  %-12s OK  %s' % (mod, getattr(m, '__version__', '')))
    except Exception as e:
        print('  %-12s NG  (%s)' % (mod, type(e).__name__))

# 書き込めそうな場所
print('')
print('[path] 書き込み候補:')
sim0 = list(document.AllSimulations)[0]
try:
    inp = sim0.GetInputFileName()
    print('  sim の Input: %s' % inp)
    print('  そのディレクトリ: %s' % os.path.dirname(inp))
except Exception as e:
    print('  Input パス取得 NG: %s' % e)
for p in (os.getcwd(), os.path.expanduser('~'), '/tmp'):
    print('  %-40s writable=%s' % (p, os.access(p, os.W_OK)))

# 断面の大きさ
print('')
print('[slice] 各 sim の断面（X=%.1fmm の YZ 平面）:' % SLICE_X_MM)
for sim in document.AllSimulations:
    try:
        res = sim.Results(); res.UpdateAll()
        of = res['Overall Field']; of.Update(0)
        key = 'p(x,y,z,f)' if 'p(x,y,z,f)' in list(of.keys()) else 'EM E(x,y,z,f0)'
        f = of[key]; f.Update()
        g = f.Data.Grid
        xa = np.asarray([float(v) for v in g.XAxis]) * 1000.0
        ya = np.asarray([float(v) for v in g.YAxis]) * 1000.0
        za = np.asarray([float(v) for v in g.ZAxis]) * 1000.0
        cx = 0.5 * (xa[:-1] + xa[1:]); cy = 0.5 * (ya[:-1] + ya[1:]); cz = 0.5 * (za[:-1] + za[1:])
        i = int(np.argmin(np.abs(cx - SLICE_X_MM)))
        print('  %-12s grid %d x %d x %d / 断面 %d(Y) x %d(Z) / X=%.2fmm を採用（要求 %.1f）/ key=%s'
              % (sim.Name, cx.size, cy.size, cz.size, cy.size, cz.size, cx[i], SLICE_X_MM, key))
        # ROI 周辺に限った場合の大きさ（描画範囲の見積り）
        js = np.where((cy >= 250) & (cy <= 360))[0]
        ks = np.where((cz >= 1500) & (cz <= 1620))[0]
        print('               ROI 周辺に限ると %d x %d = %s cells（Y 250–360 / Z 1500–1620）'
              % (js.size, ks.size, format(js.size * ks.size, ',')))
    except Exception as e:
        print('  %-12s 読めない: %s: %s' % (sim.Name, type(e).__name__, str(e)[:60]))

print('')
print('[plan] 判定:')
print('  ① matplotlib が OK かつ書き込める場所がある → **Sim4Life 側で PNG を生成**（推奨）')
print('  ② matplotlib が NG → 断面を粗くサンプリングして base64 で吐き、ローカルで描画')
print('     （ROI 周辺 110x120mm を 2mm 刻みなら 55x60=3,300 点・float16 で 6.6KB・base64 約 8,800 文字）')
print('')
print('=== Figure 1 下ごしらえ 完了（読み取りのみ）===')
