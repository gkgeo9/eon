# The standard for the EON white paper

This brief governs the paper, its figures and future revisions. The reference is
*The Ghost in the Gallery*, the ArtML/Cabinet paper: an engaging account of a
real design journey, made credible by specific evidence and honest limits.
Borrow its discipline and voice. EON needs its own argument.

## Author's direction for Edition 4 and later (30 September 2026)

These instructions from the author take precedence where they differ from the
sections below.

- **This is the project's only long-form record.** Make it detailed,
  comprehensive and valuable; length is not a constraint.
- **Half the paper is the making of EON.** The beginning and end tell the
  journey (10K_automator, standardized_sec_ai, Fintel, EON, workflows) and
  answer "why" for every component: parallelism, CLI and web UI, the Discord
  webhook, cross-device support, the database and its concurrency, efficiency,
  PDF rather than HTML or XML. The middle, shorter, covers what was asked and
  whether it was right.
- **It is a finance, AI and systems project at once.** Say what it extracted,
  where the models fell short, and why it was worth doing although it was
  never going to rival Citadel, Point72 or Medallion.
- **Visuals must tell the story.** Diagrams of the architecture, execution and
  database; colour with purpose (teal, indigo, amber, coral; no rust brown);
  editorial illustrations made with image generation and recorded in `graphics.md`.
- **Keep the evidence standard.** Everything above is in addition to, not
  instead of, the rules below: traceable numbers, stated scope, honest limits.

## Purpose and audience

**Audience:** write for all interested readers without making the argument vague.
A curious general reader should understand the goal, the design journey and the
finding. A technical reader should be able to inspect the mechanism. A finance
reader should be able to judge the method and limits. Prospective collaborators
and employers should see the author's judgement in the decisions, rather than
through claims about the author.

**One narrative, several depths:** the main text carries a plain-language story;
figures explain the important relationships; captions supply scope and limits;
appendices and artifacts support close inspection. Define specialist terms on
first use. Do not interrupt the story with a separate sales pitch for each
reader. This broad audience follows the author's explicit direction.

**The question:** how did a filing reader become a research instrument, and what
happens when its judgements are tested?

**The sentence to carry away:** a fixed question makes model output comparable;
a dated record makes its predictive claims testable.

The paper succeeds if a reader can explain the central design choice, follow
one reading through the system, distinguish the three evaluation chronologies,
and state both the most interesting result and its limit. It should show what
the author built and learned without borrowing credibility from finance jargon.

## The narrative

1. Open with the desired interaction: read a company consistently, keep its
   judgement, and return to it later.
2. Let each design teach the next: origin scripts, workflow builder, common
   panel, then explicit hypothesis workflows. Earlier designs deserve an
   explanation of what they enabled.
3. Show the engineering constraint that mattered: requests and recoverable
   progress. Implementation details earn space by explaining a decision.
4. Explain time before presenting performance: filing date, model information
   boundary, reading date, and outcome.
5. Present the historical and post-cutoff associations separately. Then show
   the origin ledger on its own terms.
6. End with a concrete next experiment and a memorable, earned final line.

Avoid a feature catalogue, a chronological development diary and a wall of
qualifications. Technical precision should strengthen the story, not stop it.

## Voice and pacing

First person for supported motives and decisions. Plain third person for
mechanisms and results. Calm, specific, generous toward earlier work. Use
familiar nouns and active verbs. Prefer one developed thought per paragraph.
Vary sentence length; use short sentences to land a point, not to manufacture
drama. Strong claims need evidence, not intensifiers.

A paragraph earns its place by supplying a necessary fact, explaining a
choice, or advancing the argument. Cut paragraphs that restate the preceding
section. Say a limitation once, next to the claim it limits, with later
cross-references only when needed.

Do not invent personal recollections. An inferred motivation belongs in the
revision notes for the author's review. Do not say the author personally ran a
new publication analysis unless that is established.

Avoid praise words such as “revolutionary”, “seamless”, “production-ready” and
“robust” without a measured property. Avoid declaring an earlier design a
mistake to make the final one seem clever. Avoid phrases that turn a result
into destiny: “the model understands”, “the cutoff proves”, “genuine alpha”.

## Evidence standards

- Every quantitative claim must lead to a stored result, a source record, or
  an explicit calculation. Keep an evidence map and machine-readable checks.
- Separate **measured**, **reported**, **illustrative**, and **proposed** claims.
  The February report is reported evidence; the Apple reading is an example;
  a deliberate frozen ledger is proposed work.
- Name the model, sample, horizon, statistic and unit. A percentage point of
  return and a percentile point of rank are not interchangeable.
- Keep the descriptive corpus distinct from the model-filtered evaluation.
  Keep pre-exclusion and post-exclusion samples distinct as well.
- A stated knowledge cutoff is an assumption used to partition observations.
  It does not independently certify the absence of contamination. A
  retrospective post-cutoff reading is not a prospective prediction.
- Local file timestamps support a chronology; they do not establish an
  independently sealed edit history. Hashes taken today establish today's
  snapshot. Do not claim they prove what was present a year ago.
- Local analysis plans and amendments are documented protocols. Use
  “preregistered” only when a dated registration and its scope can be supplied.
  Prior looks at the outcomes must be disclosed.
- Report null, negative and inconclusive findings in the main argument. They
  are part of what the project learned. Failure at one year does not disprove
  an untested multi-decade business-quality hypothesis.
- A valid JSON schema is not verified financial content. All extracted text
  is not guaranteed to be all content in the source filing.
- Do not describe an average-by-ticker t-test as cluster-robust inference.
  Do not present conditional permutations as a complete cure for dependence.
- Preserve previous artifacts before correcting a statistic. Record the old
  and new value, reason, scope and effect on interpretation.
- Production databases and original files are read-only. Publication work
  stays under EON's `docs/whitepaper/`. Do not modify ArtML or the origin project.

## Visual standard

Every figure has a job. Its title states the finding or distinction. Its
subtitle names the scope. The caption explains the encoding, evidence and
material limit. A reader scanning only figures should recover the argument.

Use native vector diagrams and reproducible plots for evidence. Use generated
editorial illustration for a specific metaphor or narrative transition,
following the author's illustrated-revision direction. Keep illustrations
unnumbered, explicitly described and separate from measured figures. Never
invent dashboards, observations or data. Preserve prompts and asset hashes.

**House style:** 6.27-inch width, DejaVu Sans for charts, teal `#0F766E`, indigo `#4C5FD5`, amber `#E8A33D`, coral `#E0605A` and restrained greys, and readable labels at final print size. Use
position, labels, shapes or hatching alongside colour. Keep the PDF's serif
prose and generous spacing consistent with the reference paper.

Bars start at zero. Show the full plotted data range. Label logarithmic scales
and explain their linear region when applicable. Mark missing outcomes as
missing. Use direct labels where a legend would make the reader decode the
chart twice. No truncated intervals without an explicit continuation mark.

An empirical null band is not a confidence interval. A descriptive standard
error is not dependence-adjusted uncertainty. Use exact empirical quantiles
when claiming that a band contains 95% of shuffles. Caption those distinctions
in ordinary language.

Do not imply causality by comparing periods. Do not put retrospective and
prospective evidence on one undifferentiated scoreboard. No cumulative wealth
curve until an actual investable portfolio protocol and its costs exist.

Render SVG for Markdown, PDF for publication and PNG for inspection from the
same script. Visually inspect every figure at print size and every PDF page.
Look for clipped labels, crowded axes, lost minus signs, stranded headings,
awkward page breaks and captions detached from their figures.

## Length and acceptance

Edition 4 follows the author's comprehensive-record direction above, replacing
the earlier nine-figure, 18–22-page target. The illustrated revision has
seventeen evidence figures and six editorial illustrations. Keep the middle
results section subordinate to the wider engineering story. A shorter clear
explanation wins; shrinking text to hit a page target does not.

A release is ready for author review when:

- The abstract states the problem, system, result and contribution.
- The first figure makes the interaction intelligible without reading code.
- A reader can distinguish the descriptive corpus from each test sample.
- Every displayed statistic matches its source and actual denominator.
- Added-late analyses, corrections and provenance limits are explicit.
- Figure sources regenerate and the PDF matches the Markdown.
- Numerical validation and page review are recorded with artifact hashes.
- Remaining author questions are specific and listed in revision notes.

The standard is concise writing with enough evidence to deserve confidence.
The goal is a paper a thoughtful reader will finish, remember and be able to
check.
