# prod2（2026-10-29）

`insula-tTIS-TUS-prod2` を scripts/ だけで素から作り直したときの出力（#25）。
トランスデューサは頭の外。下の E の5本は開口 40 mm（R_OUT 70.53 mm・F# 1.76）のときのもの。そのあと開口を 64 mm（R_OUT 80.01 mm・F# 1.25）にして TUS を流し直す。
それより前の results/ の TUS の値は、殻の 40% が頭に埋まっていた旧い形（R_OUT 48.51 mm）のもの。

| ファイル | スクリプト |
|---|---|
| tus_transducer_overlap.txt | tus_transducer_overlap.py（開口 40 mm の殻と頭の重なり 0・PASS） |
| tus_aperture_scan.txt | tus_aperture_scan.py（開口 40〜70 mm で要る R・F#・N。64 mm に決めた根拠） |
| submission_code_cell.txt | submission_code_cell.py |
| brain_by_name.txt | brain_by_name.py |
| ti_roi_threshold_fraction.txt | ti_roi_threshold_fraction.py |
| tus_safety_drive.txt | tus_safety_drive.py |
| make_fig1_slices.txt | make_fig1_slices.py |

開口 40 mm（R_OUT 70.53 mm）の出力は `*_d40.txt`、開口 64 mm（R_OUT 80.01 mm・F# 1.25）は `*_d64.txt`。ti_roi_threshold_fraction.txt は tTIS だけなので共通。
開口 64 mm では全体の最大が骨になった。ITRUSST の MItc は軟部組織で決める（骨を除く）ので、scripts/tus_mitc_soft_tissue.py で決め直す。
