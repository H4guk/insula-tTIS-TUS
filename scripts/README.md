# scripts/ 配置

Sim4Life.lite の Python コンソールに**全文を貼り付けて**実行する（コンソールはこのリポジトリを見えないため）。
直下＝本番パイプライン＋解析＋設計計算、`archive/`＝一度きりの調査 probe・使い捨て検証・回復用（履歴として保存）。

## tTIS（Phase 1–2）
- **セットアップ**: `load_yoonsun.py` `detect_coordinate_system.py` `place_electrodes.py` `define_insula_roi.py`
- **工程5–9**: `assign_materials.py` `setup_boundary.py` `setup_grid.py` `verify_voxels.py` `run_simulation.py`
- **解析・監査**: `ti_analysis.py`（TI・選択性）`current_scale.py` `sigma_map.py` `verify_grid_order.py` `audit_materials.py` `ti_focus_size.py`（5-3 -6dB 焦点サイズ） `ti_local_maxima.py`（5-3b 焦点の有無＝局所極大とプロファイル）
- 手順: `docs/reproduce.md`

## TUS（Phase 4）
- **設計計算（ローカル）**: `plan_frequency_grid.py`（f=250kHz）`plan_transducer.py`（F#=1.21）
- **本番パイプライン**: `build_transducer.py` → `tus_assign_materials.py` → `tus_setup_source.py` → `tus_setup_grid.py` → `tus_verify_voxels.py` → `tus_run.py`
- **解析**: `tus_selectivity.py`（脳マスク＋選択性）`tus_focus_analysis.py` `tus_axial_profile.py` `tus_focus_size.py`（5-2 -6dB 焦点サイズ）
- 手順: `docs/reproduce-tus.md`

## archive/（一度きり・履歴保存）
- **調査 probe**: `probe_material_source.py`（tTIS σ）/ `probe_acoustics_api.py` `probe_acoustic_materials.py` `probe_acoustic_sim_api.py` `probe_modeling_api.py` `tus_probe_boundary.py` `tus_field_probe.py`（TUS API・物性・幾何・境界の確定に使用）
- **使い捨て検証**: `tus_converge_check.py`（Periods 収束）`tus_rigid_transducer.py`（剛体でも不変＝near-field は物理）
- **回復用（現在は不要）**: `tus_fix_transducer_material.py` ← トランスデューサ材料は `tus_assign_materials.py` に統合済み（2026-08-26 再現確認）。ボクセル化後に材料を足したくなった時の回復手順として残置。
