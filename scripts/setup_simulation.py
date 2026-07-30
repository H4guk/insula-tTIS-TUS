"""（旧・分割元）工程6 ±電位 BC ＋ 工程7 グリッドを設定（Sim4Life.lite / Electro QS）。

1 シミュ = 1 電極対（TI は 2 つの近接周波数のペアを重ねる）。
まず tTIS_LF1 = ペア1（T7 +1V / P7 0V）。ペア2（Fp1–Fp2）は別シミュ tTIS_LF2 に同手順で。

グリッド: 材料付き Skin が全身なので、そのままだと Global MaxStep=[1,1,1]＝全身1mm で破綻。
  → 頭部だけ 1mm（頭部を囲む Block に ManualGridSettings）・体は Global 5mm。
★enum が read-only の壁の突破: `Prop.set(Prop.findValue('Manual'))`（Sim4Lite の汎用手）。

⚠️⚠️ 各ステップ後に s4l_v1.document.Save() で保存する（保存忘れで状態が壊れた事故あり）。
出典ノート: Claude/Knowledge/sim4life-electrode-placement.md ⑥⑦
"""
import s4l_v1.model as model
import s4l_v1.simulation.emlf as emlf
import XCoreModeling as xc

# sim = tTIS_LF1（assign_materials.py で作成済みの Electro QS シミュを使う想定）


# ===== ⑥ ±電位 BC（電極を駆動）=====
def add_dirichlet(sim, elec_name, voltage, bc_name):
    ent = [e for e in model.AllEntities() if e.Name == elec_name][0]
    bc = sim.AddBoundarySettings(ent)
    bc.Name = bc_name
    bc.BoundaryType = emlf.EnumBoundaryType.kDirichlet   # ※Deprecated警告出るが動く
    bc.DirichletValue = voltage                          # ボルト
    return bc


# 1V 駆動でよい（電場は線形。後で Inoue の 0.891mA に合わせるのは計算後にスケール）。
# 両方 0V だと電位差ゼロで電流ゼロ → 必ず +1V と 0V で差をつける。
add_dirichlet(sim, 'Elec_T7', 1.0, 'BC_T7_pos')
add_dirichlet(sim, 'Elec_P7', 0.0, 'BC_P7_gnd')


# ===== ⑦ グリッド設定（頭部 1mm / 体 5mm）=====
def V(p): return model.Vec3(*map(float, p))


# 体（Global）を粗く 5mm に（enum の read-only 突破）
ggs = sim.GlobalGridSettings
p = ggs.DiscretizationModeProp
p.set(p.findValue('Manual'))          # ★enum 設定の正解パターン
ggs.MaxStep = [5.0, 5.0, 5.0]         # 体 = 5mm

# 頭部を囲む Block に ManualGridSettings で 1mm
grid_box = xc.CreateSolidBlock(V([4, 162, 1450]), V([202, 352, 1665]))  # 頭部 envelope
grid_box.Name = 'GridBox_head'
mg = sim.AddManualGridSettings(grid_box)
mg.Name = 'Grid_head_1mm'
mg.MaxStep = [1.0, 1.0, 1.0]          # ManualGridSettings の MaxStep は素直に書ける
sim.UpdateGrid()

# 実測: CreateVoxels → グリッド次元 [229,221,246] ≈ 1229万セル（2000万以内 OK）。
