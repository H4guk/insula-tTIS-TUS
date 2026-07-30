"""工程1 Yoon-sun 頭部モデルの読み込み（Sim4Life.lite Python コンソールで実行）。

Lite の GUI からは読み込めない（ボタン無反応）ため、Python 経由で取得する:
  data.GetAvailableDownloads() → data.DownloadModel() → XCoreModeling.Import()
所要 約22秒。読み込み後、Model 直下に "Yoon-sun v3.1 Static"（配下 326 組織）が載る。

出典ノート: Claude/Knowledge/sim4life-yoonsun-implementation.md §2
注意: Step 1・2 だけではツリーに何も入らない。ツリーに載るのは Step 3 の Import()。
      import 時の `No binder found` ERROR は無害（Science 専用 enum が Lite に無いだけ）。
"""
import s4l_v1.data as data
import s4l_v1.model as model
import XCoreModeling
import time

try:
    current = list(model.AllEntities())
except Exception as e:
    print('AllEntities NG:', type(e).__name__, e); current = []

already = [e for e in current if 'Yoon' in e.Name]
if already:
    print('★既に読み込み済み:', [e.Name for e in already])
else:
    it = data.GetAvailableDownloads()[0]        # ① 列挙（Lite は1件）
    print('① モデル:', it.Name, it.Version, it.DOI)
    path = data.DownloadModel(it)               # ② DL（ツリーには入らない）
    print('② DL先 :', path)
    t0 = time.time()
    ents = XCoreModeling.Import(path)           # ③ ★ここでツリーに載る
    print('③ Import 完了: %.1f 秒' % (time.time() - t0))
    print('   エンティティ:', [e.Name for e in ents])
    try:
        XCoreModeling.ReloadViPColors()         # ④ 組織カラー
        print('④ ViP カラー適用 OK')
    except Exception as e:
        print('④ ViP カラー適用 NG:', type(e).__name__, e)
