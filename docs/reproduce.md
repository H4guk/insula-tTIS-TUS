# 再現手順（Phase 2 prod の数値を出すまで）

最終更新: 2026-08-12 ／ 到達点: **選択性 0.3758**（Inoue 2025 の ≈0.40 の 0.94×）

すべて **Sim4Life.lite のブラウザ版 Python コンソールにファイルの中身を貼る**運用。
各スクリプトは前後にゲートを持ち、`=== 工程N PASS ===` / `FAILED: 理由` を1行で出す。

**所要時間の目安**: モデル構築 ＋ 約25分（工程7-a が各5〜6分・Run が各約2分）。

---

## A. モデル構築（新規プロジェクトで1回だけ）

| # | スクリプト | 編集する定数 | 備考 |
|---|---|---|---|
| 1 | `load_yoonsun.py` | — | 工程1。GUI では読めないので Python 経由 |
| 2 | `detect_coordinate_system.py` | — | 工程2。座標系とランドマーク |
| 3 | `define_insula_roi.py` | — | 工程3。**読み取り専用**。ROI の再導出と深さ判定（外側頭皮基準 40.0mm） |
| 4 | `place_electrodes.py` | — | 工程4。球フィット → 10-20 → 皮膚投影 → 電極パッド4枚 |

> 既にモデルと電極があるプロジェクトを使う場合は A を飛ばせる。
> 工程5 の事前ゲート（電極4枚・組織59・タグ無し0件）が A の成否を兼ねて検査する。

## B. ペア1（T7–P7 / 2000 Hz）

| # | スクリプト | 編集する定数 |
|---|---|---|
| 5 | `assign_materials.py` | `SIM_NAME='tTIS_LF1'` / `FREQ=2000.0` |
| 6 | `setup_boundary.py` | `SIM_NAME='tTIS_LF1'` / `DRIVE=(('Elec_T7',1.0,'BC_T7_pos'), ('Elec_P7',0.0,'BC_P7_gnd'))` |
| 7 | `setup_grid.py` | `SIM_NAME='tTIS_LF1'`（**約5〜6分**） |
| 8 | `verify_voxels.py` | `SIM_NAME='tTIS_LF1'`（**7 が終了してから**） |
| 9 | `run_simulation.py` | `SIM_NAME='tTIS_LF1'`（**約2分**） |

## C. ペア2（Fp1–Fp2 / 2010 Hz）

同じ5本を差し替えて流す。**リポジトリの既定値はこちら**なので、C から始めるなら編集不要。

| # | スクリプト | 編集する定数 |
|---|---|---|
| 5' | `assign_materials.py` | `SIM_NAME='tTIS_LF2'` / `FREQ=2010.0` |
| 6' | `setup_boundary.py` | `SIM_NAME='tTIS_LF2'` / `DRIVE=(('Elec_Fp1',1.0,'BC_Fp1_pos'), ('Elec_Fp2',0.0,'BC_Fp2_gnd'))` |
| 7' | `setup_grid.py` | `SIM_NAME='tTIS_LF2'` |
| 8' | `verify_voxels.py` | `SIM_NAME='tTIS_LF2'` |
| 9' | `run_simulation.py` | `SIM_NAME='tTIS_LF2'` |

## D. 解析（すべて読み取り専用・保存しない）

| # | スクリプト | 何が出るか |
|---|---|---|
| 10 | `verify_grid_order.py` | flat 配列の並び順（X-fastest）の検証。**以降すべての前提** |
| 11 | `sigma_map.py` | 損失密度の規約の確定（`σ = 2·loss/\|E\|²`）と σ マップ・脳マスクの体積 |
| 12 | **`ti_analysis.py`** | **★TI 包絡 → ROI 定量 → 選択性**。ここで最終数値が出る |
| 13 | `ti_focus_size.py` | **（#36 5-2）TI 包絡の -6dB 焦点サイズ**。⚠️ **ピーク基準は tTIS では成立しない**と判明（脳内 TI 最大は標的から 96.6mm の電極側）。数値は無効・経緯は `comparison-framework.md` §4 |
| 14 | `ti_local_maxima.py` | **（#36 5-2b）焦点の有無の切り分け**。ROI 中心 ±40mm の箱で脳内の局所極大（26近傍）を列挙し、ROI 中心を通る X/Y/Z プロファイルを出す。島皮質に山があるか／電極側への裾かを判定する |
| 13 | `audit_materials.py` | 材料対応表（`material-audit.md` の中身・レポート用） |

補助（必要なときだけ）:

| スクリプト | 用途 |
|---|---|
| `current_scale.py` | 電流スケールの内訳（損失積分・面積分・面積分のプロファイル）。`ti_analysis.py` が同じ計算を内部で再実行するので**必須ではない** |
| `probe_material_source.py` | 材料がどの DB 由来かの切り分け。DB を疑うときだけ |

> **既に両ペアを Run 済みのプロジェクトが手元にあるなら、`ti_analysis.py`（#12）を1本流すだけで
> 選択性まで出る。** A〜C はモデルから作り直す場合の手順。

---

## 守る順序と落とし穴

- **工程5 → 6 → 7 の順は鉄則**。先にボクセル化すると工程6 の設定追加が
  `incompatible with this type of simulation` で弾かれる。
- **工程7 は 7-a（焼成 `setup_grid.py`）と 7-b（判定 `verify_voxels.py`）に分かれている。**
  **実行中のスクリプトからは自分が焼いた `Voxeler.log` は見えない**（ファイルが現れるのは
  スクリプト終了後）。7-a が終わってから 7-b を貼る。同一スクリプト内で待つ設計は原理的に成立しない。
- **工程7 で焼き直すと既存の Run 結果は破棄される**（`run_simulation.py` が再実行前に
  `ClearResults` する）。ペアを作り直したら工程8・9 も回し直す。
- **工程5 は同名 sim があると中断する。** 作り直すときは Explorer から先に削除する。
- **TI 包絡には両ペアが同一グリッドである必要がある。** 工程7 の出力文字列
  （`Grid 228 x 220 x 245 = 12.289 MCells`）が両ペアで一致することを必ず確認する。
  `run_simulation.py` の `total` と `NaN` 数が一致するのも同じことの裏取り。

## 期待される実測値（2026-08-12）

| 工程 | 期待される出力 |
|---|---|
| 5 | `材料 42/42 解決` / 完全一致でない解決は **Skull 系2件のみ** / `sigma check NG: 0` |
| 6 | 駆動2枚に `BC_*`・非駆動2枚は Voxeler のみ / 電位 1.0 と 0.0 |
| 7-a | `Grid 228 x 220 x 245 = 12.289 MCells`（両ペア共通） |
| 7-b | `reports=61 (expected 61)` / `not being considered 0` / `empty=1`（`Commissura_anterior`） |
| 8 | `total=12449814` / unknowns ≈ 4.08 M / dirichlet ≈ 27 k |
| 9 | 材料領域の非ゼロ率 **99.96〜99.98 %** / `NaN=8350465`（unused との相対差 ≈0.001） |
| 10 | `GetCellCenter` と X-fastest 解釈が一致・`\|E\|` 最大セルが駆動電極から 7〜12mm |
| 11 | `σ = 2·loss/\|E\|²` が既知値を **61.1 %** で再現（もう一方は 12.1 %） |
| 12 | ROI 体積 **4.186 mL** / ROI 内 σ 中央値 **0.3480** / **選択性 0.3758** |
| 13 | 欠陥 0 件・多対1 は7材料 |

数値の意味と限界 → `phase2-prod.md`。材料の一覧 → `material-audit.md`。経緯 → `progress-log.md`。
