# -*- coding: utf-8 -*-
"""提出用 notebook の仮版を組み立て、各節の語数を検算する。"""
import base64, json, re, os

ABSTRACT = """The insula is a candidate target for addiction treatment, but its depth hinders non-invasive stimulation. Temporal interference stimulation (tTIS) and transcranial ultrasound stimulation (TUS) can both reach it. However, their electric and acoustic fields share no common unit. We therefore compared their focality and reach using dimensionless measures. To this end, we simulated each method under its standard safety limit on the Virtual Population model Yoon-sun's head. TUS formed a focus but reached only 42% of the lowest effective level. tTIS formed no focus but exceeded that level (113%). Within these limits, neither method achieves both focality and reach."""

METHODS = """Because electric and acoustic fields share no unit, the two methods were compared on dimensionless measures. Both were simulated in one Sim4Life.lite 9.6 project (ZMT), each at its standard safety limit. The head was the Virtual Population model Yoon-sun v3.1 (26-year-old female), discretised at 1 mm, using the IT'IS tissue database. The target was a sphere of 10 mm radius representing the left insula (4.19 mL). The brain was the model's parenchymal tissues, identical for both methods. tTIS applied 0.891 mA to T7-P7 at 2000 Hz and 1.109 mA to Fp1-Fp2 at 2010 Hz (2 mA total) [1]. Each pair was solved separately and scaled to its current before the non-linear beat envelope was taken, assuming aligned fields. TUS used a focused transducer (40 mm aperture, 250 kHz, six cells per wavelength) at T7, scaled to the mechanical-index safety limit of 1.9 [2]. Focality was measured by selectivity, the non-target mean divided by the target mean, and by the brain volume above the target mean. Reach was the target mean relative to the lowest effective level, 0.2 V/m for tTIS [1] and 3 W/cm2 for TUS [3] (as amplitude). Fields were analysed in Python and checked against separately built projects."""

RESULTS = """Selectivity was 0.358 for tTIS and 0.193 for TUS, TUS remaining 1.6 to 1.85 times more selective under narrower brain definitions. On the insula plane the two fields differ in kind (Figure 1): the TUS field closes around the target, whereas the tTIS field decays monotonically from the electrode side without forming a maximum. The brain volume at or above the target level was 35.9 mL for tTIS, 8.6 times the ROI, against 7.3 mL for TUS, 1.7 times the ROI (Figure 2). Most of it was contiguous with the ROI, 98% for tTIS and 88% for TUS. The strongest point inside the brain was 4.6 times the target level for tTIS, on the surface of the medulla 60 mm away, whereas for TUS it was 2.8 times the target level and lay 10 mm from the target. At their safety limits the ROI mean reached 113% of the lower end for tTIS and 42% for TUS. Above the lower end lay 74.5% of the ROI for tTIS but only one or two of 4,186 cells for TUS (Figure 3). At mid-range no ROI cell reached it for either method, the ROI maxima being 93% and 44%."""

DISCUSSION = """The two methods fail in opposite ways. TUS keeps the target-level field mostly in one region around the target, 88% of it contiguous with the ROI, but the near-field pressure in the scalp fat reaches a mechanical index of 12.2 at reference drive, three times the brain peak, so the source cannot be driven hard enough for the focus to matter. tTIS is limited by the 2 mA ceiling itself. If larger apertures or phased arrays brought the scalp peak down to the brain peak, TUS could be driven three times harder, giving a ROI mean of 4.7 W/cm2, 125% of the lower end. tTIS would need 3.1 mA to reach mid-range, so it must instead create a focus, as optimised montages have done within a cadaver's posterior insula [4].

The insula is also the primary taste cortex [5]; multi-focal, temporally patterned stimulation could in future extend this line of work towards reproducing taste.

One model, a spherical ROI and uniform bone without CT limit these numbers. No statistical confidence interval follows from a single head; instead we measured reproducibility against a separate build, finding volume means within 1% and single cells varying by 6 to 7%."""

CONCLUSIONS = """On one head model, with each method in a standard configuration at its own safety limit, three things follow. First, the difference in focality is not one of size but of whether a focus exists at all: TUS forms one, tTIS does not. Second, tTIS comes closer to its effective range, the intensities at which neuromodulation has been reported rather than a firing threshold: at the lower end of each range it covers 74.5% of the ROI against one or two cells for TUS, while at mid-range neither reaches it in any cell. Third, focality and depth of reach trade off, giving a well focused but weak TUS against an unfocused but stronger tTIS, and because the limiting mechanism differs the two need different fixes."""

REFERENCES = """1. Inoue T, Otsuru N, Hirata A. Group-level and personalized optimization for the insula and hippocampus focal electric field in transcranial temporal interferential stimulation: a computational study. arXiv:2510.23290 (2025).

2. Aubry J-F, Attali D, Schafer ME, et al. ITRUSST consensus on biophysical safety for transcranial ultrasound stimulation. Brain Stimul 18(6), 1896-1905 (2025). doi:10.1016/j.brs.2025.10.007

3. Sharif F, Harmer CJ, Klein-Flügge MC, Tan H. Novel NIBS in psychiatry: unveiling TUS and TI for research and treatment. Brain Neurosci Adv 9, 23982128251322241 (2025). doi:10.1177/23982128251322241

4. Fathi Y, Boutachkourt A, Joris V, Onofrj V, Dricot L, Behets C, Hanseeuw B, Liberati G. Focal and steerable temporal interference stimulation of the human left posterior insula: a proof-of-concept validation using intracranial recordings in a human cadaver. Bioengineering 13, 1050 (2026). doi:10.3390/bioengineering13091050

5. Avery JA, Liu AG, Ingeholm JE, Riddell CD, Gotts SJ, Martin A. Taste quality representation in the human brain. J Neurosci (2020). doi:10.1523/JNEUROSCI.1751-19.2019"""

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
     "volume mean. Filled: ROI maximum, i.e. the single strongest cell. Only one or two of the "
     "4,186 TUS ROI cells reach the lower end."),
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
