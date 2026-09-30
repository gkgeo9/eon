# Graphics and illustrations: *Tomorrow's Newspaper*

## Delivered illustrated revision

Six generated illustrations now accompany the seventeen numbered, code-generated
figures. The cover, the three part openers, the compass spot and the closing
bet are integrated in the PDF; the five interior illustrations also appear in
the canonical Markdown with alt text and unnumbered captions. Evidence figures
keep numbers 1–17, with the revised architecture and database diagrams at 3
and 7. All in-text references follow those numbers.

The illustrations share a reading-room setting, precise ink drawing, fine paper
grain and teal / indigo / amber accents. The cover's optical reader returns
in the workshop; night gives way to morning at the sealed envelope. This is
an imagined setting, not a reconstruction of the author's workspace.

| Delivered asset | Placement | Editorial purpose |
|---|---|---|
| `figures/art/art-cover.png` | Full-page PDF cover | The optical reader and tomorrow's newspaper |
| `figures/art/art-part1-workshop.png` | Part I opener | The infrastructure as a working place |
| `figures/art/art-part2-three-dates.png` | Part II opener | Archive, filing and verdict as different records |
| `figures/art/art-part3-narrator.png` | Part III opener | Fluency alongside stale dates and selective attention |
| `figures/art/art-spot-compass.png` | End of §8.5 | Movement size versus direction; refers to Figure 15 |
| `figures/art/art-closing-bet.png` | Conclusion | A verdict left for the future to judge |

Built with the **built-in image generation tool**. Full prompts, selected
source paths, revision prompts, pixel dimensions and SHA-256 hashes are in
`figures/art/manifest.json`. The PNGs are preserved at native resolution, not
upscaled to imply added detail. They are raster masters, not layered artist
source or vector files. PDF titles, explanatory captions and the ledger hash
are typeset separately so they remain exact, searchable text. The closing
card's date is also checked visually.

### Selection and iterations

The workshop was refined to show a five-by-five pegboard and a clock near
midnight. The closing illustration was refined to carry the exact opening
date. The part-II concept became one quiet still life: Figure 9 already does
the precise chronology, and an invented pictorial timeline would confuse
rather than clarify it. Numerical labels stay in the evidence figures.

The keys, funnel, ledger, trader and coin spots, optional section icons, and
social cover crop remain **uncommissioned alternatives**, not missing figure
references. Their ideas are already carried by the workshop, the existing
diagrams, the cover and the company grid. Adding all of them would lengthen
the paper and weaken the few images that matter. Original briefs follow for
future use; where they differ, the delivered revision above governs this PDF.

---

## The story in one paragraph

A developer spent seventeen months building a machine that reads company annual
reports (10-Ks, often 140+ pages each) with an AI model and writes down a
verdict: buy, hold or sell. The machine grew from a folder of scripts into a
small factory: web pages printed to PDF, 25 keys each allowed 20 requests a
day, workers that lease companies and send heartbeats, a database that
remembers everything, an alarm that pings a phone at night. It read almost
30,000 times. At first its verdicts looked brilliant. Then the author realised
the AI had been trained on the very years it was being graded on: it had, in
effect, read tomorrow's newspaper. Tested honestly, it turned out to be a
careful reader with a small edge, a few bad habits (it didn't know what year
it was; it saw danger everywhere) and one real talent: it could tell which
companies would move a lot, but not which way. The paper ends with a sealed
bet, to be opened in October 2027.

**Tone:** curious, warm, a little wry, never hype. Think Stripe Press, *The
Economist*'s editorial illustrations, or a well-made science book, not a
fintech ad. No rockets, no bull-and-bear clichés, no glowing robot brains, no
dollar signs raining down.

---

## House style

**Palette** (match the charts so the whole document feels like one object):

| Role | Hex | Use |
|---|---|---|
| Ink | `#1F2A37` | Line work, text, deep shadows |
| Teal | `#0F766E` | EON, the reader, "the subject" |
| Teal mid / light | `#5FB3AB` / `#DDF1EE` | Secondary teal, glows, paper tints |
| Indigo | `#4C5FD5` | Systems, machinery, structure |
| Indigo light | `#E6E9FB` | Machinery tints |
| Amber | `#E8A33D` | Time, clocks, the 2025 origin, lamplight |
| Amber light | `#FCF0DC` | Warm paper, highlights |
| Coral | `#E0605A` | Warnings, SELL, the adverse result (sparingly) |
| Paper | `#F7F8FA` | Backgrounds |

Use the palette as a limited set: mostly ink on paper with teal and amber as
the main colours; indigo for machinery; coral only where something went wrong.
No pure black, no pure white fills, no gradients that look like 2012 web
buttons. A subtle paper or risograph grain is welcome.

**Drawing style:** editorial illustration; confident line with flat colour
fields; slightly isometric or flat-perspective architecture where machinery
appears. Figures, if any, are simplified and not caricatured.

**Hard rules**
- **No real company logos or trademarks.** Tickers as plain text are fine where
  a brief asks for them.
- **No invented data.** Numbers that appear must be the ones given in the
  brief, and only where the brief puts them.
- Minimal text inside images. The paper's captions do the explaining.
- Must read at small sizes: the paper is also read on phones.
- Accessible contrast: text and key shapes at least 4.5:1 against background.

**Formats and sizes**
- Cover: A4 portrait, 2480 × 3508 px at 300 dpi, plus a 16:9 crop
  (2400 × 1350 px) for social previews.
- Part openers and full-width spots: 1881 × 1050 px (6.27 × 3.5 in at 300 dpi).
- Small spots: 900 × 900 px.
- Deliver layered source (Affinity, Illustrator, Procreate or similar) plus
  PNG at 300 dpi and, where possible, SVG. sRGB. Leave 3% safe margins.
- Place finished files in `docs/whitepaper/figures/art/` with the filenames
  given below.

---

## 1. Cover — "Tomorrow's Newspaper"  (`art-cover`)

**Job:** make someone stop scrolling. It must say, without words, that a
machine was reading the past with knowledge of the future.

**Must contain:** a newspaper, a stack of thick annual reports, and a reader
that is clearly a machine or an instrument (not a humanoid robot).

**Idea A — the reading room at night.** A tall, quiet reading room seen from
slightly above. On a long desk: a precise brass-and-glass instrument, part
telescope, part reading lamp (a nod to the "Observatory" in EON's name),
angled over an open 10-K. Beside it, folded, a newspaper whose masthead date is
*tomorrow*: the date is the only legible text, in small type, and its day is
one after the date on the open report. Amber lamplight on the desk; teal night
through tall windows; the stack of reports rises into shadow.

**Idea B — the reflection.** A close crop of an open annual report. In a glass
lens or a polished instrument lying on the page, the reflection shows not the
report but a newspaper headline, blurred except for its date.

**Idea C — the stack.** A towering, slightly impossible stack of 10-Ks, with
one newspaper tucked halfway down, dated in the future. A small teal lamp at
the top, reading.

The title and author are set by typography in the PDF; leave the top third or
bottom third calm enough to hold them.

---

## 2. Part I opener — "The workshop"  (`art-part1-workshop`)

**Job:** turn the architecture into a place. The reader has just learned there
are five layers; this picture makes them a building they can walk through.

**Concept:** a cutaway of a small night-time workshop or print works, read
left to right like the diagram:

1. A doorway where envelopes of filings arrive from a stately, columned
   building (EDGAR). A little sign or gauge limits arrivals ("no more than ten a
   second" is the idea; no text needed).
2. A row of printing presses, each actually a browser window on a stand,
   printing web pages onto paper: the Chrome-to-PDF step. One press is jammed,
   and a small figure is resetting it.
3. A reading desk where a teal lamp reads the printed pages: the model call.
4. A wall of 25 hooks holding 25 keys (the API keys). Some keys glow amber
   (in use); some hang dark (spent for the day).
5. A clerk's ledger desk at the back with a big bound book and neatly tagged
   folders: the database, leases and heartbeats.
6. On a shelf, a small phone lit with a notification: the Discord alarm.

A large wall clock above it all reads just before midnight. It is the single
most important object in the room: the batch was idle 80% of the time, waiting
for midnight Pacific.

**Colour:** indigo machinery, amber lamps and clock, teal reading lamp, paper
walls.

---

## 3. Spot — "Twenty requests a day"  (`art-spot-keys`)

**Job:** make the quota constraint tangible in one image (Section 5.3).

**Concept:** a key ring or pegboard of 25 identical keys. Twenty small notches
on each key's bow, filed down as they are used; most keys show all twenty
notches filed. A clock face behind shows midnight approaching. Alternatively:
25 hourglasses, most run out, one still trickling.

Small spot, square.

---

## 4. Spot — "A 141-page filing becomes one word"  (`art-spot-funnel`)

**Job:** the emotional version of Figure 4.

**Concept:** a thick annual report being fed into the top of an elegant
machine (think a hand-cranked press or a still), with paper ribbons,
tables and XBRL tags (tiny angle brackets) falling away as waste. From the
spout drips a single small card stamped **SELL** (the Apple example) in coral,
or **HOLD** in grey. The contrast in scale is the point.

---

## 5. Spot — "The database is the batch's memory"  (`art-spot-ledger`)

**Job:** make leases and heartbeats friendly (Section 5.4).

**Concept:** a calm librarian or clerk at a long ledger. On a board behind,
each company is a card on a hook; each card has a small tag with a name
("worker 3") and a tiny pulsing heart icon: the heartbeat. One card's heart has
stopped and its tag is being gently returned to the "pending" tray. Below the
desk, five identical sealed boxes labelled only with numbers 1–5: the last five
backups.

---

## 6. Part II opener — "Three dates"  (`art-part2-three-dates`)

**Job:** carry the paper's central idea: the order of three dates decides what
a test can prove (Figure 9).

**Concept:** three objects side by side on a table, each with a date on it and
nothing else: a filed annual report, a closed book stamped "training data"
(or an archive box, sealed), and a sealed envelope (the verdict). Across three
panels, their order changes:

1. *With hindsight:* the envelope is opened *after* a newspaper showing the
   outcome lies on the table.
2. *After the cutoff:* the archive box is sealed before the report arrives, but
   the envelope is still opened late.
3. *Written in advance:* the envelope is sealed with wax *before* the newspaper
   arrives.

Keep text to dates only; the caption explains.

---

## 7. Spot — "Tomorrow's newspaper"  (`art-spot-trader`)

**Job:** the thought experiment that names the paper (Section 8.1).

**Concept:** a trader at a desk at dawn, calm and slightly smug, reading a
newspaper whose date is tomorrow. Through the window, today's sun is just
rising. On the desk, a trophy for "Best Returns". The joke should land in two
seconds: the record is extraordinary and means nothing.

---

## 8. Spot — "A slightly loaded coin"  (`art-spot-coin`)

**Job:** the company grid's verdict (Figure 13): 40 of 70 calls right.

**Concept:** a coin mid-air above a hand, with a faint teal glow on one face.
Perhaps the coin's rim is marked with 70 ticks, 40 of them teal. Simple,
square, wry.

---

## 9. Spot — "How far, not which way"  (`art-spot-compass`)

**Job:** the cleanest positive result (Figure 15): the model could tell which
stocks would move a lot, but not in which direction.

**Concept:** a seismograph needle drawing large swings on paper, confidently,
beside a compass whose needle spins without settling. Or a weather vane that
spins freely next to an anemometer that measures the wind exactly.

---

## 10. Part III opener — "The confident narrator"  (`art-part3-narrator`)

**Job:** introduce the model's failures (Figure 16) with affection, not scorn.

**Concept:** a well-dressed, articulate figure (the model as a charming
narrator) mid-speech at a lectern, gesturing with total confidence. Small
tells around them: a wall calendar behind showing the *previous* year; a
scoreboard where one number, 68, is scrawled over and over; a stack of
reports all stamped HOLD; a pair of binoculars pointed only at storm clouds.
The figure is sympathetic: good at sounding right.

---

## 11. Closing illustration — "The bet"  (`art-closing-bet`)

**Job:** end on anticipation (Figure 17).

**Concept:** a sealed envelope on a clean desk, closed with teal wax. The wax
seal carries a short string of characters (use exactly `b5a03624`: the start
of the ledger's fingerprint). Beside it, a small card reading **Open October
2027**. Morning light. Optionally, faint behind it, 49 small tiles like
typeset tickers, out of focus.

---

## Optional: section spot icons  (`art-icon-*`)

Twelve small monoline icons (teal or ink, 2 pt line, 256 × 256 px) for section
headers: a magnifier over a page (1), a stack of five blocks (Part I), a column
building (EDGAR), a printer (Chrome), a lamp (model), a key ring (quota), a
ledger (database), a phone with a bell (Discord), two laptops (two machines), a
gauge (efficiency), a calendar with a question mark (was it right), an envelope
with a seal (the bet).

---

## Placement summary

| File | Where | Size |
|---|---|---|
| `art-cover` | PDF cover; social preview | A4 portrait; 16:9 crop |
| `art-part1-workshop` | Before Section 2 | full width |
| `art-spot-keys` | Section 5.3 | small |
| `art-spot-funnel` | Section 5.1 | small or half width |
| `art-spot-ledger` | Section 5.4 | small |
| `art-part2-three-dates` | Before Section 7 | full width |
| `art-spot-trader` | Section 8.1 | small |
| `art-spot-coin` | Section 8.3 | small |
| `art-spot-compass` | Section 8.5 | small |
| `art-part3-narrator` | Before Section 9 | full width |
| `art-closing-bet` | Section 11 or after the conclusion | full width |

The selected assets above are now placed with alt text and unnumbered
illustration captions. The other briefs remain optional. Illustrations are
metaphors; numbered figures carry the observations and system details.
