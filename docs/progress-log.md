# 進捗ログ

> 詳細な時系列は Obsidian の `Claude/DailyLogs/` に記録。ここは本リポジトリ視点の要約。

## 現在地（2026-07-30 時点）
tTIS フェーズ1 の配管を Yoon-sun 上で構築中。**Step 1 は未完了**だが、長年の全点 NaN の**真因を特定・修正**した。残る壁は Run 起動拒否のみ。

### ✅ 全点 NaN の真因を確定（2026-07-30・SolverLog + Voxeler.log で決着）
- `Input.log`: `Degree of freedoms: ... 0 unknowns, 0 Dirichlet points, ... no lossy dielectrics`
- `Voxeler.log`: **`Error: The boundary component 'Elec_T7' is not being considered in the voxeling process.`**
- **真因 = 駆動電極 Elec_* に材料を割り当てていなかった**。材料の無いエンティティは Voxeler がボクセル化しない
  → 電極が除外 → Dirichlet BC が実体を持たず Dirichlet=0、導電領域も書かれず no lossy dielectrics → 解く dof ゼロ → NaN。
  （保存忘れでも DBリンク仕様でもなかった。）
- **修正**: 駆動電極 Elec_T7/P7 に σ=1.6 S/m を直接付与すれば Voxeler が電極を含める。

### ⚠️ 残る壁: Run 起動拒否
- `sim.RunSimulation()` が `RuntimeError: Unable to run simulation. Please check your simulation settings.` を返す。
- 比較的クリーンな sim でも発生。加えて**同一セッションで作り直しを重ねると** `incompatible with this type of simulation`（run済み sim への設定追加）や
  `HDF5: attribute already exists`（同名 sim/GridBox/結果ファイルの衝突）が出る＝**セッションの状態クラッタ**。
- **未検証**: 「セッションを完全リロードした真っさらな状態」で統合スクリプトを流すこと（これまでは汚れたセッション上で実行していた）。

## 到達済み
- Yoon-sun 読み込み（Python 経由・GUI 不可）。
- 座標系の実測確定（+X=前 / +Y=左 / +Z=上・AC-PC 傾き 3.18°＝補正不要）。
- 島皮質 ROI 確定（粗 ROI 球・中心 (99.1,295.0,1562.2)mm・r=10mm・左）。
- Montage I 電極の座標算出 → 皮膚投影 → 電極パッド 4 枚生成（Elec_T7/P7/Fp1/Fp2）。
- 材料σ割り当て（頭部59組織・IT'IS LF DB）＋ **アンダースコアマッチ修正**（`[a-z0-9]+`）＋ **電極にも材料**。
- **全点 NaN の真因特定＋修正**（電極の材料漏れ）。
- 統合スクリプト `scripts/run_step1_lf1.py`（全修正込み・クリーン実行用）を用意。

## 未達（Step 1 の残り）
- Run 起動拒否（`check your simulation settings`）を解消して有効な E 場を得る。← ★次回の最優先
  - まず「完全リロード → 統合スクリプト」で状態クラッタを排した真のクリーン実行を試す。
  - それでも拒否なら Sim4Life サポート/フォーラムへ `Input.log` 付きで照会（ツール固有の検証エラー）。

## 次工程（Step 1 完了 → Step 2）
1. **Sim4Life を完全リロード**（汚れたセッション＝壊れ sim・古い GridBox・旧結果を捨てる）。
2. `load_yoonsun.py` → `place_electrodes.py` → **`run_step1_lf1.py`**（組織59＋電極2＋BC＋グリッド＋voxel を一括・`材料数 61 / 未マップ []` を確認）。
3. `sim.RunSimulation(wait=True)` → E 場の `finite率 ≈100%` と `Degree of freedoms` の `Dirichlet points>0` を確認。
   - 拒否が続く場合はサポート照会へ。
4. ペア2（Fp1–Fp2・2010Hz）を同じ作りで `tTIS_LF2` として組み Run。
5. `ti_analysis.py` で TI=2·min(|E1|,|E2|) → 島皮質 ROI の体積重み平均 → 選択性を ≈0.40 と照合。
6. 位置最適化（重い工程）→ その後 TUS を同一 Yoon-sun・同一 ROI で組んで比較。
