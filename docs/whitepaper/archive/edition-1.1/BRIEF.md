# Editorial brief: the EON white paper

This is the standard the EON white paper is written to. Read it before you draft,
edit, add a figure, or change a number. It applies to the author, to reviewers,
and to any AI assistant working in this folder.

The reference point is *The Ghost in the Gallery*, the ArtML/Cabinet white paper.
Its author was very happy with it, and this paper should meet the same bar. We
are not copying its subject. We are copying its discipline, its voice, and its
refusal to claim more than was measured.

---

## 1. What we are making

A technical white paper about EON: what it is for, how it came to be built this
way, what it has measured, and what that measurement can and cannot say.

**Reader.** A technically literate outsider: an engineer, a quantitative
researcher, or an investor who can read a table. They have not seen the code.
They are sceptical of AI claims about markets, and they are right to be.

**The one sentence the reader should leave with.**

> A language model's verdicts can only be tested on filings it could not have
> read, so the evaluation has to be built around the model's knowledge cutoff.

Everything in the paper serves that sentence, or it is cut. The systems story
(a quota-bound reader of the whole market), the design journey (from 2025
scripts through three shapes of the same idea), and the measurements all exist to earn it.

**What it is not.** Not a README, a feature list, a pitch, or investment
advice. EON's batch queue, Discord alerts and Streamlit pages matter only where
they explain a measured result or a design decision.

---

## 2. The bar, in one paragraph

*The Ghost in the Gallery* worked because it had **one idea** (a finite question
space can be answered in advance), told as **a journey** (three designs, each
teaching the next), backed by **exact numbers** (686,116 patches, 20 bytes,
14.48 MB), and **audited against itself** (seed tests, baselines, a census of
every stored answer). Every figure argued one thing. Every caption said what the
figure could not show. Negative results were kept and framed as lessons. The
voice was first person, calm, and specific. It never sounded like marketing, and
it never sounded defensive.

That is what we are looking for.

---

## 3. Evidence: rules that are not negotiable

1. **Every number traces to a file.** A figure, a table cell, a sentence: each
   comes from `figure-data/evidence.json`, `evaluation/results.json`, a named
   source file, or an explicit formula. If it cannot be traced, it does not go in.
2. **Every empirical claim carries its scope.** Which sample, which horizon,
   which model, which dates. "Before the cutoff, 1Y, 1,756 rated readings" rather
   than "the backtest shows".
3. **Say what kind of evidence it is.** *Measured* (we ran it), *reported*
   (the project recorded it earlier), *illustrative* (a worked example), or
   *hypothetical*. Never let an illustration pass as a measurement.
4. **The claim is never stronger than the test.** A p-value from a trade-level
   t-test is not independent evidence. A backtest of a model trained on the
   outcome period is not a forecast. An underpowered null is not a negative
   result; say "could not have detected" and give the detectable size.
5. **Decide the test before running it.** `evaluation-config.yaml` fixes the
   primary questions in advance. Anything added later is labelled as added
   later, with the reason, in the config and in `revision-notes.md`.
6. **Negative and inconclusive results stay in.** They are findings. Frame them
   as what the work taught, not as confessions.
7. **Corrections are recorded, not hidden.** If a number changes, the old one,
   the new one, and the reason go in `revision-notes.md`.
8. **Nothing is written into the project's own data.** The analysis database is
   opened read-only. New artefacts live in this folder.

**Specific to this paper.** Gemini 2.5 Flash has a published knowledge cutoff of
January 2025. Any outcome that ended before that date may be in its training
data. Treat that as the central threat to validity, not a footnote. A ledger of scores written
before their outcomes (the 2025 origin readings are one) outranks any backtest,
and its results lead, whichever way they point. Also state:
the universe is companies listed in February 2026 (survivorship), industry labels
are a 2026 snapshot, and one post-cutoff vintage is one market regime.

---

## 4. Prose

**Voice.** First person for decisions and motives ("I wanted", "I chose"), plain
third person for mechanisms and results. The author is a developer explaining
what they built and learned, generously and without defensiveness. Earlier
designs are stepping stones, not mistakes.

**Sentences.** Short and declarative. One idea per paragraph. Lead with the
point; the evidence follows. Prefer the concrete noun and the exact number.

**Shape.** Each section opens with its claim and ends on its consequence, often
a single short sentence. Reserve block quotes for the paper's load-bearing ideas,
no more than four in the whole paper.

**Qualification.** Attach the limit to the claim it limits, in the same
paragraph. Do not stack hedges ("may possibly suggest"). One precise
qualification beats three vague ones.

**Words to avoid.** *Alpha* as a boast, *edge*, *enterprise-grade*,
*production-ready*, *robust* (as praise), *cutting-edge*, *seamless*,
*revolutionary*, *leverage* (as a verb), *AI-powered*, *proves*. Use
*significant* only in its statistical sense, with the test named. Say "the
model", not "the AI". Name the model and version.

**Numbers.** Exact, with units and denominators: "+13.1 percentage points over
SPY at one year (1,099 BUY-rated against 657 SELL-rated readings)". Percentages
of what, over what window, against what benchmark. Decimal units throughout.

**Before and after.**

| Avoid | Write |
|---|---|
| EON's AI demonstrates statistically significant stock-selection ability. | Before the model's cutoff, BUY-rated filings beat SELL-rated ones by 13.1 points at one year. The model may have known how that year ended. |
| Enterprise-grade batch processing handles 1,000+ companies. | The market-wide batch read 6,568 filings in 13 days, at the quota's ceiling of 500 a day. |
| Results are promising but more research is needed. | One post-cutoff vintage shows a rank spread of 5.9 points (p = 0.0051, a post-hoc statistic). The next vintage will say whether it holds. |

---

## 5. Visuals

**Each figure argues one claim.** The title *is* the claim, as a sentence. The
subtitle gives scope (sample, horizon, dates). The footer gives the source file.
If a figure has no claim, it does not go in.

**House style** (shared with the ArtML paper, set in `figure-config.yaml`):
6.27-inch print width; DejaVu Sans; text never below 9 pt; neutral greys; teal
`#126B70` for the subject; rust `#A5472D` for qualifications, cutoffs and
warnings. Meaning never depends on hue alone: use labels, hatching, line style
and marker shape as well. No 3D, no gradients, no decorative icons, no emoji.

**Honest encoding.** Bar charts start at zero. Intervals are shown whenever a
point estimate is compared with something. Log scales are labelled as log scales.
Small samples are marked as small. Schematics say they are schematic.

**Captions carry the qualification.** Every caption states its sample, what the
figure cannot establish, and its source.

**Formats.** SVG for the Markdown edition, PDF for LaTeX, 240-dpi PNG for review,
all from `render_figures.py`, all reproducible from checked-in data.

**Figures deliberately not made** are listed in `figures.md` with the reason.
Equity curves, cumulative-return lines and "portfolio growth of $10,000" charts
are banned: they hide the sample, the dependence, and the look-ahead.

---

## 6. Length

Concise, but complete enough to be checked.

| Part | Target |
|---|---|
| Abstract | 200 to 260 words, with the key numbers |
| Body, sections 1 to 14 | about 5,000 to 7,000 words |
| Figures | 8 to 10, each earning its place |
| Appendices | reproduction, glossary, figures at a glance |
| PDF | about 18 to 24 pages |

For comparison, *The Ghost in the Gallery* runs to about 11,000 words of body.
This paper has one argument rather than a systems paper's many, so it should be
shorter. Add words only for evidence or a step in the argument, never for
coverage.

The cut test: if a paragraph can be removed without the reader losing a fact
they need or a step in the argument, remove it.

---

## 7. How the work is organised

| File | Role |
|---|---|
| `eon-whitepaper.md` | The paper. The editorial source; LaTeX is generated from it. |
| `BRIEF.md` | This standard. |
| `figures.md` | Every figure's argument, evidence, limits, and the figures omitted. |
| `revision-notes.md` | What changed, why, and what needs the author's confirmation. |
| `evaluation-config.yaml` | The pre-registered test. |
| `evaluate_backtest.py` | Runs the test; writes `evaluation/`. |
| `refresh_prices.py` | Fetches prices into this folder only. |
| `prepare_figure_data.py` | Snapshots database facts into `figure-data/`. |
| `render_figures.py` | Draws every figure from the snapshots. |
| `build_paper.py` | Markdown to LaTeX, via Pandoc. |

Every script writes a `run.json` with its configuration, input hashes and output
hashes before it finishes.

---

## 8. Definition of done

A draft is ready for the author when all of these are true.

- [ ] The one-sentence thesis is stated in the abstract and earned by the end.
- [ ] Every number in text, tables and figures traces to a file.
- [ ] Every empirical claim names its sample, horizon and model.
- [ ] Pre-cutoff and post-cutoff evidence are never pooled into one claim.
- [ ] Every figure's title is a claim and its caption states a limit.
- [ ] Negative and inconclusive results are present and framed as lessons.
- [ ] The words in section 4's list appear nowhere, except in quotation.
- [ ] Length is within the targets in section 6.
- [ ] `revision-notes.md` lists every claim that needs the author's confirmation.
- [ ] The paper states once, plainly, that it is not investment advice.
