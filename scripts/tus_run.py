"""T-6a Acoustic Run と結果構造の確認（Sim4Life.lite Python コンソール）。

TUS_250k を実行し、結果が出ることと圧力場の取り出し API を確認する。
★Run が失敗しても SystemExit せず、ソルバーログの末尾を読んで理由を出す。

流れ:
  ① 事前ゲート → ② ClearResults → ③ Run（失敗しても続行しログを読む）
  ④ 成功時: sim.Results() の構造を dump（圧力場名の特定）
"""
import os
import glob
import time
import s4l_v1.document as document

SIM_NAME = 'TUS_250k'


def read_log_tail():
    out = sim.GetOutputFileName()
    uid = os.path.basename(out).split('_Output')[0]
    root = os.path.dirname(os.path.dirname(out))
    logs = glob.glob(os.path.join(root, '*_Results', uid + '_Input.log'))
    if not logs:
        logs = glob.glob(os.path.join(root, '*_Results', '*_Input.log'))
    if not logs:
        print('[log ] Input.log が見つからない')
        return
    lg = max(logs, key=os.path.getmtime)
    body = open(lg, encoding='utf-8', errors='replace').read()
    print('[log ] %s tail:' % os.path.basename(lg))
    for l in body.splitlines()[-15:]:
        print('   |', l)


sims = [s for s in document.AllSimulations if s.Name == SIM_NAME]
if len(sims) != 1:
    raise SystemExit('[pre ] FAILED - sim count %d' % len(sims))
sim = sims[0]

n_mat = sum(1 for s in sim.AllSettings if type(s).__name__ == 'MaterialSettings')
n_src = sum(1 for s in sim.AllSettings if type(s).__name__ == 'SourceSettings')
print('[pre ] materials=%d  sources=%d  grid=%s' % (n_mat, n_src, sim.GlobalGridSettings.Name))

try:
    if sim.HasResults():
        sim.ClearResults()
        print('[run ] cleared existing results')
except Exception as ex:
    print('[run ] ClearResults ERR (maybe harmless):', ex)

t0 = time.time()
run_ok = False
try:
    sim.RunSimulation(wait=True)
    run_ok = True
    print('[run ] returned after %.1f s' % (time.time() - t0))
except Exception as ex:
    print('[run ] FAILED after %.1f s: %s' % (time.time() - t0, ex))
    read_log_tail()

try:
    print('[run ] HasResults:', sim.HasResults())
except Exception as ex:
    print('[run ] HasResults ERR:', ex)

if run_ok:
    print('')
    print('[res ] sim.Results() structure:')
    try:
        res = sim.Results()
        try:
            res.UpdateAll()
        except Exception:
            pass
        try:
            top = list(res.keys())
        except Exception:
            try:
                top = [k for k in res]
            except Exception:
                top = [a for a in dir(res) if not a.startswith('_')]
        print('[res ] top keys/attrs: %s' % top)
        for k in top:
            try:
                node = res[k]
            except Exception:
                continue
            try:
                node.Update(0)
            except Exception:
                pass
            try:
                subs = list(node.keys())
            except Exception:
                subs = [a for a in dir(node) if not a.startswith('_')][:20]
            print('   [%s] -> %s' % (k, subs))
    except Exception as ex:
        print('[res ] structure error:', ex)
    print('')
    print('=== T-6a done (Run OK + results structure) ===')
else:
    print('')
    print('=== T-6a: Run 失敗（上のログ末尾を確認）===')
