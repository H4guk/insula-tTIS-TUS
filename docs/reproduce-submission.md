# 提出物の再現手順（S4L Student Competition 2026）— #25

`docs/submission/submission_draft.ipynb` の数値と図1〜3を、**素のプロジェクトから出すまで**の手順。
提出物に効くスクリプトだけを並べた。経緯や別の検算は `reproduce-integrated.md`・`reproduce.md`・`reproduce-tus.md`・`phase6-neuron.md`。

- **Sim4Life.lite 9.6 の Python コンソール**に、スクリプトの全文を貼って実行する（`exec(open(...))` は不可）。「ローカル」と書いたものだけ手元の Python で動かす
- 1つのプロジェクトに `tTIS_LF1`・`tTIS_LF2`・`TUS_250k` の3つのシミュレーションを並べる（統合版）
- 各工程の後に `s4l_v1.document.Save()` で保存する
- 所要時間: 場のシミュレーションまで約45〜60分。神経レベルは tTIS の Sundt が約7時間、TUS の Sundt が1本30分〜3時間

---

## A. モデル（1回だけ）

| # | スクリプト | 備考 |
|---|---|---|
| 1 | `load_yoonsun.py` | Yoon-sun v3.1 を読み込む（GUI では読めない） |
| 2 | `detect_coordinate_system.py` | 座標系とランドマーク |
| 3 | `define_insula_roi.py` | 読み取りのみ。ROI＝左島皮質の中心 (99.1, 295.0, 1562.2) mm・半径 10 mm。ROI は実体を作らず、各スクリプトにこの値が入っている |
| 4 | `place_electrodes.py` | 10-20 の T7・P7・Fp1・Fp2 に電極パッド4枚 |
| 5 | `build_transducer.py` | 集束トランスデューサ（250 kHz・開口 40 mm・F#=1.21）を `Elec_T7` の位置に作る。**tTIS のボクセル化より前に作る** |

## B. tTIS（2ペア）

ペアごとに 6 → 10 を流す。定数はスクリプトの先頭で書き換える。

| # | スクリプト | ペア1（T7–P7） | ペア2（Fp1–Fp2） |
|---|---|---|---|
| 6 | `assign_materials.py` | `SIM_NAME='tTIS_LF1'`・`FREQ=2000.0` | `SIM_NAME='tTIS_LF2'`・`FREQ=2010.0` |
| 7 | `setup_boundary.py` | `DRIVE=(('Elec_T7',1.0,'BC_T7_pos'), ('Elec_P7',0.0,'BC_P7_gnd'))` | `DRIVE=(('Elec_Fp1',1.0,'BC_Fp1_pos'), ('Elec_Fp2',0.0,'BC_Fp2_gnd'))` |
| 8 | `setup_grid.py` | 約5〜6分 | 同じ |
| 9 | `verify_voxels.py` | **8 が終わってから** | 同じ |
| 10 | `run_simulation.py` | 約2分 | 同じ |

両ペアのグリッドが同じ（8 の出力 `228 x 220 x 245 = 12.289 MCells`）であること。TI の包絡は同じグリッドでないと作れない。

## C. TUS

| # | スクリプト | 備考 |
|---|---|---|
| 11 | `tus_assign_materials.py` | `TUS_250k` を作り、59 組織と Transducer に ρ・c・α。電極は入れない |
| 12 | `tus_setup_source.py` | 正弦波・参照 1 MPa の音源を Transducer に付ける |
| 13 | `tus_setup_grid.py` | 1 mm のグリッド → ボクセル化（約5分） |
| 14 | `tus_verify_voxels.py` | **13 が終わってから** |
| 15 | `tus_run.py` | 約470秒 |

## D. 場のレベルの数値（読み取りのみ）

| # | スクリプト | 出るもの | 期待値 |
|---|---|---|---|
| 16 | `verify_grid_order.py` | 配列の並び（X が最も速い）。以降の前提 | X-fastest |
| 17 | `brain_by_name.py` | 脳実質 12 組織での選択性・ROI 平均を超える体積・ROI と地続きの割合（図2の値） | tTIS 0.358・35.9 mL（地続き 35.3）／TUS 0.193・7.3 mL（地続き 6.4）。脳 1041.5 mL |
| 18 | `ti_roi_threshold_fraction.py` | tTIS の ROI 平均と、0.2 V/m を超える ROI の割合 | 0.2265 V/m（113%）・74.5% |
| 19 | `tus_safety_drive.py` | MI 1.9 に合わせる音源の強さ | 参照 MI 12.2 → 音源 0.156 MPa（k = 0.15580） |
| 20 | `tus_roi_pressure.py` | 安全駆動での TUS の ROI 平均 \|p\| と、120 kPa を超える ROI の割合 | 112.6 kPa（94%）・41.1% |
| 21 | `submission_code_cell.py` | 17〜20 を1本でまとめて出す（提出物の末尾のコードセルと同じ） | `results/submission_code_cell_2026-10-29.txt` と一致 |

## E. 神経レベル

tTIS（Sim4Life）:

| # | スクリプト | 備考 |
|---|---|---|
| 22 | `neuron_offtarget_search.py` | 標的外の点 A・B を選ぶ（延髄。10 mm の線が脳に収まる点のうち TI 最大） |
| 23 | `current_scale.py` | 1 V 駆動 → 0.891 / 1.109 mA の倍率（0.2056 / 0.3316） |
| 24 | `neuron_ti_create.py` | `TI_Neuron` を作り、`tTIS_LF1` / `LF2` をつなぐ。**Source Settings 1 が 2010 Hz かを GUI で確かめる** |
| 25 | `neuron_ti_place_l2_mrg16.py`・`neuron_ti_place_l2_sundt.py` | 7 本ずつ。神経を設定に入れるのは GUI のドラッグ（上限 10 本なので MRG と Sundt は別の Run） |
| 26 | `neuron_ti_ramp_setup.py` | ランプ付きの波形（PulseType Vectors・Duration 260 ms）。Titration on |
| 27 | `neuron_ti_read_titration_l2.py` | Run の後に倍率を読む → `results/neuron_ti_titration_l2_*.json`（MRG・Sundt × ランプの有無の4本。本文はランプ付き） |

TUS（Sim4Life → ローカル）:

| # | スクリプト | 備考 |
|---|---|---|
| 28 | `neuron_tus_line_pressure2.py` | Sim4Life。7 本の線上の \|p\| と組織（k = 0.15580） |
| 29 | `neuron_tus_titrate_lines.py <fiber> <line>` | **ローカル**（MorphoSONIC・`neuron_tus_profile_source.py` を使う）。環境の作り方は `archive/neuron_morpho_gate.py` の docstring → `results/neuron_tus_titrate_lines_2026-10-15.jsonl` |
| 30 | `neuron_l2_table.py` | **ローカル**。表 → `results/neuron_l2_table_2026-10-21.md` |

期待値: ROI の軸索は TUS で MRG 0.431・Sundt 0.103 倍、tTIS で 41.8・3040 倍。標的外 ÷ 標的は TUS 11.1・11.6、tTIS 0.23・0.30。

## F. 図と notebook

| # | スクリプト | 備考 |
|---|---|---|
| 31 | `make_fig1_slices.py` | Sim4Life。図1（島皮質の断面）。確認の出力: 脳 1041.5 mL・tTIS ROI 平均 0.2265 V/m・TUS ROI 平均 \|p\| 7.225e5 Pa（参照駆動）。`/home/smu/work/workspace/` から PNG と SVG をダウンロードして `docs/figures/` へ |
| 32 | `make_figures.py` | **ローカル**。図2（体積）・図3（有効レベルとの比）。`requirements.txt` の matplotlib |
| 33 | `docs/submission/build_notebook.py` | **ローカル**。本文・図・コードセル（21）から notebook を組み立て、語数を確かめる |

---

## ほかの手順書との関係

- `reproduce-integrated.md`: 統合版を作ったときの手順（2026-08-27）。モデルとシミュレーション（A〜C）は同じ。解析（`ti_analysis.py`・`tus_selectivity.py` ほか）は旧い脳の定義なので、提出物には使っていない
- `reproduce.md`・`reproduce-tus.md`: 統合する前の tTIS・TUS それぞれの手順
- `phase6-neuron.md` §7: 神経レベルの手順と API の注意
