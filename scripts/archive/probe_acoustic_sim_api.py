"""T-1 前段: Acoustic シミュの設定 API を確定（Sim4Life.lite Python コンソール・非破壊）。

4-0 で Add系メソッド名は判明。ここでは各 Settings の**中身のフィールド名**を確定する:
  - SetupSettings: 周波数・LAPWE(ModelType)・Periods・Harmonics の実名と設定方法
  - MaterialSettings: 音響物性の入力欄（MassDensity/SoundSpeed/Attenuation/Nonlinearity…）
  - SourceSettings: 駆動（Excitation/Amplitude/Phase）
  - FieldSensorSettings / PointSensorSettings: 観測
これが分かれば assign_materials.py の音響版を推測なしで書ける。

一時 sim を作って調べ、最後に document から取り除く（保存しない）。
"""
import s4l_v1.document as document
import s4l_v1.model as model
import s4l_v1.simulation.acoustic as acoustic


def dump(obj, label, limit=60):
    attrs = [a for a in dir(obj) if not a.startswith('_')]
    print('[%s] attrs(%d): %s' % (label, len(attrs), attrs[:limit]))
    return attrs


def show_vals(obj, label, keys):
    for k in keys:
        try:
            v = getattr(obj, k)
        except Exception as ex:
            print('   %s.%s -> 取得不可 %r' % (label, k, ex))
            continue
        if callable(v):
            continue
        print('   %s.%s = %r' % (label, k, str(v)[:120]))


# ===== ① Simulation と SetupSettings =====
sim = acoustic.Simulation()
print('[sim ] created %s' % type(sim).__name__)

ss = sim.SetupSettings
dump(ss, 'setup')
# 周波数・モデル型・周期の実値
show_vals(ss, 'setup', ['Frequency', 'ModelType', 'Periods', 'Harmonics'])
# ModelType の許容 enum を掘る（LAPWE を指定する値を知りたい）
for pn in ('ModelTypeProp', 'ModelType'):
    p = getattr(ss, pn, None)
    if p is None:
        continue
    print('[setup] %s type=%s attrs=%s'
          % (pn, type(p).__name__, [a for a in dir(p) if not a.startswith('_')][:40]))
# モジュール直下に enum クラスが隠れていないか
enum_like = [a for a in dir(acoustic) if 'Enum' in a or 'Type' in a or 'Model' in a]
print('[setup] module enum 候補: %s' % enum_like)

# ===== ② MaterialSettings（音響物性の欄）=====
print('')
skin = [e for e in model.AllEntities() if e.Name == 'Skin']
if skin:
    ms = sim.AddMaterialSettings(skin[0])
    attrs = dump(ms, 'material')
    # 音響っぽい欄を総当りで表示
    ac_attrs = [a for a in attrs if any(h in a.lower()
                for h in ('density', 'sound', 'speed', 'atten', 'absorp',
                          'nonlinear', 'impedance', 'reflect', 'acoustic'))]
    print('[material] 音響欄候補: %s' % ac_attrs)
    show_vals(ms, 'material', ac_attrs)
    # AcousticProps のようなサブオブジェクトがあれば掘る
    for sub in ('AcousticProps', 'MaterialProps', 'Props'):
        o = getattr(ms, sub, None)
        if o is not None:
            print('[material] .%s attrs=%s'
                  % (sub, [a for a in dir(o) if not a.startswith('_')][:40]))
else:
    print('[material] Skin が無いので材料欄の調査は飛ばす')

# ===== ③ SourceSettings（駆動）=====
print('')
try:
    src = sim.AddSourceSettings()
except TypeError:
    # 面（Transducer）を引数に取る可能性
    tr = [e for e in model.AllEntities() if e.Name == 'Transducer']
    src = sim.AddSourceSettings(tr[0]) if tr else None
if src is not None:
    attrs = dump(src, 'source')
    sc = [a for a in attrs if any(h in a.lower()
          for h in ('excit', 'signal', 'ampl', 'phase', 'pressure', 'velocity',
                    'waveform', 'sinus', 'freq'))]
    print('[source] 駆動欄候補: %s' % sc)
    show_vals(src, 'source', sc)
else:
    print('[source] AddSourceSettings の引数形が不明（上のエラーを見て対応）')

# ===== ④ Sensor =====
print('')
for adder in ('AddFieldSensorSettings', 'AddPointSensorSettings'):
    fn = getattr(sim, adder, None)
    if fn is None:
        continue
    try:
        sn = fn()
        dump(sn, adder)
    except Exception as ex:
        print('[sensor] %s() -> %r' % (adder, ex))

# ===== ⑤ 後片付け（保存しない・document に足していないが念のため）=====
try:
    if sim in list(document.AllSimulations):
        document.AllSimulations.Remove(sim)
        print('')
        print('[clean] 一時 sim を document から除去')
except Exception as ex:
    print('[clean] 除去でエラー（無害・未保存なので影響なし）: %r' % ex)

print('')
print('=== Acoustic 設定 API 調査 完了（保存していない）===')
