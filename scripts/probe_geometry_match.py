"""5-1b 統合前の突き合わせ（両プロジェクトで流して出力を比較・読み取り専用）。

Claude/Decisions/2026-08-25-one-model-two-simulations.md の手順2:
「統合前に両プロジェクトのエンティティ数・バウンディングボックス・ROI 座標を突き合わせる。
  片方だけ動かした・直したという差分は、統合するまで気づけない」

**tTIS プロジェクトと TUS プロジェクトの両方で流し、出力を並べて比較する**。

出すもの:
  ① エンティティ総数と**ジオメトリ指紋**（全 bbox 座標の総和）— 1つでも動いていれば値が変わる
  ② 名前一覧（ソート）— 指紋がずれたとき差分を特定するため
  ③ 主要エンティティの bbox（Elec_* / Transducer / GridBox_* / Skin）
  ④ ROI が実体（エンティティ）として在るか — 無ければ座標はスクリプトのハードコード
  ⑤ Elec_T7 と Transducer の重なり（どちらも T7 に置いてあるため）
  ⑥ シミュレーション一覧と Voxeler 登録数 — 統合後に「何が場に存在するか」を決めるのはこれ
"""
import numpy as np
import s4l_v1.document as document
import s4l_v1.model as model
import XCoreModeling as xc

FOCUS_MM = np.array([99.1, 295.0, 1562.2])   # 解析スクリプトが使う ROI 中心（ハードコード値）
ROI_R_MM = 10.0
KEY_PREFIX = ('Elec_', 'Transducer', 'GridBox', 'Skin', 'Model')
# ★'roi' の部分一致は Thyroid_gland（Thy-roi-d）を拾うので使わない（2026-08-27 の実行で判明）
ROI_HINT = ('_roi', 'roi_', 'insula', 'island', '島')


def xyz(v):
    try:    return np.array([float(v[0]), float(v[1]), float(v[2])])
    except: return np.array([float(v.X), float(v.Y), float(v.Z)])


def bbox(e):
    try:
        bb = xc.GetBoundingBox([e])
        return xyz(bb[0]), xyz(bb[1])
    except Exception:
        return None


ents = list(model.AllEntities())
print('[proj] エンティティ %d 個' % len(ents))

# ===== ① 指紋 =====
names = []
fp = 0.0
n_bb = 0
for e in ents:
    try:
        nm = e.Name
    except Exception:
        continue
    names.append(nm)
    b = bbox(e)
    if b is not None:
        fp += float(b[0].sum() + b[1].sum())
        n_bb += 1
names.sort()
print('[fp  ] bbox を持つ %d 個 / **ジオメトリ指紋 = %.4f**' % (n_bb, fp))
print('       （両プロジェクトでこの値とエンティティ数が一致すれば、複製以降どちらも触っていない）')

# ===== ② 名前一覧 =====
print('')
print('[list] 名前一覧（ソート・カンマ区切り）:')
line = '       '
for nm in names:
    if len(line) + len(nm) + 2 > 110:
        print(line)
        line = '       '
    line += nm + ', '
if line.strip():
    print(line.rstrip(', '))

# ===== ③ 主要エンティティの bbox =====
print('')
print('[key ] 主要エンティティの bbox [mm]:')
found_key = False
for e in ents:
    try:
        nm = e.Name
    except Exception:
        continue
    if not any(nm.startswith(p) for p in KEY_PREFIX):
        continue
    b = bbox(e)
    found_key = True
    if b is None:
        print('       %-16s (bbox 取得不可)' % nm)
    else:
        print('       %-16s %s .. %s  size=%s'
              % (nm, np.round(b[0], 1), np.round(b[1], 1), np.round(b[1] - b[0], 1)))
if not found_key:
    print('       （該当なし）')

# ===== ④ ROI が実体として在るか =====
print('')
roi_ents = [e for e in ents
            if any(h in getattr(e, 'Name', '').lower() for h in ROI_HINT)]
if roi_ents:
    print('[roi ] ROI らしきエンティティ %d 個:' % len(roi_ents))
    for e in roi_ents:
        b = bbox(e)
        if b is None:
            print('       %-20s (bbox 取得不可)' % e.Name)
        else:
            ctr = 0.5 * (b[0] + b[1])
            print('       %-20s 中心 %s  size=%s  解析値との差 %.2f mm'
                  % (e.Name, np.round(ctr, 1), np.round(b[1] - b[0], 1),
                     float(np.linalg.norm(ctr - FOCUS_MM))))
else:
    print('[roi ] **ROI の実体エンティティは無い**')
    print('       ⇒ ROI は解析スクリプトのハードコード値（%s・r=%.0fmm）でのみ定義されている。'
          % (np.round(FOCUS_MM, 1), ROI_R_MM))
    print('       ⇒ 統合しても「物理的に同一のオブジェクト」にはならない（数値が同一なら公平性は保たれる）。')

# ===== ⑤ Elec_T7 と Transducer の重なり =====
print('')
et = [e for e in ents if getattr(e, 'Name', '') == 'Elec_T7']
tr = [e for e in ents if getattr(e, 'Name', '') == 'Transducer']
if et and tr:
    be, bt = bbox(et[0]), bbox(tr[0])
    if be and bt:
        ov = np.minimum(be[1], bt[1]) - np.maximum(be[0], bt[0])
        if np.all(ov > 0):
            print('[ovl ] **Elec_T7 と Transducer の bbox が重なる**（重なり size=%s mm）' % np.round(ov, 1))
            print('       ⇒ 統合時は Voxeler 登録で棲み分ける（TUS sim に電極を登録しない・tTIS sim に Transducer を登録しない）')
        else:
            print('[ovl ] Elec_T7 と Transducer の bbox は重ならない（間隔 %s mm）' % np.round(-ov, 1))
else:
    print('[ovl ] Elec_T7 と Transducer が同居していない（このプロジェクトには %s のみ）'
          % ('Elec_T7' if et else ('Transducer' if tr else 'どちらも無し')))

# ===== ⑥ シミュレーションと Voxeler 登録 =====
print('')
print('[sim ] シミュレーション:')
for sim in document.AllSimulations:
    try:
        n_reg = sum(1 for c in sim.AllComponents if 'Automatic Voxeler Settings' in c.Settings.keys())
    except Exception:
        n_reg = -1
    try:
        n_mat = sum(1 for s in sim.AllSettings if type(s).__name__ == 'MaterialSettings')
    except Exception:
        n_mat = -1
    print('       %-14s 材料 %-5s Voxeler登録 %-5s' % (sim.Name, n_mat, n_reg))

print('')
print('=== 5-1b 完了（読み取りのみ・保存していない）===')
print('    ★ tTIS プロジェクトと TUS プロジェクトの両方で流し、[proj] の個数と [fp] の指紋を突き合わせること')
