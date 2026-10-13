# TUS（Phase 4）再現手順

> **2026-10-14 注記（GH #17）**: ここに書かれた選択性・脳マスクの値は、当時の脳の定義（tTIS は σ 0.33〜0.44 の帯・TUS は (c, ρ) の帯）によるもの。帯には脳以外の組織が混ざり、手法ごとに定義も違っていた。現在は両手法とも Input.h5 の組織名で決めた**脳実質 12 組織（1041.5 mL）**で比べている。新旧の値の対応は `brain-mask-fix-inventory.md` §1。この記録は当時の値のまま残す。
> 旧いスクリプト（`tus_selectivity.py`）は今も (c, ρ) の帯を使うので、下の期待値（選択性 0.1978 / 0.2054）はその検算用として有効。

`docs/reproduce.md`（tTIS）の TUS 版。sim `TUS_250k` を素から再現し、選択性まで出す。
tTIS の `phase2-prod.md` / `phase4-tus.md` と対で使う。

## 前提・実行環境

- **Sim4Life.lite の Python コンソールに各スクリプトの全文を貼り付けて実行**する
  （このコンソールはリポジトリのファイルを見えないので `exec(open(...))` は不可・全文コピペ）。
- ベースは **tTIS プロジェクトの複製**（同一 Yoon-sun・同一 ROI を共有＝tier-1 条件）。

## 手順

### 0. プロジェクト準備（GUI）
1. tTIS プロジェクト（`tTIS_LF1`/`LF2`・Yoon-sun・電極 `Elec_*` がある）を開く。
2. **Save Project As** で TUS 用コピー（例 `insula-TUS`）にして、以降はコピーで作業。

### 1. トランスデューサ作成 — `build_transducer.py`
- 椀型（球面キャップ）を T7 に生成。焦点=ROI中心、R=焦点距離（実測≈48.5mm）・開口D=40mm・F#≈1.21。
- 設置点は `Elec_T7` の重心を使う（無ければスクリプト内の実測フォールバック `(94.8,335.8,1536.4)` を使用）。
- ⇒ **この直後に**、GUI で不要物を削除: `tTIS_LF1`/`tTIS_LF2` シミュ・`Elec_T7/P7/Fp1/Fp2`・`GridBox_head`。
  **Yoon-sun（Skin・各組織）と Transducer は残す**。

### 2. 材料割り当て＋Voxeler登録 — `tus_assign_materials.py`
- Acoustic(LAPWE) sim `TUS_250k`（f=0.25MHz・Periods=40）を作り、頭部59組織に ρ/c/α(250kHz) を IT'IS 5.0 から割当。
- **★Transducer にも材料（水相当 1000/1500/0）を付ける**（2026-08-25 統合済み。これが無いと Run が `[Point Source]+map::at` で落ちる）。
- Voxeler に 59組織＋Transducer を登録。`=== T-2 PASS ===` を確認。
- ※ 統合により **`tus_fix_transducer_material.py` は素の再現では不要**（`scripts/archive/` に回復用として残置）。

### 3. 音源 — `tus_setup_source.py`
- SourceSettings（正弦波・参照振幅 1 MPa・位相0）を作り Transducer をバインド。`=== T-3 PASS ===`。

### 4. グリッド→ボクセル化 — `tus_setup_grid.py` → `tus_verify_voxels.py`
- 頭部∪Transducer＋余白10mm の箱に Manual 1mm・周辺5mm。UpdateGrid でセル数（≈11.05 MCells・<2000万）を確認。
- CreateVoxels（焼成・約300秒待ち＋保存）。**このスクリプトが終わってから** `tus_verify_voxels.py` を実行して判定
  （実行中のスクリプトからは自分が焼いた Voxeler.log が見えないため・tTIS と同じ）。`Transducer` が baked・`not being considered=0` を確認。

### 5. Run — `tus_run.py`
- ClearResults → RunSimulation（約470秒＠Periods40）。`Overall Field` に `p(x,y,z,f)`/`Intensity`/`SAR` 等が出る。全域 finite・非ゼロを確認。

### 6. 解析
- **選択性**: `tus_selectivity.py` — Input.h5 の voxels→(c,ρ) で脳マスクを厳密構築し、|p| 体積重み平均で選択性（≈0.20）。
- **焦点位置/ROI**: `tus_focus_analysis.py`、軸プロファイル: `tus_axial_profile.py`。
- **焦点サイズ（5-2）**: `tus_focus_size.py` — 脳内 |p| ピークから -6dB（0.5×）の連結領域を切り出し、体積・ビーム軸長・側方径を実測（設計値 7.3/61.7mm の置き換え）。頭部全域版も出して頭皮 near-field と分離しているか確認する。
- **安全指標**: MI/ISPPA は `tus_selectivity.py` 内 or 4-4a の抽出（`docs/phase4-tus.md` 参照）。

## ロック回避の鉄則（tTIS と共通・TUS 固有）
- 材料・設定の**追加はボクセル化の前**（後だと `incompatible with this type of simulation`）。後から足すなら `sim.ResetVoxels()`。
- `SetupSettings`（Periods 等）の変更は **`HasResults` 中はロック**＝先に `sim.ClearResults()`。
- Source 割当の実体（Transducer）は**材料が無いとボクセル化されない**＝必ず材料を付ける（手順2で統合済み）。

## 再現確認（2026-08-26）
- 手順2の統合（Transducer 材料を assign に内包）後、**素から end-to-end 再実行し再現を確認済み**:
  T-2 PASS（59組織＋Transducer_mat・voxeler 60/60）→ T-3 PASS → グリッド 11.054 MCells → T-5b PASS（Transducer 3960 voxels＝**fix なしで焼ける**）→ **RUN OK（465秒・map::at 出ず）** → 選択性 **0.1978(脳)/0.2054(GM+WM)** ＝以前の値と完全一致。
- ⇒ **`tus_fix_transducer_material.py` は不要**（`scripts/archive/` に回復用として残置）。統合版だけで「押すだけ再現」できる。
