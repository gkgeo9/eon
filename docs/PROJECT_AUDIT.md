# EON Project Audit

_Last updated: 2026-05-29_

This document is the output of a full project review. It covers three things:

1. **Documentation** — what was corrected (CLI help, README, CLAUDE.md).
2. **Unused / removable files** — dead code that can be deleted safely. **Nothing
   here has been deleted** — this is a catalogue for a maintainer to action.
3. **Web UI issues** — bugs and UX gaps found in the Streamlit interface.

---

## 1. Documentation corrections (already applied)

| Area | Problem | Fix |
| ---- | ------- | --- |
| `eon --help` | Referenced non-existent flags `--workers` and `--perspective`; `Features:`/`Examples:` blocks were mangled by Click's text rewrapping (missing `\b`). | Rewrote the group help with correct, real examples and `\b` markers. |
| `eon <cmd> --help` | **Crashed** with a `ConfigurationError` when no API keys / SEC email were set — you couldn't even read the help without a fully configured `.env`. | Config validation is now deferred to the commands that need it; `--help` and discovery always work. |
| `README.md` CLI Reference | Used `--workers`, `--type`, `--filing`, and `eon scan --tickers-file` — none of which exist. | Replaced with the real commands, flags, and a complete command/option table. |
| `README.md` Project Structure | Listed files that don't exist (`processing/pipeline.py`, `processing/resume.py`), an incomplete workflow-examples list, a wrong `scripts/` entry, and migrations "v001–v012". | Rewritten to match the actual tree; migrations table extended to v014. |
| `CLAUDE.md` | `eon batch tickers.csv --workers 10` (no such flag). | Changed to `--years 7`. |
| `navigation.py` docstring | Example pointed at `pages/3_📈_Analysis_History.py` (it's page 2). | Corrected. |

The per-command help (`analyze`, `batch`, `export`, `scan-contrarian`,
`workflows`, `cache`) was already high quality and is now verified accurate. Run
`eon COMMAND --help` for any command — each includes a description, analysis-type
reference where relevant, and runnable examples.

---

## 2. Unused / removable files

All paths below are **not imported anywhere in the core application** (verified by
grep across `eon/`, `pages/`, `custom_workflows/`, `tests/`, and entry points).
They are safe to remove if you don't need the standalone research tooling.

### 2a. The entire `experimental/` directory (~480 KB)

`experimental/` is a self-contained research sandbox. Nothing under `eon/`,
`pages/`, or `streamlit_app.py` imports it, and it is not registered in
`pyproject.toml`. It can be removed wholesale, or kept as out-of-tree scratch
space. Contents:

**Standalone scripts (10):**
- `experimental/add_mcap.py`
- `experimental/check_error_null_runs_cspp_to_csv.py`
- `experimental/convert_to_pdf.py`
- `experimental/count_items.py`
- `experimental/export_cspp_full.py`
- `experimental/export_cspp_to_csv.py`
- `experimental/export_multi_analysis_to_csv.py`
- `experimental/extract_russell_1000.py`
- `experimental/make_all_pdfs.py`
- `experimental/paper_trading_tracker.py`

**Backtester sub-package (`experimental/backtester/`):**
- `backtester.py`, `data_loader.py`, `metrics.py`, `price_fetcher.py`,
  `report.py`, `run_backtest.py`, `run_spread_backtest.py`, `signals.py`,
  `__main__.py`, `__init__.py`, `BACKTEST_REPORT.md`

**Orphaned test data:**
- `experimental/test.json` (~201 KB). The only reference is in
  `experimental/convert_to_pdf.py`, and it points at the wrong path
  (`./scripts/test.json`), so it is effectively dead.

> ⚠️ Note: `experimental/make_all_pdfs.py` and `experimental/convert_to_pdf.py`
> reference the root `logo.png` / `watermark.png`. Those images are **also** used
> by the README, so keep the images even if you delete `experimental/`.

### 2b. Placeholder migration

- `eon/ui/database/migrations/v009_placeholder.sql` — intentionally a no-op
  (`SELECT 1;`) created to keep migration numbering contiguous. Harmless to keep;
  removable only if you're comfortable with a gap in the version sequence. **Low
  priority — recommend leaving it** to preserve history.

### 2c. Investigated but **NOT** removable (false positives)

These look suspect but are actively used — **do not delete**:

- `eon/ui/components/results_display_legacy.py` — despite the name, it is the
  current results renderer. `eon/ui/components/results_display/__init__.py` is a
  thin wrapper that imports from it, and page 3 uses it.
- `eon/core/formatting.py` vs `eon/ui/utils/formatting.py` — **not** duplicates.
  The former does status/duration formatting (CLI + UI); the latter builds
  markdown reports. Both are used.
- `custom_workflows/examples/*.py` — all six are loaded dynamically by
  `custom_workflows/__init__.py`'s auto-discovery, not by static imports.
- `scripts/dedup_db.py` — a standalone maintenance utility
  (`python scripts/dedup_db.py`). Keep.
- `logo.png`, `watermark.png` — referenced by the README.

### Removal summary

| Confidence | Count | Disk |
| ---------- | ----- | ---- |
| Safe to remove (`experimental/` incl. backtester + test.json) | ~21 files | ~480 KB |
| Optional (v009 placeholder migration) | 1 file | trivial |

---

## 3. Web UI issues

### Fixed in this pass

- **Results Viewer dead-end (the reported bug).** Once you opened an analysis
  (`view_run_id` set), there was no way to pick a different one without reloading
  the page or navigating away (Home/History/New Analysis all leave the page).
  Added a **"← Select a different analysis"** button at the top of the results
  view that clears `view_run_id` and reruns, bringing back the selector in place.
  (`pages/3_🔍_Results_Viewer.py`)

- **Deprecated/inconsistent `use_container_width` in Batch Queue.** Page 4 used
  `use_container_width=True` in 9 places while every other page uses the modern
  `width="stretch"` API (`use_container_width` is deprecated in recent Streamlit).
  Replaced all 9 with `width="stretch"` for consistency and future-proofing.
  (`pages/4_🌙_Batch_Queue.py`)

### Open issues (catalogued, not yet changed)

| # | File · line | Severity | Issue | Suggested fix |
|---|-------------|----------|-------|---------------|
| 1 | `pages/5_⚙️_Settings.py` · 473 vs 512 | Low–Med | The two prompt-fetch DB methods return different key names: `get_prompts_by_type()` maps `prompt_template` → `template` (so line 473's `prompt['template']` works), but `get_prompt_by_name()` returns the raw `prompt_template` (so line 512 needs a `.get('prompt_template', …)` fallback). Both work today, but the divergent keys are a latent `KeyError` footgun. | Normalize the two repository methods to return the same key (preferably `template`), then simplify the UI accessors. |
| 2 | `pages/1_📊_Analysis.py` · ~750/865/950 | Low–Med | After a batch is submitted, `st.session_state['batch_csv_df']` is never cleared, so an uploaded CSV lingers in memory across reruns/tab switches. | Delete `batch_csv_df` from session state once the batch is launched. |
| 3 | `pages/4_🌙_Batch_Queue.py` · 179 | Low | Separator check tests both `"─"` and `"---"`, but the dropdown separator built in `eon/core/analysis_types.py` only uses en-dashes (`─`). The `"---"` branch is dead code. | Drop the redundant `or …startswith("---")`. |

All three are minor and were left unchanged to keep this pass focused on
documentation accuracy and the reported Results Viewer bug. None affects
correctness of analysis output.
