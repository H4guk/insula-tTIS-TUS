"""T-2 音響材料 (ρ/c/α) の割り当てと Voxeler 登録（Sim4Life.lite Python コンソール）。

tTIS の assign_materials.py の音響版。Acoustic(LAPWE) シミュを作り、頭部59組織に
密度 ρ・音速 c・減衰 α を割り当て、Voxeler に 59組織＋Transducer を登録する。

★減衰の変換: DB の音響減衰は α(f)=α0·f^b（α0 は Np/m/MHz, f は MHz）。
  MaterialSettings.AttenuationCoefficient は「その周波数の Np/m 単一値」なので、
  f=0.25MHz で α = α0 · 0.25^b を計算して入れる。

★材料値はハードコードせず IT'IS 5.0 から実行時に読む（docs/acoustic-material-audit.md と同値）。
  期待値ハードコードは別DBを引く事故を隠すので使わない（tTIS #14 の音響版）。

★Voxeler 登録は tTIS と同じ鉄則: σ(ここでは ρ/c/α) を付けるだけでは焼かれない。
  Voxeler 設定に登録して初めてボクセル化される。Grid には登録しない（自動グリッド暴走回避）。

流れ:
  ① 対象組織59を確定（AutoAssignMaterials → 頭部グリッド内）＋ Transducer を取得
  ② 事前ゲート（組織数59・Transducer 実在・同名 sim 無し・材料が DB に全部ある）
  ③ Acoustic シミュ作成・Setup（f=0.25MHz・LAPWE・Periods=10）
  ④ 59組織に ρ/c/α を割り当て
  ⑤ Voxeler に 59組織＋Transducer を登録
  ⑥ 事後ゲート（材料59・DB値と直接照合・登録60）
"""
import s4l_v1.document as document
import s4l_v1.model as model
import s4l_v1.simulation.acoustic as acoustic
import s4l_v1.materials as materials
import XCoreModeling as xc
import numpy as np

SIM_NAME = 'TUS_250k'
FREQ_MHZ = 0.25                        # 250 kHz
PERIODS = 10
DB_NAME = "IT'IS 5.0"                   # 音響物性を持つ DB（4-1 で確定）

GX, GY, GZ = (4, 202), (162, 352), (1450, 1665)     # 頭部グリッド範囲（組織選択用・tTIS と同一）
TRANSDUCER = 'Transducer'
SKIP_EXACT = ('Model', 'Grid', 'Bones', 'GridBox_head', TRANSDUCER)

N_TISSUE = 59
N_TOTAL = N_TISSUE + 1                  # + Transducer（Voxeler 登録数）

# 物性の粗い妥当レンジ（個別値は DB と直接照合）
RHO_LO, RHO_HI = 800.0, 2400.0         # kg/m^3
C_LO, C_HI = 1300.0, 4700.0            # m/s
TOL = 0.02                             # sim 値と DB 由来値の許容相対差


def xyz(v):
    try:    return np.array([float(v[0]), float(v[1]), float(v[2])])
    except: return np.array([float(v.X), float(v.Y), float(v.Z)])


def in_grid(e):
    try:
        bb = xc.GetBoundingBox([e])
    except Exception:
        return False
    lo, hi = xyz(bb[0]), xyz(bb[1])
    return (lo[0] <= GX[1] and hi[0] >= GX[0] and
            lo[1] <= GY[1] and hi[1] >= GY[0] and
            lo[2] <= GZ[1] and hi[2] >= GZ[0])


def base(name):
    return name.split('  (')[0].strip()


def norm_name(s):
    return ''.join(ch for ch in str(s).lower() if ch.isalnum())


# ---- DB 読み出し（exact→normalized→alias） ----
db = materials.database[DB_NAME]
db_all = list(db.AllMaterials)


def resolve(nm):
    try:
        m = db[nm]
        if m is not None:
            return m
    except Exception:
        pass
    key = norm_name(nm)
    for m in db_all:
        if norm_name(m.Name) == key:
            return m
    for m in db_all:
        try:
            aliases = list(getattr(m, 'Aliases', None) or [])
        except Exception:
            aliases = []
        if any(norm_name(a) == key for a in aliases):
            return m
    return None


def prop(mat, key):
    for p in mat.AllProperties:
        nm = str(getattr(p, 'VariableName', None) or getattr(p, 'Description', None))
        if nm == key:
            try:    return float(p.Value)
            except Exception: return None
    return None


def acoustic_props(nm):
    """材料名 → (rho, c, alpha_np_m@250kHz)。DB から実行時に読む。"""
    m = resolve(nm)
    if m is None:
        return None
    rho = prop(m, 'mass_density')
    c = prop(m, 'sound_speed')
    a0 = prop(m, 'attenuation_alpha')      # Np/m/MHz
    b = prop(m, 'attenuation_b')           # 指数
    if None in (rho, c, a0, b):
        return None
    alpha = a0 * (FREQ_MHZ ** b)           # Np/m at 250kHz
    return rho, c, alpha


# ===== ① 対象の確定 =====
ents = list(model.AllEntities())
tr = [e for e in ents if e.Name == TRANSDUCER]
cands = [e for e in ents
         if e.Name not in SKIP_EXACT
         and 'Yoon' not in e.Name
         and type(e).__name__ != 'EntityGroup']
model.AutoAssignMaterials(cands)
head = [e for e in cands if getattr(e, 'MaterialName', None) and in_grid(e)]

# ===== ② 事前ゲート =====
print('[pre ] tissues=%d  transducer=%d  (expected %d + 1)' % (len(head), len(tr), N_TISSUE))
if len(tr) != 1:
    raise SystemExit('[pre ] FAILED — %r が %d 個（1個であること）' % (TRANSDUCER, len(tr)))
if len(head) != N_TISSUE:
    print('[pre ] ⚠ 組織数が %d（想定 %d）。名前一覧:' % (len(head), N_TISSUE))
    print('       ', sorted(base(e.Name) for e in head))
    raise SystemExit('[pre ] FAILED — 組織数が想定と違う')
# 既存の同名 sim は作り直しのため自動削除（再実行を idempotent にする）
for s in [s for s in document.AllSimulations if s.Name == SIM_NAME]:
    document.AllSimulations.Remove(s)
    print('[pre ] 既存の sim %r を削除して作り直す' % SIM_NAME)

want = sorted(set(e.MaterialName for e in head))
db_val, absent = {}, []
for nm in want:
    v = acoustic_props(nm)
    if v is None:
        absent.append(nm)
    else:
        db_val[nm] = v
print('[pre ] DB=%s  材料 %d/%d 解決' % (DB_NAME, len(db_val), len(want)))
if absent:
    raise SystemExit('[pre ] FAILED — %s に音響物性が無い材料: %s' % (DB_NAME, absent))

# ===== ③ シミュ作成・Setup =====
sim = acoustic.Simulation()
sim.Name = SIM_NAME
document.AllSimulations.Add(sim)
sim.SetupSettings.Frequency = FREQ_MHZ
sim.SetupSettings.Periods = PERIODS
print('[sim ] created %s  f=%s MHz  ModelType=%s  Periods=%s'
      % (sim.Name, sim.SetupSettings.Frequency, sim.SetupSettings.ModelType, sim.SetupSettings.Periods))

# ===== ④ 材料割り当て =====
created = {}
for e in head:
    rho, c, alpha = db_val[e.MaterialName]
    ms = sim.AddMaterialSettings(e)
    ms.Name = e.MaterialName
    ms.MassDensity = rho
    ms.SpeedOfSound = c
    ms.AttenuationCoefficient = alpha
    created[e.Name] = ms
sim.UpdateAllMaterials()
print('[mat ] material settings: %d' % len(created))

# ===== ⑤ Voxeler 登録（59組織 + Transducer）=====
vox = [s for s in sim.AllSettings if type(s).__name__ == 'AutomaticVoxelerSettings'][0]
targets = head + tr
for e in targets:
    sim.Add(vox, [e])
print('[reg ] registered to voxeler: %d (expected %d)' % (len(targets), N_TOTAL))

# ===== ⑥ 事後ゲート =====
fail = []
if len(created) != N_TISSUE:
    fail.append('material settings %d != %d' % (len(created), N_TISSUE))

exp_by_ent = dict((e.Name, db_val[e.MaterialName]) for e in head)
ng = []
for ent, ms in sorted(created.items()):
    exp = exp_by_ent.get(ent)
    try:
        act = (float(ms.MassDensity), float(ms.SpeedOfSound), float(ms.AttenuationCoefficient))
    except Exception:
        ng.append((ent, exp, None, 'sim 値が読めない')); continue
    if exp is None:
        ng.append((ent, exp, act, 'DB 値なし')); continue
    for i, lbl in enumerate(('rho', 'c', 'alpha')):
        if abs(act[i] - exp[i]) > max(1e-6, abs(exp[i]) * TOL):
            ng.append((ent, exp, act, '%s が DB 由来値と不一致' % lbl)); break
    else:
        # 空気（内部空洞）は ρ~1.16 / c~343 と組織レンジ外だが正当な媒質。
        # DB 値と一致していれば範囲チェックはスキップする。
        is_air = 'air' in ms.Name.lower()
        if not is_air and not (RHO_LO <= act[0] <= RHO_HI and C_LO <= act[1] <= C_HI):
            ng.append((ent, exp, act, '物性が非現実的レンジ'))
print('[post] material check NG: %d' % len(ng))
for ent, exp, act, why in ng[:20]:
    print('       %-26s exp=%s sim=%s  %s' % (ent, exp, act, why))
if ng:
    fail.append('materials')

names = set(e.Name for e in targets)
reg = [c for c in sim.AllComponents
       if base(c.Name) in names and 'Automatic Voxeler Settings' in c.Settings.keys()]
notreg = sorted(names - set(base(c.Name) for c in reg))
print('[post] voxeler registered %d/%d  not registered=%s' % (len(reg), N_TOTAL, notreg))
if len(reg) != N_TOTAL:
    fail.append('registration')

print('=== T-2 %s ===' % ('PASS' if not fail else 'FAILED: ' + ', '.join(fail)))
document.Save()
print('saved.')
