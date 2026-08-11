"""Phase 2 事前監査 — ViP 組織名 → DB 材料名 → σ の対応表を出す（読み取り専用）。

対応 Issue: #11（対応表を監査していない）・#10（Skin の σ が記録と食い違う）

工程5（`assign_materials.py`）が済んだ sim に対して実行する。**何も書き換えず・保存もしない**ので、
prod 用のモデルを触る前の確認として安全に何度でも流せる。

なぜ要るか:
  組織名 → 材料名の対応づけは `model.AutoAssignMaterials` の単語集合マッチ（`[a-z0-9]+` 分割）＋
  手動辞書なので、**"もっともらしい別材料" に当たっても気づかない**。σ は組織ごとに桁が決まっている
  ので、誤対応はレンジ外の値として現れる。

出すもの:
  ① エンティティ名 / リンクされた材料名 / σ の実値 を1行ずつ（TSV。そのまま docs に貼れる）
  ② 期待レンジとの自動照合（皮質骨 ~0.02 / 海綿骨 ~0.08 / CSF ~2 / 灰白 0.1-0.3 / 白質 0.06-0.15）
  ③ #10 用に、**上書き前の DB 生値**（IT'IS LF 5.0 の Skin）と sim の評価周波数

出典ノート: Claude/Knowledge/sim4life-material-assignment.md
"""
import s4l_v1.document as document
import s4l_v1.model as model

SIM_NAME = 'tTIS_LF1'
DB_NAME = "IT'IS LF 5.0"
SKIN_NAMES = ('Skin', 'Ear_skin_left', 'Ear_skin_right')

# 期待レンジ（材料名の部分一致・小文字で判定）。出典は docs/phase2-prod.md #11。
EXPECT = (
    ('skull_cortical',    0.010, 0.035),
    ('skull_cancellous',  0.050, 0.120),
    ('cerebrospinal',     1.500, 2.500),
    ('grey_matter',       0.080, 0.300),
    ('white_matter',      0.050, 0.150),
    ('cerebellum',        0.080, 0.250),
    ('muscle',            0.200, 0.600),
    ('fat',               0.010, 0.100),
    ('blood',             0.500, 1.000),
    ('eye_vitreous',      1.000, 2.000),
)
SANE_LO, SANE_HI = 1e-3, 3.0           # どの生体組織もこの外なら疑う（空気・電極は別扱い）
NON_TISSUE = ('air',)                  # σ=0 が正常なもの（Air_internal / Background）。レンジ判定から除く


def base(name):
    """component.Name の接尾辞 '  (Yoon-sun v3.1 Static)' を落としてエンティティ名に戻す。"""
    return name.split('  (')[0].strip()


def sigma_of(obj):
    """材料オブジェクト / 材料設定から σ を取り出す。API 差を吸収する。"""
    for path in (('ElectricProps', 'Conductivity'), ('Conductivity',)):
        cur = obj
        try:
            for attr in path:
                cur = getattr(cur, attr)
            return float(cur)
        except Exception:
            continue
    return None


# ===== ① sim と材料設定を集める =====
sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED — sim %r が %d 個' % (SIM_NAME, len(sims)))
sim = sims[0]

try:
    freq = float(sim.SetupSettings.Frequency)
except Exception:
    freq = None
print('[pre ] sim=%s  frequency=%s Hz' % (SIM_NAME, freq))

# component ごとに、その component に紐付いた MaterialSettings を実体で引く
# （材料名は重複しうる＝ Skin / Ear_skin_* が同じ材料名になるので、名前をキーにしない）
rows = []
for c in sim.AllComponents:
    ent = base(c.Name)
    try:
        keys = list(c.Settings.keys())
    except Exception:
        continue
    for k in keys:
        try:
            s = c.Settings[k]
        except Exception:
            continue
        if type(s).__name__ != 'MaterialSettings':
            continue
        rows.append((ent, s.Name, sigma_of(s)))

rows.sort()
print('[pre ] material settings on components: %d' % len(rows))
if not rows:
    raise SystemExit('[pre ] FAILED — 材料設定が1件も取れない（工程5 が済んでいない可能性）')

# ===== ② 対応表（TSV）=====
print('')
print('--- BEGIN TSV ---')
print('entity\tmaterial\tsigma')
for ent, mat, sig in rows:
    print('%s\t%s\t%s' % (ent, mat, 'None' if sig is None else '%.6g' % sig))
print('--- END TSV ---')
print('')

# ===== ③ 自動照合 =====
ng = []
skipped = []
for ent, mat, sig in rows:
    low = (mat or '').lower()
    if sig is None:
        ng.append((ent, mat, sig, 'σ が読めない'))
        continue
    if low in NON_TISSUE:             # Air は σ=0 が正常（生体組織のレンジを当てない）
        skipped.append((ent, mat, sig))
        continue
    hit = [(k, lo, hi) for k, lo, hi in EXPECT if k in low]
    if hit:
        k, lo, hi = hit[0]
        if not (lo <= sig <= hi):
            ng.append((ent, mat, sig, '期待レンジ %s [%g, %g] 外' % (k, lo, hi)))
    elif not (SANE_LO <= sig <= SANE_HI):
        ng.append((ent, mat, sig, '生体組織として非現実的（%g〜%g の外）' % (SANE_LO, SANE_HI)))

print('[chk ] range 判定を除外（非生体）: %s'
      % ', '.join('%s=%g' % (e, s) for e, m, s in skipped))
print('[chk ] range NG: %d' % len(ng))
for ent, mat, sig, why in ng:
    print('       %-28s -> %-32s sigma=%s  %s'
          % (ent, mat, 'None' if sig is None else '%.6g' % sig, why))

# 同じ材料に何個の組織がぶら下がっているか（誤対応は「多対1」として現れやすい）
bym = {}
for ent, mat, sig in rows:
    bym.setdefault(mat, []).append(ent)
multi = sorted([(m, v) for m, v in bym.items() if len(v) > 1], key=lambda x: -len(x[1]))
print('[chk ] 同じ材料を共有する組織: %d 材料' % len(multi))
for m, v in multi:
    print('       %-32s x%d  %s' % (m, len(v), ', '.join(sorted(v))))

# ===== ④ #10: 上書き前の DB 生値 =====
print('')
print('[#10 ] sim に入っている skin 系の σ（0.465 上書き後の値）:')
for ent, mat, sig in rows:
    if ent in SKIN_NAMES:
        print('       %-16s -> %-24s %s' % (ent, mat, 'None' if sig is None else '%.6g' % sig))

print('[#10 ] DB %s の生値:' % DB_NAME)
# 2026-08-09 実測: 材料プロパティは `m.electric_conductivity` に生えているが**メソッド形式**。
# ★単独で読んでも「読めた値が本当に DB 値か」を確かめられないので、**上書きしていない材料を
#   対照群として同時に読み**、sim 側の実測と一致するかで読み取り経路の正しさを検証する。
CONTROL = (('Muscle', 0.329533), ('Brain (White Matter)', 0.0639697))


def props_of(mat):
    """材料のプロパティを (名前, 値, 単位) の一覧で返す。

    `mat.electric_conductivity` はクラス属性の descriptor が返るだけで
    `TypeError: 'property' object is not iterable` になる（2026-08-09 実測）ので使わない。
    `AllProperties` の `PropertyValue` から読む。名前は `Name` ではなく
    `VariableName` / `Description` に入っている。
    """
    out = []
    for p in mat.AllProperties:
        nm = getattr(p, 'VariableName', None) or getattr(p, 'Description', None)
        out.append((str(nm), getattr(p, 'Value', None), str(getattr(p, 'Unit', ''))))
    return out


def sigma_from_props(mat):
    """名前に conduct を含むプロパティ（磁気側は除く）から σ を引く。"""
    for nm, val, unit in props_of(mat):
        low = nm.lower()
        if 'conduct' in low and 'magnet' in low:
            continue
        if 'conduct' in low and 'thermal' not in low:
            return nm, val, unit
    return None, None, None


try:
    import s4l_v1.materials as materials
    db = materials.database[DB_NAME]

    print('       --- Skin の全プロパティ（名前・値・単位）---')
    for nm, val, unit in props_of(db['Skin']):
        print('       %-32s = %-22s %s' % (nm, val, unit))

    print('       --- 対照群（sim 側で上書きしていない材料。一致すれば読み取り経路は正しい）---')
    for nm, sim_sigma in CONTROL:
        pn, pv, pu = sigma_from_props(db[nm])
        print('       %-22s DB=%s [%s %s]   sim=%g' % (nm, pv, pn, pu, sim_sigma))

    print('       --- 本題 ---')
    pn, pv, pu = sigma_from_props(db['Skin'])
    sim_skin = [s for e, m, s in rows if e == 'Skin']
    print('       %-22s DB=%s [%s %s]   sim=%s（上書き後）'
          % ('Skin', pv, pn, pu, sim_skin[0] if sim_skin else '不明'))
except Exception as ex:
    print('       取得できず: %r' % (ex,))

print('')
print('=== 監査 %s ===' % ('PASS（NG 0件）' if not ng else 'NG %d 件 — 上の行を確認' % len(ng)))
print('    書き込みは一切していない（保存もしていない）')
