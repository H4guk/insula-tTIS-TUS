# scripts/ 配置

Sim4Life.lite の Python コンソールに**全文を貼り付けて**実行する（コンソールはこのリポジトリを見えないため）。
直下＝本番パイプライン＋解析＋設計計算、`archive/`＝一度きりの調査 probe・使い捨て検証・回復用（履歴として保存）。

## tTIS（Phase 1–2）
- **セットアップ**: `load_yoonsun.py` `detect_coordinate_system.py` `place_electrodes.py` `define_insula_roi.py`
- **工程5–9**: `assign_materials.py` `setup_boundary.py` `setup_grid.py` `verify_voxels.py` `run_simulation.py`
- **比較（5-2/5-3 測り直し）**: `reach_volume.py`（標的レベル以上が及ぶ脳体積・両手法を1回で）
- **図（5-6）**: `make_figures.py`（ローカル・Fig.2/3）`make_fig1_slices.py`（**Sim4Life 側で実行**・Fig.1 場スライス）`probe_slice_export.py`（環境確認）
- **統合（5-1）**: `probe_cell_limit.py`（セル上限が合計制か判定） `probe_geometry_match.py`（5-1b 両プロジェクトのジオメトリ突き合わせ） `probe_transducer_pose.py`（5-1g トランスデューサ設置点の高精度比較）
- **解析・監査**: `ti_analysis.py`（TI・選択性）`current_scale.py` `sigma_map.py` `verify_grid_order.py` `audit_materials.py` `ti_focus_size.py`（5-3 -6dB 焦点サイズ） `ti_local_maxima.py`（5-3b 焦点の有無＝局所極大とプロファイル） `ti_roi_threshold_fraction.py`（GH #19 深部到達②: TI が 0.2 / 0.3 / 0.35 V/m を超える ROI 体積の割合）
- 手順: `docs/reproduce.md`

## TUS（Phase 4）
- **設計計算（ローカル）**: `plan_frequency_grid.py`（f=250kHz）`plan_transducer.py`（F#=1.21）
- **本番パイプライン**: `build_transducer.py` → `tus_assign_materials.py` → `tus_setup_source.py` → `tus_setup_grid.py` → `tus_verify_voxels.py` → `tus_run.py`
- **食い込みの確かめ**: `tus_transducer_overlap.py`（`tTIS_LF1` のボクセルを頭の形にして、殻が頭の組織と重ならないか・開口の中の頭の一番外を測る。#25 で殻を頭の外に出した根拠）
- **開口の走査**: `tus_aperture_scan.py`（開口 40〜70 mm ごとに、頭の外に置くのに要る R・F#・フレネル数。64 mm に決めた根拠）
- **安全**: `tus_safety_drive.py`（MI<1.9 での焦点線量・ISPPA。4-4a の再測）
- **ROI 平均の音圧**: `tus_roi_pressure.py`（安全駆動での ROI 平均 |p| [kPa]。脳内の目安 120 kPa（Lee 2021）と比べる。#20）
- **解析**: `tus_selectivity.py`（脳マスク＋選択性）`tus_focus_analysis.py` `tus_axial_profile.py` `tus_focus_size.py`（5-2 -6dB 焦点サイズ）
- 手順: `docs/reproduce-tus.md`

## 神経レベル比較（Phase 6・GH #16・L2）
手順と結果は `docs/phase6-neuron.md`。表は `neuron_l2_table.py`（ローカル）→ `results/neuron_l2_table_2026-10-21.md`。
- **標的外の選び方**: `neuron_offtarget_search.py`（10 mm の線が脳に収まる点のうち TI 最大＝標的外 A・B）
- **tTIS（Sim4Life）**: `neuron_ti_create.py`（`TI_Neuron` を作り `tTIS_LF1`/`LF2` の場をつなぐ。**Source Settings 1 が 2010 Hz かを GUI で確かめる**）→ `neuron_ti_place_l2_mrg16.py` / `neuron_ti_place_l2_sundt.py`（7 本ずつ。神経を設定に入れるのは GUI のドラッグ）→ `neuron_ti_ramp_setup.py`（ランプ付きの波形・PulseType Vectors・Duration 260 ms）→ `neuron_ti_read_titration_l2.py`（倍率を読む）
- **TUS（Sim4Life → ローカル MorphoSONIC）**: `neuron_tus_line_pressure2.py`（Sim4Life・7 本の線上の |p| と組織）→ `neuron_tus_profile_source.py`（線上の音圧を区画ごとに与える音源）→ `neuron_tus_titrate_lines.py`（**ローカル**・MRG 16 µm / Sundt の titration）
- **実装の突き合わせ（IClamp）**: `neuron_iclamp_morpho.py`（ローカル）／`neuron_iclamp_sweep_setup.py` → `neuron_iclamp_set_amps.py` → `neuron_iclamp_read.py`（Sim4Life。`neuron_iclamp_check.py` で今の設定を表示）
- 無効にした結果（1 回目・2000 Hz の不具合）は `results/invalid/`（README つき）

## 脳の定義の統一（GH #17）
- `brain_by_name.py`（Input.h5 の `material_name` で決めた脳実質 12 組織で、tTIS・TUS の選択性・到達体積・脳内最大を出し直す。旧い定義と並べて出す。結果は `results/brain_by_name_2026-10-13.txt`）。直す場所の一覧は `docs/brain-mask-fix-inventory.md`
- `selectivity_by_definition.py`（感度解析: 脳の定義を名前で 3 通り〔12 組織・大脳 GM+WM・大脳 GM のみ〕に振り、両手法で同じ定義の選択性を並べる。`ti_analysis.py`・`tus_selectivity.py` の帯による別定義の置き換え）

## archive/（一度きり・履歴保存）
- **#16 関門（tutorial）**: `neuron_tutorial_beat_check.py`（2000/2010 Hz の Source から 10 Hz のうなり）`neuron_tutorial_limit_probe.py`（Lite の神経上限 10 本） `neuron_morpho_gate.py`（MorphoSONIC の MRG に超音波・電気をかける関門。環境構築の手順も先頭に）
- **#16 1 回目（10-13・無効）**: `neuron_ti_place_axons.py` `neuron_ti_read_titration.py` `neuron_tus_site_pressure.py` `neuron_tus_pysonic.py`（RS 点神経） `neuron_tus_line_pressure.py`（旧い 6 本） `neuron_ti_place_offtarget2.py`（L2 前の MRG 20 µm）
- **#16 L2 の調査**: `neuron_offtarget_line_fit.py`（脳内 TI 最大に軸索が収まらない確認） `neuron_ti_props_probe.py` `neuron_ti_props_probe2.py`（軸索の形の項目） `neuron_tus_profile_gate.py`（自作の音源の関門） `neuron_iclamp_probe.py` `neuron_iclamp_probe2.py` `neuron_iclamp_create.py` `neuron_iclamp_titration_off.py`（IClamp の API と、Titration が外部 Source 無しで動かないこと） `neuron_ramp_probe.py`（Source の波形の項目・2000 Hz の不具合の発見） `neuron_ramp_vector_probe.py`（Vectors の値はタプルで入る）
- **#17 調査**: `neuron_offtarget_tissue_probe.py`（tTIS の「脳内 TI 最大点」が腱・靭帯だった確認）`probe_material_names.py`（組織名の在りか＝`material_name`）`list_tissues.py`（両手法の組織一覧と、脳 12 組織の決定）`ti_brain_max_boundary_check.py`（新しい脳での tTIS 最大＝延髄 1 セルが脳の端で跳ねていないか）
- **調査 probe**: `probe_material_source.py`（tTIS σ）/ `probe_acoustics_api.py` `probe_acoustic_materials.py` `probe_acoustic_sim_api.py` `probe_modeling_api.py` `tus_probe_boundary.py` `tus_field_probe.py`（TUS API・物性・幾何・境界の確定に使用）
- **使い捨て検証**: `tus_converge_check.py`（Periods 収束）`tus_rigid_transducer.py`（剛体でも不変＝near-field は物理）
- **回復用（現在は不要）**: `tus_fix_transducer_material.py` ← トランスデューサ材料は `tus_assign_materials.py` に統合済み（2026-08-26 再現確認）。ボクセル化後に材料を足したくなった時の回復手順として残置。
