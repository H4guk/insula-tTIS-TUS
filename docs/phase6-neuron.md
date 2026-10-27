# Phase 6 神経レベルの比較 — tTIS（Sim4Life 神経ソルバー）/ TUS（MorphoSONIC）

対応 Issue: GH #16（#15 提出物の計画 A3）。範囲は L2（2026-10-15 決定）。
実施: 2026-10-12〜10-21（1 回目 10-13 は無効・§6）。

**問い**: 場のレベルで見えた差（TUS は標的のそばに焦点を結ぶ／tTIS は焦点を結ばず、脳内の最大は標的から遠い延髄）は、**神経が発火するかで見ても残るか**。

**方針（L2）**:
- **両手法に同じ神経モデル**を当てる。MRG 有髄軸索 16 µm（McIntyre 2002 の表の範囲内）と、性質が正反対の無髄 Sundt 0.8 µm（Sundt 2015）。
  皮質を狙う研究の標準は皮質の錐体細胞（Wang 2023 など）だが、TUS 側（MorphoSONIC）で使えるのは線維と点神経だけなので、両手法で同じにできるのは今は線維だけ（§5-1）。
- 補強: 線維の種類と太さ（MRG 16 µm・Sundt）／実装の突き合わせ（同じ電流注入・§4-3）／TI のランプ（刺激の始まりの発火を外す・§2）。
- 錐体細胞に SONIC をかけて頭の音響計算とつなぐ L3 は将来の研究。

**同一条件**: 同一 Yoon-sun・統合版プロジェクト（`reproduce-integrated.md`）の場をそのまま使う。軸索の場所・向き・長さは両手法で同じ 7 本。

| 地点 | 座標 [mm] | 線 | 意味 |
|---|---|---|---|
| 標的 | (99.1, 295.0, 1562.2) | target_x / y / z | 左島皮質 ROI の中心（`define_insula_roi.py`） |
| 標的外 A | (73.5, 266.5, 1512.5) | offA_x / y / z | 延髄。10 mm の線が 3 方向とも脳に収まる点のうち TI 最大（標的の 2.50 倍・ROI から 62.8 mm） |
| 標的外 B | (75.5, 264.5, 1509.5) | offB_y | 延髄。y 方向だけ収まる点のうち TI 最大（4.16 倍・65.3 mm） |

標的外は `neuron_offtarget_search.py` で選んだ。脳内の TI 最大（延髄の表面・4.59 倍・60.2 mm, #17）は、どの向きの軸索も脳からはみ出すので使わない。

---

## 1. 結果

**倍率 ＝ 発火に要る強さ ÷ 標準の安全上限での強さ**（tTIS は合計 2 mA、TUS は MI<1.9）。**1 未満なら安全上限の中で発火する**。
表は `scripts/neuron_l2_table.py` → `results/neuron_l2_table_2026-10-21.md`。tTIS はランプ付き（§2）。

| 線維 | 手法 | 標的の最小 | 標的外の最小 | 標的外 ÷ 標的 | 安全上限で標的が発火するか |
|---|---|---|---|---|---|
| MRG 16 µm | TUS | **0.431** | 4.78 | **11.1** | **する** |
| MRG 16 µm | tTIS | 41.8 | 9.44 | **0.23** | しない |
| Sundt 0.8 µm | TUS | **0.103** | 1.20 | **11.6** | **する** |
| Sundt 0.8 µm | tTIS | 3040 | 912 | **0.30** | しない |

「標的外 ÷ 標的」は標的外の最小の倍率 ÷ 標的の最小の倍率。1 より大きいほど標的を選んで発火させられる。

- **場のレベルの「TUS は絞れる・tTIS は絞れない」は、神経の発火で見ても残る**。TUS は安全上限の中で標的だけが発火し、標的を約 11 倍選べる。tTIS は 2 mA ではどの線も発火せず、発火に近いのはむしろ標的外（MRG で 4.4 倍、Sundt で 3.3 倍）。
- **向きは線維の種類によらない**。太い有髄（MRG 16 µm）と細い無髄（Sundt）で、「標的外 ÷ 標的」が TUS は 11.1 と 11.6、tTIS は 0.23 と 0.30。
- **倍率の絶対値は線維で大きく違う**（tTIS の Sundt は数千倍＝数 A で、現実の値ではなく「細い無髄線維は tTIS では実質的に発火しない」と読む）。使うのは向き。
- Sundt は TUS で発火しやすく（0.10 対 0.43）、tTIS で発火しにくい（3040 対 41.8）。超音波は無髄の C 線維を選びやすいという報告（Lemaire 2021）と同じ向き。

線ごとの倍率:

| 線 | MRG TUS | MRG tTIS | Sundt TUS | Sundt tTIS |
|---|---|---|---|---|
| target_x | 0.505 | 41.8 | 0.121 | 3040 |
| target_y | 0.431 | 61.5 | 0.103 | 4640 |
| target_z | 0.491 | 77.5 | 0.116 | 6240 |
| offA_x | 4.94 | 55.0 | 1.20 | 1664 |
| offA_y | 4.78 | 164 | 4.86 | 10368 |
| offA_z | 8.84 | 9.44 | 2.10 | 912 |
| offB_y | 9.31 | 171 | 2.42 | 3648 |

## 2. TI のランプと発火の時刻（tTIS）

2 つの正弦波（2000 / 2010 Hz）が同じ位相で始まるので、包絡は |cos(2π·5t)| で山は 0・100・200 ms、谷は 50・150 ms。
ただし軸索の向きで見て 2 つの場が逆向きの所では、逆位相になる 50・150 ms で足し合わさって包絡の山になる。

ランプ無し（100 ms）では包絡の山が t = 0 にあり、急に始まる kHz の正弦波そのものでの発火（onset response）と区別できない。
そこで振幅 × sin(2πft) × ランプ（0〜50 ms で 0 → 1、200 ms まで保つ、250 ms で 0）の波形にして titration し直した（`neuron_ti_ramp_setup.py`）。

| 線維 | 倍率の変化（ランプ無し → 付き） | 最初の発火の時刻（ランプ無し → 付き） |
|---|---|---|
| MRG 16 µm | 7 本とも 7% 以内（例 target_x 39.5 → 41.75・offA_z 9.125 → 9.44） | 1〜7 ms → 94〜97 ms（4 本）、44〜48 ms → 51〜52 ms（3 本） |
| Sundt 0.8 µm | 7 本とも 8% 以内（例 target_x 2816 → 3040・offA_z 952 → 912） | 15〜20 ms → 118〜122 ms、67〜70 ms → 168〜174 ms、101〜104 ms → 118〜123 ms |

- **ランプの有無は結論に効かない**。発火は包絡の山（100 ms、逆向きの線は 50・150 ms）に移り、倍率は 8% 以内しか変わらない。
- **閾値は合成した場の振幅の最大（包絡の山の高さ）で決まる**。ランプ無しで始まりに発火していたのは、同じ高さの山が t = 0 にあったから。2000 Hz 同士の Run（§6）でも振幅の最大は同じなので倍率がほぼ同じだったことも、これで説明がつく。
- MRG は包絡の山の直前〜直後、Sundt は山の約 20 ms 後に発火する（ランプ無し・付きとも同じずれ）。

ランプ無しの値（`results/neuron_ti_titration_l2_{mrg16,sundt}_2026-10-19.json`）も `neuron_l2_table_2026-10-21.md` に並べてある。

## 3. 場のレベルとの関係（2 つの物差し）

場のレベル（`comparison-table.md` 結論②③・GH #19）と神経のレベルで、**深部到達の向きが逆になる**。

| | 場のレベル（文献の有効範囲の下端・振幅） | 神経のレベル（モデルの発火） |
|---|---|---|
| tTIS | ROI 平均で下端の **113%**（中点では 65%） | 標的の発火に **41.8 倍**（MRG）足りない |
| TUS | ROI 平均で下端の **42%**（中点では 18%） | 安全上限の **0.43 倍**（MRG）で発火する |

食い違いの原因は物差しの違い:
- **場のレベルの目安は「効果が報告されている強さの範囲」**で、発火の閾値ではない。tTIS の 0.2〜0.5 V/m は tACS で神経調節が報告された範囲、TUS の 3〜30 W/cm² はヒトの研究で設定される ISPPA の範囲（Sharif 2025）。
- **神経のレベルは「静かな試験用の線維が 1 本で発火する強さ」をモデルで出したもの**。
  - tTIS: 標的の MRG を発火させるには 2 mA の 41.8 倍。ROI 平均の TI 0.2265 V/m に掛けると約 9.5 V/m で、0.2〜0.5 V/m とは桁が違う（目安。軸索に沿った場は TI 包絡の値と同じではない）。皮質の錐体細胞の TI の発火閾値 75〜230 V/m（Wang 2023）とも同じ向き（電場で発火させるには 0.2 V/m 程度では全く足りない）。
  - TUS: SONIC モデルは MRG 16 µm が約 108 kPa、Sundt が約 26 kPa で発火すると予測する。ISPPA に直すと約 0.39 W/cm² と 0.02 W/cm²（ρc ≈ 1.5×10⁶ と仮定）で、文献の下端 3 W/cm²（約 300 kPa）よりずっと低い。

**どちらの物差しでも変わらないのは選択性**（TUS は標的を選べる・tTIS は標的外の方が強い）。**変わるのは「どこまで届くか」で、どちらの閾値を信じるかで逆転する**。
「TUS は安全上限で標的が発火する」は SONIC モデルの上での結論であり（§5-3）、「tTIS の方が目安に近い」は文献の調節の範囲の上での結論。

## 4. 実装

### 4-1. tTIS（Sim4Life.lite 神経ソルバー）

| 項目 | 値 | 出典 |
|---|---|---|
| 場 | `tTIS_LF1`（T7–P7）・`tTIS_LF2`（Fp1–Fp2）の Overall Field。Source 1/2 として別々につなぐ | `neuron_ti_create.py` |
| 波形（ランプ付き・主） | PulseType **Vectors**。振幅 × sin(2πft) × ランプ（上げ 50 ms・保持〜200 ms・下げ〜250 ms）を 10 µs 刻み 25001 点。f は **2000 Hz / 2010 Hz** | `neuron_ti_ramp_setup.py` |
| 波形（ランプ無し） | Sinusoidal 2000 Hz / 2010 Hz、開始 0、100 ms（半周期 400 / 402） | — |
| 振幅 | 0.2056 / 0.3316 ＝ Inoue 2025 の 0.891 / 1.109 mA（合計 2 mA）÷ 1 V 駆動時の 4.334 / 3.344 mA | `current_scale.py` |
| 神経（MRG） | Motor MRG 16 µm。形は MorphoSONIC の MRGFiber に合わせて直接入れた（節の間隔 1500 µm・節 5.5・FLUT 60 / 12.7・STIN 228.83 / 12.7 µm・150 枚）。線 9.0 mm で 7 節。名前 `m16_` | `neuron_ti_place_l2_mrg16.py` |
| 神経（Sundt） | Unmyelinated Sundt 0.8 µm・区画の長さ 21.93 µm（10 mm ÷ 456）・線 10 mm。名前 `sun_` | `neuron_ti_place_l2_sundt.py` |
| Solver | Duration 260 ms（ランプ無しは 110 ms）・Time Step 0.0025 ms | — |
| 判定 | Titration on（収束 1%）。2 つの Source を同じ倍率で強めるので電流比は保たれる。1 倍 = 合計 2 mA | — |
| 計算 | MRG 7 本: ランプ無し 約 13 分・付き 33 分 39 秒／Sundt 7 本: ランプ無し 2 時間 49 分・付き 約 7 時間（見込み・計っていない） | — |

読み取りは `neuron_ti_read_titration_l2.py`。

### 4-2. TUS（Sim4Life の音圧 → MorphoSONIC）

| 項目 | 値 | 出典 |
|---|---|---|
| 音圧 | `TUS_250k`（音源 1 MPa）を k = 0.15580 で MI<1.9 にスケールし、7 本の線に沿って 0.25 mm 刻み 41 点を三線形補間（組織も取り出す） | `neuron_tus_line_pressure2.py` → `results/neuron_tus_line_pressure2_2026-10-15.txt` |
| 線上の最大音圧 | 標的 214〜251 kPa（すべて脳）／offA 12〜25 kPa・offB_y 16 kPa（延髄。標的の約 4%） | 同上 |
| 音源 | 線に沿った音圧の表を区画ごとに与える自作の `ProfileAcousticSource`（MorphoSONIC に任意分布の音源が無いため）。既製の音源との差 0.05% 以内で関門を通過 | `neuron_tus_profile_source.py`・`archive/neuron_tus_profile_gate.py` |
| 神経モデル | MorphoSONIC（Lemaire 2021）の SONIC モデル。MRGFiber 16 µm・7 節／UnmyelinatedFiber（Sundt）0.8 µm・10 mm・456 区画。ソノフォア半径 32 nm・被覆率 fs = 1・36 °C | `neuron_tus_titrate_lines.py` |
| 刺激 | 250 kHz・100 ms 連続波（tTIS と同じ長さ）・その後 50 ms | 同上 |
| 判定 | titrate（二分探索）。発火は両端の節まで spike が届くこと（MorphoSONIC の標準） | 同上 |
| 計算 | MRG 1 本 1.5〜2.4 分／Sundt 1 本 30 分〜3 時間（ローカル） | `results/neuron_tus_titrate_lines_2026-10-15.jsonl` |

環境: `~/envs/insula-sonic`（構築手順は `archive/neuron_morpho_gate.py` の docstring）。

### 4-3. 実装の突き合わせ（同じ電流注入）

両ツールの軸索の中央に 0.1 ms の細胞内電流（IClamp）を流し、発火の閾値を比べた。電場や音圧を介さないので、差は軸索の実装（形・チャネル・温度）の違い。

| 線維 | MorphoSONIC の閾値 | Sim4Life の閾値 | 比 |
|---|---|---|---|
| MRG 16 µm（中央の節） | 1.455 nA | 2.18〜2.91 nA の間 | **1.5〜2.0 倍** |
| Sundt 0.8 µm（中央の区画） | 0.715 nA | 0.715〜0.787 nA の間 | **1.0〜1.1 倍** |

`neuron_iclamp_morpho.py`（MorphoSONIC）、`neuron_iclamp_sweep_setup.py`・`neuron_iclamp_set_amps.py`・`neuron_iclamp_read.py`（Sim4Life。強さを 5 段に振った軸索を 1 回の Run で回す）、結果は `results/neuron_iclamp_sim4life_2026-10-18.txt`。

- **実装の違いは MRG で最大 2 倍、Sundt でほぼ無い**。手法の中の「標的 対 標的外」は同じ実装どうしの比なので、この違いは効かない。tTIS の MRG の標的の倍率 41.8 を 2 で割っても約 21 で、2 mA で発火しないことは変わらない。
- MRG の 1.5〜2 倍の原因は特定していない（静止電位・チャネルの実装など）。温度は両ツールとも 36 °C（Sim4Life 側も 36 °C に設定したと本人が確認、2026-10-27）なので、温度は原因ではない。
- Sim4Life の Sundt は 455 区画（0〜454）で、MorphoSONIC の 456 と 1 つ違う。

## 5. 限界

### 5-1. 比較の組み方
- **神経は島皮質の神経ではない**。MRG は末梢の太い運動線維、Sundt は末梢の細い感覚線維。島皮質の発火の主役は錐体細胞などの皮質ニューロンで、形と枝を持つ。言えるのは「共通の基準の線維で比べた、神経レベルでの 2 手法の相対比較」まで。倍率の絶対値を脳の神経の閾値として読まない。
  錐体細胞にそろえられないのは、TUS 側（MorphoSONIC）に形のある皮質ニューロンへ SONIC をかける仕組みが無いため（L3・将来の研究）。
- **まっすぐ 10 mm・枝なし**。実際の軸索は曲がり、終末や分枝で閾値が下がる。
- **刺激は 100 ms（TUS・tTIS ランプ無し）／250 ms（tTIS ランプ付き）**。実際の刺激は数秒〜数分続く。計算時間に合わせた長さ。
- **1 人の頭**（Yoon-sun）・場は等方の導電率・1 mm の格子。標的外は脳脊髄液との境のそば。

### 5-2. tTIS 側
- 倍率は合成した場の振幅の最大で決まっていて（§2）、TI の包絡による発火（イオンチャネルの整流）と、kHz の正弦波そのものによる発火を、この計算では分けていない。
- TI による発火そのものにも議論がある（高周波による伝導ブロック等）。
- Sundt の最初の発火はほぼ線の端（section 7〜11・442〜447）。切れた端の効果が混ざっている。

### 5-3. TUS 側
- **SONIC（膜内キャビテーション仮説）には異論がある**。
- **SONIC の閾値は文献の有効域よりずっと低い**（MRG 約 0.39 W/cm²・Sundt 約 0.02 W/cm² 対 下端 3 W/cm²・§3）。fs = 1（膜の全面が反応）は最も発火しやすい設定。「TUS は標的で発火する」は SONIC モデルの上での結論。
- 250 kHz は lookup の 100 kHz と 500 kHz の間の補間。

### 5-4. Sim4Life.lite
- 神経は 1 回の Run に **10 本まで**。MRG と Sundt の 7 本ずつは別の Run。
- 同じ HOC の型の神経は 1 回の Run に 1 本だけ（自動軸索を使ったので影響なし）。

## 6. 経過（無効にした結果）

- **1 回目（10-13）**: 標的外を「脳内の TI 最大点 (48.5, 274.5, 1482.5)・標的の 10.7 倍」に置き、MRG 20 µm（tTIS）と RS 点神経（TUS）で比べた。その点は脳ではなく腱・靭帯だった（#17）うえ、神経モデルが手法で違ったので無効。`results/invalid/neuron_ti_titration_2026-10-13.json`・`results/invalid/neuron_tus_pysonic_2026-10-13.txt`（手順は `archive/neuron_ti_place_axons.py`・`archive/neuron_tus_site_pressure.py`・`archive/neuron_tus_pysonic.py`・`archive/neuron_ti_read_titration.py`）。
- **2000 Hz の不具合（10-17〜10-18 の L2 ③）**: TI_Neuron の 2 つ目の Source（Source Settings 1）の周波数が 2010 Hz ではなく **2000 Hz のまま**だった（10-18 に `archive/neuron_ramp_probe.py` で発見、GUI で確認）。2 つの Source が同じ周波数なので 10 Hz のうなりが出ず、TI ではなく 2 kHz の単純な正弦波刺激になっていた。10-13 の 1 回目も同じ設定。直して 10-19 に MRG・Sundt ともやり直した。無効: `results/invalid/neuron_ti_titration_l2_mrg16_2026-10-17.json`・`results/invalid/neuron_ti_titration_l2_sundt_2026-10-18.json`。
  直す前と後で倍率はほぼ同じだった（例 MRG target_x 39 → 39.5）。閾値が振幅の最大で決まるため（§2）で、結論は変わらない。

## 7. 手順（再現）

tTIS（Sim4Life.lite・統合版プロジェクト）:
1. `neuron_ti_create.py` — `TI_Neuron` を作り、`tTIS_LF1` / `LF2` の Overall Field を Source につなぐ。**Source Settings 1 の周波数が 2010 Hz になっているかを GUI で必ず確かめる**
2. `neuron_ti_place_l2_mrg16.py`・`neuron_ti_place_l2_sundt.py` — 7 本ずつ軸索を作る
3. GUI: `Neurons` → `New Settings ▾` → Automatic Axon Model Settings → 7 本をドラッグ（上限 10 本なので MRG と Sundt は別の Run）
4. Setup で Titration on。ランプ付きは `neuron_ti_ramp_setup.py`（PulseType Vectors・Solver Duration 260 ms）
5. Run → `neuron_ti_read_titration_l2.py`

TUS:
1. `neuron_tus_line_pressure2.py`（Sim4Life）— 7 本の線上の音圧と組織
2. `neuron_tus_titrate_lines.py <fiber> <line>`（ローカル・MorphoSONIC）— 閾値と倍率

表: `python3 scripts/neuron_l2_table.py`

API の注意:
- 神経の設定は `sim.Add(設定, [エンティティ])` だと `incompatible with this type of simulation` で失敗する。GUI のドラッグで入れる。
- ただの線は軸索の設定に入らない。`model.CreateAxonNeuron(s)` で神経のエンティティにしてから入れる。
- **結果が付いていると設定に鍵がかかり、Python の代入が黙って無視される**。Clear Results を先にし、代入後に読み直して確かめる。
- Source の波形を自分で入れるときは PulseType **Vectors**（UserDefined はファイルを読む種類で、`StimulusFilePath` が空だと `Error generating user defined pulse` で Run が始まらない）。TimeVector・ModulationVector は**タプル**で代入する（numpy 配列・リストは黙って入らない）。時刻は ms。
- Titration は外部の Source（電場）が無いと動かない（`No external source available`）。IClamp だけの突き合わせは Titration off にし、強さを振った軸索を並べて判定した。
- Titration の結果は `res["Titration Sensor"]["Titration"].Data.DataJson`（JSON 文字列）。位置は m、時刻は s。
- 計算はサーバーで回るので、Run 中に project を閉じても、開き直せば結果は残っている。

## 8. 次

notebook の Discussion に入れるかを #20（執筆）で判断する。入れる場合は、§3（場と神経の 2 つの物差し）と §5-1（島皮質の神経ではない）を一緒に書く。
