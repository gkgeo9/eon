## People-free artwork update — 30 September 2026

The author requested no people in any illustration. The speaker and the
workshop worker were removed using the built-in image generation tool;
all other artwork remains unchanged. The Part III caption and alt text now
describe an unattended lectern. Exact edit prompts and asset provenance are
in `figures/art/manifest.json`. Earlier briefs and revision notes are historical;
they do not override the current no-people requirement.

# Edition 4.1 — response to criticisms

Applied the statistical, editorial, typographic and figure corrections in
`criticism-response.md`. Preserved the author's preferred six illustrations,
editing only the cover and workshop to remove the optical devices. Added
formal front matter, a detailed contents page, a list of figures, three
numbered tables and a sample-reconciliation table. The rebuilt PDF has 32
pages, 17 evidence figures and six illustrations. Source numerical results
and evaluation protocols are unchanged. Public contact and author disclosure
information remain pending; historical quota approval is not established.

Previous edition: `archive/edition-4-before-review-fixes/`.

# Revision notes

## Edition 4 — illustrated revision (30 September 2026)

**Delivered:** 30 pages, seventeen numbered evidence figures and six editorial
illustrations. This adds one page to the collaborator's 29-page journey edition.
The three-part structure and its emphasis on building EON are retained.

**Artwork.** Generated with the built-in image generation tool: a full-page
reading-room cover, workshop / evidence-table / narrator part openers, the
recorder-and-compass spot, and the closing envelope. The workshop was refined
to show 25 hooks and a near-midnight clock; the closing card was refined to
read OPEN OCTOBER 2027. Native raster masters, full prompts, revision prompts,
selected source paths and hashes are in `figures/art/manifest.json`. No
numerical results are drawn by the image model. Original optional briefs
remain in `graphics.md`, with the delivered selection clearly identified.

**Diagrams and plots.** Figure 3 now traces acquisition, reading and storage
beneath the two interfaces and their shared service. Figure 7 separates
atomic work claims, serialized SQLite writes and the two table families.
Figure 5 no longer draws execution bars underneath its quota-wait interval.
Figure 15 uses compact dots and explicit percentile labels, with the same
values; Figure 16 fits its cards more economically. Light lineage cards and
amber/coral numeric cards use darker text for contrast.

**Text and navigation.** Captions and references match the revised diagrams.
All seventeen evidence figures have internal PDF links. Illustrations have
alt text in the Markdown, unnumbered explanatory captions and a generation
credit in Appendix C. They are explicitly metaphors. Figure placement now
keeps most evidence at its argument; three opener figures may float within
bounded sections. The ending stays together with its illustration.

**Precision corrections encountered during integration.** The semaphore is
process-local; per-key file locks coordinate processes on the same machine.
SQLite's retry helper permits ten attempts, not ten retries after the first
attempt. Checkpoints and leases reduce repeated work; they do not guarantee
exactly-once calls or prove that saved files were never changed. The provider's
stated cutoff is not an independent knowledge audit, and late readings remain
retrospective. The options test concerns absolute excess returns, not measured
options profitability or realised volatility. These clarifications change no
stored observation, price, evaluation result or numerical test.

**Verification.** Seven numerical check groups passed. Publication checks
verified figure order 1–17, five interior illustration blocks plus the cover,
all artwork hashes, matching Markdown/LaTeX provenance, 41 resolved internal
PDF links reaching all seventeen figures, and text within page bounds.
The final TeX log has no overfull/underfull boxes, missing glyphs or warnings.
All pages were reviewed as contact sheets, with full-size checks of the cover,
part openers, revised diagrams, options page and ending. See
`publication-validation.json` and `layout-review.json`.

The previous publication is preserved in `archive/edition-4-before-illustrations/`.
Production databases and the original project were not modified. Earlier
revision notes below describe their respective editions, not this layout.

---

## Edition 4 — the journey edition (30 September 2026)

At the author's request, the paper now spends about half its length on how EON
was built and why, with the evaluation as a shorter middle part. It is intended
as the project's only long-form record.

**Structure.** Prologue (§1); Part I, building the reader (§§2–6: the 2025
workshop, standardized_sec_ai, Fintel, EON's five layers, workflows); Part II,
what it read (§§7–8); Part III, what it taught (§§9–12). Body about 7,000
words; 29 pages; 17 figures.

**New research, all read-only.**
- Lineage recovered: `stock_stuff_06042025/standardized_sec_ai` (Oct–Nov 2025;
  Pydantic structured output; `ppee.py`, source of the three-lens prompt) sits
  between the 2025 scripts and Fintel.
- Design history from git and recovered documents: the threading-lock
  concurrency bug, the machine-wide file lock with its 65-second pause, per-key
  locks with a semaphore, the double-counting commit that halved capacity,
  the v014 double-save fix, `fintel.db.corrupted`, the multi-OS pull request.
- Pipeline measurements (`measure_pipeline.py`): median 10-K 141 pages,
  ~394,000 characters (~99k tokens); raw HTML 5.6–19.6× its visible text;
  1,170–3,888 inline XBRL tags; Kraft Heinz 2022's hidden XBRL header larger
  than its visible report. This answers "why PDF, not HTML or XML".
- Throughput: peak 189 readings an hour; active in only 62 hours of 13 days.
- Inventory: 29,375 stored model answers across all versions.
- A second dated ledger, EON's own: the February 2026 options scan (1,365
  companies graded). Direction: no skill (calls − puts −2.9 percentile points,
  p = 0.62). Magnitude: yes (asymmetry score vs absolute move, Spearman 0.12,
  p = 0.0001; straddle vs no edge, p = 0.031). Rules in `stories-config.yaml`,
  written before the test ran.
- Model shortcomings measured: 62% put bias vs 2% call bias; 24% of compounder
  scores exactly 68; success factors credited to 100% of great companies.
- The sealed bet (`make_sealed_ledger.py`): 1,257 verdicts frozen with prices
  on 28 September 2026, SHA-256 b5a03624…; test fixed in advance.

**Responding to the second round of reader feedback.** The staircase figure
that mixed a different score into one sequence is gone; its replacement
(Figure 10) compares the same statistic before and after the cutoff. The
fading-edge claim, which had no trend test, is gone. "The model reads well"
is no longer asserted. The FY2025 "filed 2026" label error disappears with its
figure.

**Palette.** Teal, indigo, amber and coral replace the rust brown.

**Illustrations.** `graphics.md` briefs a cover, three part openers, a
closing image and spot illustrations for an artist.

**Needs the author's confirmation.**
1. Motives written in the first person (why build a reader; why it was worth
   doing; the Citadel, Point72 and Medallion comparison).
2. That the February 2026 batch ran on Windows and development on a Mac (the
   stored paths suggest it).
3. That no other significant version or experiment belongs in the lineage;
   `stock_stuff_06042025` holds many other experiments (CSPP, options, SEDAR,
   earnings calls) that the paper does not cover.
4. That committing or publishing the sealed ledger's hash is acceptable.
5. The earlier editions' questions below still stand.

---

## Edition 3 — the narrative edition (30 September 2026)

Written after two fresh readers (a curious generalist and a sceptical quant)
read Edition 2 as a PDF only. Both would have stopped reading around page 5:
the paper opened with its build history, never explained its title, buried
its most surprising result on page 11, and hedged almost every paragraph.

**Structure.** Puzzle first. §1 states the too-good result and the
tomorrow's-newspaper problem, with the three tests summarised in Figure 1.
§2 shows the reader; §3 the three dates; §§4–6 run the tests in order of
strictness; §7 gathers every limitation in one place; §8 moves the build
history (four stages, quota) after the evidence. Body about 4,250 words.

**New evidence (descriptive, `stories-config.yaml`, rules fixed before use).**
- Verdict ladder: before the cutoff, mean return percentile rises through all
  five verdicts (0.431 → 0.598; Spearman 0.135, p = 0.0001). After it, BUY
  stays high but SELL (0.489) no longer ranks below HOLD (0.472);
  Spearman 0.094, p = 0.0012.
- Year-by-year one-year rank spread: 14.9, 8.8, 12.1, 7.0 before the cutoff,
  5.3 for FY2024.
- A seeded draw of 24 companies (seed 20260930) from the 195 read every year
  with at least one BUY and one SELL: 40 of 70 directional calls right.
- Babcock & Wilcox's price series verified against Nasdaq: $0.4577 to $15.72,
  no split. The company is now named. It stood at $9.52 when read.
- Apple's FY2025 SELL: −0.9 points against SPY over six months.

**Unchanged.** Every Edition 2 correction and number: permutation centring,
model filter, denominators, p-values (post-cutoff 1Y rank p = 0.0059; 6M
p = 0.094 and 0.055; 1Y mean p = 0.215 and 0.102).

**Presentation.** Eleven figures: four new (staircase, verdict ladder, fading
edge, company grid), five retitled to state their claim, two moved to §8,
two retired (verdict mix, horizons). Cover shows the three numbers and the
puzzle. References now list sources in full. Contents no longer duplicated.

**Needs the author's confirmation.**
1. The first-person opening ("I did not start out worried about this…") and
   the framing of the February report as having "skipped a question".
2. The memory interpretation of the fading edge and the SELL collapse is
   offered as consistent with, not proof of, leakage. Comfortable?
3. Figure 1 is a combined scoreboard of the kind Edition 2 deliberately
   omitted (it can blur prediction timing). It labels each bar by what the model
   could have known and says the third bar is a different score. Keep it?
4. The Edition 2 questions below still stand.

---

## Edition 2 — argument, evidence and publication review

Revised 29 September 2026 at the author's request to match the editorial
ambition of *The Ghost in the Gallery*. The author subsequently asked for the
paper to engage all audiences while maintaining excellent writing. The revised
brief therefore specifies one accessible narrative with increasing depth in
figures, captions, appendices and reproduction artifacts.

### What changed

The paper is rebuilt around one constructive idea: **a fixed question makes
model output comparable; a dated record makes its predictive claims testable**.
The title is retained. The subtitle now covers both building and testing.
Fourteen sections and three appendices become ten sections and two appendices.
The main text is about 4,200 words and the abstract is 248 words.

The design journey now shows what each stage enabled. Claims about schema
validation, full-filing extraction, quotas and model independence are stated
at the level supported by the code. The paper explains specialist terms where
needed and separates engineering usefulness from predictive performance.

The statistical results remain in the main argument, including the adverse
compounder association and inconclusive later mean-return tests. The original
compounder ambition concerned decades; a one-year return test does not settle
that long-term question. No new model calls or market-price downloads were made.

### Material evidence corrections

1. **Cutoff versus prediction timing.** The former thesis said a model could
   only be tested on filings it could not have read. That is too strong and
   conflates two clocks. The new text separates historical outcomes,
   retrospective post-cutoff readings and dated predictions. Google's stated
   cutoff is an explicit assumption, not an audited exclusion guarantee.
2. **Permutation centre.** The main evaluator measured `abs(null)` against
   `abs(observed)`, despite an industry-conditioned null whose mean need not
   be zero. It now compares distances from that null mean, matching the
   method already used in the origin evaluator. The data, seed and shuffle
   count stay fixed. `validation.json` includes an independent exact-enumeration
   fixture: centred p = 1/3, sampled p ≈ 0.333, while the incorrect zero-centred
   reference gives p = 1.
3. **Model scope.** Of 6,653 unique company-years, 6,651 name Gemini 2.5 Flash.
   JOBY FY2025 and ACHR FY2025 name Gemini 3.5 Flash in July run configurations.
   The evaluator now explicitly filters by recorded model after choosing the
   first stored company-year. Those two readings already failed verdict parsing,
   so the priced sample remains 6,203 and this filter changes no return estimate.
4. **Denominators.** Industry-block tests drop singleton groups. Figure 7 now
   labels the actual groups: 1,061 BUY / 635 SELL historically, and 323 / 190
   after the cutoff. The descriptive groups are 1,099 / 657 and 339 / 201.
5. **Null bands.** Figure 9 previously called mean ±1.96 SD “95% of shuffles”.
   It now uses empirical 2.5th and 97.5th percentiles saved by the evaluator.
   They are labelled as null ranges, not confidence intervals.
6. **False strength removed.** Local protocols are no longer described as
   independent preregistrations. The narrow anachronism search no longer
   “rules out” leakage. Missing price series are not all labelled acquisitions.
   The reading's claimed current valuation is not treated as verified fact.
7. **An unused diagnostic renamed.** `ticker_clustered_p` was a t-test on
   ticker averages, not a cluster-robust estimator. Its output key is now
   `ticker_averaged_naive_p`; the paper does not rely on it.

### Changed p-values

Same price snapshot, observations and permutation seed. Rounded here; exact
values remain in the old and new JSON results.

| Comparison | Edition 1.1 | Edition 2 |
|---|---:|---:|
| Post-cutoff 6M, within vintage | 0.1139 | 0.0937 |
| Post-cutoff 6M, vintage + industry | 0.048 | 0.0553 |
| Post-cutoff 6M rank, vintage + industry | 0.0806 | 0.1602 |
| Post-cutoff 1Y mean, within vintage | 0.22 | 0.2148 |
| Post-cutoff 1Y mean, vintage + industry | 0.29 | 0.1024 |
| Post-cutoff 1Y rank, vintage + industry | 0.0051 | 0.0059 |

The six-month industry-controlled result no longer falls below 0.05. The
one-year rank association remains positive and exploratory. The historical
p-values remain at 0.0001 at published precision. The origin scores' point
estimates and p-values are unchanged.

### Visual and layout changes

Nine figures retained, each with a distinct job. The design chronology now
precedes the quota chart. Figure 5 becomes a readable three-clock schematic.
Figure 7 loses its causal title and gains correct sample labels. Figure 8 shows
the full return range and labels excess-return units as percentage points.
Figure 9 contains only the dated origin hypotheses; threshold ties and the
separate Spearman/contrast statistics are explained. Figure footers, print-size
labels and PDF page breaks were reviewed rather than relying on a successful
TeX compile alone.

See `validation.json` for the numerical checks, `figures/run.json` for asset
hashes, and `layout-review.json` for the final page review. The previous edition
is preserved under `archive/edition-1.1/`.

### Final release checks

The final PDF has **17 pages**, including cover, contents and both appendices;
**nine figures**, a **248-word abstract**, and approximately **4,177 body words**
(including captions). It is shorter than the nominal page budget because the
argument fits without smaller type or an isolated conclusion page.

Seven numerical validation groups pass, including independent return/rank
recomputation and an exact combinatorial reference for the permutation fix.
The final source and figure hashes match their build manifests. All seventeen
pages were inspected in overview, with detailed page and figure inspection
during layout revision. The TeX log has no overfull/underfull boxes or missing
characters; extracted text stays inside page bounds. The production database's
hash is unchanged from the archived pre-revision snapshot.

### Author review before public release

These are review questions, not assertions supplied by the revision:

- Confirm the personal motivation attributed to the origin experiment: finding
  shared traits of excellent businesses, then scoring other companies for
  resemblance. The scripts support this interpretation.
- Confirm whether the original output files were ever edited, regenerated or
  copied in a way that changed modification times. The paper deliberately
  qualifies their chronology and does not claim an immutable historical seal.
- Confirm whether the April Gemini preview was the only origin model used.
  The scripts name it; the current archive does not establish every historical
  call's configuration independently.

No application code, production database, original filing, ArtML file or origin
project file was changed. All retained publication artifacts are under EON's
`docs/whitepaper/`.

---

## Previous revision record

The following entries describe superseded editions and retain their original
wording for provenance. Their stronger claims and old p-values are not the
current paper's claims.

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
