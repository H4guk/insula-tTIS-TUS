"""5-1a セル上限が「プロジェクト合計」か「シミュレーション単位」かを判定する（読み取り専用）。

#36 の本番測定は 1プロジェクト・2シミュレーションに統合して行う
（Claude/Decisions/2026-08-25-one-model-two-simulations.md）。唯一の未確認リスクが
**Sim4Life.lite の 2,000万セル上限がプロジェクト合計か**。合計制なら
tTIS 12.289 ＋ TUS 11.05 = 23.3 MCells で現構成のまま統合できない。

判定の考え方:
  tTIS プロジェクトには tTIS_LF1 / tTIS_LF2 の **2 sim** があり、Phase2 では
  **両方 Run して** TI 包絡（2·min(|E1|,|E2|)）を作っている。各 12.289 MCells なら
  合計 24.58 MCells ＝ もし合計制ならその時点で上限を超えており Run できなかったはず。
  ⇒ **両 sim が結果を持っていること自体が「合計制ではない」ことの実例**になる。

セル数は結果グリッドの軸から直接数える（ti_analysis.py と同じ経路）。重い処理はしない。
このスクリプトは **tTIS プロジェクト**を開いた状態で流す（TUS 側でも動くが sim が1つなので判定はできない）。
"""
import s4l_v1.document as document

LIMIT = 20_000_000


def grid_cells(sim):
    """sim の結果グリッドから (nx, ny, nz, cells) を返す。結果が無ければ None。"""
    try:
        res = sim.Results()
        res.UpdateAll()
        of = res['Overall Field']
        of.Update(0)
        keys = list(of.keys())
        if not keys:
            return None
        f = of[keys[0]]
        f.Update()
        g = f.Data.Grid
        nx = len(list(g.XAxis)) - 1
        ny = len(list(g.YAxis)) - 1
        nz = len(list(g.ZAxis)) - 1
        return nx, ny, nz, nx * ny * nz, keys[0]
    except Exception as e:
        return ('ERR', str(e)[:60])


sims = list(document.AllSimulations)
print('[proj] シミュレーション %d 個' % len(sims))
print('')
print('  %-14s %-10s %-22s %-14s %s' % ('sim', '結果', 'グリッド', 'セル数', '読んだ場'))

total = 0
n_ok = 0
for sim in sims:
    g = grid_cells(sim)
    if g is None:
        print('  %-14s %-10s %-22s %-14s %s' % (sim.Name, 'なし', '-', '-', '-'))
    elif g[0] == 'ERR':
        print('  %-14s %-10s %-22s %-14s %s' % (sim.Name, 'エラー', '-', '-', g[1]))
    else:
        nx, ny, nz, cells, key = g
        total += cells
        n_ok += 1
        print('  %-14s %-10s %-22s %-14s %s'
              % (sim.Name, 'あり', '%d x %d x %d' % (nx, ny, nz), format(cells, ','), key))

print('')
print('[sum ] 結果を持つ sim %d 個 / セル数合計 %s（上限 %s）'
      % (n_ok, format(total, ','), format(LIMIT, ',')))

print('')
if n_ok >= 2 and total > LIMIT:
    print('[判定] **セル上限はシミュレーション単位**。')
    print('       同一プロジェクト内で合計 %s セル（上限の %.2f 倍）が既に Run できている＝合計制ではない。'
          % (format(total, ','), float(total) / LIMIT))
    print('       ⇒ tTIS 12.289M ＋ TUS 11.05M = 23.3M の統合は **現構成のまま可能**。')
    print('       ⇒ 決定ノートの代替案（ジオメトリのマスター1つ＋計算用の複製2つ）は不要。')
elif n_ok >= 2:
    print('[判定] 保留 — sim は %d 個あるが合計 %s が上限 %s を超えていない。'
          % (n_ok, format(total, ','), format(LIMIT, ',')))
    print('       この論法では決まらない。統合用プロジェクトで実際にボクセル化して確かめる必要がある。')
else:
    print('[判定] 保留 — 結果を持つ sim が %d 個しかない（tTIS プロジェクトで流したか確認）。' % n_ok)
    print('       tTIS_LF1 / tTIS_LF2 の両方が Run 済みのプロジェクトで実行すること。')

print('')
print('=== 5-1a 完了（読み取りのみ・保存していない）===')
