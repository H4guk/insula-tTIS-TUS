"""#36 5-6 図の生成（ローカル実行・Sim4Life 不要）。

統合版（1プロジェクト・3シミュレーション）の確定値から、提出物用の図を作る。
数値の出所は docs/comparison-table.md §2。
2026-10-14（GH #17）: 脳を脳実質 12 組織（両手法共通）にして選択性と Fig.3 を出し直した（`results/brain_by_name_2026-10-13.txt`）。
Fig.2 は ROI だけで決まる量なので変わらない。
2026-10-20（GH #19）: Fig.2 の目安を両手法とも文献の有効範囲の下端（0.2 V/m・3 W/cm²）にし、TUS は振幅に直した（√(ISPPA/3)）。

  Fig.1  selectivity          選択性（非標的/標的・小さいほど良い）＋ Inoue 2025 参照線
  Fig.2  reach_volume         標的レベル以上が及ぶ脳体積（地続き / 飛び地の内訳つき）
  Fig.3  dose_vs_threshold    標的の強さ / 有効範囲の下端（振幅・1.0 = 下端）
  （番号は提出物の図の番号。2026-10-29 にファイル名を合わせた。下の 10-14・10-20 の記録の Fig.2/3 は当時の番号）

設計（dataviz スキル準拠）:
  - 形: 3枚とも「2手法の比較 + 参照線」なので横棒に統一
  - 色: categorical slot 1 = tTIS(blue) / slot 2 = TUS(orange)。**固定順・循環させない**
        validate_palette.js で全チェック PASS（CVD ΔE 24.7 / 通常視 33.6 / 対比 >=3:1）
  - 内訳は色を増やさず **texture（ハッチ）** で分ける＝CVD・印刷・forced-colors で安全
  - grid/axes は recessive、値は直接ラベル、参照線はグレー破線
実行: python3 scripts/make_figures.py   → docs/figures/*.png (+ .svg)
"""
import os

os.environ.setdefault('MPLCONFIGDIR', '/tmp/claude-501/mpl')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ---- palette（dataviz reference palette・light surface）----
SURFACE = '#fcfcfb'
INK = '#0b0b0b'
INK2 = '#52514e'
MUTED = '#8a8983'
TTIS = '#2a78d6'      # categorical slot 1
TUS = '#eb6834'       # categorical slot 2

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'figures')
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    'figure.facecolor': SURFACE,
    'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE,
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.edgecolor': MUTED,
    'axes.linewidth': 0.8,
    'text.color': INK,
    'axes.labelcolor': INK2,
    'xtick.color': INK2,
    'ytick.color': INK,
    'xtick.labelsize': 10,
    'ytick.labelsize': 12,
})


def base_axes(figsize=(7.6, 2.7)):
    fig, ax = plt.subplots(figsize=figsize)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(MUTED)
    ax.xaxis.grid(True, color='#e6e5e1', linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis='y', length=0)
    return fig, ax


def refline(ax, x, text, ha='center'):
    """参照線と、その注記を**軸の上端**に置く。
    invert_yaxis() を使うとデータ座標の上下が反転するので、注記は axes 座標に固定する。"""
    ax.axvline(x, color=MUTED, linestyle='--', linewidth=1.2)
    ax.annotate(text, xy=(x, 1.0), xycoords=('data', 'axes fraction'),
                xytext=(0, 6), textcoords='offset points',
                ha=ha, va='bottom', fontsize=9, color=INK2)


def save(fig, name):
    fig.tight_layout()
    for ext in ('png', 'svg'):
        fig.savefig(os.path.join(OUT, '%s.%s' % (name, ext)), dpi=200)
    plt.close(fig)
    print('  wrote %s.png / .svg' % name)


# ===== Fig.1 選択性 =====
fig, ax = base_axes()
labels = ['tTIS', 'TUS']
vals = [0.3576, 0.1929]
bars = ax.barh(labels, vals, height=0.5, color=[TTIS, TUS])
refline(ax, 0.40, 'Inoue 2025 ≈ 0.40', ha='right')
for b, v in zip(bars, vals):
    ax.text(v + 0.008, b.get_y() + b.get_height() / 2, '%.4f' % v,
            va='center', ha='left', fontsize=12, color=INK)
ax.set_xlim(0, 0.46)
ax.set_xlabel('non-target mean / ROI mean   (lower is better)')
ax.set_title('Selectivity in the brain', loc='left', fontsize=13, pad=22)
ax.invert_yaxis()
save(fig, 'fig1_selectivity')

# ===== Fig.3 標的の強さ / 有効範囲の下端（dumbbell）=====
# ★旧版は tTIS の「ROI 平均」と TUS の「ROI 最大」を並べていた（2026-08-28 に発覚）。
#   統計量を揃えると評価が変わるので、**平均と最大の両方を1本の線で示す**形にした。
# ★GH #19: 目安は両手法とも有効範囲の下端。量は振幅にそろえる（ISPPA ∝ p² なので TUS は √）。
#   下端超えの ROI 割合は results/ti_roi_threshold_fraction_2026-10-20.txt（tTIS）・tus_safety_drive.py（TUS）。
# ★#20（2026-10-28）: TUS の目安 3 W/cm² は頭蓋なし（incident）の値だった（Lee 2021 表5）。
#   脳内の下端 120 kPa と ROI の |p| をそのまま比べる（results/tus_roi_pressure_2026-10-28.txt）。
fig, ax = base_axes(figsize=(7.6, 3.1))
rows = [
    ('tTIS', 0.2265 / 0.2,          0.3259 / 0.2,         'above it in 74.5 % of the ROI',      TTIS),
    ('TUS',  112.6 / 120.0,         313.0 / 120.0,        'above it in 41.1 % of the ROI',      TUS),
]
for i, (lab, mean, mx, frac, col) in enumerate(rows):
    ax.plot([mean, mx], [i, i], color=col, linewidth=2.5, solid_capstyle='round', zorder=2)
    ax.plot(mean, i, 'o', ms=11, color=SURFACE, markeredgecolor=col,
            markeredgewidth=2.5, zorder=3)          # 白抜き = ROI 平均
    ax.plot(mx, i, 'o', ms=11, color=col, zorder=3)  # 塗り   = ROI 最大
    ax.text(mean, i - 0.30, '%.0f %%' % (100 * mean), ha='center', va='bottom',
            fontsize=11, color=INK)
    ax.text(mx, i - 0.30, '%.0f %%' % (100 * mx), ha='center', va='bottom',
            fontsize=11, color=INK,
            bbox=dict(facecolor=SURFACE, edgecolor='none', pad=1))  # 1.0 の破線に重なっても読める
    ax.text(2.85, i, frac,
            ha='left', va='center', fontsize=10, color=INK2)
ax.set_yticks([0, 1]); ax.set_yticklabels([r[0] for r in rows])
ax.axvline(1.0, color=MUTED, linestyle='--', linewidth=1.2)
ax.annotate('lowest effective level', xy=(1.0, 1.0), xycoords=('data', 'axes fraction'),
            xytext=(0, 6), textcoords='offset points',
            ha='right', va='bottom', fontsize=9, color=INK2)
ax.set_xlim(0, 3.6)
ax.set_xticks([0.0, 0.5, 1.0, 1.5, 2.0, 2.5])   # データ域だけ目盛る（右は注記の場所）
ax.set_ylim(1.6, -0.6)
ax.set_xlabel('ROI amplitude / lowest effective level   (1.0 = 0.2 V/m; 120 kPa in situ)\n'
              'open circle = ROI mean · solid circle = ROI maximum (single strongest voxel)')
ax.set_title('tTIS exceeds the lowest effective level; TUS comes close',
             loc='left', fontsize=13, pad=22)
save(fig, 'fig3_dose_vs_threshold')

# ===== Fig.2 標的レベル以上が及ぶ脳体積（内訳つき）=====
fig, ax = base_axes(figsize=(7.6, 3.1))
labels = ['tTIS', 'TUS']
contig = [35.3, 6.4]                 # ROI と地続き
island = [35.9 - 35.3, 7.3 - 6.4]    # 飛び地
colors = [TTIS, TUS]
for i, (lab, c, isl, col) in enumerate(zip(labels, contig, island, colors)):
    ax.barh(i, c, height=0.5, color=col)
    ax.barh(i, isl, left=c, height=0.5, color=col, alpha=0.42,
            hatch='///', edgecolor=SURFACE, linewidth=2.0)
ax.set_yticks([0, 1])
ax.set_yticklabels(labels)
ax.axvline(4.186, color=MUTED, linestyle='--', linewidth=1.2)
ax.text(35.9 + 1.0, 0, '35.9 mL   8.6× ROI', va='center', ha='left', fontsize=12, color=INK)
ax.text(7.3 + 1.0, 1, '7.3 mL   1.7× ROI', va='center', ha='left', fontsize=12, color=INK)
ax.text(35.3 / 2, 0, '98 % contiguous', va='center', ha='center', fontsize=10, color='white')
ax.text(6.4 / 2, 1, '88 %', va='center', ha='center', fontsize=10, color='white')
ax.set_xlim(0, 50)
ax.set_xlabel('brain volume above the ROI mean [mL]\n'
              'solid = contiguous with the ROI · hatched = detached · dashed = ROI volume (4.19 mL)')
ax.set_title('TUS confines the field above the ROI mean; tTIS does not',
             loc='left', fontsize=13, pad=14)
ax.invert_yaxis()
save(fig, 'fig2_reach_volume')

print('figures -> %s' % OUT)
