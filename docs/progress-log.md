# 進捗ログ

> 詳細な時系列は Obsidian の `Claude/DailyLogs/` に記録。ここは本リポジトリ視点の要約。

## 現在地（2026-07-23 時点）
tTIS フェーズ1 の配管を Yoon-sun 上で構築中。**Step 1 は未完了**（材料σを組んで Run まで到達したが全点 NaN）。

- ⚠️ 直近の Run は全点 NaN（`no used dofs / no lossy dielectrics`＝σを持つ導電領域が無いとソルバーが判断）。
  Run 自体は「finished successfully」で終わるが解が空。E 場・電位とも nan。
- 原因は未確定。①保存忘れによる状態喪失で不整合になった状態のせいか、②`LinkMaterialWithDatabase` が
  σ を実際にセットしていない仕様か、切り分けできていない（材料設定に GlobalMaterialSettings が混在する等の
  不整合も観測 → ①の疑いが濃い）。
- 方針: **完全にクリーンな新規プロジェクトで記録通りに組み直す**（各ステップ後に `document.Save()`）。
  Run 前に SolverLog の "used dofs" を確認。再発したら σ 直接設定（ElectricProps.Conductivity）へ切替を検討（未検証）。

## 到達済み
- Yoon-sun 読み込み（Python 経由・GUI 不可）。
- 座標系の実測確定（+X=前 / +Y=左 / +Z=上・AC-PC 傾き 3.18°＝補正不要）。
- 島皮質 ROI 確定（粗 ROI 球・中心 (99.1,295.0,1562.2)mm・r=10mm・左）。
- Montage I 電極の座標算出 → 皮膚投影 → 電極パッド 4 枚生成（Elec_T7/P7/Fp1/Fp2）。
- グリッド設定（頭部 1mm / 体 5mm）→ CreateVoxels → 次元 [229,221,246]≈1229万セル（2000万以内 OK）。
- TI 定量の道具立て（SAM head で `get_E`＋`2·min` を検証・深部 TI 6.404 再現）。

## 未達（Step 1 の残り）
- 材料σを効かせて Run を成功させる（現状 no lossy dielectrics で全点 NaN）。← ★次回の最優先

## 次工程（Step 1 完了 → Step 2）
1. クリーンな新規プロジェクトで load → detect → place → assign → setup を順に実行（各後で Save）。
2. **材料σが効いているか Run 前に検証**（SolverLog の used dofs / 個別材料の σ）。効かなければ σ 直接設定へ。
3. ペア1（T7–P7・2000Hz）／ペア2（Fp1–Fp2・2010Hz）を別シミュで Run。
4. `ti_analysis.py` で TI=2·min(|E1|,|E2|) → 島皮質 ROI の体積重み平均 → 選択性を ≈0.40 と照合。
5. 位置最適化（重い工程）→ その後 TUS を同一 Yoon-sun・同一 ROI で組んで比較。
