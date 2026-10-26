"""図1（Sim4Life 内でしか描けない）の画像の文字だけを、新しい用語に差し替える。
場のデータには触れない。元の画像の上に、地の色の四角で古い文字を隠し、同じ位置・同じ書体で新しい文字を書く。
入力 = 引数1（元の PNG）、出力 = 引数2。
2026-10-27（#20）: 本文の用語（ROI mean）にそろえるために使った。元の PNG は `git show 233fc29:docs/figures/fig1_field_slices.png`。
Sim4Life で make_fig1_slices.py を流し直せば、この差し替えは要らない（ラベルは同じに直してある）。"""
import sys, os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/claude-501/mpl')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
src, dst = sys.argv[1], sys.argv[2]
SURFACE = '#fcfcfb'; INK2 = '#52514e'; MUTED = '#8a8983'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.labelcolor': INK2,
                     'ytick.color': INK2, 'savefig.facecolor': SURFACE, 'figure.facecolor': SURFACE})
img = plt.imread(src)
h, w = img.shape[:2]
fig = plt.figure(figsize=(w / 200, h / 200), dpi=200)
bg = fig.add_axes([0, 0, 1, 1]); bg.imshow(img); bg.axis('off')
# 古い文字を隠す（下の注記・カラーバーのラベル）
fig.add_artist(Rectangle((0, 0), 1, 0.075, transform=fig.transFigure, color=SURFACE, zorder=5))
fig.add_artist(Rectangle((0.927, 0.12), 0.073, 0.80, transform=fig.transFigure, color=SURFACE, zorder=5))
# 新しい文字（make_fig1_slices.py と同じ位置・大きさ）
fig.text(0.02, 0.03, 'dashed circle = ROI (r = 10 mm) · black line = ROI-mean contour (1.0) · '
         'grey line = brain outline · area outside the brain is dimmed', fontsize=9, color=INK2, zorder=6)
cax = fig.add_axes([0.875, 0.20, 0.018, 0.66], zorder=6); cax.patch.set_alpha(0)
cax.set_ylim(0, 4); cax.set_yticks([0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4])
cax.yaxis.tick_right(); cax.yaxis.set_label_position('right'); cax.set_xticks([])
for t in cax.get_yticklabels(): t.set_alpha(0)
cax.tick_params(axis='y', length=0)
for sp in cax.spines.values(): sp.set_visible(False)
cax.set_ylabel('field strength / ROI mean', color=INK2, labelpad=12)
fig.savefig(dst, dpi=200)
print('wrote', dst)
