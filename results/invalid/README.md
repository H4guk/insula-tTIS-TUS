# 無効にした結果（GH #16）

使わない結果を、取り違えないようにここへ移した（2026-10-21）。理由は `docs/phase6-neuron.md` §6。

| ファイル | 中身 | 無効の理由 |
|---|---|---|
| `neuron_ti_titration_2026-10-13.json` | 1 回目の tTIS（MRG 20 µm・標的と旧い標的外） | 標的外 (48.5, 274.5, 1482.5) が脳ではなく腱・靭帯だった（#17）。神経モデルも手法で違った。2 つの Source が両方 2000 Hz だった |
| `neuron_tus_pysonic_2026-10-13.txt` | 1 回目の TUS（PySONIC の RS 点神経・2 地点） | 同じ旧い標的外。神経モデルが tTIS と違った |
| `neuron_ti_titration_l2_mrg16_2026-10-17.json` | L2 ③ の tTIS × MRG 16 µm | Source Settings 1 が 2010 Hz ではなく 2000 Hz のままで、TI ではなく 2 kHz の刺激だった |
| `neuron_ti_titration_l2_sundt_2026-10-18.json` | L2 ③ の tTIS × Sundt 0.8 µm | 同上 |

使う結果は `results/neuron_l2_table_2026-10-21.md`（`scripts/neuron_l2_table.py`）の一覧のとおり。
