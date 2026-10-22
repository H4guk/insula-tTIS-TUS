# -*- coding: utf-8 -*-
"""提出用 notebook の仮版を組み立て、各節の語数を検算する。"""
import json, re, os

ABSTRACT = """The insula is a candidate target for treating addiction, but its depth hinders non-invasive access. Temporal interference stimulation (tTIS) and transcranial ultrasound stimulation (TUS) both promise deep access, yet have been compared only qualitatively, with TUS judged far more focal. We compared them quantitatively on one head model, each in a standard configuration at its own safety limit. TUS did form a focus, but its amplitude reached only 42% of the lower end of its effective range; tTIS formed no focus yet exceeded that lower end (113%). Focality and reach trade off, and each method needs a different fix."""

METHODS = """tTIS and TUS are the two non-invasive candidates that can plausibly reach deep targets, so we compared them directly. Both were built on the same Yoon-sun v3.1 model inside one Sim4Life.lite project holding three simulations, so that any difference is attributable to the method rather than to the head. The target was a 10 mm sphere at the left insula (4.19 mL), identical in both. tTIS used montage I (T7-P7 at 2000 Hz, Fp1-Fp2 at 2010 Hz) scaled to 0.891 and 1.109 mA, giving the envelope 2*min(|E1|,|E2|); TUS used a single focused bowl (F# 1.21, 250 kHz) placed at T7 and driven until the global mechanical index reached 1.9. Head tissue was discretised at 1 mm, giving 12.3 and 11.1 million cells. The brain was defined identically for both methods as the twelve brain-parenchyma tissues of the model, selected by tissue name. Three quantities were compared: selectivity, defined as non-target over target mean; the brain volume at or above the target level; and the target amplitude relative to the lower end of each effective range, 0.2 V/m for tTIS [1] and 3 W/cm2 for TUS [2] (square-rooted). The integrated build reproduced separately built projects to within 1% on volume means."""

RESULTS = """Selectivity was 0.358 for tTIS and 0.193 for TUS, TUS remaining 1.6 to 1.85 times more selective under narrower brain definitions. On the insula plane the two fields differ in kind rather than in degree (Figure 1): the TUS field closes around the target, whereas the tTIS field decays monotonically from the electrode side without forming a maximum. The brain volume at or above the target level was 35.9 mL for tTIS, 8.6 times the ROI, against 7.3 mL for TUS, 1.7 times the ROI (Figure 2). Most of it was contiguous with the ROI, 98% for tTIS and 88% for TUS, so the tTIS field spreads as one large region around the target. The strongest point inside the brain was 4.6 times the target level for tTIS, on the surface of the medulla 60 mm away, whereas for TUS it was 2.8 times the target level and lay 10 mm from the target. At their safety limits the ROI mean reached 113% of the lower end for tTIS and 42% for TUS (65% and 18% at mid-range). Above the lower end lay 74.5% of the ROI for tTIS and 0.0% for TUS, one or two cells (Figure 3)."""

DISCUSSION = """The two methods fail in opposite ways. TUS keeps the target-level field mostly in one region around the target, 88% of it contiguous with the ROI, but the near-field pressure in the scalp fat reaches a mechanical index of 12.8 at reference drive, so the source cannot be driven hard enough for the focus to matter. tTIS is limited by the 2 mA current ceiling itself, yet its field at the target is closer to its effective range precisely because the insula sits on a monotonic decay from the electrodes rather than at a focus. The improvement paths therefore differ: multi-pair optimisation to create a focus for tTIS, and larger apertures or phased arrays to spare the scalp for TUS.

The insula is also the primary taste cortex [3]; multi-focal, temporally patterned stimulation could in future extend this line of work towards reproducing taste.

One model, a spherical ROI and uniform bone without CT limit these numbers. No statistical confidence interval follows from a single head; instead we measured reproducibility against a separate build, finding volume means within 1% and single cells varying by 6 to 7%."""

CONCLUSIONS = """On one head model, with each method at its own safety limit, three things follow. First, the difference in focality is not one of size but of whether a focus exists at all: TUS forms one, tTIS does not. Second, tTIS comes closer to its effective range: at the lower end of each range it covers 74.5% of the ROI against none for TUS, while at the midpoint neither reaches it. Third, focality and depth of reach trade off, giving a well focused but weak TUS against an unfocused but stronger tTIS, and because the limiting mechanism differs the two need different fixes."""

REFERENCES = """1. Inoue T, Otsuru N, Hirata A. Group-level and personalized optimization for the insula and hippocampus focal electric field in transcranial temporal interferential stimulation: a computational study. arXiv:2510.23290 (2025).

2. Sharif F, Harmer CJ, Klein-Flügge MC, Tan H. Novel NIBS in psychiatry: unveiling TUS and TI for research and treatment. Brain Neurosci Adv 9, 23982128251322241 (2025). doi:10.1177/23982128251322241

3. Avery JA, Liu AG, Ingeholm JE, Riddell CD, Gotts SJ, Martin A. Taste quality representation in the human brain. J Neurosci (2020). doi:10.1523/JNEUROSCI.1751-19.2019"""

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
CODE = '''# Target-level reach volume — the number behind Figures 2 and 3.
# Run inside the Sim4Life project that holds tTIS_LF1, tTIS_LF2 and TUS_250k.
# Full scripts: https://github.com/H4guk/insula-tTIS-TUS  (scripts/brain_by_name.py)
# brain3 = the twelve brain-parenchyma tissues, picked by material_name in Input.h5 (same for both methods).

import numpy as np, s4l_v1.document as document

FOCUS_MM, ROI_R_MM = np.array([99.1, 295.0, 1562.2]), 10.0

def reach(field3, brain3, roi3, vol3):
    """Volume at or above the target level, and how much of it touches the ROI."""
    w = vol3[roi3 & brain3]
    target = float((field3[roi3 & brain3] * w).sum() / w.sum())   # ROI volume mean
    ge = brain3 & (field3 >= target)                              # at or above it
    mL = lambda m: float(vol3[m].sum()) * 1e6
    return dict(target=target, v_ge=mL(ge), v_roi=mL(roi3),
                ratio=mL(ge) / mL(roi3), brain_pct=100 * mL(ge) / mL(brain3))

# tTIS: TI = 2*min(s1|E1|, s2|E2|); the current scaling cannot be skipped because
# min() is non-linear, so the two pairs must be scaled before they are combined.
# TUS: |p| straight from the acoustic solver.
# -> tTIS 35.9 mL (8.6x ROI, 3.45% of the brain) / TUS 7.3 mL (1.7x ROI, 0.70%)
'''

FIG_CAPS = [
    ("figures/fig1_field_slices.png",
     "**Figure 1** Field on the insula plane (X = 99.5 mm), both panels normalised to the target "
     "level (ROI volume mean). Black line: target level (1.0). Dashed circle: ROI (r = 10 mm). "
     "Grey line: brain outline; area outside the brain is dimmed. TUS closes a contour around the "
     "target; tTIS does not."),
    ("figures/fig3_reach_volume.png",
     "**Figure 2** Brain volume at or above the target level. Solid: contiguous with the ROI. "
     "Hatched: detached. Dashed line: ROI volume (4.19 mL). Almost all of the tTIS volume is "
     "contiguous with the target but 8.6 times the ROI; the TUS volume stays within 1.7 times."),
    ("figures/fig2_dose_vs_threshold.png",
     "**Figure 3** Target amplitude relative to the lower end of each method's effective range "
     "(1.0 = 0.2 V/m for tTIS; 3 W/cm2 ISPPA, converted to amplitude, for TUS). Open circle: ROI "
     "volume mean. Filled: ROI maximum, i.e. the single strongest cell. Only the strongest TUS "
     "cell reaches the lower end."),
]

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}

cells = [
    md("# Focality and reach trade off: tTIS versus TUS targeting the human insula\n"),
    md("### *by {NAME SURNAME}*\n\n*Submitted to S4L Student Competition 2026*\n"),
    md("## Abstract\n"), md(ABSTRACT + "\n"),
    md("## Methods\n"), md(METHODS + "\n"),
    md("## Results\n"), md(RESULTS + "\n"),
    md("## Discussion\n"), md(DISCUSSION + "\n"),
    md("## Conclusions\n"), md(CONCLUSIONS + "\n"),
    md("## References\n"), md(REFERENCES + "\n"),
    md("## Figures\n"),
]
for path, cap in FIG_CAPS:
    cells.append(md("![](%s)\n" % path))
    cells.append(md(cap + "\n"))
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
