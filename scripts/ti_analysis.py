"""Step 2（Phase 2 / GH #7）E 場抽出 → TI 包絡線 → 島皮質 ROI 定量（Sim4Life.lite Python コンソール）。

前半（get_E / TI 計算 / reshape / 深部代理点）は lec8 で SAM head 上で検証済みの実コード。
後半（本番 ROI: mm 球 ROI での体積重み平均・選択性）は、tTIS-field-simulation.md に
"確立した関数" として記述された仕様からの実装。★実機の確定版はコンソール履歴で要確認。

TI = 2·min(|E1|,|E2|)（Grossman 等方近似）。
選択性 = 非標的領域の平均EFE / 標的(ROI)の平均EFE（小さいほど良い）→ Inoue 2025 の ≈0.40 と照合。

出典ノート: Study record/sim4life/Sim4life-lec8.md（前半・検証済み）
           Claude/Projects/tTIS-field-simulation.md「本番トラック」（後半・ROI 仕様）
"""
import s4l_v1.document as document
import numpy as np


# ===== E 場抽出（lec8・検証済み）=====
# ⚠️ Python で作った sim は document.AllSimulations に自動登録されない（v10）。
#    Run 後に document.AllSimulations.Add(sim) で登録してからでないと、下の
#    辞書アクセス document.AllSimulations[sim_name] も sim.Results() も使えない。
def get_E(sim_name):                       # シミュ名 → E場 numpy配列 を返す
    sim = document.AllSimulations[sim_name]
    res = sim.Results(); res.UpdateAll()
    of = res['Overall Field']; of.Update()
    ef = of['EM E(x,y,z,f0)']; ef.Update()
    return ef.Data.Field(0)                # (N, 3) complex：各点の E ベクトル


def ti_envelope(arr1, arr2):               # 2 場 → TI 包絡線マップ（各点スカラー）
    mag1 = np.sqrt(np.sum(np.abs(arr1) ** 2, axis=1))   # |E1|
    mag2 = np.sqrt(np.sum(np.abs(arr2) ** 2, axis=1))   # |E2|
    return 2.0 * np.minimum(mag1, mag2)                 # 両方揃って強い点が生き残る


# ===== グリッド幾何（★本番・documented spec から実装・要実機確認）=====
# tTIS-field-simulation.md の実測知見:
#   ef.Data.Grid は RectilinearGrid（XAxis/YAxis/ZAxis を保持）。
#   ValueLocation=1（セル中心データ）＝軸はセル境界 → 中心 = 0.5*(axis[:-1]+axis[1:])。
#   GetUnit()=m（半径10mm=0.010）。並びは X-fastest：flat = x + nx*(y + ny*z)。
#   グリッドは非一様（graded）→ ROI 内平均はセル体積 dz*dy*dx で重み付け必須。
def grid_cell_centers(field_data):
    g = field_data.Grid
    def ax(a):
        a = np.asarray([float(v) for v in a], dtype=float)
        return 0.5 * (a[:-1] + a[1:])      # セル境界 → セル中心
    xc = ax(g.XAxis); yc = ax(g.YAxis); zc = ax(g.ZAxis)
    return xc, yc, zc                       # 単位 m・長さ nx,ny,nz


def sphere_mask(field_data, center_mm, radius_mm):
    """mm 指定の球 ROI を X-fastest の flat マスクで返す（単位変換 mm→m）。"""
    xc, yc, zc = grid_cell_centers(field_data)
    cx, cy, cz = (c / 1000.0 for c in center_mm); r = radius_mm / 1000.0
    # X-fastest: flat = x + nx*(y + ny*z)
    X, Y, Z = np.meshgrid(xc, yc, zc, indexing='ij')     # (nx,ny,nz)
    d2 = (X - cx) ** 2 + (Y - cy) ** 2 + (Z - cz) ** 2
    return (d2 <= r ** 2).transpose(2, 1, 0).ravel()     # → (nz,ny,nx) flat


def cell_volumes(field_data):
    """各セルの体積 dz*dy*dx（非一様グリッド用の重み）を X-fastest flat で返す。"""
    g = field_data.Grid
    def dax(a):
        a = np.asarray([float(v) for v in a], dtype=float); return np.diff(a)
    dx, dy, dz = dax(g.XAxis), dax(g.YAxis), dax(g.ZAxis)
    VX, VY, VZ = np.meshgrid(dx, dy, dz, indexing='ij')  # (nx,ny,nz)
    return (VX * VY * VZ).transpose(2, 1, 0).ravel()


def roi_stats(ti_flat, mask, vol):
    """ROI 内の体積重み平均・最大・ROI 体積(mL) を返す。"""
    v = vol[mask]; f = ti_flat[mask]
    return {"mean_weighted": float((f * v).sum() / v.sum()),
            "max": float(f.max()),
            "volume_mL": float(v.sum() * 1e6)}            # m^3 → mL


# ===== 実行例（本番・ペア1=2000Hz / ペア2=2010Hz を Run 済みの前提）=====
# ⚠️ 工程8（`run_simulation.py`）で Run した sim の**実際の名前**を下の NAME1 / NAME2 に入れること
#    （同名の sim が既にあると結果ファイルが衝突するので、名前を変えて作る場合がある）。
NAME1, NAME2 = 'tTIS_LF1', 'tTIS_LF2'

if __name__ == '__main__':
    arr1 = get_E(NAME1)                    # ペア1（T7–P7）
    arr2 = get_E(NAME2)                    # ペア2（Fp1–Fp2）※別シミュとして Run 済み
    ti = ti_envelope(arr1, arr2)

    # E 場データ本体（グリッド幾何の取得用）
    ef = document.AllSimulations[NAME1].Results()['Overall Field']['EM E(x,y,z,f0)']
    ef.Update(); fd = ef.Data

    roi = sphere_mask(fd, (99.1, 295.0, 1562.2), 10.0)    # 左島皮質 ROI（configs/parameters.py）
    vol = cell_volumes(fd)
    target = roi_stats(ti, roi, vol)
    nontarget = roi_stats(ti, ~roi, vol)
    selectivity = nontarget["mean_weighted"] / target["mean_weighted"]

    print('標的ROI:', target)
    print('選択性 (非標的平均/標的平均) = %.3f  ← Inoue 2025 の ≈0.40 と照合' % selectivity)
