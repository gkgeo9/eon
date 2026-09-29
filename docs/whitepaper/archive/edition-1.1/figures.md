# Figures for *Tomorrow's Newspaper*

Nine figures, numbered in order of first appearance. Each argues one claim; the
title is the claim, the subtitle the scope, the footer the source. The Markdown
paper is the editorial source; LaTeX is generated from it.

| Figure | Argument | Location | Vector preview |
|---|---|---|---|
| 1 | One filing becomes one countable verdict | §1.1 | [One reading](figures/01-one-reading.svg) |
| 2 | The quota is the clock | §4.2 | [Quota clock](figures/02-quota-clock.svg) |
| 3 | Fix the question, then read everything | §5 | [Four designs](figures/03-three-designs.svg) |
| 4 | Half of every vintage is HOLD | §6 | [Verdict mix](figures/04-verdict-mix.svg) |
| 5 | Most outcomes predate the model's cutoff | §7.2 | [Cutoff timeline](figures/05-cutoff-timeline.svg) |
| 6 | After the cutoff: same sign, wider intervals | §9.1 | [Spread by horizon](figures/06-horizons.svg) |
| 7 | The cutoff removed the industry tilt, not the rest | §9.2 | [Decomposition](figures/07-decomposition.svg) |
| 8 | One stock can decide a mean | §9.3 | [Tails](figures/08-tails.svg) |
| 9 | The clean tests do not agree | §9.5 | [Forward tests](figures/09-forward-tests.svg) |

Each figure is rendered as SVG (Markdown), PDF (LaTeX) and 240-dpi PNG (review).
House style: 6.27-inch width, DejaVu Sans, text at least 9 pt, neutral greys,
teal `#126B70` for the subject, rust `#A5472D` for cutoffs and qualifications.
Meaning never depends on hue alone.

## Rebuild

```sh
python docs/whitepaper/prepare_figure_data.py   # database facts -> figure-data/
python docs/whitepaper/render_figures.py        # figure-data/ -> figures/
```

Rendering reads only `figure-data/evidence.json` and `figure-config.yaml`. It
never opens the database, calls a model, or touches the network.

## Evidence and interpretation

**Figure 1.** The first stored reading (row 1): Apple, fiscal 2025, filed 31
October 2025. Chosen because it is first, not because it is typical or right.
It postdates the cutoff and has no outcome yet. Field lists are paraphrased
labels of the 11 fields per lens; verdict text is quoted.

**Figure 2.** Readings of batch `all_comp_08022026`, bucketed by hour (UTC).
Quota days start at 08:00 UTC, midnight Pacific in February. Per-day totals are
printed above the bars. The day boundary is an approximation of the provider's
reset, so a day can show slightly more than 500.

**Figure 3.** The origin bar spans the first dated reading (3 May 2025) to the
options pass (4 June 2025), from file modification times in the origin project.
Later milestone dates are read from git by `prepare_figure_data.py`; workflow
counts come from `data/archive/fintel.db`; batch spans from stored reading
timestamps. The Design 3 bar spans the CSPP split (20 May 2026) to the
anchored-score commit (4 June 2026). Bar length is calendar time only; the file
name keeps its earlier `three-designs` stem.

**Figure 4.** Dated readings with a parsed verdict, by fiscal-year label, for
vintages with at least 400. Shares are of each vintage. FY2025 coverage is
partial because the batch ran in February 2026.

**Figure 5.** Median entry date per vintage plus one year; whiskers are the
10th–90th percentile of entry dates. Colour marks whether the median window
closes before the cutoff, straddles it, or starts after it; the evaluation
itself classifies each reading individually. FY2025's early whisker reflects
fiscal-year labels that run ahead of the calendar. The dashed outline is the
part of a window after the price data ends.

**Figure 6.** Point estimates with 1.96 Welch standard errors, for display. The
tests in the paper are permutation tests. The post-cutoff one-year mean interval
is clipped at 45 in panel A; the arrow marks the clip.

**Figure 7.** From the within-vintage-and-industry rank permutation test. The
hatched part is the null distribution's mean (the industry tilt), the teal part
the observed spread minus it. Totals differ slightly from Figure 6 because
readings alone in their industry block are dropped from the permutation test.
The rank statistic was added after inspecting the tails; see
`evaluation-config.yaml`.

**Figure 8.** All post-cutoff readings with a one-year outcome, by leg, jittered
vertically. The x-axis is symmetric-log, linear between −100% and +100%. BW's
return is Yahoo Finance's adjusted series and has not been checked against a
second source.

**Figure 9.** One point per clean test, each a high-minus-low difference in
mean within-sample percentile rank of excess return over SPY, with the central
95% of 10,000 within-industry shuffles. EON: BUY minus SELL, one year, filed
after the cutoff (the post-hoc rank statistic). 2025 compounder and contrarian
scores: top minus bottom fifth, one year from the reading. 2025 options: calls
minus puts, six months. The four tests differ in score, timing and sample and
are shown on one axis for orientation, not pooled. About 37% of ledger companies
lack an industry label and form one block. Source: both results files.

## Figures deliberately not made

- **Equity curves and "growth of $10,000".** They hide sample size, dependence
  between readings, and the look-ahead problem this paper is about.
- **A per-stock "hits" gallery.** Chosen examples would advertise the verdicts;
  Figure 8 shows every post-cutoff reading instead.
- **A league table of the three lenses.** Not tested under the protocol, so a
  chart would imply a finding that does not exist.
- **A pipeline architecture diagram.** Figure 1 shows the part that matters.
