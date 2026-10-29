# -*- coding: utf-8 -*-
"""提出用 notebook の仮版を組み立て、各節の語数を検算する。"""
import base64, json, re, os

ABSTRACT = """The insula is a candidate target for addiction treatment, but its depth hinders non-invasive stimulation. Temporal interference stimulation (tTIS) and transcranial ultrasound stimulation (TUS) can both reach it. However, they have not been compared in the insula, and their electric and acoustic fields share no common unit. This study therefore compared their focality and reach using dimensionless measures. Each method was simulated at its safety limit on the Virtual Population model Yoon-sun. tTIS exceeded the lowest effective level (113%), whereas TUS reached 85%. TUS was nevertheless more focal and fired ROI axons selectively at the neuron level."""

METHODS = """Both methods were simulated in one Sim4Life.lite 9.6 project on Virtual Population model Yoon-sun v3.1. It was discretised at 1 mm with IT'IS properties. The region of interest (ROI) was a 10 mm-radius sphere representing the left insula. The brain comprised the model's parenchymal tissues.

tTIS applied 0.891 mA to T7-P7 at 2000 Hz and 1.109 mA to Fp1-Fp2 at 2010 Hz, totalling the standard 2 mA limit [1]. Its beat envelope was computed after scaling, assuming aligned fields. TUS used a 250 kHz, 64 mm-aperture, 80 mm-curvature focused transducer aimed from T7 and water-coupled outside the head. Its mechanical index, including skull, was scaled to the 1.9 safety limit [2].

Focality was judged by whether the ROI-mean contour enclosed the ROI. It was also quantified by selectivity (non-target mean/ROI mean) and the brain volume above the ROI mean. Reach was the ROI mean relative to the lowest effective level and the ROI fraction above it. This level was 0.2 V/m for tTIS [1] and 120 kPa in situ for TUS [3]. Firing thresholds of myelinated (MRG) and unmyelinated (Sundt) axons in and outside the ROI were also titrated with Sim4Life's neuron solver for tTIS and MorphoSONIC for TUS [4]."""

RESULTS = """The two methods were compared at their safety limits for focality (Figures 1 and 2) and reach (Figure 3). On the insula plane, the ROI-mean contour enclosed the ROI for neither method (Figure 1). Selectivity was 0.358 for tTIS and 0.224 for TUS. The brain volume above the ROI mean was 35.9 mL for tTIS, 8.6 times the ROI, and 18.2 mL for TUS, 4.3 times (Figure 2). The ROI mean reached 113% of the lowest effective level for tTIS and 85% for TUS (Figure 3). tTIS exceeded this level in 74.5% of the ROI, and TUS in 34.8%. At the neuron level, MRG and Sundt ROI axons fired at 0.55 and 0.15 times the TUS safety-limit amplitude. For tTIS, they needed 42 and 3040 times its limit. Off-target axons needed 12 and 11 times the ROI threshold for TUS but only 0.23 and 0.30 times for tTIS. In summary, neither method enclosed the ROI, but TUS was more focal on selectivity and volume. In reach, tTIS exceeded the effective level, whereas TUS approached it. TUS also fired the ROI axons selectively at the neuron level."""

DISCUSSION = """At their safety limits, TUS was more focal than tTIS and approached the lowest effective level in reach. tTIS had lower focality, but its field-level reach exceeded that level. At the neuron level, however, TUS fired the ROI axons selectively, whereas tTIS fired none. The levels differ because the effective level reflects modulation, not axonal firing.

The tTIS results agree with the existing literature, and the results of both methods explain each method's limit. tTIS selectivity (0.36) is close to the 0.4 reported for this insula montage [1]. As tTIS was limited by its 2 mA current limit, optimised montages could improve its focality, as in a cadaver insula [5]. As TUS was limited by a pressure peak at the skull exceeding the brain peak, phased arrays could improve its reach [6].

This study has three limitations. First, one head model gives no confidence interval. Second, the TUS effective level rests on skull-derated estimates [3], and MorphoSONIC models only intramembrane cavitation. Third, the axons were peripheral fibres, not cortical pyramidal neurons [7]. Therefore, comparisons across more head models using pyramidal neurons are required."""

CONCLUSIONS = """tTIS and TUS have not been compared in the insula, and their fields share no common unit. This study therefore compared their focality and reach using dimensionless measures. At their safety limits, TUS was more focal on selectivity and volume and approached the lowest effective level in reach. At the neuron level, only TUS fired the ROI axons. tTIS exceeded the effective level with lower focality, and its off-target axons fired first as the drive increased beyond the safety limit. In this model, TUS therefore targeted the insula better than tTIS. Since these findings rest on one head model and peripheral axons, they should be tested on more heads and pyramidal neurons. Phased arrays for TUS and optimised montages for tTIS may then show whether either method fully achieves both."""

REFERENCES = """1. Inoue T, Otsuru N, Hirata A.  
Group-level and personalized optimization for the insula and hippocampus focal electric field in transcranial temporal interferential stimulation: a computational study.  
Comput Biol Med., 200:111374 (2026). doi:10.1016/j.compbiomed.2025.111374

2. Aubry JF, Attali D, Schafer ME, et al.  
ITRUSST consensus on biophysical safety for transcranial ultrasound stimulation.  
Brain Stimul., 18:1896–1905 (2025). doi:10.1016/j.brs.2025.10.007

3. Lee W, Weisholtz DS, Strangman GE, Yoo SS.  
Safety review and perspectives of transcranial focused ultrasound brain stimulation.  
Brain Neurorehabil., 14:e4 (2021). doi:10.12786/bn.2021.14.e4

4. Lemaire T, Vicari E, Neufeld E, Kuster N, Micera S.  
MorphoSONIC: a morphologically structured intramembrane cavitation model reveals fiber-specific neuromodulation by ultrasound.  
iScience, 24:103085 (2021). doi:10.1016/j.isci.2021.103085

5. Fathi Y, Boutachkourt A, Joris V, et al.  
Focal and steerable temporal interference stimulation of the human left posterior insula: a proof-of-concept validation using intracranial recordings in a human cadaver.  
Bioengineering, 13:1050 (2026). doi:10.3390/bioengineering13091050

6. Martin E, Roberts M, Grigoras IF, et al.  
Ultrasound system for precise neuromodulation of human deep brain circuits.  
Nat Commun., 16:8024 (2025). doi:10.1038/s41467-025-63020-1

7. Wang B, Aberra AS, Grill WM, Peterchev AV.  
Responses of model cortical neurons to temporal interference stimulation and related transcranial alternating current stimulation modalities.  
J Neural Eng., 19:066047 (2022). doi:10.1088/1741-2552/acab30"""

def wc(t):
    t = re.sub(r'\s+', ' ', t).strip()
    return len(t.split(' '))

LIMITS = [('Abstract', ABSTRACT, 100), ('Methods', METHODS, 200), ('Results', RESULTS, 200),
          ('Discussion', DISCUSSION, 200), ('Conclusions', CONCLUSIONS, 150)]
print('%-12s %6s %6s  %s' % ('section', 'words', 'limit', 'status'))
total = 0
for name, txt, lim in LIMITS:
    n = wc(txt); total += n
    print('%-12s %6d %6d  %s' % (name, n, lim, 'OK' if n <= lim else '*** OVER by %d ***' % (n - lim)))
print('%-12s %6d %6d' % ('TOTAL', total, 850))

# ============ notebook を組み立てる ============

FIG_CAPS = [
    ("figures/fig1_field_slices.png",
     "**Figure 1** Field distributions on the insula plane (*X* = 99.5 mm). The left panel shows the tTIS "
     "beat-envelope amplitude and the right panel the TUS pressure amplitude, both normalised to the ROI mean. "
     "The solid black line is the ROI-mean contour (1.0), the dashed circle is the ROI (*r* = 10 mm) and the "
     "grey line is the brain outline; the area outside the brain is dimmed. The contour encloses the ROI for "
     "neither method: it spreads widely for tTIS, whereas for TUS it forms an elongated band along the beam."),
    ("figures/fig2_reach_volume.png",
     "**Figure 2** Brain volume above the ROI mean for each method. Solid bars are the parts contiguous with "
     "the ROI, hatched bars the detached parts, and the dashed line marks the ROI volume (4.19 mL). As 98% of "
     "the tTIS volume and 73% of the TUS volume are contiguous with the ROI, the tTIS field spreads as one "
     "large region around it, 8.6 times the ROI, whereas the TUS volume stays within 4.3 times."),
    ("figures/fig3_dose_vs_threshold.png",
     "**Figure 3** ROI amplitude relative to the lowest effective level. The level (1.0, dashed line) is "
     "0.2 V/m for tTIS and 120 kPa in situ for TUS. Open circles show the ROI mean and solid circles the ROI "
     "maximum, the single strongest voxel. The values on the right give the fraction of the ROI above this level."),
]

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}

cells = [
    md("# Focality and Reach of Transcranial Ultrasound Versus Temporal Interference Stimulation of the Human Insula Within Safety Limits: A Computational Study\n"),
    md("### *by Ryo Shimbo*\n\n*Submitted to S4L Student Competition 2026*\n"),
    md("## Abstract\n"), md(ABSTRACT + "\n"),
    md("## Methods\n"), md(METHODS + "\n"),
    md("## Results\n"), md(RESULTS + "\n"),
    md("## Discussion\n"), md(DISCUSSION + "\n"),
    md("## Conclusions\n"), md(CONCLUSIONS + "\n"),
    md("## References\n"), md(REFERENCES + "\n"),
    md("## Figures\n"),
]
HERE = os.path.dirname(os.path.abspath(__file__))
# 図は notebook に埋め込む（添付）。notebook だけ渡しても図が出る
for path, cap in FIG_CAPS:
    fn = os.path.basename(path)
    with open(os.path.join(HERE, '..', path), 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    cell = md("![%s](attachment:%s)\n" % (fn, fn))
    cell["attachments"] = {fn: {"image/png": b64}}
    cells.append(cell)
    cells.append(md(cap + "\n"))
# 末尾の code cell は scripts/ の実物をそのまま入れる（notebook と repo で食い違わないように）
with open(os.path.join(HERE, '..', '..', 'scripts', 'submission_code_cell.py')) as f:
    CODE = f.read()
cells.append({"cell_type": "code", "execution_count": None, "metadata": {},
              "outputs": [], "source": CODE.splitlines(keepends=True)})

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Sim4Life", "language": "python", "name": "python3"},
                   "language_info": {"name": "python", "version": "3.11.9"}},
      "nbformat": 4, "nbformat_minor": 5}

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Shimbo_insula_tTIS_TUS.ipynb')
with open(out, 'w') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print('')
print('wrote %s  (%d cells)' % (out, len(cells)))
