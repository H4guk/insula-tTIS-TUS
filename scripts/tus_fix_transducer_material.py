"""T-2fix Transducer に音響材料を付けて再ボクセル化（Sim4Life.lite Python コンソール）。

Run が `[Point Source] + map::at` で失敗した原因＝Transducer が材料を持たずボクセル化されず、
Source が面にマップできなかった。lec7 では Transducer に既定材料が入っていた。

★ボクセル化後は設定追加がロックされる（incompatible with this type of simulation・tTIS 既知）。
  T-5a で既に焼いているので、まず ResetVoxels でボクセルを解除してから材料を足す。

流れ:
  ① TUS_250k・Transducer 取得
  ② ResetVoxels でボクセル解除（設定追加ロックを外す）
  ③ Transducer に MaterialSettings 付与（水相当）＋ UpdateAllMaterials
  ④ CreateVoxels 再実行 → BAKE_WAIT 待つ → Save
"""
import time
import s4l_v1.document as document
import s4l_v1.model as model

SIM_NAME = 'TUS_250k'
TRANSDUCER = 'Transducer'
BAKE_WAIT = 200
RHO, C, ATTEN = 1000.0, 1500.0, 0.0


def base(name):
    return name.split('  (')[0].strip()


sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

tr = [e for e in model.AllEntities() if e.Name == TRANSDUCER]
if len(tr) != 1:
    raise SystemExit('[pre ] FAILED — %r が %d 個' % (TRANSDUCER, len(tr)))
tr = tr[0]

comp = [c for c in sim.AllComponents if base(c.Name) == TRANSDUCER]
print('[pre ] Transducer keys: %s' % (sorted(comp[0].Settings.keys()) if comp else []))

# ② ボクセル解除（設定追加ロックを外す）
try:
    sim.ResetVoxels()
    print('[rst ] ResetVoxels 実行（ボクセル解除）')
except Exception as ex:
    print('[rst ] ResetVoxels ERR:', ex)

# ③ Transducer に材料付与
already = [s for s in sim.AllSettings if type(s).__name__ == 'MaterialSettings'
           and 'transducer' in s.Name.lower()]
if already:
    ms = already[0]
    print('[mat ] 既存の Transducer 材料を再利用:', ms.Name)
else:
    ms = sim.AddMaterialSettings(tr)
    ms.Name = 'Transducer_mat'
    print('[mat ] Transducer に MaterialSettings を新規付与')
ms.MassDensity = RHO
ms.SpeedOfSound = C
ms.AttenuationCoefficient = ATTEN
sim.UpdateAllMaterials()
print('[mat ] rho=%s c=%s atten=%s' % (RHO, C, ATTEN))

# Voxeler 登録が生きているか（消えていたら付け直す）
comp = [c for c in sim.AllComponents if base(c.Name) == TRANSDUCER]
keys = sorted(comp[0].Settings.keys()) if comp else []
print('[chk ] Transducer keys after: %s' % keys)
if not any('Voxeler' in k for k in keys):
    vox = [s for s in sim.AllSettings if type(s).__name__ == 'AutomaticVoxelerSettings'][0]
    sim.Add(vox, [tr])
    print('[chk ] Voxeler 登録を付け直した')

# ④ 再ボクセル化（焼成のみ・判定は T-5b）
t0 = time.time()
sim.CreateVoxels()
print('[vox ] CreateVoxels returned（非同期）')
time.sleep(BAKE_WAIT)
document.Save()
print('[vox ] baked+saved in %.0f s' % (time.time() - t0))
print('=== T-2fix 完了（Transducer 材料付与＋再焼成）===')
print('    次: T-5b で Transducer が baked か確認 → T-6a 再Run')
