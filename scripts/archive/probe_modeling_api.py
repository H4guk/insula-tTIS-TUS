"""Phase 4-3 幾何作成 API の確認（Sim4Life.lite Python コンソール・読み取りのみ）。

トランスデューサ（球面キャップ）を Python で作るには「球ソリッド作成」と
Boolean（減算/積）の正確な関数名が要る。lec7 は GUI で作ったので Python 名が不明。
XCoreModeling / model の中から候補を洗い出す（何も作らない・読み取りのみ）。

流れ:
  ① XCoreModeling の Create* / Solid* 系（球・円柱・箱）を列挙
  ② Boolean 系（Subtract / Intersect / Unite / Difference …）を列挙
  ③ 各候補の docstring / signature を可能な範囲で表示
"""
import XCoreModeling as xc
import s4l_v1.model as model
import inspect

names = [a for a in dir(xc) if not a.startswith('_')]

# ① 形状作成系
CREATE_HINT = ('sphere', 'cylinder', 'block', 'box', 'cone', 'solid', 'create', 'draw')
creators = [a for a in names if any(h in a.lower() for h in CREATE_HINT)]
print('[create] 形状作成の候補 (%d):' % len(creators))
for a in sorted(creators):
    print('   %s' % a)

# ② Boolean 系
BOOL_HINT = ('bool', 'subtract', 'intersect', 'unite', 'union', 'difference',
             'cut', 'merge', 'combine')
booleans = [a for a in names if any(h in a.lower() for h in BOOL_HINT)]
print('')
print('[bool  ] Boolean の候補 (%d):' % len(booleans))
for a in sorted(booleans):
    print('   %s' % a)

# ③ docstring / signature（C++ バインドは signature が取れないことが多いので doc も見る）
print('')
print('[sig   ] 主要候補の詳細:')
WANT = [a for a in names
        if any(h in a.lower() for h in ('sphere', 'cylinder'))
        or any(h in a.lower() for h in ('subtract', 'intersect', 'unite', 'union', 'difference'))]
for a in sorted(set(WANT)):
    obj = getattr(xc, a)
    line = '   %s' % a
    try:
        line += '  sig=%s' % inspect.signature(obj)
    except Exception:
        pass
    print(line)
    doc = (getattr(obj, '__doc__', None) or '').strip()
    if doc:
        first = doc.splitlines()[0][:120]
        print('        doc: %s' % first)

# ④ model 側にも作成系がないか一応見る（Vec3 は既知）
print('')
mnames = [a for a in dir(model) if not a.startswith('_')]
mcreate = [a for a in mnames if any(h in a.lower() for h in CREATE_HINT + BOOL_HINT)]
print('[model ] model 側の作成/Boolean 候補: %s' % sorted(mcreate))

print('')
print('=== 幾何 API 調査 完了（読み取りのみ）===')
