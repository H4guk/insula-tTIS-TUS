# -*- coding: utf-8 -*-
"""提出用 notebook の仮版を組み立て、各節の語数を検算する。"""
import base64, json, re, os

ABSTRACT = """The insula is a candidate target for addiction treatment, but its depth hinders non-invasive stimulation. Temporal interference stimulation (tTIS) and transcranial ultrasound stimulation (TUS) can both reach it. However, they have not been compared in the insula, and their electric and acoustic fields share no common unit. We therefore compared their focality and reach using dimensionless measures. We simulated each method at its safety limit on the Virtual Population model Yoon-sun. TUS formed a focus but reached only 42% of the lowest effective level. tTIS formed no focus but exceeded that level (113%). Within these limits, neither method achieved both."""

METHODS = """Electric and acoustic fields share no unit, so both methods were compared on dimensionless measures. Both were simulated in one Sim4Life.lite 9.6 project. The head, Virtual Population model Yoon-sun v3.1, was discretised at 1 mm and assigned IT'IS database properties. The region of interest (ROI) was a 10 mm-radius sphere representing the left insula. The brain was the model's parenchymal tissues.

tTIS applied 0.891 mA to T7-P7 at 2000 Hz and 1.109 mA to Fp1-Fp2 at 2010 Hz, totalling the standard 2 mA limit [1]. Its beat envelope was taken after scaling, assuming aligned fields. TUS used a 250 kHz, 40 mm-aperture focused transducer at T7, scaled to the mechanical-index safety limit of 1.9 [2].

Focality was judged by whether the ROI-mean contour enclosed the ROI. It was quantified by selectivity, the non-target mean divided by the ROI mean, and the brain volume above that mean. Reach was the ROI mean relative to the lowest effective level, 0.2 V/m for tTIS and 3 W/cm2 for TUS converted to amplitude [1,3], and the ROI fraction above it. At the neuron level, firing thresholds in and outside the ROI were titrated with Sim4Life's neuron solver for tTIS and MorphoSONIC for TUS [4]."""

RESULTS = """The two methods were compared at their safety limits for focality (Figures 1 and 2) and reach (Figure 3). On the insula plane, the contour at the ROI mean did not close around the ROI for tTIS but did for TUS (Figure 1). Selectivity was 0.358 for tTIS and 0.193 for TUS, roughly half. The brain volume above the ROI mean was as much as 35.9 mL for tTIS, 8.6 times the ROI, but only 7.3 mL for TUS, 1.7 times the ROI (Figure 2). The ROI mean reached 113% of the lowest effective level for tTIS but only 42% for TUS (Figure 3). tTIS exceeded this level in 74.5% of the ROI, whereas TUS did so in only one or two of its 4,186 cells. At the neuron level, myelinated (MRG) and unmyelinated (Sundt) ROI axons fired at 0.43 and 0.10 times the TUS safety limit, but needed 42 and 3,040 times the tTIS limit. Off-target axons needed 11 times the ROI threshold for TUS but only 0.23 to 0.30 times for tTIS. In summary, tTIS reached the effective level without forming a focus, whereas TUS formed a focus and, at the neuron level, fired the ROI selectively."""

DISCUSSION = """At their safety limits, neither the TUS nor the tTIS field targeted the insula with both focality and reach: TUS confined its field to the ROI but stayed below the lowest effective level, whereas tTIS exceeded that level without a focus. At the neuron level, TUS fired the ROI axons, whereas tTIS fired none. TUS stayed more selective on both yardsticks, whereas the method reaching the ROI switched.

These findings agree with earlier work and explain each method's limit. tTIS selectivity (0.36) is close to the 0.4 reported for this insula montage [1]. As tTIS was limited by the current itself, optimised montages could improve its focality, as in a cadaver insula [5]. For TUS, the lower threshold of unmyelinated fibres also matches MorphoSONIC predictions [4]. As TUS was limited by scalp near-field pressure exceeding the brain peak, phased arrays could improve its reach [6].

This study has three limitations. First, one head model gives no confidence interval. Second, TUS neuron results rest on MorphoSONIC, which models only intramembrane cavitation and predicts thresholds far below human-study intensities [3]. Third, the axons were peripheral fibres, not cortical pyramidal neurons [7]. Therefore, comparisons across more head models using pyramidal neurons are needed."""

CONCLUSIONS = """On one head model, with each method in a standard configuration at its own safety limit, three things follow. First, the difference in focality is not one of size but of whether a focus exists at all: TUS forms one, tTIS does not. Second, tTIS comes closer to its effective range, the intensities at which neuromodulation has been reported rather than a firing threshold: at the lower end of each range it covers 74.5% of the ROI against one or two cells for TUS, while at mid-range neither reaches it in any cell. Third, focality and depth of reach trade off, giving a well focused but weak TUS against an unfocused but stronger tTIS, and because the limiting mechanism differs the two need different fixes."""

REFERENCES = """1. Inoue T, Otsuru N, Hirata A.  
Group-level and personalized optimization for the insula and hippocampus focal electric field in transcranial temporal interferential stimulation: a computational study.  
arXiv:2510.23290 (2025).

2. Aubry JF, Attali D, Schafer ME, et al.  
ITRUSST consensus on biophysical safety for transcranial ultrasound stimulation.  
Brain Stimul., 18:1896–1905 (2025). doi:10.1016/j.brs.2025.10.007

3. Sharif F, Harmer CJ, Klein-Flügge MC, Tan H.  
Novel NIBS in psychiatry: unveiling TUS and TI for research and treatment.  
Brain Neurosci Adv., 9:23982128251322241 (2025). doi:10.1177/23982128251322241

4. Lemaire T, Vicari E, Neufeld E, Kuster N, Micera S.  
MorphoSONIC: a morphologically structured intramembrane cavitation model reveals fiber-specific neuromodulation by ultrasound.  
iScience, 24:103085 (2021). doi:10.1016/j.isci.2021.103085

5. Fathi Y, Boutachkourt A, Joris V, Onofrj V, Dricot L, Behets C, Hanseeuw B, Liberati G.  
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
     "**Figure 1** Field on the insula plane (X = 99.5 mm), both panels normalised to the ROI mean. "
     "Black line: ROI-mean contour (1.0). Dashed circle: ROI (r = 10 mm). Grey line: brain outline; "
     "area outside the brain is dimmed. The contour encloses the ROI for TUS but not for tTIS."),
    ("figures/fig3_reach_volume.png",
     "**Figure 2** Brain volume above the ROI mean. Solid: contiguous with the ROI. Hatched: detached. "
     "Dashed line: ROI volume (4.19 mL). 98% of the tTIS volume and 88% of the TUS volume are contiguous "
     "with the ROI, so the tTIS field spreads as one large region around it, 8.6 times the ROI; the TUS "
     "volume stays within 1.7 times."),
    ("figures/fig2_dose_vs_threshold.png",
     "**Figure 3** ROI amplitude relative to the lowest effective level (1.0 = 0.2 V/m for tTIS; "
     "3 W/cm2 ISPPA for TUS, converted to amplitude). Open circle: ROI mean. Filled: ROI maximum, the "
     "single strongest cell. Only one or two of the 4,186 TUS ROI cells exceed the lowest effective level."),
]

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}

cells = [
    md("# Focus without reach, reach without focus: TUS and tTIS at their safety limits in the human insula\n"),
    md("### *by {NAME SURNAME}*\n\n*Submitted to S4L Student Competition 2026*\n"),
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

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'submission_draft.ipynb')
with open(out, 'w') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print('')
print('wrote %s  (%d cells)' % (out, len(cells)))
