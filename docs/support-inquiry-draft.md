# ZMT サポート / フォーラム照会の下書き（Run 拒否）

送り先: `s4l-support@zmt.swiss` ／ フォーラム https://forum.zmt.swiss/
使うタイミング: **リロード済みの素のセッションで `run_step1_lf1.py` を流しても Run が拒否される場合**
（ツール固有の検証エラーなので、こちら側の推測では詰められない領域と判断したら送る）。

添付するも（送る前に用意）:
- `Input.log`（ソルバー入力・`Degree of freedoms` 行を含むもの）
- `Voxeler.log`
- `dump_logs.py` の出力（コンソールのコピー）
- スクリーンショット: Explorer のツリー（sim・材料・BC が見える状態）

---

## 本文（英語・そのまま送れる形）

Subject: Sim4Life.lite — "Unable to run simulation. Please check your simulation settings." on a clean Electro Ohmic Quasi-Static setup

Hello,

I am a student using Sim4Life.lite (free student licence) for a research project on
transcranial temporal interference stimulation (tTIS) targeting the insular cortex.
I build everything from the Python console because the anatomical model could not be
loaded through the GUI in my environment.

**Setup (built by script, in this order):**
1. Yoon-sun (ViP V3, included with .lite) loaded via `data.DownloadModel` + import of the `.sab`.
2. Four disc electrodes created as solids (`CreateSolidCylinder`), named `Elec_T7`, `Elec_P7`, `Elec_Fp1`, `Elec_Fp2`.
3. `emlf.ElectroQsOhmicSimulation()`, `SetupSettings.Frequency = 2000 Hz`, registered with `document.AllSimulations.Add(sim)`.
4. Material settings for the 59 head tissues inside the grid box, linked to the **IT'IS LF 5.0** database
   (`sim.LinkMaterialWithDatabase(ms, material_object)`), plus an explicit conductivity of 1.6 S/m
   on the two driving electrodes `Elec_T7` / `Elec_P7`.
5. Dirichlet boundary settings: `Elec_T7 = 1 V`, `Elec_P7 = 0 V`.
6. Grid: global `MaxStep = 5 mm`, plus a manual grid setting of 1 mm on a block enclosing the head
   (X 4–202, Y 162–352, Z 1450–1665 mm). `UpdateGrid()` then `CreateVoxels()` **last**, after all assignments.
   Resulting grid ≈ 12.3 million cells (below the 20 M limit of .lite).
7. `document.Save()`, then `sim.RunSimulation(wait=True)`.

**Problem:**
`sim.RunSimulation(wait=True)` raises

```
RuntimeError: Unable to run simulation. Please check your simulation settings.
```

The only log produced is `<uuid>_Voxeler.log`, which contains

```
Error: The boundary component 'Elec_T7' is not being considered in the voxeling process.
```

**No `Input.log` is produced at all**, so the solver never starts — the run stops during voxeling.
This happens in a completely fresh session (verified before the run: no existing simulations,
no duplicated entities, all four electrodes present, 59 head tissues in the grid box), and the
material assignment reports 61 material settings (59 tissues + the 2 driving electrodes) with
nothing unmapped. The HDF5 messages (`H5A__create(): attribute already exists`) also appear in this
fresh session, so they look like a symptom rather than the cause.

**Observation that may be the key:**
The failure mode changes depending on whether the electrode solid has a material:

| electrode solid | result |
|---|---|
| Dirichlet BC only, no material | run completes, but `0 Dirichlet points` / `no lossy dielectrics` → all field values NaN |
| Dirichlet BC **and** a material (σ = 1.6 S/m) | run is **rejected** with the message above |

So assigning both a volume material and a Dirichlet boundary condition to the *same solid entity*
seems to be the problem. **Should the Dirichlet boundary condition be applied to a surface / face of
the electrode solid instead of to the solid itself?** If so, what is the correct way to obtain that
surface from the Python API for a solid created with `CreateSolidCylinder`?

**What I have already ruled out:**
- Simulation not registered — it is added to `document.AllSimulations`.
- Missing conductivities — every tissue material has a non-zero conductivity (verified by reading
  `ms.ElectricProps.Conductivity`); only `Air_internal` is 0, which is expected.
- Wrong material database — materials were re-linked from **IT'IS LF 5.0** (passing the material object,
  not the name string, so the default IT'IS 5.0 is not picked up).
- Voxeling order — `CreateVoxels()` is called after all material and boundary assignments.
- The earlier cause of an all-NaN result was found and fixed: the driving electrodes had **no material
  assigned**, so the voxeler reported
  `Error: The boundary component 'Elec_T7' is not being considered in the voxeling process.`
  and the solver reported `0 unknowns, 0 Dirichlet points, no lossy dielectrics`.
  Electrodes now get a conductivity, and the whole setup is rebuilt in one clean script.

**Question:**
Which validation check produces "Unable to run simulation. Please check your simulation settings."
in an Electro Ohmic Quasi-Static simulation, and where can I see the specific reason?
Is there a way to obtain the validation report / the list of failed checks from the Python API,
so I can see which setting is considered invalid?

Logs are attached (`Input.log`, `Voxeler.log`).

Thank you very much for your help.

Best regards,
（署名）

---

## 送る前のチェック
- [ ] リロード後の素のセッションで1回だけ再試行した（同名衝突を除外した）
- [ ] `Input.log` の `Degree of freedoms` 行を本文に貼った（実数値）
- [ ] `Voxeler.log` に `not being considered` が無いことを確認した（あれば真因は電極材料側なので送らない）
- [ ] 添付ファイルを付けた
