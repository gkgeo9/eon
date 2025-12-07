# Remaining Quick Wins (Part A)

## ✅ COMPLETED (Just Now)
1. ✅ 10-Q, 8-K, 4, DEF 14A filing support
2. ✅ Auto dark mode toggle (CSS injection)
3. ✅ Export page (single, bulk, time-series, comparison)

## ⏳ TODO (Can be added later)

### 1. Bulk Delete in History (30 min)
**What:** Select multiple analyses and delete at once
**Where:** `pages/3_📈_Analysis_History.py`
**How:**
```python
# Add checkbox column
selected = st.multiselect("Select analyses to delete", analyses_df['run_id'])

if st.button("Delete Selected"):
    for run_id in selected:
        db.delete_analysis_run(run_id)
```

### 2. Better Error Messages (1 hour)
**Current:** Generic "Analysis failed"
**Better:** Specific messages:
- "Failed to download 10-K for XYZ (Ticker not found on SEC EDGAR)"
- "PDF extraction failed for 2020 (File corrupted - skip this year)"
- "AI analysis timeout (Try smaller year range or different model)"

**Files to update:**
- `fintel/ui/services/analysis_service.py` (lines 186-190)
- `fintel/data/sources/sec/downloader.py` (error handling)
- `fintel/data/sources/sec/converter.py` (error handling)

### 3. More Tooltips (1 hour)
**Add help text to:**
- Every analysis type (what it does, when to use)
- Year selection modes (examples)
- Custom prompts (how to write effective prompts)
- Export formats (what's included in each)

**Pattern:**
```python
st.text_input("Field", help="📖 Clear explanation with example")
```

### 4. Benchmarking Score Display (2 hours)
**What:** Show COMPOUNDER DNA scores (0-100) in Results Viewer
**Where:** `pages/4_🔍_Results_Viewer.py`
**How:**
- Parse BenchmarkComparison results
- Display as progress bars
- Show category breakdown (90-100: Future Compounder, etc.)
- Visualize with charts

## 💡 Additional Ideas (Future)

### Tags/Labels System
- Tag analyses as "portfolio", "watchlist", "research"
- Filter by tags in History
- Quick access sidebar

### Estimated Time/Cost
- Before running analysis, show:
  - "This will analyze 3 companies × 5 years = 15 filings"
  - "Estimated time: 45-60 minutes"
  - "Estimated API cost: ~$2.50"

### Analysis Templates
- Pre-configured templates for common workflows
- "Deep Dive Single Company" (all lenses)
- "Quick Screen" (fundamental only)
- "Portfolio Risk Check" (Taleb lens, multi company)

### Keyboard Shortcuts
- `Ctrl+N`: New analysis
- `Ctrl+E`: Export
- `Ctrl+H`: View history
- `/`: Focus search

### Saved Filters
- Save frequently used filter combinations
- "My Portfolio Companies"
- "Last 30 Days Buffett Analyses"
- "High Score Candidates (>80)"
