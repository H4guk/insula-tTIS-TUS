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
