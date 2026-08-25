"""Phase 4-1 音響物性(ρ/c/減衰)が IT'IS DB に揃っているか確認（Sim4Life.lite Python コンソール・読み取りのみ）。

tTIS の σ 対応表（docs/material-audit.md）の音響版を作る前段。
Yoon-sun の各材料が DB に音響物性を持つか、正式な property 名は何か、どの DB か、
特に頭蓋（Bone/Skull）に値があるかを1回の読み取りで洗い出す。

流れ:
  ① 使える材料 DB を列挙
  ② 材料名の一覧を tTIS_LF1 の MaterialSettings から取る（無ければ監査表の固定リスト）
  ③ 代表材料で AllProperties を全ダンプ → 音響 property の正式名を特定
  ④ 音響物性を持つ DB を選び、全材料で ρ/c/α の有無を集計（欠落・頭蓋を明示）

書き込みなし（sim を作らない・document.Save() も呼ばない）。
出典: assign_materials.py の DB 解決ロジック（exact→normalized→alias）を流用。
"""
import s4l_v1.document as document
import s4l_v1.materials as materials

SIM_NAME = 'tTIS_LF1'   # 材料名の一覧をここから取る（59 組織設定・electrode は材料なし）

# tTIS_LF1 が無い場合の固定リスト（docs/material-audit.md の 42 材料。Air は除く）
FALLBACK_MATERIALS = [
    'Blood', 'Bone (Cancellous)', 'Bone (Cortical)', 'Brain (Grey Matter)',
    'Brain (White Matter)', 'Cartilage', 'Cerebellum', 'Cerebrospinal Fluid',
    'Commissura Anterior', 'Commissura Posterior', 'Dura', 'Esophagus',
    'Eye (Cornea)', 'Eye (Lens)', 'Eye (Sclera)', 'Eye (Vitreous Humor)', 'Fat',
    'Hippocampus', 'Hypophysis', 'Hypothalamus', 'Intervertebral Disc', 'Larynx',
    'Lymphnode', 'Medulla Oblongata', 'Midbrain', 'Mucous Membrane', 'Muscle',
    'Nerve', 'Pineal Body', 'Pons', 'SAT (Subcutaneous Fat)', 'Salivary Gland',
    'Skin', 'Skull (Cancellous)', 'Skull (Cortical)', 'Spinal Cord',
    'Tendon\\Ligament', 'Thalamus', 'Tongue', 'Tooth', 'Trachea',
]

# 音響 property の VariableName 候補（正式名が不明なので緩く拾う）。③で実名を確定する。
AC_HINT = ('densit', 'sound', 'acoust', 'attenu', 'absorp', 'nonlinear', 'b_over_a')


def norm_name(s):
    return ''.join(ch for ch in str(s).lower() if ch.isalnum())


def _fmt(v):
    """数値は 6 桁に丸めて表示、None は '-'。"""
    if v is None:
        return '-'
    try:
        return '%.6g' % float(v)
    except Exception:
        return str(v)


def all_props(mat):
    """(VariableName, Value, Unit) の一覧を返す。"""
    out = []
    for p in mat.AllProperties:
        nm = str(getattr(p, 'VariableName', None) or getattr(p, 'Description', None))
        try:
            val = p.Value
        except Exception:
            val = None
        unit = getattr(p, 'Unit', None)
        out.append((nm, val, unit))
    return out


# ===== ① 材料 DB を列挙 =====
dbc = materials.database
dbs = []
try:
    for d in dbc:
        dbs.append(d)
except Exception:
    pass
if not dbs:
    for nm in ("IT'IS 5.0", "IT'IS LF 5.0", "IT'IS 4.1", "IT'IS 4.0", "IT'IS 3.0"):
        try:
            d = dbc[nm]
            if d is not None:
                dbs.append(d)
        except Exception:
            pass
print('[db  ] 利用可能な DB: %s' % [getattr(d, 'Name', '?') for d in dbs])
if not dbs:
    raise SystemExit('[db  ] FAILED — 材料 DB が1つも取れない')


def resolve(db, nm):
    """材料名を DB の材料オブジェクトに解決（exact→normalized→alias）。"""
    try:
        m = db[nm]
        if m is not None:
            return m, 'exact'
    except Exception:
        pass
    try:
        allm = list(db.AllMaterials)
    except Exception:
        return None, None
    key = norm_name(nm)
    for m in allm:
        if norm_name(m.Name) == key:
            return m, 'normalized'
    for m in allm:
        try:
            aliases = list(getattr(m, 'Aliases', None) or [])
        except Exception:
            aliases = []
        if any(norm_name(a) == key for a in aliases):
            return m, 'alias'
    return None, None


# ===== ② 材料名の一覧 =====
sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if sims:
    want = sorted(set(s.Name for s in sims[0].AllSettings
                      if type(s).__name__ == 'MaterialSettings' and norm_name(s.Name) != 'air'))
    print('[mat ] 材料名は %s の MaterialSettings から取得: %d 件' % (SIM_NAME, len(want)))
else:
    want = FALLBACK_MATERIALS
    print('[mat ] %s が無いので固定リストを使用: %d 件' % (SIM_NAME, len(want)))

# ===== ③ 代表材料で全 property をダンプし音響 property の実名を特定 =====
REP = ['Bone (Cortical)', 'Brain (Grey Matter)', 'Water', 'Skin']
print('')
print('[dump] 代表材料の全 property（音響っぽい名前を ★ で強調）:')
ac_keys = set()
for db in dbs:
    for repn in REP:
        m, how = resolve(db, repn)
        if m is None:
            continue
        props = all_props(m)
        acoustic = [(nm, v, u) for (nm, v, u) in props
                    if any(h in nm.lower() for h in AC_HINT)]
        if not acoustic:
            continue
        print('  --- DB=%s  material=%s (%s) ---' % (getattr(db, 'Name', '?'), m.Name, how))
        for nm, v, u in acoustic:
            print('    ★ %-34s = %-16s %s' % (nm, v, u))
            ac_keys.add(nm)
        break   # この DB は1材料ダンプできれば十分
print('')
print('[dump] 拾えた音響 property 名: %s' % sorted(ac_keys))

# 音響 property は **名前で明示的に読む**（推測 pick はやめた・2026-08-20）。
# IT'IS の減衰モデルは α(f)=alpha·f^b（alpha は Np/m/MHz, f は MHz）なので、
# 減衰は alpha と指数 b の2つを別々に持つ。B/A は非線形（4.2/5.0 系のみ）。
DENS = 'mass_density'          # ρ [kg/m^3]
SPEED = 'sound_speed'          # c [m/s]
ALPHA = 'attenuation_alpha'    # α0 [Np/m/MHz]  ← これが実際の減衰係数
BEXP = 'attenuation_b'         # b  [-]          べき乗則の指数
BA = 'nonlinearity_ba'         # B/A [-]
print('[dump] 音響prop（明示）: 密度=%r 音速=%r 減衰α0=%r 指数b=%r 非線形BA=%r'
      % (DENS, SPEED, ALPHA, BEXP, BA))

# ===== ④ DB を選び、全材料で 5 物性を読む =====
# 音響値は全 DB でほぼ同一。最新かつ非線形 B/A を持つ IT'IS 5.0 を採用（無ければ音響 prop 最多の DB）。
PREFERRED_DB = "IT'IS 5.0"


def ac_count(db):
    m, _ = resolve(db, 'Brain (Grey Matter)')
    if m is None:
        m, _ = resolve(db, 'Bone (Cortical)')
    if m is None:
        return 0
    return sum(1 for (nm, _, _) in all_props(m) if any(h in nm.lower() for h in AC_HINT))


best = None
for d in dbs:
    if getattr(d, 'Name', None) == PREFERRED_DB:
        best = d
        break
if best is None:
    best = max(dbs, key=ac_count)
print('')
print('[cov ] 採用 DB = %s' % getattr(best, 'Name', '?'))


def prop_val(mat, key):
    for p in mat.AllProperties:
        nm = str(getattr(p, 'VariableName', None) or getattr(p, 'Description', None))
        if nm == key:
            try:
                return float(p.Value)
            except Exception:
                return p.Value
    return None


print('')
hdr = '%-24s %-8s %-10s %-10s %-12s %-6s %-6s' % (
    'material', 'resolve', 'rho', 'c', 'alpha0', 'b', 'BA')
print(hdr)
miss = {'rho': [], 'c': [], 'alpha': []}
unresolved = []
BONE_HINT = ('bone', 'skull', 'tooth', 'hyoid', 'mandible', 'cortical', 'cancellous')
bone_rows, csv_rows = [], []
for nm in want:
    m, how = resolve(best, nm)
    if m is None:
        unresolved.append(nm)
        print('%-24s %-8s %s' % (nm, 'NONE', '(DB に無い)'))
        continue
    rho = prop_val(m, DENS)
    c = prop_val(m, SPEED)
    a0 = prop_val(m, ALPHA)
    b = prop_val(m, BEXP)
    ba = prop_val(m, BA)
    if rho is None:
        miss['rho'].append(nm)
    if c is None:
        miss['c'].append(nm)
    if a0 is None:
        miss['alpha'].append(nm)
    print('%-24s %-8s %-10s %-10s %-12s %-6s %-6s'
          % (nm, how, _fmt(rho), _fmt(c), _fmt(a0), _fmt(b), _fmt(ba)))
    csv_rows.append((nm, m.Name, rho, c, a0, b, ba))
    if any(h in nm.lower() for h in BONE_HINT):
        bone_rows.append((nm, rho, c, a0, b))

print('')
print('[cov ] 材料 %d 件中: rho欠落=%d c欠落=%d alpha0欠落=%d DB未解決=%d'
      % (len(want), len(miss['rho']), len(miss['c']), len(miss['alpha']), len(unresolved)))
for k, v in miss.items():
    if v:
        print('       %s 欠落: %s' % (k, v))
if unresolved:
    print('       DB 未解決: %s' % unresolved)

print('')
print('[bone] 頭蓋・骨・歯の音響物性（CT 無し一様骨近似の対象）:')
for nm, rho, c, a0, b in bone_rows:
    print('       %-22s rho=%-8s c=%-10s alpha0=%-10s b=%s'
          % (nm, _fmt(rho), _fmt(c), _fmt(a0), _fmt(b)))

# 監査ノート用の CSV ブロック（そのまま docs/acoustic-material-audit.md に貼れる）
print('')
print('[csv ] ---- ここから docs 用（material,db_name,rho,c,alpha0,b,BA）----')
for r in csv_rows:
    print('%s,%s,%s,%s,%s,%s,%s'
          % (r[0], r[1], _fmt(r[2]), _fmt(r[3]), _fmt(r[4]), _fmt(r[5]), _fmt(r[6])))
print('[csv ] ---- ここまで ----')

fail = len(unresolved) > 0 or len(miss['rho']) or len(miss['c']) or len(miss['alpha'])
print('')
if not fail:
    print('=== 工程4-1(調査) PASS: DB=%s / ρ・c・α0(Np/m/MHz)・b・B/A を全 %d 材料で取得 ==='
          % (getattr(best, 'Name', '?'), len(want)))
else:
    print('=== 工程4-1(調査) 要対応: 欠落あり（上の一覧を見る）===')
