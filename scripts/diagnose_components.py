"""電極が voxeler に considered されない理由を切り分ける**読み取り専用**診断（2026-07-30 夜）。

背景（この診断が必要になった経緯）:
  クリーンなセッション（既存sim 0件・重複0）で run_step1_lf1.py を流し、材料61個（組織59+電極2）が
  付いた状態でも Voxeler.log に
      Error: The boundary component 'Elec_T7' is not being considered in the voxeling process.
  が出て Run が拒否された。Input.log は生成されず＝**ソルバー起動前（ボクセル化段）で止まっている**。
  HDF5 `attribute already exists` はクリーンセッションでも出るので**症状であり原因ではない**と判明。

検証したい仮説:
  H1. 同一ソリッドに「材料σ」と「Dirichlet BC」を両方付けると、どちらかが無効化される
      （＝BC が considered されない）。→ 電極の材料設定と BC が両方 sim に生きているかを見る。
  H2. HDF5 衝突は結果ディレクトリに残った過去ファイルが原因。→ 結果ディレクトリの中身を見る。
  H3. BC はソリッドではなく**面（surface/face）**に付けるべき。→ 面を取り出す API があるか探す。

使い方: run_step1_lf1.py を流した**同じコンソール**にこのファイルの中身を貼る（`sim` が生きている前提）。
        何も変更しない（読み取りのみ）。
"""
import os
import time

import s4l_v1
import s4l_v1.model as model
import s4l_v1.document as document
import XCoreModeling as xc

TARGETS = ('Elec_T7', 'Elec_P7')

# sim を拾う（同じコンソールに無ければ AllSimulations から）
if 'sim' not in dir():
    sims = list(document.AllSimulations)
    sim = sims[-1] if sims else None
print('対象 sim:', getattr(sim, 'Name', None))

# ---- H2) 結果ディレクトリの中身（HDF5 衝突の元を確認）----
print('\n=== [H2] 結果ディレクトリ ===')
roots = ['/home/smu/work/workspace']
for r in roots:
    if not os.path.isdir(r):
        continue
    for dirpath, dirnames, filenames in os.walk(r):
        if dirpath.count(os.sep) - r.count(os.sep) > 2:
            dirnames[:] = []
            continue
        if not filenames:
            continue
        print('--', dirpath)
        rows = []
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:    st = os.stat(p)
            except Exception: continue
            rows.append((st.st_mtime, st.st_size, fn))
        for mt, sz, fn in sorted(rows, reverse=True)[:15]:
            print('   %s  %9d B  %s' % (time.strftime('%m-%d %H:%M', time.localtime(mt)), sz, fn))

# ---- H1) 電極が「材料」と「BC」の両方に生きているか ----
print('\n=== [H1] sim のコンポーネント（電極が何に属しているか）===')
try:
    comps = list(sim.AllComponents)
    print('AllComponents 数:', len(comps))
    for c in comps:
        nm = getattr(c, 'Name', '?')
        if any(t in str(nm) for t in TARGETS) or 'BC_' in str(nm):
            print('  - %-24s type=%s' % (nm, type(c).__name__))
            for attr in ('Components', 'Entities', 'Entity', 'Parent', 'MaterialName'):
                v = getattr(c, attr, None)
                if v is not None:
                    try:    v = list(v)
                    except Exception: pass
                    print('      %-12s %s' % (attr, v))
except Exception as e:
    print('AllComponents を読めない:', type(e).__name__, e)

# 材料設定側から σ を読み直す（run_step1_lf1.py の created が生きていれば）
print('\n--- 電極の材料σ（BC を付けた後に生き残っているか）---')
created = globals().get('created')
for t in TARGETS:
    ms = (created or {}).get(t)
    if ms is None:
        print('  %-9s 材料設定オブジェクトが見つからない（created に無い）' % t)
        continue
    try:
        print('  %-9s σ=%s / name=%s' % (t, ms.ElectricProps.Conductivity, ms.Name))
    except Exception as e:
        print('  %-9s σ を読めない: %s %s' % (t, type(e).__name__, e))

# ---- H3) BC を「面」に付けられるか（API の有無を調べるだけ）----
print('\n=== [H3] 面(surface/face)を取り出す API 候補 ===')
cands = [n for n in dir(xc) if any(k in n.lower() for k in ('surface', 'face', 'sheet', 'shell'))]
print('XCoreModeling:', cands)
ent = [e for e in model.AllEntities() if e.Name == 'Elec_T7']
if ent:
    e0 = ent[0]
    print('Elec_T7 の型:', type(e0).__name__)
    print('Elec_T7 の属性（面関連）:',
          [n for n in dir(e0) if any(k in n.lower() for k in ('face', 'surface', 'body', 'geom'))])

print('\n★判定の読み方:')
print('  [H1] 電極の材料設定と BC が両方生きているのに voxeler が BC を無視 →')
print('       「同一ソリッドに材料+BC」の組み合わせ自体が不可の可能性 → H3 の面BCへ')
print('  [H2] 結果ディレクトリに過去の .h5 が残っていれば HDF5 衝突の元（ただし主因ではない）')
print('  [H3] 面を取り出す API があれば「電極ソリッド=材料σ / その外側の面=Dirichlet」を試す価値あり')
