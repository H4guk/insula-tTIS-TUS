"""#10 / #11 追加切り分け — sim の材料σがどの DB 由来かを特定する（読み取り専用）。

2026-08-09 の監査で、**IT'IS LF 5.0 と指定して読んだ格納値が sim の値と一致しない**ことが分かった。

    Muscle                DB 0.4610  vs  sim 0.3295   (1.40x)
    Brain (White Matter)  DB 0.3480  vs  sim 0.0640   (5.44x)

対照が外れているので、同じ経路で読んだ Skin の 0.1483 も「sim に入る値」とは断定できない。
説明の候補は2つあり、**予測が食い違うので1回で判別できる**:

  (A) sim は別の DB（IT'IS 5.0）から引いている
      `assign_materials.py` は `LinkMaterialWithDatabase(ms, e.MaterialName)` と**名前文字列**を渡す。
      2026-07-29 に「名前文字列だけ渡すと既定の IT'IS 5.0 を引く」と記録した罠と同じ形。
      → この説なら **IT'IS 5.0 の格納値が sim と一致する**。

  (B) DB の格納値は基準周波数の値で、sim は 2000 Hz で分散モデルから評価している
      `Material` に A0/A1/C0/C1/E0/F1/alpha/tau（Cole-Cole）と gabriel_parameters=4.0 がある。
      → この説なら **どちらの DB の格納値も sim と一致しない**。

読み取りのみ。`document.Save()` も呼ばない。
"""
import s4l_v1.document as document

SIM_NAME = 'tTIS_LF1'

# 上書きしていない材料だけを対照に使う（Skin は 0.465 に上書き済みなので参考表示）
TARGETS = ('Muscle', 'Brain (White Matter)', 'Brain (Grey Matter)',
           'Cerebrospinal Fluid', 'Bone (Cortical)', 'Skin')

KNOWN_DB = ("IT'IS LF 5.0", "IT'IS 5.0", "IT'IS 4.0", "IT'IS 3.0")


def base(name):
    return name.split('  (')[0].strip()


def sigma_from_props(mat):
    """AllProperties から electric_conductivity を引く（`mat.electric_conductivity` は descriptor で読めない）。"""
    for p in mat.AllProperties:
        nm = str(getattr(p, 'VariableName', None) or getattr(p, 'Description', None))
        if nm == 'electric_conductivity':
            return getattr(p, 'Value', None)
    return None


# ===== ① sim 側の実値（sim が無ければ DB 側の調査だけ行う）=====
# ★sim が無くても DB は読めるので**止めない**。工程5 がゲートで中断した直後は sim が存在しない。
sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
sim = sims[0] if len(sims) == 1 else None
sim_sigma = {}
if sim is None:
    print('[pre ] sim %r は %d 個 → sim 側の比較は飛ばし、DB の調査だけ行う'
          % (SIM_NAME, len(sims)))
else:
    print('[pre ] sim=%s  frequency=%s Hz' % (SIM_NAME, sim.SetupSettings.Frequency))
    for s in sim.AllSettings:
        if type(s).__name__ != 'MaterialSettings':
            continue
        try:
            sim_sigma.setdefault(s.Name, float(s.ElectricProps.Conductivity))
        except Exception:
            pass
    print('[sim ] material settings: %d' % len(sim_sigma))

# ===== ② DB の列挙 =====
import s4l_v1.materials as materials
dbc = materials.database
print('[db  ] container type=%s' % type(dbc).__name__)
print('[db  ] container attrs=%s' % [a for a in dir(dbc) if not a.startswith('_')])

dbs = []
try:
    for d in dbc:                     # イテレーション可能なら名前を集める
        dbs.append(d)
    print('[db  ] iterated: %s' % [getattr(d, 'Name', '?') for d in dbs])
except Exception as ex:
    print('[db  ] イテレーション不可: %r' % (ex,))

if not dbs:                           # 既知名で引く
    for nm in KNOWN_DB:
        try:
            dbs.append(dbc[nm])
        except Exception as ex:
            print('[db  ] %-16s 取得できず: %r' % (nm, ex))

print('[db  ] 対象 DB: %s' % [getattr(d, 'Name', '?') for d in dbs])

# ===== ③ DB ごとの格納値 vs sim =====
print('')
print('%-24s %-14s %s' % ('material', 'sim', '  '.join('%-22s' % getattr(d, 'Name', '?') for d in dbs)))
for nm in TARGETS:
    cells = []
    for d in dbs:
        try:
            cells.append('%-22s' % sigma_from_props(d[nm]))
        except Exception:
            cells.append('%-22s' % '(無し)')
    print('%-24s %-14s %s'
          % (nm, sim_sigma.get(nm, '(sim に無し)'), '  '.join(cells)))

# ===== ④ sim 側の MaterialSettings が持つリンク情報 =====
print('')
print('[link] MaterialSettings のリンク情報:')
probe = [] if sim is None else [s for s in sim.AllSettings
                                if type(s).__name__ == 'MaterialSettings' and s.Name == 'Muscle']
if sim is None:
    print('       sim が無いので飛ばす')
elif probe:
    ms = probe[0]
    print('       attrs=%s' % [a for a in dir(ms) if not a.startswith('_')])
    for a in [a for a in dir(ms) if not a.startswith('_')]:
        low = a.lower()
        if 'database' not in low and 'material' not in low and 'id' != low:
            continue
        try:
            v = getattr(ms, a)
        except Exception as ex:
            print('       %-28s 取得できず: %r' % (a, ex))
            continue
        if callable(v):
            continue
        print('       %-28s = %s' % (a, repr(v)[:160]))
else:
    print('       Muscle の MaterialSettings が見つからない')


# ===== ⑤ LF DB に見つからない材料の候補を、**別名も含めて**洗い出す（2026-08-11 追加）=====
# `assign_materials.py` の事前ゲートで 'Skull Cancellous' / 'Skull Cortical' が
# 「LF 5.0 に無い」と出た。ただし 2026-08-09 の監査ではこの2つが
# 'Skull (Cancellous)' / 'Skull (Cortical)' と括弧つきで表示されていた＝
# `LinkMaterialWithDatabase` は別名を辿って解決するが `db['名前']` は完全一致しか見ない、
# という差の可能性が高い。DB 側の Aliases を実際に見て確かめる。
LF_DB = "IT'IS LF 5.0"
MISSING = ('Skull Cancellous', 'Skull Cortical')


def norm(s):
    return ''.join(ch for ch in str(s).lower() if ch.isalnum())


print('')
print('[find] %s の中で骨・頭蓋に関係する材料を別名ごと列挙する' % LF_DB)
lf = materials.database[LF_DB]
try:
    mats = list(lf.AllMaterials)
except Exception as ex:
    mats = []
    print('       AllMaterials を取れない: %r' % (ex,))
print('       材料数: %d' % len(mats))

for miss in MISSING:
    key = norm(miss)
    toks = [t for t in str(miss).lower().split() if t]
    print('  --- %r の候補 ---' % miss)
    found = 0
    for m in mats:
        try:
            aliases = list(getattr(m, 'Aliases', None) or [])
        except Exception:
            aliases = []
        names = [m.Name] + aliases
        nn = [norm(n) for n in names]
        exact = key in nn
        partial = any(all(t in n for t in toks) for n in nn)
        loose = any(toks[0] in n for n in nn)          # 'skull' を含むもの
        if not (exact or partial or loose):
            continue
        found += 1
        tag = 'EXACT' if exact else ('PARTIAL' if partial else 'LOOSE')
        print('    [%-7s] %-28s sigma=%s' % (tag, m.Name, sigma_from_props(m)))
        print('              aliases=%s' % (aliases[:14],))
    if not found:
        print('    候補なし')

print('  --- 参考: 名前に bone を含む材料 ---')
for m in mats:
    if 'bone' in norm(m.Name):
        try:
            aliases = list(getattr(m, 'Aliases', None) or [])
        except Exception:
            aliases = []
        print('    %-28s sigma=%s' % (m.Name, sigma_from_props(m)))
        print('              aliases=%s' % (aliases[:14],))

print('')
print('=== 切り分け完了（読み取りのみ・保存していない）===')
