# 統合版 再現手順（1プロジェクト・3シミュレーション）— #36 5-1

> **2026-10-14 注記（GH #17）**: ここに書かれた選択性・脳マスクの値は、当時の脳の定義（tTIS は σ 0.33〜0.44 の帯・TUS は (c, ρ) の帯）によるもの。帯には脳以外の組織が混ざり、手法ごとに定義も違っていた。現在は両手法とも Input.h5 の組織名で決めた**脳実質 12 組織（1041.5 mL）**で比べている。新旧の値の対応は `brain-mask-fix-inventory.md` §1。この記録は当時の値のまま残す。
> `tus_focus_size.py`・`ti_local_maxima.py` は 2026-10-14 に脳実質 12 組織へ替えたので、それらの期待値は変わる（TUS -6dB 焦点 2509 mm³・脳 1041.5 mL。`results/tus_focus_size_2026-10-14.txt`・`results/ti_local_maxima_2026-10-14.txt`）。`ti_analysis.py`・`tus_selectivity.py` は帯のままなので下の期待値で検算できる。

**素から作る**。`reproduce.md`（tTIS）と `reproduce-tus.md`（TUS）を1本にまとめ、
**同一の Yoon-sun 上に tTIS 2ペア ＋ TUS の3シミュレーションを並べる**（`Claude/Decisions/2026-08-25-one-model-two-simulations.md`）。

> **なぜ複製でなく素から作るか**（2026-08-27・本人判断）: Save Project As だと「元プロジェクトに何が入っていたか」が
> 暗黙のまま残る。素から通せば**統合版が1本の手順で再現できることそのものが検証になり**、
> コンテストの審査項目「手法・検証の質」にも直結する。

すべて **Sim4Life.lite の Python コンソールにファイルの中身を貼る**運用（`exec(open(...))` は不可）。
各スクリプトは前後にゲートを持ち `=== 工程N PASS ===` / `FAILED: 理由` を出す。

**所要時間の目安**: 約45〜60分（tTIS ボクセル化 5〜6分×2・tTIS Run 2分×2・TUS ボクセル化 5分・TUS Run 8分）。

---

## 分離版からの変更点（3つ）

| # | 変更 | 理由 |
|---|---|---|
| 1 | **`build_transducer.py` を電極の直後（工程5）に前倒し** | ① `Elec_T7` の重心を使う本来の設計どおりに動く（分離版は電極削除後だったので実測フォールバック値を使っていた）② **tTIS のボクセル化より前に置くことで**「ボクセル化後の設定追加は `ResetVoxels()` で解除される」（`tus-field-simulation` 4-5）を構造的に回避 |
| 2 | `assign_materials.py` の `SKIP_EXACT` に **`Transducer` / `GridBox_TUS`** を追加 | 統合では先に Transducer が存在するので、除外しないと**組織59のカウントに混入して事前ゲートで落ちる** |
| 3 | `tus_assign_materials.py` の `SKIP_EXACT` に **電極4枚**を追加 | 同上（分離版では電極を削除済みだったので表面化しなかった） |

**棲み分けの原則**: **Voxeler に登録しなければその場に存在しない**。
tTIS sim には Transducer を登録せず、TUS sim には電極を登録しない ⇒ **分離版と同じ物理条件**が保たれる。

---

## A. モデル構築（1回だけ）

| # | スクリプト | 編集する定数 | 備考 |
|---|---|---|---|
| 1 | `load_yoonsun.py` | — | GUI では読めないので Python 経由 |
| 2 | `detect_coordinate_system.py` | — | 座標系とランドマーク |
| 3 | `define_insula_roi.py` | — | **読み取り専用**。ROI の再導出と深さ判定（外側頭皮基準 40.0mm）。※ROI は実体オブジェクトを作らない＝各解析スクリプトのハードコード値 (99.1,295.0,1562.2)・r=10mm を使う |
| 4 | `place_electrodes.py` | — | 球フィット → 10-20 → 皮膚投影 → 電極パッド4枚 |
| **5** | **`build_transducer.py`** | — | **★統合版で前倒し**。椀型（F#=1.21・開口40mm・R≈48.5mm）を `Elec_T7` 重心に生成。中間体 `_tus_*` は自動削除 |

**工程5 の合否**: 生成された `Transducer` の bbox が分離版と一致すること
＝ `[75.3, 318.6, 1521.8] .. [115.4, 343.0, 1557.4]`（size `40.1 × 24.4 × 35.6`）。
ズレたら `Elec_T7` の重心か ROI 中心が違う。

## B. tTIS ペア1（T7–P7 / 2000 Hz）

| # | スクリプト | 編集する定数 |
|---|---|---|
| 6 | `assign_materials.py` | `SIM_NAME='tTIS_LF1'` / `FREQ=2000.0` |
| 7 | `setup_boundary.py` | `SIM_NAME='tTIS_LF1'` / `DRIVE=(('Elec_T7',1.0,'BC_T7_pos'), ('Elec_P7',0.0,'BC_P7_gnd'))` |
| 8 | `setup_grid.py` | `SIM_NAME='tTIS_LF1'`（**約5〜6分**） |
| 9 | `verify_voxels.py` | `SIM_NAME='tTIS_LF1'`（**8 が終了してから**） |
| 10 | `run_simulation.py` | `SIM_NAME='tTIS_LF1'`（**約2分**） |

## C. tTIS ペア2（Fp1–Fp2 / 2010 Hz）

同じ5本を差し替えて流す（リポジトリの既定値はこちら）。

| # | スクリプト | 編集する定数 |
|---|---|---|
| 6' | `assign_materials.py` | `SIM_NAME='tTIS_LF2'` / `FREQ=2010.0` |
| 7' | `setup_boundary.py` | `SIM_NAME='tTIS_LF2'` / `DRIVE=(('Elec_Fp1',1.0,'BC_Fp1_pos'), ('Elec_Fp2',0.0,'BC_Fp2_gnd'))` |
| 8' | `setup_grid.py` | `SIM_NAME='tTIS_LF2'` |
| 9' | `verify_voxels.py` | `SIM_NAME='tTIS_LF2'` |
| 10' | `run_simulation.py` | `SIM_NAME='tTIS_LF2'` |

## D. TUS（250 kHz）

| # | スクリプト | 備考 |
|---|---|---|
| 11 | `tus_assign_materials.py` | Acoustic(LAPWE) sim `TUS_250k` 作成・59組織＋Transducer に ρ/c/α。**電極は除外**（変更点3） |
| 12 | `tus_setup_source.py` | SourceSettings（正弦波・参照1MPa・位相0）を Transducer にバインド |
| 13 | `tus_setup_grid.py` | 箱（頭部∪Transducer＋余白10mm）に Manual 1mm・Global 5mm → UpdateGrid → CreateVoxels（**約5分**） |
| 14 | `tus_verify_voxels.py` | **13 が終了してから**。`Transducer` が baked・`not being considered=0` |
| 15 | `tus_run.py` | ClearResults → Run（**約470秒**） |

## E. 解析（すべて読み取り専用）

| # | スクリプト | 何が出るか |
|---|---|---|
| 16 | `verify_grid_order.py` | flat 配列の並び順（X-fastest）。以降すべての前提 |
| 17 | `sigma_map.py` | `σ = 2·loss/\|E\|²` の規約確定と脳マスク体積 |
| 18 | **`ti_analysis.py`** | ★tTIS の TI 包絡 → ROI 定量 → **選択性** |
| 19 | **`tus_selectivity.py`** | ★TUS の脳マスク＋**選択性**・MI/ISPPA |
| 20 | `probe_geometry_match.py` | 統合後のエンティティ数・指紋（分離版と突き合わせ） |
| 21 | `probe_cell_limit.py` | 3 sim のセル数（合計は上限を超えてよい＝sim 単位） |

---

## 5-1g 一致確認（分離版を再現できるか）

移植で壊れていないことの検査。**ここが合わなければグリッド・材料割り当て・座標系のどこかが違う**。

| 指標 | 分離版の値 | 出所 |
|---|---|---|
| tTIS グリッド | `228 x 220 x 245 = 12.289 MCells`（両ペア共通） | 工程8 の出力 |
| tTIS ROI 内 TI（体積重み平均） | **0.2265 V/m**（ROI 中心セル 0.2229） | 工程18 |
| **tTIS 選択性（脳 WM+GM − ROI）** | **0.3758** | 工程18 |
| tTIS 脳マスク | **945 mL** | 工程17/18 |
| TUS グリッド | `220 x 212 x 237 = 11.05 MCells` | 工程13 |
| TUS ROI 中心 \|p\| | **1.26 MPa**（参照1MPa 駆動） | 工程19 |
| **TUS 選択性（脳broad − ROI）** | **0.198** | 工程19 |
| TUS -6dB 焦点体積 | **2576 mm³**（分離版・(c, ρ) 帯。2026-10-14 以降の `tus_focus_size.py`〔統合版・12 組織〕では **2509 mm³**） | `tus_focus_size.py` |
| エンティティ数 / 指紋 | 統合版は **333 個**（tTIS 331 ＋ `Transducer` ＋ `GridBox_TUS`）の見込み | 工程20 |

⚠️ **tTIS のセル数が 12.289 MCells から変わる可能性**: 統合版では `Transducer` と `GridBox_TUS` が
同居するため `Model`（全体グループ）の bbox が広がる（分離版 TUS で x −6..212・z 0..1675 を確認）。
tTIS sim に Transducer を登録しない限り影響しないはずだが、**工程8 の出力で必ず確認する**。
変われば TI も選択性も変わるので、その場合は原因を切り分けてから先へ進む。

## 守る順序と落とし穴（分離版から継承）

- **工程6 → 7 → 8 の順は鉄則**。先にボクセル化すると工程7 の設定追加が `incompatible` で弾かれる。
- **ボクセル化（8 / 13）と判定（9 / 14）は別スクリプト**。実行中のスクリプトからは自分が焼いた
  `Voxeler.log` が見えない（ファイルが現れるのはスクリプト終了後）。
- **焼き直すと既存の Run 結果は破棄される**（`run_simulation.py` が `ClearResults` する）。
- **同名 sim があると工程6 / 11 は中断する**。作り直すときは Explorer から先に削除。
- **TI 包絡には両ペアが同一グリッドである必要がある**。工程8 の `Grid ... MCells` が両ペアで一致すること。
- **TUS の Source 実体は材料が無いとボクセル化されず Run が `map::at` で落ちる**（工程11 で Transducer にも材料を付ける）。
