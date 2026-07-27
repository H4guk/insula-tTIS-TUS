# 進捗ログ

> 詳細な時系列は Obsidian の `Claude/DailyLogs/` に記録。ここは本リポジトリ視点の要約。

## 現在地（2026-07-27 時点）
tTIS フェーズ1 の配管を Yoon-sun 上で構築中。**Step 1（材料σ割り当て）まで完了**。
次は **Step 2（電極駆動 → 2 シミュ Run → ROI 内 TI 定量）**。

- ⚠️ 直近の Run は全点 NaN（`no used dofs / no lossy dielectrics`）。原因は保存忘れによる状態喪失の疑い。
  → **新規プロジェクトで記録通りに組み直す**方針（各ステップ後に `document.Save()`・Run 前に skin σ=0.465 を再確認）。

## 到達済み
- Yoon-sun 読み込み（Python 経由・GUI 不可）。
- 座標系の実測確定（+X=前 / +Y=左 / +Z=上・AC-PC 傾き 3.18°＝補正不要）。
- 島皮質 ROI 確定（粗 ROI 球・中心 (99.1,295.0,1562.2)mm・r=10mm・左）。
- Montage I 電極の座標算出 → 皮膚投影 → 電極パッド 4 枚生成（Elec_T7/P7/Fp1/Fp2）。
- 材料σ割り当て（頭部 59 組織・IT'IS LF DB 自動リンク + skin 上書き）。
- TI 定量の道具立て（SAM head で `get_E`＋`2·min` を検証・深部 TI 6.404 再現）。

## 次工程（Step 2）
1. クリーンな新規プロジェクトで load → detect → place → assign → setup を順に実行（各後で Save）。
2. ペア1（T7–P7・2000Hz）／ペア2（Fp1–Fp2・2010Hz）を別シミュで Run。
3. `ti_analysis.py` で TI=2·min(|E1|,|E2|) → 島皮質 ROI の体積重み平均 → 選択性を ≈0.40 と照合。
4. 位置最適化（重い工程）→ その後 TUS を同一 Yoon-sun・同一 ROI で組んで比較。
