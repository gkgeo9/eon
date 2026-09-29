# EON white paper

*Tomorrow's Newspaper: testing a language-model analyst on filings it could not
have read.*

**Start with [BRIEF.md](BRIEF.md).** It sets the standard this paper is written
to: what we are arguing, the evidence rules, the prose and visual style, and the
definition of done. Then read the paper,
[eon-whitepaper.md](eon-whitepaper.md), or its PDF.

| File | What it is |
|---|---|
| `BRIEF.md` | The editorial standard. Read first. |
| `eon-whitepaper.md` | The paper. The editorial source. |
| `eon-whitepaper.tex`, `.pdf` | Generated from the Markdown. Do not edit the `.tex`. |
| `figures.md` | Each figure's argument, evidence, limits, and figures deliberately omitted. |
| `revision-notes.md` | What changed, corrections, and **what the author must confirm**. |
| `evaluation-config.yaml` | The pre-registered test and its disclosed amendments. |
| `origin-ledger-config.yaml` | The pre-registered test of the 2025 origin scores. |
| `evaluation/` | Results, per-reading trades, run records; `v1-feb-cache/` is the first run; `origin-ledger/` the 2025 ledger. |
| `figure-data/` | The frozen snapshot every figure is drawn from. |
| `figures/` | SVG, PDF and PNG for all nine figures. |

## Rebuild

From the eon root. The database is only ever opened read-only, and every
output stays in this folder.

```sh
python docs/whitepaper/refresh_prices.py        # network; needs yfinance
python docs/whitepaper/evaluate_backtest.py     # offline, ~30 s
python docs/whitepaper/refresh_prices.py --origin   # network; 2025 ledger tickers
python docs/whitepaper/evaluate_origin_ledger.py    # reads the origin project read-only
python docs/whitepaper/prepare_figure_data.py
python docs/whitepaper/render_figures.py
python docs/whitepaper/build_paper.py --pandoc /path/to/pandoc   # Pandoc 3.x
cd docs/whitepaper && tectonic -X compile eon-whitepaper.tex
```

The analysis steps need NumPy, pandas, SciPy, Matplotlib and PyYAML. EON's own
virtual environment lacks Matplotlib and SciPy; this edition was run with a
separate Python 3.12 environment rather than changing EON's.

Changing a number means rerunning from the step that produces it, then
re-reading every sentence that quotes it. Captions and prose are never updated
automatically.
