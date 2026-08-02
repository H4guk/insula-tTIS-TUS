# Phase 1 — tTIS のベース実装（dev）検証記録

対応 Issue: [#4](https://github.com/H4guk/insula-tTIS-TUS/issues/4)
目的: Yoon-sun + Montage I（T7–P7 / Fp1–Fp2）で tTIS 電場計算を**動く状態にする**（精度は Phase 2 / #7）。

このファイルは **工程を1つずつ検証した記録**。完成時に成果物としてまとめ直すための一次記録なので、
「何を確かめて / 何が分かって / 何が未確認か」を工程ごとに残す。

## 工程とスクリプトの対応（2026-07-31 決定・9工程 = 9スクリプト）

**1工程 = 1スクリプト**にする。工程3（島皮質ROI）は工程2から独立させる。

| 工程 | スクリプト | 状態 |
|---|---|---|
| 1 モデルの用意 | `load_yoonsun.py` | ある・検証済 |
| 2 座標系検出 | `detect_coordinate_system.py` | ある・検証済（ROI 算出は工程3へ分離済み） |
| 3 島皮質 ROI | `define_insula_roi.py` | **ある**（2026-07-31 新設・再計算＋妥当性検証） |
| 4 電極配置 | `place_electrodes.py` | ある・検証済 |
| 5 組織の検出・材料σ | （未作成） | 旧 `assign_materials.py` は電極スキップ（#2）・σ値未検証のため削除 |
| 6 電圧設定（BC） | （未作成） | 面BC が正解と判明済み（`error-log.md` 2026-07-30） |
| 7 グリッド → ボクセル | （未作成） | ~~ブロッカー~~ **2026-08-03 原因解決**（Voxeler/Grid 設定への登録漏れ。工程5に手順を追記済み） |
| 8 RUN | （未作成） | — |
| 9 検証 | （未作成） | — |

- `ti_analysis.py` は Step 2（Phase 2 / #7）の解析なので**9工程の外**。
- 工程5〜9 は**検証しながら1本ずつ作る**（判断の記録＝Obsidian `Claude/Decisions/2026-07-31-reset-overbuilt-scripts.md`）。
- 削除したスクリプト（診断4本・統合・ゲート・`setup_simulation.py`・`assign_materials.py`）は
  git 履歴 `3ac4756`〜`440b6e6` から復元可能。得られた知見は `error-log.md` と本ファイルに残してある。

工程ごとの検証結果は以下に記録する。

---

## 工程1: モデルの用意（Yoon-sun 読込）

**確かめたこと**: エンティティが**閉じた立体（volume を持つ）**かどうか。
ボクセル化は「立体の内側を格子で塗る」処理なので、殻（面だけ）だと塗る内側が定義できず焼かれない。
ノートに「Skin は符号付き距離を返さない＝薄い殻」（2026-07-21）と「閉じたソリッド」（2026-07-29）の
**食い違った記録**が残っていたため、ここで確定させる必要があった。

**実行**（読み取りのみ）:

```python
import s4l_v1
import s4l_v1.model as model
import XCoreModeling as xc

cands = [n for n in dir(xc)
         if any(k in n.lower() for k in ('volume', 'closed', 'solid', 'watertight', 'valid', 'mass'))]
print('API 候補:', cands)

skin = [e for e in model.AllEntities() if e.Name == 'Skin'][0]
print('Skin 型:', type(skin).__name__)
for fn in cands:
    try:    print('  %-22s -> %s' % (fn, getattr(xc, fn)(skin)))
    except Exception as e: print('  %-22s -> 呼べない (%s)' % (fn, type(e).__name__))
```

**結果**（2026-07-31）:

| 項目 | 値 |
|---|---|
| `Skin` の型 | **`TriangleMesh`** |
| `xc.IsClosedSolidBody(skin)` | **False** |
| `xc.ConvertToSolid(skin)` | RuntimeError（引数不足・オプションが必要そう） |
| `xc.MeasureVolume(skin)` | TypeError（TriangleMesh には呼べない） |
| 全エンティティ数 | 330 |
| bbox | X 0–210.3 / Y 0–515.5 / Z 0–1661.2 mm（全身・足元原点） |

**判定: 工程1は原因ではない（✅ 読込は正常）**

理由:
1. `IsClosedSolidBody` は名前のとおり **`Body`（ソリッド）型を判定する API**。`TriangleMesh` に対する False は
   「型が Body でない」ことを言っているだけの可能性が高く、**メッシュが水密かどうかの判定にはなっていない**。
2. **決定的**: 箱テスト `BOXTEST_body` は `CreateSolidBlock` で作った**本物のソリッド Body** だが、
   **それも焼けなかった**。＝ **エンティティの型は焼ける/焼けないの分かれ目になっていない**。

**未確認として残すこと**:
- ViP メッシュが水密かどうか（`IsClosedSolidBody` では判定できていない）。
  ただし上記2により、これが工程7の主因である可能性は低い。

**★追記（2026-07-31）: ViP は「ライセンス保護されたパート」で変換できない**
`xc.ConvertToSolid(skin)` を呼んだ際、Logger に

```
[ERROR] [XCore.CLog] Cannot convert licensed part
```

が出た（Python 側は `RuntimeError`）。＝ **ViP（Yoon-sun）のジオメトリは .lite ではライセンス保護されており、
ソリッドへの変換が許可されていない**。→ **「ViP を Body 化してから焼く」という回避ルートは使えない**。
ただし自作ソリッド（`CreateSolidBlock` の箱）も焼けていないので、**変換不可そのものが工程7の原因ではない**。

**無害と判定したエラー（起動時ノイズ）**:
```
Failed to define static enum for 'ScaleType' @ RecruitmentEvaluator          （ニューロン解析）
Failed to define static enum for 'MagneticProps.MaterialModel' @ _emfdtd_impl（EM FDTD・高周波）
```
どちらも Python API 初期化時の enum 登録失敗。本プロジェクトは **Electro Ohmic Quasi-Static（低周波）**
のみを使い、ニューロン解析・FDTD は触らないため無関係。ボクセル化にも影響しない。

**参照**: `Claude/Knowledge/sim4life-yoonsun-implementation.md` / `Claude/DailyLogs/2026-07-31.md`

---

## 工程2: 座標系検出（＋グリッド範囲の妥当性）

**確かめたこと**: ノートに記録された座標系の解釈が今のセッションでも正しいか。特に
**グリッド範囲 X 4–202 / Y 162–352 / Z 1450–1665 mm が本当に頭を囲んでいるか**。
囲めていなければ「焼く対象がグリッド内に無い」＝空ボクセルの直接原因になるため、工程7の候補として先に潰す。

**実行**（読み取りのみ・各エンティティの bbox をグリッド範囲と突き合わせ）:

```python
GX, GY, GZ = (4, 202), (162, 352), (1450, 1665)
for nm in ('Skin', 'Cerebrum_grey_matter', 'Skull_cortical', 'Cerebrospinal_fluid'):
    ...  # bbox を取り、GX/GY/GZ と重なるか判定
```

**結果**（2026-07-31）:

| エンティティ | X | Y | Z | グリッド内 |
|---|---|---|---|---|
| Skin（全身） | -0–210 | 0–516 | -0–1661 | ○（全身なので当然） |
| Cerebrum_grey_matter | 22–176 | 196–322 | 1531–1642 | ○ **完全に収まる** |
| Skull_cortical | 14–185 | 189–328 | 1484–1653 | ○ **完全に収まる** |
| Cerebrospinal_fluid | 22–178 | 196–322 | 1009–1646 | ○（Z1009 は脊髄側・頭部側は範囲内） |
| Elec_T7 | 84.8–104.8 | 330.5–341.2 | 1526.4–1546.3 | ○（Y 上限 352 に 11mm の余裕） |
| Elec_P7 | 32.5–50.6 | 322.0–337.4 | 1536.0–1556.2 | ○ |

**判定: 工程2は正常（✅）。原因ではない**
- 座標系の解釈（X=前後 / Y=左右 / Z=上下・単位 mm・原点は足元）はノートの記録と一致。
- **グリッド範囲は脳・頭蓋・電極をすべて含んでいる** → 「グリッドが実体と重なっていない」という筋は消えた。

**副産物**: 電極の Y 上限（341.2）とグリッド Y 上限（352）の余裕は 11mm。電極を外側に動かす最適化（Phase 3）で
グリッド範囲を広げる必要が出る可能性があるので記録しておく。

---

## 工程3: 島皮質 ROI の特定

**確かめたこと**: ROI 球 中心 (99.1, 295.0, 1562.2) / r=10mm が妥当な位置か。
判定基準はノート自身が定めたもの＝**MNI ±38, 0, 0 相当・頭皮から 3–4cm 深**。

**実行**（読み取りのみ・`xc.GetEntityPointDistance` で ROI 中心から各組織への符号付き距離）

**結果**（2026-07-31）:

| 測定 | 値 | 判定 |
|---|---|---|
| 正中 Y=260.5 からの左右オフセット | **34.5 mm** | ✅ 期待値 34.5（MNI 38mm × 脳幅補正 0.91）と一致 |
| `Cerebrum_white_matter` への距離 | **−5.6 mm（負＝内部）** | 記録どおり「ROI は白質ラベル領域に載る」 |
| `Cerebrum_grey_matter` への距離 | +5.6 mm | 灰白質の 5.6mm 内側 |
| `Skull_cortical` への距離 | +15.8 mm | — |
| `Skin` への距離 | **+25.0 mm** | ⚠️ ノート基準「3–4cm」より 5mm 浅い |
| ROI 球（r=10mm）がグリッド内 | True | ✅ |

**判定: 工程3は「決定どおりの位置にある」（✅）。ただし深さの基準からは 5mm 外れる**

**★副産物: 7/21 と 7/29 の記録の食い違いが解けた**
「Skin は符号付き距離を返さない」（7/21）vs「閉じたソリッド」（7/29）の矛盾は、**Skin が薄い層**であることが原因。
頭の内側の点は「皮膚層の**外側**」なので正の距離になる。一方 `Cerebrum_white_matter` は塗られた体積なので
内部の点は **−5.6mm** と負で返る ＝ **符号付き距離は正常に機能している**。
7/21 の記録は「Skin という薄い層に対しては内外判定に使えない」が正確な表現。

**未解決として残すこと（Phase 2 / #7 で扱う）**:
- 頭皮からの深さ 25.0mm は、ノート基準 30–40mm を下回る。
  Yoon-sun は脳幅 127mm（MNI 140mm の 0.91倍）の小さめの頭なので換算すると 27–36mm 相当で、**その下限をわずかに割る**。
  また測定値は「最近傍の皮膚点までの距離」であり、側頭部の皮膚が近い方向に引っ張られる性質がある。
- ＝ **致命的ではないが基準外**。ROI 精度は Phase 2 の論点なので、そこで「深さ基準を Yoon-sun スケールに合わせて
  再定義する」か「ROI 中心を数 mm 内側へ寄せる」かを判断する。→ Issue #9 に切り出した。

---

## 工程4: 電極配置（皮膚への接触）

**確かめたこと**: 電極パッドが**皮膚に接触しているか**。
lec6 の教訓「電極と皮膚の間にすき間があると空気になって電流が入らない」への対応として、
電極は皮膚に **1.5mm めり込ませ＋外側 2.0mm**（厚 3.5mm・直径 20mm）で作ってある。それが効いているかを検証する。
工程3で符号付き距離が機能することを確認できたので、この検証が可能になった。

**結果**（2026-07-31）:

| 電極 | 中心 | 皮膚までの距離 | bbox サイズ |
|---|---|---|---|
| Elec_T7 | (94.8, 335.8, 1536.4) | +0.25 mm | 20.1 × 10.6 × 19.9 |
| Elec_P7 | (41.6, 329.7, 1546.1) | +0.22 mm | 18.1 × 15.5 × 20.3 |
| Elec_Fp1 | (184.6, 286.9, 1566.1) | +0.24 mm | 9.4 × 20.1 × 20.0 |
| Elec_Fp2 | (184.4, 235.5, 1562.4) | −0.25 mm | 8.6 × 20.2 × 20.1 |

**判定: 工程4は正常（✅）**
- 4枚すべて中心が皮膚層から **±0.25mm**＝実質的に皮膚面上。設計（内 1.5mm / 外 2.0mm）から、
  **パッドが皮膚をまたいでいる＝すき間なし**と言える。符号 ±0.25 は薄い層への最近傍距離なので内外の意味はない。
- サイズは **直径 20mm・厚 3.5mm の円板が座標軸に対して 20〜25° 傾いている**と読める
  （2辺が 20mm 前後＝直径、残り1辺 8.6〜15.5mm＝傾いた厚み）。軸を皮膚法線に向けている設計どおり。

**未確認として残すこと**:
- 電極モデルの簡略化（我々＝σ 1.6 の円板1層 / Inoue 2025＝導電ゴム σ0.1 厚1mm ＋ 生理食塩水スポンジ σ1.6 厚5mm の 20mm角）。
  dev では簡略化のままで良いが、**レポートに限界として明記**する必要がある → Phase 2（#7）のチェックリスト。
- 目視確認は未実施（3Dビューのピボット問題が未解決）。数値では確認できているので dev では問題なし。


---

## 工程7 突破のための手順（ブロッカー）

現象・切り分け・最小再現ケースは `error-log.md`（2026-07-31）にまとめてある。ここでは手順だけ書く。

### 鉄則（NaN を避ける順序）
**材料σ（組織＋電極）→ 電極BC（面に付ける）→（全部終えてから最後に）`CreateVoxels` → Run → ログ確認。**
ボクセル化は割り当てのスナップショットなので、割り当て後に必ず作り直す。各段のあと `document.Save()`。

### 手順
1. ブラウザ／プロジェクトを**完全リロード**（壊れ sim・古い GridBox・旧結果を捨てる）。
2. 工程1 → 工程2 → 工程3 → 工程4 を順に実行（`load_yoonsun.py` → `detect_coordinate_system.py`
   → `define_insula_roi.py` → `place_electrodes.py`）。
3. 工程5（材料σ）: 頭部59組織 ＋ **駆動電極にも σ=1.6**。割り当て後に **期待値（61）と実数を突き合わせる**。
   σ の値は **`sim.AllSettings`** を回して `MaterialSettings` から読む（`AllComponents` は σ を持たない）。
   ★**2026-08-03 追加・最重要**: σ を付けただけでは **voxeler の対象にならない**。同じエンティティを
   **Voxeler 設定と Grid 設定にも登録する**こと（これが 7/22〜8/3 のブロッカーの根本原因だった）:

   ```python
   vox = [s for s in sim.AllSettings if type(s).__name__ == 'AutomaticVoxelerSettings'][0]
   grd = [s for s in sim.AllSettings if type(s).__name__ == 'AutomaticGridSettings'][0]
   for e in entities:
       sim.Add(vox, [e])
       sim.Add(grd, [e])
   ```

   検証は `component.Settings` のキーが **3種類**（Material / Grid / Voxeler）になること。
   詳細レシピ → Obsidian `Claude/Knowledge/sim4life-material-assignment.md`「★★最重要」節。
4. 工程6（BC）: Dirichlet を**電極の外側の面**に付ける（`xc.GetFaces` → `IsPlanarFace` →
   頭の中心 (96.5, 258.9, 1566.8) から最も遠い平面）。ソリッドに直接付けると Run が拒否される。
5. 工程7（グリッド→ボクセル）: 体 5mm ＋ 頭部 Block 1mm → `UpdateGrid()` → `CreateVoxels()`。
   **`Voxeler.log` の `Voxel Scene Memory Consumption` が MB 級になっているか**を必ず確認する。
6. 工程8（RUN）→ 工程9（検証）: `Input.log` の `Degree of freedoms` 行で
   **`unknowns > 0` かつ `Dirichlet points > 0`**、E 場の **finite 率 ≈ 100%** を確認。

### ログの取り方
結果ディレクトリは **`os.path.dirname(sim.GetOutputFileName())`** で取れる。
その中の `*_Voxeler.log` / `*_Input.log` の最新を読む。見るべき行:

| ログ | 見る行 | 正常な状態 |
|---|---|---|
| `Voxeler.log` | `Voxel Scene Memory Consumption` | **kB 級で正常**（★2026-08-03 訂正: 旧記述「MB 級」は誤り。動作実績のある `Lec8-practice`（251,378 セル）の実測が **0.132734 kB / 0.229 s**。判定は絶対値でなく**動く sim との相対比較**で行う。失敗例＝421,875 セルで 0.003414 kB / 0.0128 s） |
| `Voxeler.log` | `... is not being considered in the voxeling process` | **出ないこと** |
| `Input.log` | `Degree of freedoms: ... N unknowns, M Dirichlet points` | **N > 0 かつ M > 0** |

### それでも通らない場合: ZMT サポート/フォーラムへの照会

送り先: `s4l-support@zmt.swiss` / https://forum.zmt.swiss/
添付: `Input.log`・`Voxeler.log`・最小再現コード・Explorer のツリーのスクリーンショット。

送る前のチェック:
- [ ] リロード済みの素のセッションで再現することを確認した
- [ ] 最小再現ケース（ViP・電極・BC を使わない箱1個）で再現することを確認した
- [ ] `Voxel Scene Memory Consumption` の実測値を本文に書いた

照会文（英語・骨子）:

> I am using Sim4Life.lite (free student licence) and building an Electro Ohmic Quasi-Static
> simulation from the Python console. `CreateVoxels()` completes ("Voxeling succeeded") but the
> voxel scene is essentially empty (`Voxel Scene Memory Consumption: 0.001196 kB`), and the
> voxeler reports `Error: The material component '<name>' is not being considered in the voxeling
> process.` The solver then reports `0 unknowns, 0 Dirichlet points` and all field values are NaN.
>
> This reproduces with a **minimal case that uses neither the anatomical model nor any boundary
> condition**: a single solid block created with `CreateSolidBlock`, one `AddMaterialSettings` with
> `ElectricProps.Conductivity = 0.5`, a manual global grid, then `CreateVoxels()`.
> It also reproduces in a freshly reloaded session, so it is not leftover session state.
>
> Which registration step makes an entity "considered" by the voxeler? Is there a step, in addition
> to `AddMaterialSettings`, that adds the entity to the simulation's model / solid region
> (the solver warning says "Check your model and solid region settings")?
> `AssignEntities` appears to have been removed in v10 — what replaces it?
