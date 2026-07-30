"""VOXTEST: ViP のソリッド（Skin 1個）が Python 経由で voxel 化できるかだけを確かめる最小診断。

なぜこれを見るのか:
  面BC で Run 拒否は解消したが結果は全点NaN。`Voxeler.log` の
  `Voxel Scene Memory Consumption: 0.001196 kB` ＝ **ボクセルシーンがほぼ空**で、
  σを付けた59組織すら1つも焼かれていない。だから `0 unknowns / no lossy dielectrics` → NaN。
  電極の `not being considered` はその結果に過ぎない。
  ＝ 本丸は「そもそも voxel 化できているのか」。組織1個まで削って確定させる。

判定:
  Skin の Voxel Scene が **MB 級（非空）** → ViP は Python で焼ける。犯人は本番simの構成側（電極/BC/グリッド）
  Skin でも **0.001 kB（空）**      → ViP が API 経由で焼けない。最小再現ケースとしてサポート照会に使える

使い方: Sim4Life.lite の Python コンソールに丸ごと貼って Shift+Enter。
        本番 sim（tTIS_LF1*）には触らない。グリッドを 10mm にしてあるので速い。
"""
import glob
import os

import s4l_v1
import s4l_v1.document as doc
import s4l_v1.model as model
import s4l_v1.simulation.emlf as emlf
import s4l_v1.materials.database

db_lf = s4l_v1.materials.database["IT'IS LF 5.0"]

# 既存 VOXTEST を掃除（作り直しで同名が増えないように）
for s in list(doc.AllSimulations):
    if s.Name == 'VOXTEST':
        for attempt in (lambda: doc.AllSimulations.Remove(s), lambda: s.Delete()):
            try:
                attempt(); break
            except Exception:
                pass

# 電極なし・組織1個(Skin)だけの最小 sim
sim2 = emlf.ElectroQsOhmicSimulation(); sim2.Name = 'VOXTEST'
doc.AllSimulations.Add(sim2)
sim2.SetupSettings.Frequency = 2000.0

skin = [e for e in model.AllEntities() if e.Name == 'Skin'][0]
ms = sim2.AddMaterialSettings(skin); ms.Name = 'Skin'
sim2.LinkMaterialWithDatabase(ms, db_lf['Skin'])
sim2.UpdateAllMaterials()
print('Skin σ =', ms.ElectricProps.Conductivity)

# 粗いグリッドで速く（焼けるか"だけ"見る）
ggs = sim2.GlobalGridSettings
p = ggs.DiscretizationModeProp
p.set(p.findValue('Manual'))
ggs.MaxStep = [10.0, 10.0, 10.0]
sim2.UpdateGrid()
sim2.CreateVoxels()
print('VOXTEST CreateVoxels 完了')

# voxeler ログの最新を読む（結果ディレクトリは GetOutputFileName から取れる）
d = os.path.dirname(sim2.GetOutputFileName())
logs = glob.glob(os.path.join(d, '*_Voxeler.log'))
newest = max(logs, key=os.path.getmtime) if logs else None
print('log:', os.path.basename(newest) if newest else None)
if newest:
    with open(newest, 'r', errors='replace') as fh:
        for ln in fh.readlines()[-12:]:
            print('  ' + ln.rstrip())
