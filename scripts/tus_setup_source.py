"""T-3 音源（Source）の設定と Transducer 割り当て（Sim4Life.lite Python コンソール）。

T-2（tus_assign_materials.py）で作った TUS_250k に対し、正弦波の音源を作り、
Transducer（お椀）をソース面に割り当てる。lec7 の Step7 の Python 版。

参照振幅 1 MPa で駆動する。LAPWE は線形なので、実 TUS の ISPPA/MI へのスケールは
場を出した後（4-6）に線形にかければよい（tTIS を 1V で回して電流スケールしたのと同じ）。

流れ:
  ① TUS_250k・Transducer を取得、既存 Source が無いことを確認
  ② SourceSettings 作成（Sinusoidal / 1 MPa / 0 deg）
  ③ Transducer をソースにバインド（sim.Add）
  ④ 事後ゲート（Transducer に Source 設定が付いた・振幅/型が正しい）＋境界/背景の既定を表示
"""
import s4l_v1.document as document
import s4l_v1.model as model

SIM_NAME = 'TUS_250k'
TRANSDUCER = 'Transducer'
AMPLITUDE_MPA = 1.0                    # 参照振幅（線形なので後スケール）
PHASE_DEG = 0.0


def base(name):
    return name.split('  (')[0].strip()


# ===== ① 取得と事前ゲート =====
sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個（T-2 を先に）' % (SIM_NAME, len(sims)))
sim = sims[0]

n_mat = sum(1 for s in sim.AllSettings if type(s).__name__ == 'MaterialSettings')
print('[pre ] sim=%s  materials=%d' % (sim.Name, n_mat))
if n_mat < 59:
    raise SystemExit('[pre ] FAILED — 材料が %d 件（T-2 未完）' % n_mat)

tr = [e for e in model.AllEntities() if e.Name == TRANSDUCER]
if len(tr) != 1:
    raise SystemExit('[pre ] FAILED — %r が %d 個' % (TRANSDUCER, len(tr)))
tr = tr[0]

existing = [s for s in sim.AllSettings if type(s).__name__ == 'SourceSettings']
if existing:
    for s in existing:
        sim.Remove(s) if hasattr(sim, 'Remove') else None
    print('[pre ] 既存 Source %d 件を除去して作り直す（%s）'
          % (len(existing), [s.Name for s in existing]))

# ===== ② Source 作成 =====
src = sim.AddSourceSettings()
src.Amplitude = AMPLITUDE_MPA
src.Phase = PHASE_DEG
try:
    print('[src ] Excitation=%s  Amplitude=%s  Phase=%s'
          % (src.ExcitationType, src.AmplitudeProp, src.PhaseProp))
except Exception:
    print('[src ] Amplitude=%s Phase=%s' % (src.Amplitude, src.Phase))

# ===== ③ Transducer をソースにバインド =====
sim.Add(src, [tr])
print('[bind] %s をソースにバインドした' % TRANSDUCER)

# ===== ④ 事後ゲート =====
fail = []
comp = [c for c in sim.AllComponents if base(c.Name) == TRANSDUCER]
if not comp:
    fail.append('Transducer コンポーネントが無い')
else:
    keys = sorted(comp[0].Settings.keys())
    print('[post] Transducer の設定キー: %s' % keys)
    has_src = any('Source' in k for k in keys)
    if not has_src:
        fail.append('Transducer に Source 設定が付いていない')
    # Voxeler 登録が生きているか（T-2 の登録が壊れていないこと）
    if not any('Voxeler' in k for k in keys):
        fail.append('Transducer の Voxeler 登録が消えた')

src_settings = [s for s in sim.AllSettings if type(s).__name__ == 'SourceSettings']
print('[post] SourceSettings 数: %d' % len(src_settings))
if len(src_settings) != 1:
    fail.append('SourceSettings が %d 件（1件であること）' % len(src_settings))
else:
    s = src_settings[0]
    if abs(float(s.Amplitude) - AMPLITUDE_MPA) > 1e-9:
        fail.append('振幅が %s（期待 %s）' % (s.Amplitude, AMPLITUDE_MPA))

# 参考: 境界と背景の既定（次の T-4/T-5 の判断材料）
try:
    gb = [s for s in sim.AllSettings if type(s).__name__ == 'GlobalBoundarySettings']
    for g in gb:
        attrs = [a for a in dir(g) if not a.startswith('_')]
        bt = [a for a in attrs if 'ound' in a.lower() or 'type' in a.lower()]
        print('[info] GlobalBoundary: %s' % [(a, str(getattr(g, a))[:40]) for a in bt if not callable(getattr(g, a))])
except Exception as ex:
    print('[info] 境界の取得エラー（無害）: %r' % ex)

print('=== T-3 %s ===' % ('PASS' if not fail else 'FAILED: ' + '; '.join(fail)))
document.Save()
print('saved.')
