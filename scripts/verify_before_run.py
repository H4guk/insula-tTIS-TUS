"""Step 1 の Run 前ゲート：全点 NaN（no lossy dielectrics / no used dofs）を Run 前に検知する。

背景: Run は "finished successfully" でも E 場・電位が全点 NaN になる事象がある。
ソルバーログの `0 unknowns / 0 Dirichlet points / no lossy dielectrics` は
「材料σも電極BCもボクセルモデルに載っていない」を意味する（σの値ミスではなく"未反映"）。

使い方:
  assign_materials.py を実行した直後（同じコンソール名前空間に sim / created /
  full_map / get_mat が生きている状態）に、このファイルの中身を貼って Shift+Enter。
  → ①sim の登録 ②各σの実値 ③σ=0 の直接設定フォールバック ④BC/ボクセル順序の注意 を出す。

★重要な順序（NaN を避ける鉄則）:
  材料σ → 電極BC → （全部終わってから最後に）CreateVoxels → Run。
  ボクセル化は「割り当てのスナップショット」なので、割り当て後に必ず作り直す。
"""
import s4l_v1.document as document

# ---- 1) sim が document.AllSimulations に登録されているか（v10: Python 作成 sim は未登録）----
sims = list(document.AllSimulations)
if sim not in sims:
    document.AllSimulations.Add(sim)
    print('[1] sim を AllSimulations に登録:', sim.Name)
else:
    print('[1] sim 登録済み:', sim.Name, '/ 全 sim:', [s.Name for s in sims])

# ---- 2) 各材料の実効σを読む（DBリンクが σ を入れているか）----
zero = []
for nm, ms in created.items():
    try:
        sigma = float(ms.ElectricProps.Conductivity)
    except Exception as e:
        sigma = None
    if (sigma is None) or (sigma <= 0):
        zero.append(nm)
print('[2] 材料数:', len(created), '/ σ=0 または未設定:', len(zero))
if zero:
    print('    σ=0 の例:', zero[:12])

# ---- 3) σ=0 が出たら直接設定フォールバック（DBリンクを介さず ElectricProps に明示コピー）----
#     DB material オブジェクトから σ を読んで直接入れる。DB名の σ が読めない組織は空気等なので skip。
if zero:
    print('[3] DBリンクσが未反映の疑い → 直接設定フォールバックを実行')
    fixed, failed = 0, []
    for nm in zero:
        try:
            mat = get_mat(full_map[nm])            # assign_materials.py の関数/辞書を再利用
            dbsig = float(mat.ElectricProps.Conductivity)
            if dbsig > 0:
                created[nm].ElectricProps.Conductivity = dbsig
                fixed += 1
        except Exception as e:
            failed.append((nm, type(e).__name__))
    sim.UpdateAllMaterials()
    print('    直接設定できた組織:', fixed, '/ 読めなかった:', failed[:8])
    # 空気系（Air_internal 等）は σ≈0 が正常なので、残っても問題なし。
else:
    print('[3] σ は全組織で正（フォールバック不要）')

# ---- 4) 次の順序リマインド（この後にやること）----
print('[4] この後の順序を厳守:')
print('    (a) 電極BC を付ける（+1V / 0V。Elec_* に AddBoundarySettings）')
print('    (b) すべて終えてから最後に  sim.CreateVoxels()  を実行（割り当て後に必ず作り直す）')
print('    (c) sim.RunSimulation(wait=True) → 完了後に **SolverLog を必ず読む**')
print('    (d) SolverLog の "Degree of freedoms" 行を確認:')
print('        used dofs が 0 でなく、Dirichlet points > 0 なら成功。')
print('        0 のままなら NaN 確定 → その行をそのまま記録して次の切り分けへ。')
print('    ※ 各段のあと s4l_v1.document.Save() を忘れない（保存忘れで状態が壊れる）。')
