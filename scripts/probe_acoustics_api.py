"""Phase 4-0 音響ソルバーが Python から組めるか確認（Sim4Life.lite Python コンソール・読み取りのみ）。

lec7 の TUS は全て GUI で組んだ。本番の tTIS 工程5〜9 は `s4l_v1.simulation.emlf` の Python。
音響側に同型の Python API（材料 ρ/c/減衰・Source・Sensor・Simulation 生成）があるか、
最小の introspection で確かめる。ここが通らないと 4-1 以降が全て GUI 手作業になる。

判定:
  PASS = 音響シミュレーションモジュールが import でき、`*Simulation` クラスがあり、
         材料/Source/Sensor を足す Add系メソッドが見つかる
  FAIL = モジュールが無い（Lite で音響ソルバーが Python 非公開の疑い）
         or Simulation は作れるが Add系メソッドが見当たらない（正しい名前を dir() から拾う）

書き込みなし（Simulation を document に足さない・document.Save() も呼ばない）。
"""
import importlib
import inspect

# ===== ① 音響シミュレーションモジュールの候補を順に import =====
# emlf と同じ階層 s4l_v1.simulation.* に音響ソルバーがあるはず。名前が不明なので候補を総当りする。
CANDIDATES = (
    's4l_v1.simulation.acoustics',
    's4l_v1.simulation.pacoustics',
    's4l_v1.simulation.acoustic',
    's4l_v1.simulation.fullwave',
    's4l_v1.simulation.ultrasound',
)

mod, mod_name = None, None
for name in CANDIDATES:
    try:
        mod = importlib.import_module(name)
        mod_name = name
        print('[imp ] OK   %s' % name)
        break
    except Exception as ex:
        print('[imp ] miss %-32s %r' % (name, ex))

# 候補が全滅なら s4l_v1.simulation 直下に何があるかを列挙して手掛かりにする
if mod is None:
    print('')
    print('[imp ] 候補が全滅。s4l_v1.simulation 直下のサブモジュール/属性を列挙する:')
    try:
        import s4l_v1.simulation as sim_pkg
        print('       %s' % [a for a in dir(sim_pkg) if not a.startswith('_')])
        import pkgutil, os
        pkg_dir = os.path.dirname(sim_pkg.__file__)
        subs = [m.name for m in pkgutil.iter_modules([pkg_dir])]
        print('       submodules on disk: %s' % subs)
    except Exception as ex:
        print('       s4l_v1.simulation も読めない: %r' % ex)
    print('')
    print('=== 工程4-0 FAILED: 音響モジュールが見つからない（上の列挙から正しい名前を拾う）===')
    raise SystemExit(1)

# ===== ② モジュール内のクラスを列挙し、Simulation クラスを探す =====
names = [a for a in dir(mod) if not a.startswith('_')]
print('')
print('[mod ] %s の公開名 (%d): %s' % (mod_name, len(names), names))

sim_classes = [a for a in names if a.endswith('Simulation')]
print('[mod ] Simulation 候補: %s' % sim_classes)

setting_classes = [a for a in names
                   if a.endswith('Settings') or 'Source' in a or 'Sensor' in a or 'Material' in a]
print('[mod ] 材料/Source/Sensor/Settings 候補: %s' % setting_classes)

# ===== ③ Simulation を1つ作ってみて Add系メソッドを見る（document には足さない）=====
if not sim_classes:
    print('')
    print('=== 工程4-0 FAILED: %s に *Simulation クラスが無い ===' % mod_name)
    raise SystemExit(1)

cls_name = sim_classes[0]
cls = getattr(mod, cls_name)
print('')
print('[sim ] 試作: %s()' % cls_name)
try:
    sim = cls()
    print('[sim ] インスタンス化 OK')
except Exception as ex:
    print('[sim ] インスタンス化できない: %r' % ex)
    print('')
    print('[sim ] クラス %s のシグネチャ/メンバだけ表示する:' % cls_name)
    try:
        print('       __init__ %s' % inspect.signature(cls.__init__))
    except Exception:
        pass
    print('       members=%s' % [a for a in dir(cls) if not a.startswith('_')])
    print('')
    print('=== 工程4-0 PARTIAL: クラスはあるが引数が要る。上の members から Add系を確認 ===')
    raise SystemExit(0)

members = [a for a in dir(sim) if not a.startswith('_')]
add_methods = [a for a in members if a.startswith('Add')]
create_methods = [a for a in members if a.startswith('Create') or a.startswith('New')]
print('[sim ] Add系メソッド:    %s' % add_methods)
print('[sim ] Create/New 系:    %s' % create_methods)

# 材料・Source・Sensor に対応する Add* があるか（名前で緩く判定）
def has(kw):
    return [a for a in add_methods if kw in a.lower()]

mat_add = has('material')
src_add = has('source') or has('transducer') or has('driving') or has('excitation')
sns_add = has('sensor') or has('detector')
grid_add = [a for a in members if 'Grid' in a or 'Voxel' in a]
print('')
print('[chk ] 材料Add : %s' % mat_add)
print('[chk ] SourceAdd: %s' % src_add)
print('[chk ] SensorAdd: %s' % sns_add)
print('[chk ] Grid/Voxeler 関連: %s' % grid_add)

# SetupSettings（周波数など全体設定）も見ておく
try:
    ss = sim.SetupSettings
    print('[chk ] SetupSettings attrs: %s'
          % [a for a in dir(ss) if not a.startswith('_')][:40])
except Exception as ex:
    print('[chk ] SetupSettings 取得不可: %r' % ex)

ok = bool(mat_add) and bool(src_add) and bool(sns_add)
print('')
if ok:
    print('=== 工程4-0 PASS: %s で材料/Source/Sensor を Python から追加できる ===' % mod_name)
else:
    missing = []
    if not mat_add:
        missing.append('材料Add')
    if not src_add:
        missing.append('SourceAdd')
    if not sns_add:
        missing.append('SensorAdd')
    print('=== 工程4-0 PARTIAL: %s は import 可・Simulation 化 OK だが %s が緩い名前判定で拾えない '
          '（上の Add系一覧から実名を確認）===' % (mod_name, '/'.join(missing)))
