# Step 1 の全点 NaN を潰す手順（クリーン再構築 + Run 前ゲート）

## 症状と意味
Run は "finished successfully" で終わるが E 場・電位が**全点 NaN**。SolverLog:

```
Degree of freedoms: 12449814 total, 0 unknowns, 0 Dirichlet points, 12449814 unused.
WARNING: The system has no used degrees of freedom (dofs). ... no lossy dielectrics
```

→ ボクセル格子に **導電セルが 0・電極BCノードが 0**。σ の値ミスではなく、**材料も BC もボクセルモデルに載っていない**（未反映）。材料と BC が同時に消える＝「割り当てがボクセル化に届いていない」問題。

## 原因（効きやすい順）
1. **ボクセル化の順序/古さ** — 割り当て前に（or 後に作り直さず）`CreateVoxels` した。
2. **sim 未登録** — v10 では Python 作成 sim は `document.AllSimulations` に自動登録されない。Run が空パイプラインを見た。
3. **保存忘れの壊れ状態** — GlobalMaterialSettings 混在・材料数が 59→44→46 と変動。
4. σ が実際に入っていない（DBリンク未反映）。単独では 0 Dirichlet を説明できないので主因ではない。

## 鉄則（NaN を避ける順序）
**材料σ → 電極BC →（全部終えてから最後に）CreateVoxels → Run → SolverLog 確認。**
ボクセル化は割り当てのスナップショットなので、割り当て後に必ず作り直す。各段のあと `document.Save()`。

## 手順（クリーンな新規プロジェクトで最初から）
1. **新規プロジェクト**を作る（壊れた既存はデバッグせず捨てる）。
2. `scripts/load_yoonsun.py` → Yoon-sun 読み込み。`document.Save()`。
3. `scripts/detect_coordinate_system.py` → 座標系・ROI 確認（数値が記録と一致するか）。
4. `scripts/place_electrodes.py` → Elec_T7/P7/Fp1/Fp2 生成。`document.Save()`。
5. `scripts/assign_materials.py` → 頭部59組織にσ割り当て（sim=tTIS_LF1 が作られる）。
6. **★ここで `scripts/verify_before_run.py` を貼る**（同じ名前空間で sim/created を検査）:
   - sim を AllSimulations に登録（未登録なら Add）。
   - 各σの実値を確認。σ=0 が出たら DB material から直接コピーするフォールバックが走る。
   - `document.Save()`。
7. `scripts/setup_simulation.py` の**⑥電極BC 部分**を実行（+1V / 0V を Elec_T7 / Elec_P7 に）。`document.Save()`。
8. **最後に**グリッド設定 → `sim.CreateVoxels()`（＝割り当て後に作り直す）。`document.Save()`。
9. `sim.RunSimulation(wait=True)` → 完了後 **SolverLog の "Degree of freedoms" 行を必ず読む**。
   - `used dofs > 0` かつ `Dirichlet points > 0` → 成功（NaN 解消）。次は ti_analysis.py。
   - まだ 0 → その行をそのまま記録。原因4（σ未反映）以外、順序・登録は満たしたので次はボクセル/コンポーネントの中身を個別に見る。

## Run 拒否（`Unable to run simulation. Please check your simulation settings.`）2026-07-30〜

全点NaN の真因（電極の材料漏れ）を直した後も **Run 自体が拒否される**事象が残った。切り分け手順:

1. **ブラウザ／プロジェクトを完全リロード**（これが一番効く。前回の拒否は同名衝突が主因）。
2. `scripts/load_yoonsun.py` → `scripts/place_electrodes.py`。
3. `scripts/preflight_check.py` — 既存 sim・重複エンティティ・電極の有無を確認。
   **既存 sim が 0 件・重複なし**が理想。残骸があっても続行可（次で名前が衝突しない）。
4. `scripts/dump_logs.py` を貼る（`dump_logs()` を定義しておく。次のステップから自動で呼ばれる）。
5. `scripts/run_step1_lf1.py` — 材料(組織59+電極2=61) → BC → グリッド → CreateVoxels → **Run** まで自動。
   - sim 名は未使用のものを自動選択（`tTIS_LF1` が使用中なら `tTIS_LF1_r2`）＝**HDF5 属性衝突を構造的に回避**。
   - `GridBox_head` は既存を再利用（作り直しで重複が増えるのを防ぐ）。
   - Run の成否どちらでもログの決定的な行が自動で出る。
6. 判定:
   - `finite率 ≈ 100%` → ✅ 成功。ペア2（Fp1/Fp2）→ `ti_analysis.py`。
   - ログに `not being considered` → その電極に材料σが付いていない（＝真因の再発）。
   - ログに `HDF5 / attribute already exists` → まだ同名衝突。リロードして素の名前で1回だけ再試行。
   - どれも無く拒否のみ → **深追いしない**。`docs/support-inquiry-draft.md` で ZMT サポート/フォーラムへ
     `Input.log` 添付で照会する（ツール固有の検証エラーで、こちら側の推測では詰められない領域）。

## 記録して報告してほしいもの（次の切り分けに必要）
- `verify_before_run.py` の出力（σ=0 の組織数・フォールバックで直せた数）。
- Run 後の SolverLog "Degree of freedoms" 行（used dofs / Dirichlet points の数）。
この2つで「σ未反映か・BC未反映か・ボクセル未反映か」が確定する。
