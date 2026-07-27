# insula-tTIS-TUS

**非侵襲脳刺激の比較シミュレーション：tTIS vs TUS による島皮質ターゲティング**

島皮質（insular cortex）に非侵襲で刺激を届けるのに **tTIS（時間干渉刺激）** と **TUS（経頭蓋集束超音波）** の
どちらが適するかを、Sim4Life 上のシミュレーションで比較検討する研究リポジトリ。

- 意義: 島皮質は依存症の因果的中枢（Naqvi 2007）。非侵襲で最適に刺激できれば依存症治療の新規標的になる。
- 最終目標との接続: 島皮質は味覚処理の中枢でもあり、「非侵襲で味覚を再現する」長期目標の足場になる。
- 千葉工大「学習・研究における AI 活用推進助成プログラム」採択プロジェクト（期間 2026-07-28〜2027-05-01）。

> 詳細な研究設計・評価枠組み・先行研究は Obsidian の研究ノート側で管理。本リポジトリは**コード・設定・手法ドキュメント**を扱う。

## リポジトリ構成

```
insula-tTIS-TUS/
├── README.md          # 本ファイル（概要・再現手順・Yoon-sun 入手方法）
├── requirements.txt   # 後処理・可視化用ライブラリ（s4l_v1 は Sim4Life が提供）
├── .gitignore         # *.smash / モデルデータ / 出力フィールド / 秘密情報 を除外
├── scripts/           # Sim4Life.lite Python コンソールで実行するスクリプト
│   ├── load_yoonsun.py            # ① Yoon-sun 頭部モデルの読み込み
│   ├── detect_coordinate_system.py# ② 座標系・ランドマーク・島皮質 ROI の検出
│   ├── place_electrodes.py        # ③ 10-20 → 球フィット → 電極パッド生成（Montage I）
│   ├── assign_materials.py        # ④ 頭部組織へ σ を割り当て（IT'IS LF DB + skin 上書き）
│   ├── setup_simulation.py        # ⑤ ±電位 BC + グリッド（頭部 1mm / 体 5mm）
│   └── ti_analysis.py             # ⑥ E 場抽出 → TI 包絡線 → ROI 定量
├── configs/           # モンタージュ・材料・BC・グリッド・ROI のパラメータ集約
│   └── parameters.py
├── notebooks/         # 解析ノートブック
├── docs/              # 手法・評価枠組み・進捗ログ
│   ├── method.md
│   └── progress-log.md
└── results/           # 小さい図・指標 CSV（大きい出力フィールドは .gitignore）
```

## 実行環境

- **Sim4Life.lite**（クラウド・https://s4l-lite.io ・Chrome / macOS）の**内蔵 Python コンソール**（Python 3.11.9）で実行。
- `scripts/` は `s4l_v1` / `XCoreModeling` に依存し、**ローカル単体では動かない**（Sim4Life が提供する API）。コンソールに貼って `Shift+Enter`。
- Lite の制限: モデルは Yoon-sun 1体固定 / グリッド 2000万セルまで / HPC ソルバーなし。

## 再現手順（新規プロジェクトで最初から）

1. Sim4Life.lite で新規プロジェクトを作成。
2. `scripts/load_yoonsun.py` を実行 → Yoon-sun をモデルツリーに読み込む（GUI では不可・Python 経由）。
3. `scripts/detect_coordinate_system.py` → 軸の意味・ランドマーク・島皮質 ROI を確認。
4. `scripts/place_electrodes.py` → Montage I（T7 / P7 / Fp1 / Fp2）の電極パッドを生成。
5. `scripts/assign_materials.py` → 頭部 59 組織に σ を割り当て（skin は 0.465 に上書き）。
6. `scripts/setup_simulation.py` → ±電位 BC とグリッドを設定。
7. **各ステップ後に `s4l_v1.document.Save()` で保存**（保存忘れで状態が壊れた事故あり）。
8. ペア1（T7–P7）／ペア2（Fp1–Fp2）を別シミュとして Run（2000 / 2010 Hz）。
9. `scripts/ti_analysis.py` → 2 つの E 場から `TI = 2·min(|E1|,|E2|)` を計算 → 島皮質 ROI で定量。
10. 選択性（非標的平均 / 標的平均）を先行研究 Inoue 2025 の **≈0.40** と桁で照合。

## Yoon-sun 頭部モデルの入手方法

- モデルデータ（`*.sab`）は **IT'IS Foundation の Virtual Population（ViP）** の資産で、**再配布不可**のためリポジトリには含めない（`.gitignore`）。
- Sim4Life.lite には **Yoon-sun v3.1**（DOI `10.13099/ViP11016-03-0`）が同梱されており、`scripts/load_yoonsun.py` が
  `s4l_v1.data.GetAvailableDownloads()` → `DownloadModel()` → `XCoreModeling.Import()` で取得・読み込む。
- ViP の詳細: https://itis.swiss/virtual-population/

## 参考

- Inoue, Otsuru, Hirata (2025) "Group-Level and Personalized Optimization for the Insula and Hippocampus
  Focal Electric Field in tTIS" arXiv:2510.23290 — Montage I（T7–P7 + Fp1–Fp2）・選択性 ≈0.40 の出典。
- Grossman et al. (2017) Cell — TI の原理実証。
