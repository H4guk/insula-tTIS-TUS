"""T-4 前段: 音響シミュの境界設定を確認（Sim4Life.lite Python コンソール・読み取り）。

LAPWE（時間発展の波動）ではグリッド端で反射させない吸収境界（ABC/PML）が要る。
TUS_250k の GlobalBoundarySettings の欄・境界タイプの選択肢・既定値・背景材を洗い出す。
書き込みなし（Save しない）。
"""
import s4l_v1.document as document
import s4l_v1.simulation.acoustic as acoustic

SIM_NAME = 'TUS_250k'


def dump(obj, label):
    attrs = [a for a in dir(obj) if not a.startswith('_')]
    print('[%s] attrs: %s' % (label, attrs))
    return attrs


def show_enum(prop, label):
    """EnumerationValue から選べる値を列挙する。"""
    for how in ('StaticEnums', 'enum'):
        try:
            e = getattr(prop, how)
            vals = list(e) if not callable(e) else None
            if vals:
                print('   %s.%s = %s' % (label, how, [str(v) for v in vals]))
        except Exception as ex:
            print('   %s.%s -> %r' % (label, how, ex))


sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

# ===== ① sim 内の GlobalBoundarySettings =====
gbs = [s for s in sim.AllSettings if type(s).__name__ == 'GlobalBoundarySettings']
print('[bound] GlobalBoundarySettings 数: %d' % len(gbs))
for g in gbs:
    attrs = dump(g, 'gbound')
    for a in attrs:
        if a.endswith('Prop') or callable(getattr(g, a, None)):
            continue
        try:
            print('   %s = %r' % (a, str(getattr(g, a))[:100]))
        except Exception as ex:
            print('   %s -> %r' % (a, ex))
    # 境界タイプらしき Prop の選択肢を列挙
    for a in attrs:
        if a.endswith('Prop') and ('ound' in a.lower() or 'type' in a.lower() or 'abc' in a.lower()
                                    or 'pml' in a.lower() or 'condition' in a.lower()):
            print('[bound] %s の選択肢:' % a)
            show_enum(getattr(g, a), a)

# ===== ② クラス定義側（インスタンスに無い項目の保険）=====
print('')
for cls in ('GlobalBoundarySettings', 'BoundarySettings'):
    c = getattr(acoustic, cls, None)
    if c is not None:
        print('[class] %s: %s' % (cls, [a for a in dir(c) if not a.startswith('_')]))

# ===== ③ 背景材（Water）の確認 =====
print('')
mats = [s for s in sim.AllSettings if type(s).__name__ == 'MaterialSettings']
bg = [s for s in mats if 'water' in s.Name.lower() or 'background' in s.Name.lower()]
print('[bg   ] 背景材候補: %s' % [s.Name for s in bg])
for s in bg:
    try:
        print('   %s: rho=%s c=%s atten=%s' % (s.Name, s.MassDensity, s.SpeedOfSound, s.AttenuationCoefficient))
    except Exception as ex:
        print('   %s: 読めない %r' % (s.Name, ex))

print('')
print('=== 境界 API 調査 完了（保存していない）===')
