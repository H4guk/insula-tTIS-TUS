"""Step 1 を組む前に「このセッションが本当にクリーンか」を1発で可視化する偵察スクリプト。

背景（2026-07-30 の失敗）: リロードせず同じセッションで統合スクリプトを流したため、
`tTIS_LF1` / `GridBox_head` / 旧結果ファイルが同名衝突し、Run が
`HDF5: attribute already exists` を大量に出して
`RuntimeError: Unable to run simulation. Please check your simulation settings.` で拒否された。
→ **組む前に「既存 sim・重複エンティティ・電極の有無」を見て、汚れていれば分かるようにする。**

使い方: Sim4Life.lite の Python コンソールにこのファイルの中身を丸ごと貼って Shift+Enter。
        （load_yoonsun.py / place_electrodes.py の後、run_step1_lf1.py の前）

判定:
  - 既存 sim が 0 件           → クリーン。そのまま run_step1_lf1.py へ。
  - 既存 sim / 重複あり        → run_step1_lf1.py は**新しい名前で作る**ので続行可（衝突しない）。
                                 それでも Run 拒否が続くならリロードしてやり直す。
  - Yoon-sun or 電極が無い     → load_yoonsun.py / place_electrodes.py に戻る。
"""
import collections

import s4l_v1
import s4l_v1.model as model
import s4l_v1.document as document
import XCoreModeling as xc

GX, GY, GZ = (4, 202), (162, 352), (1450, 1665)   # 頭部グリッド envelope
ELECS = ('Elec_T7', 'Elec_P7', 'Elec_Fp1', 'Elec_Fp2')


def xyz(v):
    try:    return float(v[0]), float(v[1]), float(v[2])
    except: return float(v.X), float(v.Y), float(v.Z)


ents = list(model.AllEntities())
names = [e.Name for e in ents]
dup = {n: c for n, c in collections.Counter(names).items() if c > 1}

# ---- 1) 既存シミュレーション（同名衝突と run 済み状態の温床）----
sims = list(document.AllSimulations)
print('[1] 既存 sim: %d 件' % len(sims))
for s in sims:
    try:    has = s.HasResults()
    except Exception: has = '?'
    print('    - %-16s HasResults=%s' % (s.Name, has))
if not sims:
    print('    → クリーン（理想の状態）')

# ---- 2) 重複エンティティ（GridBox_head の作り直しで増える）----
print('[2] 重複エンティティ: %d 種' % len(dup))
for n, c in sorted(dup.items()):
    print('    - %-24s x%d' % (n, c))
if not dup:
    print('    → 重複なし')

# ---- 3) 必須ジオメトリ（Yoon-sun / 電極4枚）----
skin = [e for e in ents if e.Name == 'Skin']
print('[3] Skin(Yoon-sun): %s / 全エンティティ数: %d' % ('OK' if skin else 'なし★', len(ents)))
for nm in ELECS:
    hit = [e for e in ents if e.Name == nm]
    if len(hit) == 1:
        lo, hi = xyz(xc.GetBoundingBox(hit)[0]), xyz(xc.GetBoundingBox(hit)[1])
        ctr = [(lo[i] + hi[i]) / 2 for i in range(3)]
        print('    %-9s OK   中心 (%.1f, %.1f, %.1f)' % (nm, ctr[0], ctr[1], ctr[2]))
    else:
        print('    %-9s %s★' % (nm, 'なし' if not hit else '重複 x%d' % len(hit)))

# ---- 4) 頭部組織数（材料割り当ての期待値 59 と合うか）----
head = set()
for e in ents:
    bb = xc.GetBoundingBox([e])
    if not bb:
        continue
    lo, hi = xyz(bb[0]), xyz(bb[1])
    if hi[2] >= GZ[0] and lo[2] <= GZ[1] and hi[0] >= GX[0] and lo[0] <= GX[1] \
       and hi[1] >= GY[0] and lo[1] <= GY[1]:
        n = e.Name
        if n.startswith('Elec_') or 'Yoon' in n or n in ('Bones', 'Model') or n.startswith('GridBox'):
            continue
        head.add(n)
print('[4] グリッド内の頭部組織: %d 個（期待 59）' % len(head))

# ---- 5) 判定 ----
print('[5] 判定:')
if not skin or any(len([e for e in ents if e.Name == nm]) != 1 for nm in ('Elec_T7', 'Elec_P7')):
    print('    ✗ ジオメトリ不足 → load_yoonsun.py / place_electrodes.py をやり直す')
elif sims or dup:
    print('    △ セッションに残骸あり。run_step1_lf1.py は未使用の新しい名前で作るので続行可。')
    print('      （それでも Run 拒否が続く場合はブラウザをリロードして最初からやり直す）')
else:
    print('    ✓ クリーン。run_step1_lf1.py をそのまま貼ってよい。')
