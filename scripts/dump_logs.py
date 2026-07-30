"""Run 拒否／全点NaN の**証拠ログ（Input.log / Voxeler.log / SolverLog）を1発で吐く**スクリプト。

背景: 2026-07-29〜30 の切り分けは「症状 → ログを見てもらう → 報告 → 次の手」の往復で時間を溶かした。
真因（電極の材料漏れ）を確定させたのも Voxeler.log の1行
`Error: The boundary component 'Elec_T7' is not being considered in the voxeling process.` だった。
→ **Run の成否にかかわらず、直後に自動でログの決定的な行を出す**ようにして往復を無くす。

使い方: Sim4Life.lite の Python コンソールに貼って Shift+Enter。
        run_step1_lf1.py の中からも自動で呼ばれる（同じ名前空間に貼ってあれば dump_logs() が使える）。

出力: 最近更新された *.log を新しい順に列挙し、各ファイルから
      dof行 / Dirichlet / lossy dielectrics / not being considered / Error / HDF5 / attribute
      を含む行だけを抜き出して表示する。
      → この出力をそのまま Obsidian と（必要なら）ZMT サポートへの照会に貼れる。

注: Lite クラウドの実ファイル配置は環境依存なので、API で結果ディレクトリが取れない場合は
    候補ルートを走査するフォールバックで探す（best effort・見つからなければ「見つからない」と出す）。
"""
import os
import time

KEYS = ('degree of freedom', 'unknown', 'dirichlet', 'lossy dielectric', 'not being considered',
        'error', 'hdf5', 'attribute', 'voxel scene', 'warning: the system')
SKIP_DIRS = ('.vip', 'yoonsun', 'node_modules', '.git', 'site-packages', '__pycache__')
MAX_FILES = 4000


def _candidate_roots():
    roots = []
    # ① API から現在のプロジェクト/結果ディレクトリを取れるなら最優先（取れない環境もある）
    try:
        import s4l_v1.document as document
        for attr in ('FileName', 'FileFolder', 'Folder', 'Path'):
            v = getattr(document, attr, None)
            v = v() if callable(v) else v
            if isinstance(v, str) and v:
                roots.append(v if os.path.isdir(v) else os.path.dirname(v))
    except Exception:
        pass
    # ② 定番の場所
    roots += [os.getcwd(), os.path.expanduser('~'), '/tmp', '/.data']
    out, seen = [], set()
    for r in roots:
        if r and os.path.isdir(r) and r not in seen:
            seen.add(r); out.append(r)
    return out


def find_logs(max_age_h=24.0, limit=12):
    """更新が新しい *.log を新しい順に返す。"""
    now, found, scanned = time.time(), [], 0
    for root in _candidate_roots():
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if not d.startswith('.') or d in ('.data',)]
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            if dirpath.count(os.sep) - root.count(os.sep) > 6:
                dirnames[:] = []
                continue
            for fn in filenames:
                if not fn.lower().endswith('.log'):
                    continue
                p = os.path.join(dirpath, fn)
                scanned += 1
                if scanned > MAX_FILES:
                    break
                try:    mt = os.path.getmtime(p)
                except Exception: continue
                if (now - mt) <= max_age_h * 3600:
                    found.append((mt, p))
            if scanned > MAX_FILES:
                break
    uniq = {}
    for mt, p in found:
        uniq[os.path.realpath(p)] = mt
    return [(mt, p) for p, mt in sorted(uniq.items(), key=lambda kv: -kv[1])][:limit]


def show(path, tail_lines=400):
    print('-' * 72)
    print('%s  (更新 %s)' % (path, time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(path)))))
    try:
        with open(path, 'r', errors='replace') as f:
            lines = f.readlines()[-tail_lines:]
    except Exception as e:
        print('  読めない:', type(e).__name__, e); return
    hits = [l.rstrip() for l in lines if any(k in l.lower() for k in KEYS)]
    if hits:
        for l in hits[-40:]:
            print('  ', l)
    else:
        print('   （キーワード該当なし・末尾5行）')
        for l in lines[-5:]:
            print('  ', l.rstrip())


def dump_logs(max_age_h=24.0, limit=12):
    logs = find_logs(max_age_h, limit)
    if not logs:
        print('*.log が見つからなかった。GUI の Logger / 結果フォルダから手動で取得する。')
        print('探索したルート:', _candidate_roots())
        return []
    print('=== 直近 %.0fh の *.log: %d 件（新しい順）===' % (max_age_h, len(logs)))
    for mt, p in logs:
        show(p)
    print('-' * 72)
    print('★確認ポイント:')
    print('  Input.log   : "Degree of freedoms: ... N unknowns, M Dirichlet points"')
    print('                → unknowns>0 かつ Dirichlet points>0 なら正常')
    print('  Voxeler.log : "not being considered in the voxeling process" が**無い**こと')
    print('                （出ていたら、その電極に材料σが付いていない＝全点NaNの真因）')
    print('  Run拒否時   : "HDF5" / "attribute already exists" があれば同名衝突')
    print('                → リロードして真っさらなセッションでやり直す')
    return [p for _, p in logs]


dump_logs()      # 貼った時点で1回走る（run_step1_lf1.py からも自動で呼ばれる）
