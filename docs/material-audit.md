# 材料対応表の監査（IT'IS LF 5.0）

対応 Issue: [#11](https://github.com/H4guk/insula-tTIS-TUS/issues/11)（ViP 組織名→DB 材料名の対応表を監査していない）
実測日: 2026-08-12 ／ 出力元: `scripts/audit_materials.py`（読み取り専用）
対象: `tTIS_LF1`（頭部グリッド内の 59 組織 ＋ 既定の Air ＝ 60 材料設定 / 42 の異なる材料）

**この表はレポートの材料表としてそのまま使える。**

---

## なぜ監査が要ったか

組織名 → 材料名の対応づけは自動なので（`model.AutoAssignMaterials` の単語集合マッチ
＋ 手動辞書 ＋ DB 側の別名・表記ゆれ解決）、**"もっともらしい別材料" に当たっても気づかない**。
σ の値だけ見て「妥当なレンジだ」と判断すると、隣接組織の値に当たっている誤対応を見逃す。

実際に 2026-08-09 の監査で、**σ が意図した DB（IT'IS LF 5.0）ではなく
非 LF DB を 2 kHz で評価した値だった**ことが発覚している（詳細 → `progress-log.md` 2026-08-09）。

## 検証の仕組み（どこで何を担保しているか）

| 検査 | 担保している場所 | 内容 |
|---|---|---|
| σ の値そのもの | `assign_materials.py` の事後ゲート | **リンク先 DB の格納値と全件直接照合**（期待値をハードコードしない） |
| 材料が DB に存在するか | 同 事前ゲート | sim を作る**前**に全材料を解決。無ければ副作用ゼロで中断 |
| 表記ゆれの可視化 | 同 事前ゲート | 完全一致でない解決（正規化名・別名）を**必ず出力に出す** |
| 対応表の妥当性 | `audit_materials.py` | 本ファイルの表を出力。多対1 の一覧で誤対応を検出 |
| 場に反映されているか | `sigma_map.py` | `σ = 2·loss/\|E\|²` で場から σ を逆算し、既知値と照合 |

★ **期待値のハードコードは使わない。** ハードコードすると、別 DB を引く事故が
「期待値の方を書き換えれば通る」形になり原理的に検出できない（#14 の教訓）。

---

## 材料ごとの σ（42 材料）

| 材料 | σ [S/m] | 割り当て組織数 |
|---|---|---|
| Air | 0 | 2 |
| Blood | 0.66246 | 2 |
| Bone (Cancellous) | 0.0804595 | 6 |
| Bone (Cortical) | 0.006302 | 7 |
| Brain (Grey Matter) | 0.419055 | 1 |
| Brain (White Matter) | 0.347954 | 2 |
| Cartilage | 0.73926 | 3 |
| Cerebellum | 0.576612 | 1 |
| Cerebrospinal Fluid | 1.879 | 1 |
| Commissura Anterior | 0.347954 | 1 |
| Commissura Posterior | 0.347954 | 1 |
| Dura | 0.06 | 1 |
| Esophagus | 0.163536 | 1 |
| Eye (Cornea) | 0.62 | 1 |
| Eye (Lens) | 0.345333 | 1 |
| Eye (Sclera) | 0.62 | 1 |
| Eye (Vitreous Humor) | 2.16486 | 1 |
| Fat | 0.0776213 | 1 |
| Hippocampus | 0.419055 | 1 |
| Hypophysis | 1.05162 | 1 |
| Hypothalamus | 0.419055 | 1 |
| Intervertebral Disc | 0.73926 | 1 |
| Larynx | 0.73926 | 1 |
| Lymphnode | 0.220522 | 1 |
| Medulla Oblongata | 0.357 | 1 |
| Midbrain | 0.35 | 1 |
| Mucous Membrane | 0.461008 | 1 |
| Muscle | 0.461008 | 1 |
| Nerve | 0.347954 | 1 |
| Pineal Body | 0.4811 | 1 |
| Pons | 0.558392 | 1 |
| SAT (Subcutaneous Fat) | 0.0776213 | 1 |
| Salivary Gland | 0.5586 | 1 |
| Skin | 0.148297 | 3 |
| Skull (Cancellous) | 0.09975 | 1 |
| Skull (Cortical) | 0.00644673 | 1 |
| Spinal Cord | 0.610954 | 1 |
| Tendon\Ligament | 0.367577 | 1 |
| Thalamus | 0.475 | 1 |
| Tongue | 0.461008 | 1 |
| Tooth | 0.006302 | 1 |
| Trachea | 0.341987 | 1 |

## 組織 → 材料の対応（59 組織 ＋ Air 2）

| ViP 組織 | 材料 | σ [S/m] |
|---|---|---|
| Air_internal | Air | 0 |
| Artery | Blood | 0.66246 |
| Background | Air | 0 |
| Cartilage | Cartilage | 0.73926 |
| Cerebellum | Cerebellum | 0.576612 |
| Cerebrospinal_fluid | Cerebrospinal Fluid | 1.879 |
| Cerebrum_grey_matter | Brain (Grey Matter) | 0.419055 |
| Cerebrum_white_matter | Brain (White Matter) | 0.347954 |
| Commissura_anterior | Commissura Anterior | 0.347954 |
| Commissura_posterior | Commissura Posterior | 0.347954 |
| Corpus_callosum | Brain (White Matter) | 0.347954 |
| Dura_mater | Dura | 0.06 |
| Ear_cartilage_left | Cartilage | 0.73926 |
| Ear_cartilage_right | Cartilage | 0.73926 |
| Ear_skin_left | Skin | 0.148297 |
| Ear_skin_right | Skin | 0.148297 |
| Esophagus_wall | Esophagus | 0.163536 |
| Eye_cornea | Eye (Cornea) | 0.62 |
| Eye_lens | Eye (Lens) | 0.345333 |
| Eye_sclera | Eye (Sclera) | 0.62 |
| Eye_vitreous_humor | Eye (Vitreous Humor) | 2.16486 |
| Fat | Fat | 0.0776213 |
| Hippocampus | Hippocampus | 0.419055 |
| Hyoid_cortical | Bone (Cortical) | 0.006302 |
| Hypophysis | Hypophysis | 1.05162 |
| Hypothalamus | Hypothalamus | 0.419055 |
| Intervertebral_disc | Intervertebral Disc | 0.73926 |
| Larynx | Larynx | 0.73926 |
| Lymph_node | Lymphnode | 0.220522 |
| Mandible_cancellous | Bone (Cancellous) | 0.0804595 |
| Mandible_cortical | Bone (Cortical) | 0.006302 |
| Medulla_oblongata | Medulla Oblongata | 0.357 |
| Midbrain | Midbrain | 0.35 |
| Mucosa | Mucous Membrane | 0.461008 |
| Muscle | Muscle | 0.461008 |
| Nerve | Nerve | 0.347954 |
| Pineal_body | Pineal Body | 0.4811 |
| Pons | Pons | 0.558392 |
| SAT | SAT (Subcutaneous Fat) | 0.0776213 |
| Salivary_gland | Salivary Gland | 0.5586 |
| Skin | Skin | 0.148297 |
| Skull_cancellous | Skull (Cancellous) | 0.09975 |
| Skull_cortical | Skull (Cortical) | 0.00644673 |
| Spinal_cord | Spinal Cord | 0.610954 |
| Tendon_ligament | Tendon\Ligament | 0.367577 |
| Thalamus | Thalamus | 0.475 |
| Tongue | Tongue | 0.461008 |
| Tooth | Tooth | 0.006302 |
| Trachea_wall | Trachea | 0.341987 |
| Vein | Blood | 0.66246 |
| Vertebra_cancellous_C1〜C5 | Bone (Cancellous) | 0.0804595 |
| Vertebra_cortical_C1〜C5 | Bone (Cortical) | 0.006302 |

## 多対1 の対応（7 材料）— すべて正当と判断

| 材料 | 組織数 | 組織 | 判断 |
|---|---|---|---|
| Bone (Cortical) | 7 | Hyoid・Mandible・Vertebra C1–C5 の皮質 | 同一組織種なので正当 |
| Bone (Cancellous) | 6 | Mandible・Vertebra C1–C5 の海綿 | 同上 |
| Cartilage | 3 | Cartilage・Ear_cartilage 左右 | 同上 |
| Skin | 3 | Skin・Ear_skin 左右 | **DB 側の公式な別名**に `Ear_skin_left` / `Ear_skin_right` が含まれる |
| Air | 2 | Air_internal・Background | σ=0 が正常 |
| Blood | 2 | Artery・Vein | 動脈と静脈で同じ材料は正当 |
| Brain (White Matter) | 2 | Cerebrum_white_matter・Corpus_callosum | 脳梁は白質なので正当 |

★ **頭蓋骨は `Bone (…)` ではなく `Skull (…)` を使っている。** LF 5.0 は両方を持ち、
値が違う（皮質 0.006302 / 0.00644673 はほぼ同じだが、**海綿は 0.0804595 / 0.09975 で 24% 違う**）。
頭部専用の `Skull` 系を当てるのが正しい。

---

## 監査の結論

- **誤対応は 1 件も見つからなかった**（欠陥 0 件・多対1 はすべて正当）。
- σ を場から逆算した値（`sigma_map.py`）が既知値と一致し、**材料が場に正しく反映されている**
  ことも確認済み（体積上位: Muscle 791 mL・灰白質 530 mL・Skin 397 mL・白質 393 mL・
  皮質骨 319 mL・CSF 80 mL）。工程5 のゲートは**設定値**しか見ないので、これは場の側からの独立確認。
- σ マップで未同定だった最大の塊（σ=0.0776・1709 mL）は **`Fat` ＋ `SAT`** と判明。

### LF と非 LF の差は皮膚・骨だけではない

材料を IT'IS LF 5.0 に移す前は、非 LF DB の分散モデル（Gabriel 4-Cole-Cole）を 2 kHz で
評価した値が入っていた。差が大きい組織:

| 組織 | 非 LF（2 kHz 評価） | LF 5.0 | 比 |
|---|---|---|---|
| Skin | 0.0002（乾燥角質） | 0.148297 | 741× |
| Cartilage | 0.174946 | 0.73926 | 4.2× |
| Cerebellum | 0.122764 | 0.576612 | 4.7× |
| Brain (Grey Matter) | 0.102764 | 0.419055 | 4.1× |
| Brain (White Matter) | 0.0639697 | 0.347954 | 5.4× |
| Skull (Cortical) | 0.0202361 | 0.00644673 | 0.32× |
| Dura | 0.500917 | 0.06 | 0.12× |
| Cerebrospinal Fluid | 2.0 | 1.879 | 0.94× |

**脳組織は 4〜5倍高く、頭蓋骨と Dura は逆に低い。** 頭蓋骨が電流を通しにくくなり、
脳内の導電率が上がる方向なので、電場分布への影響は小さくない。
LF 帯（2 kHz）の計算では LF データセットを使うのが妥当（分散モデルの低周波外挿には
既知の過小評価があり、**乾燥皮膚 0.0002 S/m という非物理的な値が出ること自体がその症状**）。

### ⚠️ 解析側への申し送り: 選択性の「脳マスク」には脳以外が少量混ざる

`ti_analysis.py` は非標的領域を σ の帯で切り出している（`σ ∈ [0.33, 0.44]` ＝ 白質 0.347954
＋ 灰白質 0.419055）。この帯には**脳以外も入る**:

| 材料 | σ | 脳か |
|---|---|---|
| Nerve / Commissura Anterior・Posterior | 0.347954 | 実質脳（交連線維・神経） |
| Midbrain 0.35 / Medulla Oblongata 0.357 | 0.35 / 0.357 | 脳 |
| Hippocampus / Hypothalamus | 0.419055 | 脳 |
| **Tendon\Ligament** | 0.367577 | **違う** |
| **Eye (Lens)** | 0.345333 | **違う** |
| **Trachea** | 0.341987 | **違う** |

ただし混入分は σ ヒストグラムの体積上位20件（20位が 8.19 mL）に入っておらず、
**合計 ≲15 mL / 945 mL ≈ 1.5%**。しかも頸部・眼で電場が弱い領域なので、
**選択性 0.376 という値は実質変わらない**。組織ラベルが使えるモデルに移れる場合は
ラベルベースのマスクの方が厳密（Yoon-sun では σ 経由が唯一の手段）。

なお `Cerebellum` 0.576612・`Pons` 0.558392・`Thalamus` 0.475 は帯の外なので、
現在の「脳」マスクは**大脳の GM+WM 中心**（小脳・脳幹・視床は含まない）。
