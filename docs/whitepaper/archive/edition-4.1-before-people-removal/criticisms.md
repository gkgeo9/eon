# Criticisms: Edition 4, illustrated revision

Review of `eon-whitepaper.pdf` (30 pages, 17 figures, 6 AI-generated
illustrations) on 29 September 2026. The question was whether the paper still
reads as a professional, formal white paper now that the illustrations are in.

Three reviewers read it independently. Each saw only the PDF (and the art
director also saw the illustration files). None saw the Markdown, the brief or
each other's reports. Their personas:

- **The editor:** a research-publisher editor, judging formal conventions.
- **The art director:** judging the document as a visual object.
- **The quant:** a systematic-fund researcher reading it cold, judging
  credibility.

I added my own pass and checked their factual claims against the source and
configs. Page numbers are **printed folios**; the PDF page is the folio plus 2.

---

## Verdict

**No. It is no longer unmistakably a formal white paper.** It now reads as a
well-made illustrated long-read: an engineering memoir wrapped around a
careful evaluation. All three reviewers reached this independently:

- **Editor:** "a well-made long-form narrative feature … not a formal white
  paper. I would not publish it as-is under a formal imprint. With the changes
  below I would."
- **Art director:** the cover says "serious *book*, not technical paper".
- **Quant:** the illustrations "lower trust, but only a little … they do move
  the tone toward a brochure".

The illustrations are not the only cause, but they tipped it. They are more
finished than anything around them:

- They make the default LaTeX type and default matplotlib figures look
  unstyled.
- Three of them need captions that apologise for them ("This seal is a
  metaphor", "introduces the question; Figure 9 specifies…").

The evaluation is still the paper's strongest asset, and every reviewer
praised it. The fix is to let it lead again, not to throw the craft away.

---

## Where the reviewers agree

Consensus points, with how many of the three reviewers raised each.

| # | Criticism | Raised by | Status |
|---|---|---|---|
| 1 | **The Part III narrator (folio 23) should go.** A smiling young man at a lectern is the only human face. It reads as stock art or an author portrait, and personifying the model undercuts the section's point. | 3/3 | Agreed |
| 2 | **Body text cites the compass illustration as if it were evidence** (folio 22: "the recorder and unsettled compass in the illustration"). | 3/3 | Verified, line 625 of the Markdown |
| 3 | **The cover says "book", not "paper".** The telescope-with-magnifier is an AI mash-up; the title type is timid; "Illustrated revision" is production jargon. | 3/3 | Agreed |
| 4 | **The Part II opener does not show what its caption claims.** "Three records, different clocks" shows one clock, a ribbon box that reads as a gift, and a sunset that breaks the night palette. | 2/3 | Agreed |
| 5 | **Float holes.** The bottom 30–45% is blank on folios 1, 5, 8, 10, 13, 17 and 19, where figures were pushed to the next page. That adds about three pages of air. | 2/3, plus my pass | Verified on folio 1 |
| 6 | **Register.** The Citadel/Point72/Medallion name-drop appears twice. Other offenders: the "Two front doors and a doorbell" heading, "money lying on the pavement", "humbling in the right way", and the bold slogan ending ("Let the next year answer back"). | 2/3 | Agreed |
| 7 | **Double captioning.** Every figure carries its title, subtitle and source inside the graphic and again in the caption, and the source paths clutter both. | 2/3 | Agreed |
| 8 | **The same room four times.** Four of the six illustrations share the same arched windows, domed skyline and bridge. | 1/3, plus my pass | Agreed |
| 9 | **The closing wax seal implies custody the ledger doesn't have.** The caption has to concede it. | 2/3 | Agreed; the image still works |
| 10 | **The workshop (Part I) is the one opener that earns its space.** | 2/3 | Keep |

---

## Substantive criticisms (the quant, checked against the source)

These matter more than the art. A formal reader will find them.

1. **The surviving positive result is post hoc, and the pre-registered
   post-cutoff test failed.** The primary post-cutoff test in
   `evaluation-config.yaml` is 6M, mean statistic: 4.6 points, p = 0.094. The
   1Y test is a v2 amendment, and the rank statistic is declared "a robustness
   check, not a replacement". The paper discloses this in §8.2, but the
   abstract and conclusion lead with the "small rank association".
   *Verified.* The fix is to lead with the pre-registered failure.
2. **"How far, not which way" has no volatility baseline.** Predicting the size
   of a move (ρ = 0.12) is roughly what trailing volatility, size or sector
   already gives for free. Without a trailing-volatility or sector control, the
   "one modest talent" is unproven as a model skill. *Valid;* the
   "not realised volatility" caveat does not answer it.
3. **No factor or survivorship controls, and survivorship biases the headline
   SELL finding.** A universe of companies still listed in 2026 drops the
   failures, which lifts SELL-group returns after the cutoff. That is exactly
   the "SELL calls stop working" result. *Valid;* §8.6 names the survivorship
   limit but not its direction.
4. **Numbers appear with two values and are never reconciled.** Checked:

   | Pair | Explanation | Fix |
   |---|---|---|
   | 6.2 vs 5.9 | Plain rank spread (Fig 10) vs within-industry rank (text). | Label each. |
   | Contrarian +0.01 vs −0.3 | Spearman correlation (text) vs quintile spread (Fig 14). | Label each. |
   | 873 vs 847 put bias | Whole scan vs the graded 1,365. | Say so. |
   | Readings 6,973 / 8,157 / 6,653 / 6,411 / 6,203 | Different stages of the pipeline. | A reconciliation table in Appendix A. |
   | Companies 1,358 / 1,327 / 1,309 / 1,257 | Different stages of the pipeline. | Same table. |

   None is an error, but the paper reads as inconsistent.
5. **"Perfect staircase" (folio 17) is wrong.** STRONG SELL and SELL are both
   at the 43rd percentile. *Verified.* Say "a staircase" or "ordered".
6. **Smaller points:**
   - "p = 0.0001" should be written "p ≤ 0.0001", because it is the
     permutation floor.
   - "About 42% of it came from favouring the right industries" gives no
     method.
   - Figure 13's 57% hit rate mixes hindsight and post-cutoff years.
   - Figure 17's title sells the 49 tails, while the pre-registered test covers
     all BUY-type against all SELL-type verdicts.
7. **The engineering half is heavy for a technical reader.**
   - Folios 3–13 run ten pages before any evidence.
   - The quant would keep the quota clock, the XBRL-bloat measurement, PDF
     versus HTML, and schema validation.
   - They would compress the lock saga, §5.5 (Discord) and §5.6 (two machines).
   - **Author's call:** Part I's length was your explicit request, so this is
     a trade-off, not a defect. Tightening is still worth considering.
8. **Compliance optics.**
   - Twenty-five rotated keys at 20 requests a day looks like quota
     circumvention, and a fund's compliance team would ask. The paper should
     say whether the provider's terms allowed it.
   - Thirty green STRONG BUY tiles under a one-line disclaimer look like a tip
     sheet.

---

## Formal conventions (the editor)

- **Title page:** no affiliation beyond the self-named "Erebus Observatory
  Network", no contact, no keywords, no series or version line and no boxed
  disclaimer.
- **Contents:** Part lines are indistinguishable from sections, and no
  subsections are listed (§5 spans nine pages). There is no list of figures.
  Half the page is empty.
- **Abstract:** memoir register ("Over seventeen months I built…"), the fund
  name-drop, and an idiom presented as a finding.
- **Headings:** feature-style ("One stock, and twenty-four", "The bet"); the
  appendix titles are lower case.
- **Tables:** the tables on folio 14 and in Appendix C are unnumbered and
  uncaptioned.
- **References:**
  - Only five, folded into an appendix.
  - In-text citations carry no years.
  - The Google entry has a broken hanging indent.
  - The standard text-analysis literature (Loughran–McDonald) is missing.
- **Missing statements:** no data availability, no conflicts of interest and no
  acknowledgements.
- **Appendix C** reads as internal production notes.
- **AI-art disclosure** is buried in Appendix C. It belongs in a front-matter
  colophon.
- **Split code literals:** "sec-edgar / -downloader" (folio 6); "fintel. /
  db.corrupted" and "eon scan- / contrarian" (folio 12).
- **Figure 13** truncates company names ("Kratos Defense & Secur…").

---

## Visual system (the art director)

- **Illustration craft:**
  - Cover: a telescope-and-magnifier hybrid, impossible optics, clipped edges,
    blank spines.
  - Workshop: nonsense press mechanisms, a faceless worker, a door opening onto
    a river. It still earns its place.
  - Narrator: stacks with meaningless teal dots, an ill-proportioned lectern.
  - Closing: the envelope stands unsupported on its edge.
- **Figure defects:**
  - Fig 8: labels overprint the bubbles; the Fintel dot is invisible.
  - Fig 12: "mean +25.2" sits on the points.
  - Fig 10: the zero lines don't align between panels, which defeats the
    comparison.
  - Fig 14: the diamond marker reads as punctuation.
  - Fig 7: the "C" heading is jammed against the note above.
  - Fig 16: the tile colours are arbitrary.
- **Colour meanings are overloaded:** teal means EON, the model call and STRONG
  BUY; coral means SELL and the quota reset.
- **Phone legibility:** figure text is about 6–7 pt at print size, and Figures
  5, 8, 13 and 15 fail on a phone. Set 8 pt as the minimum.
- **Figure 1** says "illustrative, not evidence" but shows a real stored
  reading (`render_figures.py:142`). Use "first stored reading" or "a single
  example".
- **Typography:** default Computer Modern body, DejaVu Sans figures and
  painterly art are three visual languages. Choose one serif and one sans
  across both text and figures.
- **Part openers** share their page with body text, so the hierarchy is weak.

---

## What I recommend

The aim is a formal paper that is still a pleasure to read: rigour first,
craft second.

**Illustrations: keep two, cut or rework four.**

| Keep | Cut or rework |
|---|---|
| Workshop, as the Part I opener, perhaps at about 70% height. | Part III narrator: cut. |
| Closing envelope, smaller, placed after the conclusion rather than inside it. | Compass spot: cut, along with the sentence that cites it. Figure 15 carries the point. |
| | Part II opener: cut, or regenerate as a night still life of three dated objects. |
| | Cover: replace with a typographic cover and a restrained crop of the reading room, or a plain title page. |

Move the AI-generation credit to a colophon on the reverse of the title page.

**Rigour, before any polish:**

1. Lead the abstract and conclusion with the failed pre-registered post-cutoff
   test. Then state the post-hoc rank result and the options result as
   exploratory.
2. Add a trailing-volatility and sector baseline to the options magnitude test,
   or drop "talent". This is cheap: prices are already frozen.
3. State the direction of the survivorship bias beside the SELL finding.
4. Add a reconciliation table (readings and companies at each stage) to
   Appendix A, and label every statistic by its type.
5. Fix "perfect staircase", write p ≤ 0.0001, and give the 42% method or cut it.

**Form:**

1. A title page with author, contact, date and version, keywords and a boxed
   disclaimer. A contents page with subsections and a list of figures.
2. Descriptive headings (for example, "5.5 Interfaces and alerting"). Cut the
   second fund name-drop and the bold slogan.
3. One caption per figure: keep the in-graphic title, and reduce the caption to
   one sentence plus a short source. Move repository paths to Appendix C.
4. Close the float holes, stop code literals breaking across lines, and fix the
   label collisions in Figures 8, 10, 12 and 13.
5. Number and caption the tables. Add a proper references section with years,
   and add Loughran–McDonald.

**Leave alone:**

- The three-part structure.
- The first person where it records decisions.
- The sealed bet.
- Figures 1, 2, 9, 11, 13 and 17, which all reviewers liked.

---

## Would a stranger read it?

The quant would read the abstract ("the strongest thing in the document"),
skip from folio 5 to Part II, and come back for §9. That is a fair picture of
the paper today. The opening and the evaluation hold attention; the middle of
Part I loses a technical reader; the illustrations neither win nor lose
readers, but they cost trust with exactly the audience the evaluation is
written for.
