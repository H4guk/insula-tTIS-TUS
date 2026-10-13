# Phase 6 神経レベルの比較 — tTIS（Sim4Life 神経ソルバー）/ TUS（PySONIC）

対応 Issue: GH #16（#15 提出物の計画 A3）。関門 2026-10-15。
実施: 2026-10-12〜10-13。

**問い**: 場のレベルで見えた差（TUS は焦点を結ぶ／tTIS は届くが焦点を結ばない・脳内に標的の 10.7 倍強い場所がある）は、**神経が発火するかで見ても残るか**。

**同一条件**: 同一 Yoon-sun・統合版プロジェクト（`reproduce-integrated.md`）の場をそのまま使う。神経を置く2か所も両手法で同じ。

| 地点 | 座標 [mm] | 意味 |
|---|---|---|
| 標的 | (99.1, 295.0, 1562.2) | 左島皮質 ROI の中心（`define_insula_roi.py`） |
| 標的外 | (48.5, 274.5, 1482.5) | tTIS の脳内 TI 最大点。ROI 中心から 96.6 mm・標的の 10.7 倍（`comparison-framework.md`） |

---

## 1. 結果

**倍率 ＝ 発火に要る強さ ÷ 標準の安全な強さ**（tTIS は合計 2 mA、TUS は MI<1.9）。**1 未満なら標準の強さで発火する**。

| | 標的 | 標的外 |
|---|---|---|
| tTIS（合計 2 mA） | 32.25（発火しない） | 6.375（発火しない） |
| TUS（MI<1.9） | **0.187（発火する）** | 6.314（発火しない） |

- **場のレベルの差は、神経のレベルでも残る**。TUS は標的だけが発火し、標的外は発火しない。tTIS は 2 mA ではどちらも発火せず、発火に近いのはむしろ標的外（倍率で約 5 倍、32.25 ÷ 6.375）。
- tTIS の「標的外は約 5 倍発火しやすい」は、場の 10.7 倍と向きは同じだが値は一致しない。軸索が反応するのは TI 包絡の大きさではなく、軸索に沿った場とその変化だから。同じ場所でも向きで倍率が 2〜20 倍変わる（§2-1 の表）。
- TUS の標的の音圧は 1 セルで ±25% 動くが、まわり 3×3×3 の最小（151.72 kPa）でも倍率 0.253 で、結論は変わらない。

## 2. 実装

### 2-1. tTIS（Sim4Life.lite 神経ソルバー）

| 項目 | 値 | 出典 |
|---|---|---|
| 場 | `tTIS_LF1`（T7–P7）・`tTIS_LF2`（Fp1–Fp2）の Overall Field。Source 1/2 として別々につなぐ | `neuron_ti_create.py` |
| 波形 | Sinusoidal 2000 Hz / 2010 Hz（EM を計算した周波数・差 10 Hz）、開始 0、刺激 100 ms（半周期 400 / 402） | — |
| 振幅 | 0.2056 / 0.3316 ＝ Inoue 2025 の 0.891 / 1.109 mA（合計 2 mA）÷ 1 V 駆動時の 4.334 / 3.344 mA | `current_scale.py`（統合版でも分離版と同値） |
| 神経 | Motor MRG 有髄軸索・直径 20 µm（既定）・長さ 10 mm。各地点に x / y / z の3方向（線維の向きが分からないため）、計 6 本 | `neuron_ti_place_axons.py` |
| Solver | Duration 110 ms・Time Step 0.0025 ms（2010 Hz の1周期を約 200 点） | — |
| 判定 | Titration on（NEURON・収束 1%・Threshold）。2つの Source を同じ倍率で強めるので電流比は保たれる | — |
| 計算 | 6 本で 10 分 32 秒 | — |

神経ごとの倍率（`results/neuron_ti_titration_2026-10-13.json`）:

| 地点 | x | y | z |
|---|---|---|---|
| 標的 | 32.25 | 47.75 | 128.0 |
| 標的外 | 45.5 | 15.0 | 6.375 |

最初の発火の位置は置いた座標と一致した（神経は意図どおりの場所にある）。

### 2-2. TUS（Sim4Life の音圧 → PySONIC）

| 項目 | 値 | 出典 |
|---|---|---|
| 音圧 | `TUS_250k`（音源 1 MPa の参照駆動）を k = 0.15580 で MI<1.9 にスケール（記録 0.1558 と一致） | `neuron_tus_site_pressure.py`・`tus_safety_drive.py` |
| 2地点の音圧 | 標的 205.33 kPa（3×3×3 で 151.72〜235.29）／標的外 6.09 kPa（1.18〜16.77） | 同上 |
| 神経モデル | PySONIC（Lemaire et al. 2019, J Neural Eng）の SONIC モデル。大脳皮質 RS 点神経・ソノフォア半径 32 nm・被覆率 fs = 1 | `neuron_tus_pysonic.py` |
| 刺激 | 250 kHz・100 ms 連続波（tTIS と同じ長さ） | 同上 |
| 閾値 | titrate（二分探索）で 38.45 kPa | 同上 |
| 計算 | 約 37 秒（ローカル） | — |

出力は `results/neuron_tus_pysonic_2026-10-13.txt`。

## 3. 限界

### 3-1. 比較の組み方
- **神経のモデルが手法で違う**。tTIS は MRG 有髄軸索、TUS は RS 点神経。Sim4Life の神経ソルバーは電場による刺激しか扱えず、PySONIC は超音波による刺激しか扱えないので、同じ神経にそろえられない。比べているのは「その手法の標準の強さで、その場所の神経が発火するか」。
- **刺激は 100 ms**（TI のうなり 10 Hz の1周期ぶん）。実際の刺激は数秒〜数分続く。計算時間に合わせて決めた長さで、文献の値ではない。
- **神経は各地点に1本（tTIS は3方向）**。その場所の神経の種類・向き・密度の分布は反映していない。

### 3-2. tTIS 側
- **倍率で強めたときの発火は、ほぼ全部が刺激の始まり直後（約 7 ms）**。何倍にも強めた kHz の正弦波は、包絡と関係なく始まりの瞬間に軸索を発火させうる（onset response）。倍率の値は TI の 10 Hz 包絡による発火ではない可能性があるので、**主な結論は「2 mA では両方とも発火しない」とし、倍率の比は参考に留める**。標的の z 向き（128.0）だけは 100.59 ms で、刺激の終わり直後。
- **MRG 20 µm は太い（発火しやすい側）**。脳の軸索の多くは数 µm 以下なので、実際にはさらに発火しにくい。
- TI による発火そのものにも議論がある（高周波による伝導ブロック等）。

### 3-3. TUS 側
- **SONIC（膜内キャビテーション仮説）には異論がある**。
- **閾値が実験の有効域よりずっと低い**。PySONIC の閾値 38.45 kPa は ISPPA に直すと 0.05 W/cm² 程度で、場のレベルの比較で使った有効域 3〜30 W/cm²（Sharif 2025）より 2 桁低い。標的の 205 kPa も ISPPA では約 1.3 W/cm² で有効域の下端に届かない。**「TUS は標的で発火する」は SONIC モデルの上での結論**で、場のレベルの「有効域の下端ぎりぎり」とは食い違う。fs = 1（膜の全面が反応）は最も発火しやすい設定。
- 点神経（形を持たない）なので、軸索の向きによる差は出ない。

### 3-4. Sim4Life.lite
- 神経は1回の Run に **10 本まで**（`Light version does not support number of neurons over 10.`）。
- **同じ HOC の型の神経は1回の Run に1本だけ**（2本だと `Failed to write neurons to input file.`）。今回は自動軸索（MRG）を使ったので影響なし。

## 4. 手順（再現）

tTIS（Sim4Life.lite・統合版プロジェクト）:
1. `neuron_ti_create.py` — `TI_Neuron` を作り、`tTIS_LF1` / `LF2` の Overall Field を Source につなぐ
2. `neuron_ti_place_axons.py` — 2地点 × 3方向の MRG 軸索を作る
3. GUI: `Neurons` を選ぶ → `New Settings ▾` → Automatic Axon Model Settings → 6 本をドラッグ
4. GUI: Source 1/2 に §2-1 の波形・振幅、Solver、Setup（Titration on）
5. Python: `sim.AddOverallLineSensor()` → Run
6. `neuron_ti_read_titration.py` — 倍率を読む

TUS:
1. `neuron_tus_site_pressure.py`（Sim4Life）— 2地点の音圧
2. `neuron_tus_pysonic.py`（ローカル・PySONIC）— 閾値と倍率

API の注意:
- 神経の設定は `sim.Add(設定, [エンティティ])` だと `incompatible with this type of simulation` で失敗する。GUI のドラッグで入れる。
- ただの線は軸索の設定に入らない。`model.CreateAxonNeuron(s)` で神経のエンティティにしてから入れる。
- Source は `sim.AddSource(em_sim, "Overall Field")` で EM とつながる。
- Titration の結果は `res["Titration Sensor"]["Titration"].Data.DataJson`（JSON 文字列）。位置は m、時刻は s。

関門（2026-10-13 に達成）: tutorial（Electrode with Nerve Model）が Lite で動く・2000 / 2010 Hz の2つの Source で 10 Hz のうなりが出る（`archive/neuron_tutorial_beat_check.py`）・神経の上限 10 本（`archive/neuron_tutorial_limit_probe.py`）・PySONIC が手元で動く。

## 5. 次

notebook の Discussion（Level 2）に入れるかを判断する（Issue #16 の最後の項目）。入れる場合も、§3 の限界、特に「SONIC の閾値が有効域より 2 桁低い」と「tTIS の倍率は onset response の可能性」を一緒に書く。
