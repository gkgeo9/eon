# EON white paper

**[Read the PDF](eon-whitepaper.pdf)** · [Markdown edition](eon-whitepaper.md)

*Tomorrow's Newspaper: the making of EON, a machine that reads annual reports,
and an honest test of what it could see.* Gabriel George. Edition 4,
30 September 2026.

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
| `graphics.md` | Briefs for commissioned illustrations |
| `revision-notes.md` | Corrections, measured changes and author-review questions |
| `evaluation-config.yaml`, `origin-ledger-config.yaml` | Main and 2025-ledger protocols |
| `stories-config.yaml` | Verdict ladder, company draw, February 2026 options test |
| `sealed-ledger-config.yaml` | The bet, frozen at publication |
| `evaluation/` | Results, per-reading records, verification, pipeline measurements, sealed ledger |
| `figure-data/` | Frozen plotting evidence |
| `figures/` | Seventeen figures in SVG, PDF and PNG |
| `render_figures.py`, `render_diagrams.py` | Figure code |
| `validate_paper.py`, `validation.json` | Independent arithmetic and method checks |
| `archive/edition-1.1/` | Preserved earlier edition |

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
