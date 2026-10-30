# insula-tTIS-TUS

## English summary

Code and results for *Focality and Reach of Transcranial Ultrasound Versus Temporal Interference Stimulation of the Human Insula Within Safety Limits: A Computational Study* (Ryo Shimbo, Sim4Life Student Competition 2026).
Code comments and the notes below this section are mostly in Japanese.

### Contents
- `scripts/`: scripts pasted into the Sim4Life.lite Python console. They rebuild the whole project from an empty document. Figures and the MorphoSONIC runs are done locally. `scripts/README.md` lists every script.
- `results/prod2/`: outputs of the final rebuild (2026-10-29/30). All numbers in the report come from here.
- `docs/submission/`: the report notebook and `build_notebook.py`, which builds the notebook and checks the word limits.

### Rebuild order (Sim4Life.lite 9.6, Python console)
| Step | Scripts (in order) |
|---|---|
| Model | `load_yoonsun`, `detect_coordinate_system`, `define_insula_roi`, `place_electrodes`, `build_transducer` |
| tTIS pair 2 (Fp1-Fp2, 2010 Hz) | `assign_materials`, `setup_boundary`, `setup_grid`, `verify_voxels`, `run_simulation` |
| tTIS pair 1 (T7-P7, 2000 Hz) | the same five scripts, with `SIM_NAME = 'tTIS_LF1'`, `FREQ = 2000.0` and `DRIVE` on `Elec_T7`/`Elec_P7` |
| TUS | `tus_assign_materials`, `tus_setup_source`, `tus_setup_grid`, `tus_verify_voxels`, `tus_run`, `tus_transducer_overlap` |
| Field results (read-only) | `submission_code_cell`, `brain_by_name`, `ti_roi_threshold_fraction`, `tus_safety_drive`, `make_fig1_slices`, `tus_mitc_soft_tissue` |
| tTIS neurons | `neuron_offtarget_search`, `neuron_ti_create`, `neuron_ti_place_l2_mrg16`, `neuron_ti_place_l2_sundt`, `neuron_ti_ramp_setup`, `neuron_ti_pulse_window`, then Run and `neuron_ti_read_titration_l2` (once for the MRG axons, once for the Sundt axons) |
| TUS neurons | `neuron_tus_line_pressure2` (Sim4Life), then locally `LINE_PRESSURE=results/prod2/neuron_tus_line_pressure2_d64.txt python scripts/neuron_tus_titrate_lines.py <mrg16\|sundt> <line>` for each of the 7 lines |
| Implementation check | `neuron_iclamp_create`, `neuron_iclamp_sweep_setup`, `neuron_iclamp_set_amps`, Run, `neuron_iclamp_read` |
| Figures 2 and 3 | `make_figures.py` locally (numpy, matplotlib) |

### Steps done in the GUI
- `TI_Neuron` sources: Sinusoidal, 2000 Hz with amplitude 0.2056 and 2010 Hz with amplitude 0.3316 (the scales that turn the 1 V fields of `tTIS_LF1` and `tTIS_LF2` into 0.891 and 1.109 mA, from `ti_analysis.py`). Check that the second source really is 2010 Hz.
- Set the temperature of `TI_Neuron` and `IClamp_Neuron` to 36 °C, the same as MorphoSONIC.
- Press Clear Results before changing a simulation that already has results; otherwise the scripts' assignments are silently ignored.
- `TI_Neuron`: put the 7 MRG axons, then the 7 Sundt axons, into the neuron settings and Run with Titration on.
- `IClamp_Neuron`: set the solver duration to 40 ms and turn Titration off before Run.
- File → Save.

### Local MorphoSONIC environment
Python 3.11 with PySONIC (tjjlemaire/PySONIC 10ed530) and MorphoSONIC (tjjlemaire/MorphoSONIC 5d0d264) installed with `pip install -e --no-deps`, NEURON 9.0.2, numpy 1.26.4 and pandas 2.1.4 (pandas 3 silently breaks PySONIC).
Run `nrnivmodl` in `MorphoSONIC/nmodl`, and fetch the Git LFS lookup tables `MRGnode_lookups_fs1.00.pkl` and `SUseg_lookups_fs1.00.pkl`.
Details are in the docstring of `scripts/archive/neuron_morpho_gate.py`.

### Where the report numbers come from (`results/prod2/`)
| Report | File |
|---|---|
| Selectivity, volume above the ROI mean, reach | `submission_code_cell_d64.txt`, `brain_by_name_d64.txt` |
| Skull pressure peak at the safety limit | `tus_mitc_soft_tissue_d64.txt` |
| tTIS firing thresholds (MRG, Sundt) | `neuron_ti_titration_l2_mrg16_ramp.json`, `neuron_ti_titration_l2_sundt_ramp.json` |
| TUS firing thresholds | `neuron_tus_titrate_lines_d64.jsonl` |
| Sim4Life vs MorphoSONIC check | `neuron_iclamp_sim4life.txt` |

### Not included
- Yoon-sun model data: IT'IS Virtual Population, not redistributable. Sim4Life.lite ships it, and `load_yoonsun.py` loads it.
- The `.smash` project, which was submitted to the competition.

---

> 以下は日本語の研究メモ（初期の tTIS 部分のまま）。最新の再現手順と提出物の数値の出どころは、上の English summary と `scripts/README.md` を見る。

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
5. `scripts/assign_materials.py` → 頭部 59 組織に σ を割り当て（IT'IS LF DB 自動リンク）。
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
