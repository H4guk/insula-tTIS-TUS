# エラーログ

その日に出たエラーを**下に追記していく**。1件ごとに次の3点を書く。

- **症状**: 出たメッセージ・観測された挙動（そのまま貼る）
- **原因と解決**: 何が起きていたか / どう直したか
- **なぜその方法を選んだか**: 代替案と、それを採らなかった理由（技術選定の根拠）

進捗は `progress-log.md`、フェーズの設計・検証は `phase1-dev.md` / `phase2-prod.md`。

---

## 2026-07-21

### GUI から Yoon-sun を読み込めない
- **症状**: Model タブ → `Models / Phantoms` → `Humans (Region)` を選んでもモデル一覧が開かない。
  Logger にエラーは無く、出るのは `Unexpected category for doc link` の無害な警告のみ＝**何も起きていない**。
- **原因と解決**: ライセンス制限ではない（Lite には Yoon-sun が1体含まれると公式に確認）。UI が応答していないだけ。
  **Python 経由で迂回**して解決: `s4l_v1.data.GetAvailableDownloads()` → `data.DownloadModel(item)` で
  `.sab` を取得 → 既知の Import 経路でモデルツリーへ。
- **なぜその方法を選んだか**: サポート照会やフォーラム検索は返信待ちが発生する。Logger に失敗の痕跡が無く
  「機能は存在するが UI が応答していない」と切り分けられたので、**同じ機能を叩く別経路（API）**を試すのが最短だった。
  結果としてこれ以降の全工程を Python で再現できるようになり、git に成果を残せる形にもなった。

### `Skin` への距離が内外判定に使えず、球フィットが破綻した
- **症状**: 頭部の球フィットで半径 50mm というデタラメな値が出た（18分無駄にした）。
  頭の中心でも `Skin` への符号付き距離が **+44.84**（正）を返す。
- **原因と解決**: `Skin` は**薄い層**なので「内部なら負」という前提が成立しない。
  レイキャスト二分探索（内外判定に依存する）を捨て、**`ClosestPosition` 方式**（外側の遠い点を置いて
  最近傍の表面点を拾う）に変更して解決。中心 (96.5, 258.9, 1566.8) / R=91.0mm・残差 mean 4.8mm を得た。
- **なぜその方法を選んだか**: 二分探索は内外判定が正しい前提でしか動かない。層状メッシュではその前提が壊れるため、
  **判定に依存しない「最近傍点を1回で取る」方式**に切り替えた。方向ごと1回の呼び出しで済み速度も良い。

---

## 2026-07-22

### `GlobalGridSettings.MaxStep` が read-only で書けない
- **症状**: グリッドの最大ステップを設定しようとすると読み取り専用で拒否される。
  デフォルトが全身 1mm のままだとセル数が数億で破綻する。
- **原因と解決**: `DiscretizationMode = Automatic` の間は `MaxStep` が read-only。
  enum の代入も `IntEnumValue.__new__() missing 2 required position` 等で失敗する。
  **`p = ggs.DiscretizationModeProp; p.set(p.findValue('Manual'))`** で Manual にすると書けるようになる。
- **なぜその方法を選んだか**: `type(enum)` からメンバー取得、`EnumWrap(1)` での生成をいずれも試して失敗した。
  Sim4Lite の enum は **`XxxProp.set(XxxProp.findValue('メンバー名'))`** が唯一通るパターンで、
  以降 `BoundaryType` 等でも同じ手が使える汎用解になった。

### グリッドが全身を囲んでしまう
- **症状**: 材料を割り当てた `Skin` が全身なので、グリッドが全身を囲み、頭部 1mm では現実的なセル数にならない。
- **原因と解決**: グリッド範囲を数値で直接指定するプロパティは無い。
  **頭部を囲む Block（`GridBox_head`）を作り、そこに `AddManualGridSettings` で 1mm** を割り当て、
  Global は 5mm（体）に設定。結果 [229, 221, 246] ≈ 1229万セル（Lite の 2000万以内）。
- **なぜその方法を選んだか**: モデルを頭部でクロップする案もあったが、**体を粗く含めた方が電流の帰り道として物理的に正確**。
  Block ＋ Manual グリッドなら、モデルを壊さずに解像度だけを局所的に上げられる。

---

## 2026-07-29

### 材料 DB が IT'IS 5.0（低周波でない方）を引いていた
- **症状**: Logger に `assigned from [IT'IS 5.0] ... switch to [IT'IS LF 5.0]` の警告。
- **原因と解決**: `LinkMaterialWithDatabase(ms, "材料名")` のように**名前文字列を渡すとデフォルト DB を引く**。
  **`database["IT'IS LF 5.0"]["材料名"]` で材料オブジェクトを取得して渡す**ように変更して解決。
- **なぜその方法を選んだか**: 低周波オーム解法では LF DB の値を使うのが前提。名前文字列に依存すると
  どの DB を引いたかがコードから読めないため、**DB を明示してオブジェクトで渡す**形にした。
  なお、この修正だけでは voxel が空である問題は解消しなかった（別原因）。

---

## 2026-07-30

### 材料が 44 組織にしか付かない（15組織が黙って抜ける）
- **症状**: `材料割り当て組織数: 44`。頭部組織は 59 のはず。エラーは出ない。
  `set(head) - set(created)` で **CSF `Cerebrospinal_fluid`・頭蓋 `Skull_cortical`/`_cancellous`・`Eye_*` 等15組織**が欠落。
- **原因と解決**: 単語分割に `re.findall(r'\w+', ...)` を使っており、**`\w` が `_` を単語文字として扱う**ため
  `Cerebrospinal_fluid` が1トークンになり、DB 側の `Cerebrospinal Fluid`（2語）と集合一致しなかった。
  **`re.findall(r'[a-z0-9]+', ...)`** に変更して 59/59 に。
- **なぜその方法を選んだか**: 正規表現を `[a-z0-9]+` にすると `_`・空白・括弧をすべて区切りとして扱えるため、
  複合名（`Skull_cortical` ↔ `Skull (Cortical)`）にも一律で効く。
  加えて**エラーの出ない取りこぼし**という性質から、**期待値（59）と実数の突き合わせを常設**する方針にした。

### 全点 NaN（`0 unknowns / 0 Dirichlet points / no lossy dielectrics`）
- **症状**: Run は成功と出るが E 場・電位が全点 NaN。`Input.log` に
  `Degree of freedoms: ... 0 unknowns, 0 Dirichlet points, ... no lossy dielectrics`、
  `Voxeler.log` に **`Error: The boundary component 'Elec_T7' is not being considered in the voxeling process.`**
- **原因と解決**: **駆動電極（`Elec_*`）に材料を割り当てていなかった**。
  材料の無いエンティティは Voxeler がボクセル化しないため、電極が「considered されない」→
  電極に載せた Dirichlet BC が実体を持たず Dirichlet points = 0 → 解く自由度ゼロ → NaN。
  **電極に σ=1.6 S/m（生理食塩水スポンジ相当）を付与**して解決。
- **なぜその方法を選んだか**: σ を DB リンクではなく `ElectricProps.Conductivity` へ**直接指定**した。
  電極は解剖組織ではないので DB に対応物が無く、また Inoue 2025 のスポンジ σ=1.6 に合わせられるため。
  1層の円板で簡略化した点は限界として明記する（→ `phase2-prod.md`）。

### `ValueError: MaterialSettings is incompatible with this type of simulation`
- **症状**: 既存 sim に後から `AddMaterialSettings` すると弾かれる。
- **原因と解決**: **voxel 化・Run 済みの sim は確定状態**で、設定の追加を受け付けない。
  その sim にねじ込むのを諦め、**新規 sim を作って「組織＋電極」を最初から一緒に割り当てる**ことで解決。
- **なぜその方法を選んだか**: 壊れた／確定した状態でのデバッグは「状態のせいか API のせいか」を切り分けられない。
  ジオメトリ（モデル・電極）は再利用できるので、**sim だけ作り直す**のが最小の手戻りだった。

### `HDF5-DIAG: ... H5A__create(): attribute already exists`
- **症状**: Run 時に HDF5 の属性重複エラーが大量に出て、`RuntimeError: Unable to run simulation.` で拒否される。
- **原因と解決**: 当初は「同名の sim・`GridBox_head`・旧結果ファイルの衝突」と判断したが、
  **クリーンなセッションでも再現**したため**症状であって原因ではない**と判明。
  真因は **同一エンティティが材料設定と BC の両方に登録されていた**こと（同じ属性を二度書こうとする）。
  BC を電極の**外側の面**に移す（下記）と解消した。
- **なぜその方法を選んだか**: 「目立つエラーを主因と決め打ちしない」ため、**クリーン環境での再現テスト**を先に通した。
  再現したことで誤った仮説を早く捨てられた。

### `RuntimeError: Unable to run simulation. Please check your simulation settings.`（Run 起動拒否）
- **症状**: 材料 61 個・未マップ 0 の健全な状態でも Run が拒否される。`Input.log` すら生成されない
  （＝ソルバー起動前、ボクセル化の段で停止）。`Voxeler.log` に `'Elec_T7' is not being considered`。
- **原因と解決**: **電極ソリッドに材料σと Dirichlet BC を両方付けていた**ため、voxeler が boundary component を除外していた。
  挙動の対比が根拠: **材料なし＋BC → 走って全点 NaN** / **材料あり＋BC → Run 拒否**。
  **BC を電極の「外側の面」に付ける**ことで解決（`xc.GetFaces` → `xc.IsPlanarFace` で平面に絞り →
  頭の中心 (96.5, 258.9, 1566.8) から最も遠い平面を選ぶ）。Run が完走し、初めて `Input.log` が生成された。
- **なぜその方法を選んだか**: 材料と BC を同一エンティティに載せる構成が受け付けられていないと切り分けられたので、
  **BC の載せ先を別エンティティ（面）に移す**のが筋だった。面の選択は「頭の中心から最も遠い平面＝皮膚の外側」
  という幾何条件で自動化し、電極ごとに手で選ばない（再現性のため）。
  `xc.GetFaces` / `IsPlanarFace` は実機で存在を確認してから使った（未確認 API を推測で使わない）。

---

## 2026-07-31

### ★未解決: ボクセルシーンが空（`Voxel Scene Memory Consumption: 0.001196 kB`）
- **症状**: Run は完走するが全点 NaN。`Voxeler.log` に
  `Error: The material component '...' is not being considered in the voxeling process.` ＋ `Voxeling succeeded.`
  （＝中身が空のまま正常終了）。ソルバーは `12449814 total, 0 unknowns, 0 Dirichlet points`。
  ソルバー警告は `Check your model and solid region settings.`
- **切り分け（すべて否定）**:
  - 同名衝突・セッション状態の汚れ → **リロード直後の素のセッションでも再現**
  - ViP（Yoon-sun）固有 → **自作ソリッド（`CreateSolidBlock` の箱）1個でも再現**
  - 結果ディレクトリの古いファイル → 中身は当該実行の `Input.h5` と `Voxeler.log` の2つだけ
  - メッシュ型（`TriangleMesh`）が原因 → 本物のソリッド Body も焼けないので無関係
  - 組織数・電極・BC・グリッド範囲 → 組織1個・電極なし・BC なしでも再現／グリッドは頭を正しく囲む
- **最小再現ケース**:

  ```python
  box = xc.CreateSolidBlock(model.Vec3(80.,240.,1550.), model.Vec3(120.,280.,1590.))
  sim = emlf.ElectroQsOhmicSimulation(); doc.AllSimulations.Add(sim)
  ms = sim.AddMaterialSettings(box); ms.ElectricProps.Conductivity = 0.5
  sim.UpdateAllMaterials()
  ggs = sim.GlobalGridSettings; p = ggs.DiscretizationModeProp
  p.set(p.findValue('Manual')); ggs.MaxStep = [2.,2.,2.]
  sim.UpdateGrid(); sim.CreateVoxels()
  ```

- **本命の仮説**: `AddMaterialSettings` は `sim.AllComponents` に載るが、
  **エンティティが sim の Model / solid region に登録されていない**（v10 で `AssignEntities` が廃止された分の
  代替手順が抜けている疑い）。ソルバー警告と整合する。
- **次の一手とその理由**: ①**GUI で同じ最小 sim を作って Create Voxels** → 焼ければ GUI と Python の
  sim 構造を突き合わせて不足設定を特定し Python に翻訳。**lec6〜8 は GUI で成功していた**ので、
  「動く経路」と比べるのが最短。②焼けなければ **ZMT サポート/フォーラムへ照会**（最小再現ケースがあるので
  こちらの設定ミスと切り分けられた状態で聞ける）。

### `[ERROR] [XCore.CLog] Cannot convert licensed part`
- **症状**: `xc.ConvertToSolid(skin)` が `RuntimeError`、Logger に上記エラー。
- **原因と解決**: **ViP（Yoon-sun）のジオメトリはライセンス保護されており、変換が許可されていない**（.lite）。
  解決ではなく**回避ルートの断念**として確定させた（「ViP を Body 化してから焼く」案は使えない）。
- **なぜその方法を選んだか**: 箱（自作ソリッド）でも焼けないと分かっていたため、
  **メッシュ型を疑う筋自体が主因ではない**と判断でき、変換路にこだわる意味が無かった。

### 起動時の `Failed to define static enum ...`（無害と判定）
- **症状**: `ScaleType @ RecruitmentEvaluator`（ニューロン解析）と
  `MagneticProps.MaterialModel @ _emfdtd_impl`（EM FDTD）で enum 定義に失敗するエラーが起動時に出る。
- **原因と解決**: Python API 初期化時に全モジュールの enum を登録しようとして一部の名前解決に失敗している**ノイズ**。
  本プロジェクトは **Electro Ohmic Quasi-Static（低周波）**のみを使い、ニューロン解析・FDTD は触らない。
  ボクセル化にも無関係なので**対処不要**と判定。
- **なぜその方法を選んだか**: エラーメッセージの発生モジュールが使用中の機能と無関係であることを確認した。
  無関係なノイズを追うと本命の切り分けが薄まるため、判定して記録し切り上げた。

### 材料σを `sim.AllComponents` から読もうとして 0 件になった（診断側の誤り）
- **症状**: 材料設定を検証するスクリプトで「σ を読めた設定数: 0」。一見「材料が付いていない」ように見えた。
- **原因と解決**: `sim.AllComponents` が返すのは**エンティティ参照のコンポーネント**（`ApiComponent`）で、
  `ElectricProps` を持たない。**`sim.AllSettings`** を回して `MaterialSettings` 型を拾うのが正しい
  （`AllSettings` は 76 件・`ElectricProps=True`）。
- **なぜその方法を選んだか**: 「材料が付いていない」と結論する前に、**別の API で同じことを確かめた**
  （既に `created` 辞書経由で σ=1.6 を読み戻せていた事実と矛盾したため、測定方法を疑った）。
  検証方法が誤っているのに対象を疑うと、正しい実装を壊しに行ってしまう。

---

## 2026-08-03

### ★ GUI で最初から組んでもボクセルシーンが空（`0.003414 kB`）— Python 固有ではないと確定

- **症状**: 新規プロジェクト `#31 VOXTEST_GUI` を作り、**GUI だけで**「箱 `BOXTEST`（50mm角）→ Electro Quasi-Static sim →
  材料 σ=0.5 S/m をドラッグで割り当て → Manual グリッド 2mm（75×75×75 = 421,875 セル）→ Create Voxels」
  を実行したところ、`Topological Voxeler Report: Complete Voxel Scene / Voxel Scene Memory Consumption: **0.003414 kB**`。
  Python で組んだ最小ケース（`0.001196 kB`）と**同じく実質空**。
- **原因と解決**: 未解決。ただし切り分けとしては決定的で、**「Python の組み方に登録ステップが足りない」という
  2026-07-31 の本命仮説は否定**された。GUI が内部で行う登録手順を経ても同じ結果になるため。
- **なぜその方法を選んだか**: 2026-07-29 に「GUI の Create Voxels でも空」を確認済みだったが、
  それは **Python で組んだ sim を GUI のボタンで焼いた**ケースだった。今回は **sim の作成・材料割り当て・グリッドまで
  すべて GUI** で行っており、条件が異なる。ここを分けないと「Python 起因」を否定しきれないため実施した。
- **副次的に判明した2点**:
  1. **`... is not being considered in the voxeling process` が出ていない**（Python 版では出ていた）。
     エラーすら出さずに空になる。※ Logger 全体を確認しきれていないので要再確認。
  2. **バージョンは `Sim4Life light 9.6.0.22584`＝v10 ではない**。
     → 「v10 で `AssignEntities` が廃止された分の代替手順が抜けている」という仮説は**前提が誤り**。
     照会文からこの記述を外す必要がある。
- **次**: ZMT サポート/フォーラムへの照会に切り替える（`phase1-dev.md` の照会文を、
  ①GUI のみでも再現 ②v9.6 ③実測値 0.003414 kB に合わせて書き換える）。

### Logger 全文で確定した3点（同上・2026-08-03）

1. **`... is not being considered in the voxeling process` は出ていない**。Python 版では出ていたので、
   **症状は同一ではない**（GUI 版はエラーを出さずに空になる）。
2. **`Wall Clock Time: 0.0127833 s`** — 421,875 セルに対して12.8ミリ秒。
   処理が速いのではなく、**対象ゼロと判断して即終了している**ことを示す最も強い証拠。
3. Python 版のログには無かった警告が3種:
   - `[WARNING] [s4l_core.types.db_mode_manager] Failed to find node with id: 0-1`（×5）
   - `[WARNING] [s4l_core.simulation.simulation_manager] [simulation_manager::_translate_target] Unhandled target type: FormType.simulation_options`（×13）
   - `[WARNING] [s4l_core.monitor.monitor_base] App status: Unresponsive`

   `s4l_core.*` は**ブラウザ版フロントエンド層**（`s4l-lite.io` / `web-lite/9.6`）。
   フロントエンドがモデルツリー／シミュ設定をバックエンドへ渡しきれていない可能性を示唆するが、**断定はしない**
   （無害なノイズの可能性が残るため）。照会文には**原文のまま添付**する。

**★リグレッション説（要検証）**: Obsidian `Claude/Projects/tTIS-field-simulation.md` に
「**2026-07-20 に SAM head で lec8 の深部TI 6.404 を再現＝全配管が正しいと確定**」の記録がある。
Run できていた以上ボクセル化も成功していたはずで、`Sim4life-lec6` では **GUI の `Draw → Block` で作った電極**を
含む sim が焼けている。＝ **今日失敗した操作と本質的に同じことが約2週間前には通っていた**。
→ 照会文を書き換える前に、**既存 `Lec8-practice` を開いて `Create Voxels` を1回押す**判別テストを行う。
焼ける＝環境は正常（新規プロジェクト側に原因・動く sim と差分比較）／
焼けない＝**リグレッション**（照会が質問ではなくバグ報告になる）。

### ★訂正: 「正常なら Voxel Scene が MB 級」は誤り（2026-08-03）

- **症状（診断側の誤り）**: `phase1-dev.md` のログ判定表に「`Voxel Scene Memory Consumption` は **MB 級**が正常」と
  書いていた。この基準では、**実際に動作実績のある `Lec8-practice` すら「異常」と誤判定**してしまう。
- **原因と解決**: 実測すると、動く sim（`Lec8-practice` / SAM head / 251,378 セル）の値は **0.132734 kB**
  （さらに `Compressed size: 0.011168 kB`）。ボクセルシーンは圧縮表現で保持されるため、**均質なモデルでは kB 級が正常**。
  判定基準を「**絶対値ではなく、動く sim との相対比較**」に改めた。
- **正しい比較（同一環境・同一バージョン・同日 2026-08-03 実測）**:

  | | Lec8-practice（動く） | VOXTEST_GUI（動かない） |
  |---|---|---|
  | セル数 | 251,378（79×37×86） | 421,875（75×75×75） |
  | Voxel Scene | **0.132734 kB** | **0.003414 kB** |
  | Wall Clock | **0.229447 s** | **0.012783 s** |

  → セル数は 1.7 倍多いのに中身は 1/39・時間は 1/18。**VOXTEST_GUI では実体が焼かれていない**で確定。
- **なぜその方法を選んだか**: 「MB 級」は根拠のない見込み値だった。**動作実績のあるプロジェクトを対照群として実測**すれば
  基準そのものを検証できる。1分で済み、しかも**環境リグレッション説の否定**という別の収穫も同時に得られた。
- **副産物**: **環境・バージョンは正常**（同日・同環境で `Lec8-practice` は焼ける）。
  → 原因は**プロジェクト／sim の構成の差**にある。次は動く sim と動かない sim の**構造差分**を取る。
- ⚠️ **副作用**: `Create Voxels` により `Lec8-practice` で `[WARNING] Results Were Deleted`。
  既存の計算結果は破棄された（Run し直せば再生成可能。lec8 の TI=6.404 は記録に残っている）。

### ★否定: 「エンティティが sim に登録されていない」仮説（2026-08-03・構造差分）

- **確かめたこと**: 動く sim（`Lec8-practice` / `LF 1`）と動かない sim（`VOXTEST_GUI` / `LF`）で
  `type(sim)` / `sim.AllComponents` / `sim.AllSettings` を出力し、1対1で突き合わせた（読み取りのみ）。
- **結果**: **ほぼ同一構成**。

  | 項目 | Lec8 `LF 1`（焼ける） | `VOXTEST_GUI`（焼けない） |
  |---|---|---|
  | 型 | `ElectroQuasiStaticSimulation` | 同じ |
  | `AutomaticVoxelerSettings` | あり | あり |
  | `AutomaticGridSettings` | あり | あり |
  | `Plane X+ 〜 Z-` | あり | あり |
  | `Background` | あり | あり |
  | 対象エンティティ | `SAM_Shell` `SAM_Liquid` `Electrode±` | **`BOXTEST` が載っている** |

- **結論**: **`BOXTEST` は `AllComponents` に載っている** → 2026-07-31 の本命仮説
  「エンティティが sim の Model / solid region に登録されていない（v10 で `AssignEntities` 廃止分の
  代替手順が抜けている）」は**完全に否定**。登録されているのに voxeler が焼かない。
- **副産物**: 本番 Python は `emlf.ElectroQsOhmicSimulation()` を使っているが、
  **動作実績のある lec8 の sim は `ElectroQuasiStaticSimulation`（Ohmic なし）**。
  今回の失敗の原因ではない（VOXTEST_GUI も後者）が、**本番側の差分としては残る**ので Phase 1 再開時に確認する。
- **新仮説（未検証）**: **「GUI/API で描いた CAD ソリッドは voxeler の対象にならない」**。
  根拠＝本番で繰り返し出た `Elec_T7 is not being considered` の電極も「描いた Block」であり、
  lec8 では電極が焼かれなくても頭（`.sab` メッシュ）が焼かれていたため Run が通っていた、という説明が成り立つ。
  ただし **Yoon-sun（ViP メッシュ）も焼けていない**ので全体は説明できない。**断定しない**。
- **次の1手**: `Lec8-practice` の **`Voxel Log`** で、実際に焼かれたエンティティ一覧を確認する。
  `SAM_*` のみで `Electrode±` が無ければ新仮説どおり。電極も載っていれば仮説は外れ。

### ★否定: 「描いた CAD ソリッドは焼かれない」仮説（2026-08-03・Voxel Log）

- **確かめたこと**: `Lec8-practice` の `Voxel Log` で、実際に焼かれたエンティティの内訳を見た。
- **結果**: **電極（GUI で描いた Block）も焼かれている**。

  | エンティティ | 出自 | Voxels | Edges |
  |---|---|---|---|
  | SAM_Shell | `.sab` メッシュ | 3,994 | None |
  | SAM_Liquid | `.sab` メッシュ | 37,255 | None |
  | Electrode− | GUI の Block | **274** | 1,379 |
  | Electrode+ | GUI の Block | **254** | 1,331 |

  → **メッシュも CAD ソリッドも両方焼ける**（`Edges` の有無から処理経路は異なるが、どちらも成功）。
  「描いた CAD ソリッドは voxeler の対象にならない」は**成立しない**。
- **★収穫（形式そのものが手がかり）**: 動く sim では **エンティティごとに1レポート**が出力される。
  一方 `VOXTEST_GUI` の Logger には **`Complete Voxel Scene` の行しか無かった**。
  → `BOXTEST` のレポートが1件も出ていない可能性が高い。
- **次の1手**: `VOXTEST_GUI` で `Voxel Log` を開き、`BOXTEST` の行の有無を確認する。
  - **行が無い** → voxeler が **処理対象にすらしていない**（試行前に除外）
  - **行があって `Voxels: 0`** → 処理は試みたが1ボクセルも生成できない（ジオメトリ／グリッド位置の問題）

  この2つは原因が全く異なるため、照会文の書き方もここで決まる。

### ★★ 重大な訂正: 「ボクセルシーンが空」は誤診断だった（2026-08-03・Voxel Log）

- **確かめたこと**: `VOXTEST_GUI` で `Voxel Log` を開き、エンティティ単位の内訳を見た。
- **結果**: **`BOXTEST` は正常に焼かれていた**。

  ```
  Topological Voxeler Report: BOXTEST
      Voxels: 15625            ← 25³ = 50mm 角を 2mm で刻んだ正確な数
      Memory Consumption: 0.001869 kB
  ```

- **誤診断の原因**: `Voxel Scene Memory Consumption` を「中身の量」と解釈していたが、
  **これは幾何的な複雑さ（ランレングス的な圧縮効率）の指標**であって、ボクセル数に比例しない。

  | エンティティ | ボクセル数 | メモリ |
  |---|---|---|
  | BOXTEST（軸平行の箱1個） | **15,625** | 0.001869 kB |
  | SAM_Shell（解剖メッシュ） | 3,994 | 0.014854 kB |
  | SAM_Liquid（解剖メッシュ） | 37,255 | 0.014198 kB |

  → 軸に平行な箱は voxel 数が多くてもメモリは極小。`0.003414 kB` は**空ではなく単純**だった。
  `Wall Clock 12.8 ms` も箱1個なら妥当な速度で、「対象ゼロで即終了」ではなかった。
- **教訓（一般化）**: **集約値（Complete Voxel Scene）だけで判定してはいけない。
  必ず `Voxel Log` の"エンティティ単位の内訳"を見る。** 判定に使うべき指標は
  **`Voxels:` の件数**であって Memory Consumption ではない。
- **★これで話が逆転する**: 2026-07-31 に **Python の `CreateSolidBlock` で作った箱**では
  `Error: The material component 'BOXTEST_body' is not being considered in the voxeling process.` が出ていた。
  今日の **GUI 製の箱ではこのエラーが1行も出ていない**＝成功している。
  → **「Python で作ったエンティティは焼かれず、GUI で作ったエンティティは焼かれる」** となり、
  2026-07-31 の仮説「**Python 側に登録ステップが足りない**」が**復活**する。
- **同日の構造差分による"否定"は無効**: あの比較は **GUI 製 sim（Lec8）vs GUI 製 sim（VOXTEST_GUI）** であり、
  **どちらも動く側同士**だった。Python 製については何も検証できていない＝**比較の設計が誤っていた**。
- **次の1手（同一プロジェクト内での対照実験）**: `VOXTEST_GUI` の中に **Python で 2個目の箱 `PYBOX`** を作り、
  Python で σ を割り当てて、同じグリッド・同じ sim で `Create Voxels` → `Voxel Log` を見る。
  - `BOXTEST` は焼かれ `PYBOX` が焼かれない → **Python 生成が原因と確定**（1プロジェクト・1グリッド・1sim 内で分離できる最強の証拠）
  - 両方焼かれる → Python 生成は原因でない。差は本番プロジェクト固有（ViP / 電極 / 材料DB）に戻る

### ★★★ 原因の分離に成功: Python 経由で作ったエンティティが voxeler に無視される（2026-08-03）

- **実験**: 同一プロジェクト `VOXTEST_GUI` の中で、**GUI で描いた箱** と **Python で作った箱** を並べ、
  同じ sim・同じグリッド・同じ σ=0.5 でボクセル化した。
  - `BOXTEST` … GUI の `Draw → Block`
  - `PYBOX`  … Python の `xc.CreateSolidBlock`（型は `Body`）＋ `sim.AddMaterialSettings([pybox])`
- **結果**:

  ```
  Error: The material component 'PYBOX' is not being considered in the voxeling process.
  Start voxeling
  Topological Voxeler Report: BOXTEST    Voxels: 15625    ← 焼かれた
  （PYBOX のレポートは無い）
  ```

  → **GUI 製は焼かれ、Python 製は無視される**。環境・バージョン・プロジェクト・sim・グリッド・材料値が
  すべて共通なので、**残る差は「どう作ったか」だけ**。原因の分離に成功した。
- **本番の症状と一致**: `Elec_T7 is not being considered` / `Skin (Yoon-sun v3.1 Static) is not being considered`
  はこれと同じ現象。本番の電極は Python の `CreateSolidCylinder`、Yoon-sun は Python の Import で作っている。
- **まだ分かっていないこと（次に切り分ける）**: 「Python 製」のどこが効いているのか。候補は2つ。
  1. **エンティティ側** … `xc.CreateSolidBlock` で作った Body が、voxeler が見る対象リストに入っていない
  2. **材料設定側** … `sim.AddMaterialSettings([e])` による紐付けが、GUI のドラッグ紐付けと等価でない
- **次の1手（GUI ドラッグでの判別）**: Python で作った材料設定 `PYBOX Material` を削除し、
  **`PYBOX` を GUI のドラッグで既存の `Material Settings`（GUI 製）に紐付けて**ボクセル化する。
  - 焼ける → **原因は材料設定側（②）**。`AddMaterialSettings` の代替手順を探せば解決
  - 焼けない → **原因はエンティティ側（①）**。Python で作った Body 自体が対象外
- **付随して再確認した既知エラー**: voxel 化済みの sim に `AddMaterialSettings` すると
  `ValueError: ... incompatible with this type of simulation`。**`Reset Voxels` で確定状態を解除すれば通る**
  （従来の記録は「新規 sim を作る」だったが、**Reset Voxels でも回避できる**ことが今回確認できた）。

### ★★★★ 真因を特定: `sim.AddMaterialSettings()` による紐付けが voxeler に効かない（2026-08-03）

- **実験（①エンティティ側 vs ②材料設定側の判別）**: `PYBOX`（Python の `CreateSolidBlock` 製）を**そのまま**残し、
  材料の付け方だけを **Python の `AddMaterialSettings` → GUI のドラッグ**に変えて再ボクセル化した。
- **結果**:

  ```
  Topological Voxeler Report: BOXTEST   Voxels: 15625   （GUI 製・GUI 紐付け）
  Topological Voxeler Report: PYBOX     Voxels: 3375    （Python 製・GUI 紐付け）← 焼けた
  ```

  `3375 = 15³` は 30mm 角を 2mm で刻んだ正確な数。**Python 製エンティティでも、材料を GUI で紐付ければ焼ける**。

  | 疑い | 判定 |
  |---|---|
  | ① エンティティ側（`CreateSolidBlock` の Body が voxeler の対象外） | **シロ** |
  | ② 材料設定側（`sim.AddMaterialSettings([e])` の紐付け） | **クロ＝真因** |

- **結論**: 本番の `Elec_T7 is not being considered` / `Skin (Yoon-sun v3.1 Static) is not being considered`、
  および `0 unknowns / 0 Dirichlet points / no lossy dielectrics` の正体は、
  **材料σの割り当て方（`AddMaterialSettings` / `AutoAssignMaterials` 系）が voxeler から見えない形で紐付いていたこと**。
  σ の値は正しく入っていたので `sim.AllSettings` からは読めており、それが誤診断を長引かせた。
- **これで説明がつくこと**: 2026-07-22 以降の全点 NaN・Run 拒否・ボクセル空はすべて同じ原因の派生。
  ジオメトリ（Yoon-sun・電極）・グリッド・BC・材料DB は**いずれも無罪**（切り分けで1つずつ潰した通り）。
- **次の1手**: **GUI ドラッグと等価な Python API を特定する**。手がかり＝
  `AddMaterialSettings` が作るのは `s4l_v1.simulation._emlf_shared_impl.MaterialSettings` で、
  voxel 確定状態の sim では `ValueError: ... is incompatible with this type of simulation` と言われる。
  ＝ **sim 種別ごとの MaterialSettings クラスが別に存在する可能性**。
  GUI が作った（動く）材料設定オブジェクトの**実クラスとモジュールを Python から読み出し**、同じものを生成して紐付ける。

#### 補足: MaterialSettings のクラスは GUI 製と Python 製で同一（2026-08-03）

`sim.AllSettings` の実クラスを出力したところ、GUI が作った（焼ける）`Material Settings` も
**`s4l_v1.simulation._emlf_shared_impl.MaterialSettings`** で、`AddMaterialSettings` が作るものと**同一クラス**。
sim 種別ごとの専用 MaterialSettings クラスは**存在しない**（`ElectroQuasiStaticSimulation` 自体は `_emlf_impl`）。
→ **差はクラスではなく、オブジェクトのプロパティ値か、エンティティとの紐付け方**にある。
次に見るのは `MaterialType` / `ElectricProps.Conductivity` / `MassDensity` / `DatabaseLink` の実値比較
（ソルバーの `no lossy dielectrics` は `MaterialType` の違いで説明できる可能性がある）。

#### 補足2: 材料設定の中身も GUI 製と Python 製で完全一致（2026-08-03）

1プロジェクト内に3つの箱を並べた対照表:

| 箱 | エンティティの作り方 | 材料の紐付け方 | 結果 |
|---|---|---|---|
| `BOXTEST` | GUI `Draw → Block` | GUI ドラッグ | **15,625 voxels** |
| `PYBOX` | Python `CreateSolidBlock` | GUI ドラッグ | **3,375 voxels** |
| `PYBOX2` | Python `CreateSolidBlock` | **Python `AddMaterialSettings`** | **`not being considered`** |

そのうえで両者の材料設定のプロパティを実値で比較したところ、**完全に一致**した:
`MaterialType = MaterialTypeEnum.Dielectric` / `MassDensity = 1000.0` / `DatabaseLink = None` / `Conductivity = 0.5`。

→ **`MaterialType` 説は外れ**。設定オブジェクトの中身は同一なので、
差は **「設定とエンティティを結びつけているコンポーネント（紐付け）側」** に確定。
次は `sim.AllComponents` の各コンポーネント（`BOXTEST` / `PYBOX` / `PYBOX2`）の実体を比較する。

### ★★★★★ 根本原因を確定: エンティティが Voxeler/Grid 設定に登録されていない（2026-08-03）

- **決め手**: `sim.AllComponents` の各コンポーネントの `Settings` 辞書を比較した。

  ```
  PYBOX2（焼けない）
     Settings = {'PYBOX2 Material': MaterialSettings}

  BOXTEST / PYBOX（焼ける）
     Settings = {'Material Settings'          : MaterialSettings,
                 'Automatic'                  : AutomaticGridSettings,
                 'Automatic Voxeler Settings' : AutomaticVoxelerSettings}
  ```

- **原因**: **voxeler は「Voxeler 設定に登録されたエンティティ」だけを処理対象にする**。
  Python の `sim.AddMaterialSettings([e])` は **材料設定しか紐付けない**ので、
  σ は正しく入っているのに voxeler からは対象外＝`... is not being considered in the voxeling process.` になる。
  **GUI のドラッグは、材料への紐付けと同時に Grid / Voxeler 設定にも自動登録している**——これが両者の差だった。
- **これで 2026-07-22 以降の全事象が1本で説明できる**:
  - `Skin (Yoon-sun v3.1 Static) is not being considered` / `Elec_T7 is not being considered`
  - ボクセルシーンが空 → `0 unknowns / 0 Dirichlet points / 12,449,814 unused` → **全点 NaN**
  - `no lossy dielectrics`（voxel 化されていないので導電体が1つも無い）
  - σ 検算は毎回パスしていた（材料設定自体は正しく作られていたため）＝**誤診断が長引いた理由**
- **無罪が確定したもの**: Yoon-sun（ViP）・電極ジオメトリ・グリッド範囲・BC・材料DB（IT'IS 5.0 / LF 5.0）・
  メッシュ vs ソリッド・Python vs GUI・環境・バージョン。すべて切り分けで潰した通り。
- **修正方針（工程5）**: 材料σを割り当てたら、**同じエンティティを Voxeler 設定と Grid 設定にも登録する**。
  ```python
  vox = [s for s in sim.AllSettings if type(s).__name__ == 'AutomaticVoxelerSettings'][0]
  grd = [s for s in sim.AllSettings if type(s).__name__ == 'AutomaticGridSettings'][0]
  sim.Add(vox, [entity])
  sim.Add(grd, [entity])
  ```
  検証は `component.Settings` のキーが**3種類**（Material / Grid / Voxeler）になること、
  および `Voxel Log` に当該エンティティの `Voxels:` 行が出ること。

#### ✅ 解決を実証（2026-08-03）

`PYBOX2`（生成も材料紐付けも 100% Python）に `sim.Add(vox, [e])` / `sim.Add(grd, [e])` を追加して再ボクセル化:

```
BOXTEST   Voxels: 15625
PYBOX2    Voxels: 3375     ← 焼けた
PYBOX     Voxels: 3375
```

`not being considered` は消滅。**工程7のブロッカーは解決**。再利用レシピは
Obsidian `Claude/Knowledge/sim4life-material-assignment.md` の「★★最重要」節に集約した。
