# Revision notes

## Edition 1.1, 29 September 2026: origins and the 2025 ledger

Added at the author's request, to show the project's history from its origin in
`stock_stuff_06042025/10K_automator` (read only; nothing there was changed).

**New section.** §2, *Where it started: a study of excellence*: the May–June
2025 scripts, 11,741 filing readings of 2,175 companies, the 39-company
meta-analysis, the contrarian and options passes, and what EON inherited.
Sections 2–13 became 3–14; all cross-references were renumbered by script.

**New evidence.** The 2025 scores were recorded before their outcomes, so they
form a forward ledger. `origin-ledger-config.yaml` was written before the test;
`evaluate_origin_ledger.py` ran it. The author's own 14 Jul 2026 check
(`score_vs_realized_return_*`) is disclosed as a prior look.

| Ledger | n | Result |
|---|---:|---|
| Compounder score, 1Y | 1,766 | Spearman −0.14, p = 0.0001; top fifth −17.8 vs bottom +18.6 mean excess |
| Contrarian alpha, 1Y | 1,780 | Spearman +0.01, p = 0.71 |
| Options direction, 6M | 849 | calls − puts +2.8 percentile points, p = 0.54 |
| EON verdict vs compounder score | 1,054 | Spearman 0.05: nearly unrelated |

**What changed in the argument.** The abstract, §9.7 and the conclusion now say
the clean tests disagree: one positive, two null, one negative. New lessons
§10.7 (resemblance is not a forecast) and §10.8 (tell the model the date). New
Figure 9; Figure 3 now shows four designs from May 2025.

**Build.** 22 pages, reviewed visually; no overfull or underfull boxes.

**Also found.** The 2025 model stamped 1,916 of 1,919 analyses with a 2024
date, and 91 options readings suggested expiries in 2024: a measured case of a
model reasoning from its training-time present.

**Needs the author's confirmation.**
1. The origin's purpose as described: learn what excellent companies share, then
   score everyone else on resemblance.
2. That the 2025 outputs were never edited after they were written (file times
   agree, but only you can confirm).
3. Whether other origin experiments exist that should be mentioned, and whether
   `stock_stuff_06042025` (git history from April 2025) predates the scripts.
4. Whether `gemini-2.5-flash-preview-04-17` was the only model used in 2025.

---


## Edition 1, 29 September 2026

*Section numbers in this entry are Edition 1's; Edition 1.1 added §2 and
shifted §§2–13 to 3–14.*

First draft of *Tomorrow's Newspaper*, written to `BRIEF.md`. This file records
how the evidence was produced, every change to the protocol after it was fixed,
and what the author should confirm before the paper is shared.

### New evidence produced for this edition

| Check | Result |
|---|---|
| Unique readings | 6,653 company-years, 1,358 companies (6,973 stored rows) |
| Priced readings | 6,203, of 1,309 companies |
| Before cutoff, 1Y | +13.1 pts, 1,099 BUY / 657 SELL, permutation p = 0.0001 |
| Rank decomposition before | 11.5: 4.8 industry tilt, 6.6 within industry |
| After cutoff, 6M (primary) | +4.6 pts, p = 0.11 (vintage), 0.048 (industry) |
| After cutoff, 1Y mean | +14.9 pts ±23, p = 0.22 / 0.29 |
| After cutoff, 1Y rank | 5.9: 0.1 tilt, 5.9 within, p = 0.0051 (post-hoc statistic) |
| Anachronism probe | 0 early mentions; IRA in 300 readings, none early |
| High conviction, 1Y | +13.3 vs +11.9 for all readings |

### Changes to the protocol after it was fixed

All are recorded in `evaluation-config.yaml` with their reasons.

1. **Prices refreshed (v2).** v1 used `data/price_cache` (ends 6 Feb 2026). v2
   uses a Yahoo refresh of 29 Sep 2026, written only to this folder. v1 outputs
   are kept in `evaluation/v1-feb-cache/`. v1 gave +12.7 historical (p = 0.0001)
   and +1.0 / −0.1 after the cutoff at six months, on fewer post-cutoff readings.
2. **One-year post-cutoff test added.** Mirrors the historical primary exactly.
3. **Rank statistic added** after one reading (BW, +3,314%) was found to move
   the post-cutoff one-year mean by about 10 points. Applied to every sample.
4. **Anachronism probe added.** Exploratory; term list and dates in the config.

### Corrections made during the edition

- **Verdict parsing.** 462 readings began "Overall investment recommendation:"
  or similar and were first left unparsed. The fixed parser reads 6,519 of 6,653.
  No conclusion changed.
- **Conviction parsing.** The model writes conviction several ways; the first
  parser missed most. Now 6,296 of 6,411 dated readings parse. This overturned
  the February report's finding that high conviction doubles the spread.
- **Figure 8 median.** Updated from +1.5% to +0.3% after the verdict fix.
- **Decomposition rounding.** Text said 6.7 and 5.8 (differences of rounded
  numbers); the figure's 6.6 and 5.9 come from unrounded values and are correct.
- **Draft claims removed on checking.** A 65-second global serialisation lock
  (contradicted by bursts of ~190 readings an hour) and a guessed reason for the
  PDF detour.
- **Citation withdrawn.** Kim, Muhn and Nikolaev (arXiv 2407.17866) has been
  withdrawn by its authors and is not cited.

### Verified external facts

- Gemini 2.5 Flash knowledge cutoff "January 2025":
  ai.google.dev/gemini-api/docs/models/gemini-2.5-flash, checked 29 Sep 2026.
- arXiv 2309.17322, 2304.07619 and SSRN 4754678: titles and authors checked.
- The three journal DOIs (Loughran and McDonald; Cohen, Malloy and Nguyen;
  Harvey, Liu and Zhu) were not re-checked in this session.

### Needs the author's confirmation

These are the places where the draft infers intent or history from the code,
the way *The Ghost in the Gallery* was later checked against an interview.

1. **Author name.** "Gabriel George", taken from the ArtML paper and git history.
2. **Motives in first person.** "I wanted a reader that never tires", and why the
   workflow builder was set aside (§2). Inferred from the archive and commits.
3. **The three-design framing.** Is this how you would tell the history?
4. **Quota.** 25 keys at 20 requests a day comes from `eon/ai/api_config.py`.
   Confirm this was the operating limit for the February batch.
5. **Readings made without web search.** `use_google_search` defaults to off
   and nothing in `eon/` enables it. Confirm no run enabled it.
6. **The CSPP schema figures** (about 106 KB, 28 times a lens) are quoted from
   the workflow's own docstring, not re-measured.
7. **BW.** Worth checking its 2025–26 price series against a second source.
8. **Title.** *Tomorrow's Newspaper* refers to the thought experiment of trading
   with tomorrow's paper. Alternatives: *After the Cutoff*; *The Analyst Who
   Remembers*.

### Layout review

Built with Pandoc 3.12 and Tectonic 0.17 (both run from a temporary directory,
not installed). All 20 pages were reviewed visually. Changes from the ArtML
generator, all in `build_paper.py` and `paper-preamble.tex`: float barriers only
before §6, §9 and Appendix A; no forced page break before §8; lead-in paragraphs
no longer bound to block quotes; widow and club penalties 1,000. These removed
gaps of a third to three-quarters of a page. No overfull or underfull boxes.
PDF SHA-256 begins `f1fd9be8bc68d55a`.

### Not done in this edition

- No model was called and no reading was generated or changed.
- No factor controls, anonymised re-reading, or second price source.
