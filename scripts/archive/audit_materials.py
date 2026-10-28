"""材料対応表の監査 — (ViP 組織名 → DB 材料名 → σ) を出力する（読み取り専用）。

対応 Issue: #11（対応表を監査していない）/ #14（期待レンジが非 LF 前提だった）

工程5（`assign_materials.py`）が済んだ sim に対して実行する。**何も書き換えず・保存もしない**。

なぜ要るか:
  組織名 → 材料名の対応づけは `model.AutoAssignMaterials` の単語集合マッチ（`[a-z0-9]+` 分割）＋
  手動辞書＋DB 側の別名解決なので、**"もっともらしい別材料" に当たっても気づかない**。
  59組織すべてを目視できる形に並べ、レポートの材料表としてもそのまま使えるようにする。

★2026-08-12（#14）: **σ のレンジ判定を落とした。**
  σ の正しさは工程5 の事後ゲートが「**リンク先 DB の格納値と直接照合**」して担保している。
  監査側にもハードコードした期待レンジを置くと、**同じことを2箇所で判定して片方だけ古くなる**
  ——実際に材料を IT'IS LF 5.0 へ移行した際、監査側のレンジ（非 LF の 2 kHz 評価値が前提）が
  取り残されて正常な材料を NG と判定する状態になった。ここは**対応表の出力に専念**する。
  残す検査は「σ が読めない / 非 Air なのに 0 以下」だけ（工程5 のゲートが見ていない種類の欠陥）。

出力:
  ① エンティティ名 / リンクされた材料名 / σ を1行ずつ（TSV。そのまま docs に貼れる）
  ② 同じ材料を共有する組織の一覧（誤対応は多対1として現れやすい＝監査の観点そのもの）
  ③ 材料ごとの σ 一覧（レポートの材料表の素）

出典ノート: Claude/Knowledge/sim4life-material-assignment.md
"""
import s4l_v1.document as document

SIM_NAME = 'tTIS_LF1'
AIR_NAMES = ('air',)                   # σ=0 が正常なもの（Air_internal / Background）


def base(name):
    """component.Name の接尾辞 '  (Yoon-sun v3.1 Static)' を落としてエンティティ名に戻す。"""
    return name.split('  (')[0].strip()


def sigma_of(obj):
    """MaterialSettings から σ を取り出す。"""
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

# component ごとに、その component に紐付いた MaterialSettings を**実体で**引く
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
print('[pre ] material settings on components: %d（組織59 ＋ 既定の Air ＝ 60 が想定）' % len(rows))
if not rows:
    raise SystemExit('[pre ] FAILED — 材料設定が1件も取れない（工程5 が済んでいない可能性）')

# ===== ② 対応表（TSV）=====
print('')
print('--- BEGIN TSV ---')
print('entity\tmaterial\tsigma')
for ent, mat, sig in rows:
    print('%s\t%s\t%s' % (ent, mat, 'None' if sig is None else '%.6g' % sig))
print('--- END TSV ---')

# ===== ③ 欠陥の検査（工程5 のゲートが見ていない種類だけ）=====
print('')
bad = []
for ent, mat, sig in rows:
    low = (mat or '').lower()
    if sig is None:
        bad.append((ent, mat, sig, 'σ が読めない'))
    elif sig <= 0 and low not in AIR_NAMES:
        bad.append((ent, mat, sig, '非 Air なのに σ <= 0'))
print('[chk ] 欠陥: %d 件' % len(bad))
for ent, mat, sig, why in bad:
    print('       %-28s -> %-28s sigma=%s  %s' % (ent, mat, sig, why))
print('[chk ] ※ σ の値そのものの検算は工程5（assign_materials.py）が DB 格納値と直接照合する。')
print('       ここでは重複させない（#14）。')

# ===== ④ 同じ材料を共有する組織（誤対応は多対1として現れやすい）=====
bym = {}
for ent, mat, sig in rows:
    bym.setdefault(mat, []).append(ent)
multi = sorted([(m, v) for m, v in bym.items() if len(v) > 1], key=lambda x: -len(x[1]))
print('')
print('[chk ] 同じ材料を共有する組織: %d 材料' % len(multi))
for m, v in multi:
    print('       %-30s x%d  %s' % (m, len(v), ', '.join(sorted(v))))

# ===== ⑤ 材料ごとの σ（レポートの材料表の素）=====
print('')
print('--- 材料ごとの σ（%d 材料・レポート用）---' % len(bym))
print('material\tsigma\tn_entities')
seen = {}
for ent, mat, sig in rows:
    seen[mat] = sig
for mat in sorted(bym.keys()):
    sig = seen.get(mat)
    print('%s\t%s\t%d' % (mat, 'None' if sig is None else '%.6g' % sig, len(bym[mat])))

print('')
print('=== 監査 %s ===' % ('PASS（欠陥 0 件）' if not bad else 'NG %d 件' % len(bad)))
print('    書き込みは一切していない（保存もしていない）')
