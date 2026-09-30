# EON white paper

**[Read the PDF](eon-whitepaper.pdf)** · [Markdown edition](eon-whitepaper.md)

*Tomorrow's Newspaper: the making of EON, a machine that reads annual reports,
and an honest test of what it could see.* Gabriel George. Edition 4,
30 September 2026. Illustrated revision: **30 pages, 17 evidence figures,
6 illustrations**.

The paper has three parts. Part I tells how EON was built across five versions,
from 2025 scripts to a quota-bound system, and why each component exists.
Part II describes everything the model was asked and tests its answers. Part
III covers how the model failed, why the project was worth doing, and a sealed
bet to be graded in October 2027. It is the project's only long-form record.

Read **[BRIEF.md](BRIEF.md)** before revising.

| File | Purpose |
|---|---|
| `eon-whitepaper.md` | Canonical editorial source |
| `eon-whitepaper.pdf`, `.tex` | Generated publication editions |
| `BRIEF.md` | Editorial standard and definition of excellence |
| `figures.md` | Every figure's claim, source and limitation |
| `graphics.md` | Delivered artwork, placements and retained optional briefs |
| `revision-notes.md` | Corrections, measured changes and author-review questions |
| `criticisms.md` | Independent reviews of the illustrated Edition 4, with a ranked fix list |
| `evaluation-config.yaml`, `origin-ledger-config.yaml` | Main and 2025-ledger protocols |
| `stories-config.yaml` | Verdict ladder, company draw, February 2026 options test |
| `sealed-ledger-config.yaml` | The bet, frozen at publication |
| `evaluation/` | Results, per-reading records, verification, pipeline measurements, sealed ledger |
| `figure-data/` | Frozen plotting evidence |
| `figures/` | Seventeen numbered figures in SVG, PDF and PNG |
| `figures/art/` | Six generated illustrations, prompts and asset manifest |
| `render_figures.py`, `render_diagrams.py` | Figure code |
| `validate_paper.py`, `validation.json` | Independent arithmetic and method checks |
| `archive/edition-1.1/` | Preserved earlier edition |
| `archive/edition-4-before-illustrations/` | Preserved collaborator draft before this visual pass |

## Rebuild without new model calls

From the EON root, with NumPy, pandas, SciPy, PyYAML, Matplotlib and a Parquet
reader installed:

```sh
python docs/whitepaper/evaluate_backtest.py
python docs/whitepaper/evaluate_origin_ledger.py
python docs/whitepaper/evaluate_stories.py
.venv/bin/python docs/whitepaper/measure_pipeline.py   # needs PyPDF2 (EON's env)
python docs/whitepaper/prepare_figure_data.py
python docs/whitepaper/render_figures.py
python docs/whitepaper/validate_paper.py
python docs/whitepaper/build_paper.py --pandoc /path/to/pandoc
cd docs/whitepaper
tectonic -X compile --keep-logs eon-whitepaper.tex
```

Pandoc 3.x and Tectonic are needed for the PDF. Databases and original project
files are read-only inputs.

`make_sealed_ledger.py` has already run and refuses to run again: the ledger
it wrote is the paper's forecast. Commit it, or publish its SHA-256
(`b5a03624…`, full value in `evaluation/sealed-ledger/ledger.json`), somewhere
timestamped before its outcomes arrive. Grade it after October 2027 with the
test fixed in `sealed-ledger-config.yaml`.

`refresh_prices.py` is a network operation. A fresh download can change
historical adjusted prices; freeze and record a new snapshot before evaluating
a new horizon.

## Illustrations

The PDF has a new full-page cover and five interior illustrations. They are
unnumbered metaphors; the seventeen evidence figures retain their numbers.
Artwork PNGs are frozen inputs to the normal build, so rebuilding needs no
image-generation call. The built-in image generation tool made the images;
`figures/art/manifest.json` records the full prompts and selected outputs.

For the publication-only checks after a rebuild:

```sh
python docs/whitepaper/validate_publication.py
```

The optional `--pdf` flag additionally inspects the compiled PDF with PyMuPDF.
