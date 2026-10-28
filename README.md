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
├── README.md          # 本ファイル（概要・再現手順の入口・Yoon-sun 入手方法）
├── requirements.txt   # ローカルの図・表用ライブラリ（s4l_v1 は Sim4Life が提供）
├── scripts/           # Sim4Life.lite の Python コンソールに貼るスクリプト（一部ローカル）。分類は scripts/README.md
│   └── archive/       # 一度きりの調査・置き換えられたもの（履歴として保存）
├── docs/              # 手法・評価枠組み・再現手順・経過
│   ├── reproduce-submission.md  # ★提出物の再現手順
│   ├── figures/       # 図1〜3（PNG・SVG）
│   └── submission/    # 提出物の notebook と組み立てスクリプト
└── results/           # 数値の出力（大きい場のファイルは .gitignore）
```

## 実行環境

- **Sim4Life.lite**（クラウド・https://s4l-lite.io ・Chrome / macOS）の**内蔵 Python コンソール**（Python 3.11.9）で実行。
- `scripts/` は `s4l_v1` / `XCoreModeling` に依存し、**ローカル単体では動かない**（Sim4Life が提供する API）。コンソールに貼って `Shift+Enter`。
- Lite の制限: モデルは Yoon-sun 1体固定 / グリッド 2000万セルまで / HPC ソルバーなし。

## 再現手順

提出物（`docs/submission/submission_draft.ipynb`）の数値と図1〜3を出す手順は **`docs/reproduce-submission.md`** にまとめた。流れは次のとおり。

1. **モデル**: Yoon-sun の読み込み → 座標系と ROI → 電極4枚 → トランスデューサ（`load_yoonsun.py` → `detect_coordinate_system.py` → `define_insula_roi.py` → `place_electrodes.py` → `build_transducer.py`）
2. **シミュレーション**: tTIS 2ペア（`tTIS_LF1` 2000 Hz・`tTIS_LF2` 2010 Hz）と TUS（`TUS_250k` 250 kHz）を1つのプロジェクトで Run
3. **場のレベルの数値**: `brain_by_name.py`・`ti_roi_threshold_fraction.py`・`tus_safety_drive.py`・`tus_roi_pressure.py`。`submission_code_cell.py` で全部をまとめて確かめられる
4. **神経レベル**: tTIS は Sim4Life の神経ソルバー、TUS は MorphoSONIC（ローカル）→ `neuron_l2_table.py`
5. **図と notebook**: `make_fig1_slices.py`（Sim4Life）・`make_figures.py`（ローカル）→ `docs/submission/build_notebook.py`

各工程の後に `s4l_v1.document.Save()` で保存する（保存忘れで状態が壊れた事故あり）。

## Yoon-sun 頭部モデルの入手方法

- モデルデータ（`*.sab`）は **IT'IS Foundation の Virtual Population（ViP）** の資産で、**再配布不可**のためリポジトリには含めない（`.gitignore`）。
- Sim4Life.lite には **Yoon-sun v3.1**（DOI `10.13099/ViP11016-03-0`）が同梱されており、`scripts/load_yoonsun.py` が
  `s4l_v1.data.GetAvailableDownloads()` → `DownloadModel()` → `XCoreModeling.Import()` で取得・読み込む。
- ViP の詳細: https://itis.swiss/virtual-population/

## 参考

- Inoue, Otsuru, Hirata (2026) "Group-level and personalized optimization for the insula and hippocampus
  focal electric field in transcranial temporal interferential stimulation: a computational study"
  Comput Biol Med 200:111374（arXiv:2510.23290）— Montage I（T7–P7 + Fp1–Fp2）・選択性 ≈0.40 の出典。
- Grossman et al. (2017) Cell — TI の原理実証。
