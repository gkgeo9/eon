# Fintel Web UI - Quick Start Guide

## ✅ Installation Complete!

The Streamlit-based web interface has been successfully implemented. Here's how to get started.

---

## 🚀 Launch the Application

```bash
cd fintel
streamlit run streamlit_app.py
```

The app will automatically open in your browser at `http://localhost:8501`

**Note:** On first launch, the database will be automatically created at `data/fintel.db`

---

## 📋 What You Can Do

### 1. Single Company Analysis (Main Feature)

**Path:** Click "New Analysis" or navigate to "📊 Single Analysis"

**Steps:**
1. Enter ticker symbol (e.g., AAPL, MSFT, GOOGL)
2. Select analysis type:
   - **Fundamental**: Basic analysis for a single year
   - **Excellent Company**: Multi-year analysis for known winners (success-focused)
   - **Objective Company**: Multi-year unbiased analysis
   - **Buffett Lens**: Value investing perspective
   - **Taleb Lens**: Antifragility and risk analysis
   - **Contrarian Lens**: Variant perception and hidden opportunities
   - **Multi-Perspective**: All three lenses combined
3. Choose filing type (10-K recommended)
4. Select years to analyze:
   - **Number of Years**: Analyze last N years
   - **Specific Years**: Choose exact years
5. (Optional) Select a custom prompt
6. Click "Run Analysis"

**Wait Time:** 1-5 minutes per year (depends on API key availability)

### 2. View Results

**Formats Available:**
- **Formatted View**: Clean markdown with collapsible sections
- **JSON View**: Interactive JSON tree for technical users
- **Export**: Download as JSON, CSV, or Markdown

**Navigation:**
- After analysis completes, click "View Results"
- Or go to "🔍 Results Viewer" and select an analysis

### 3. Analysis History

**Path:** "📈 Analysis History"

**Features:**
- Filter by ticker, type, status, date range
- View past analyses
- Re-run analyses
- Delete old analyses
- View statistics

### 4. Custom Prompts

**Path:** "⚙️ Settings" → "Custom Prompts" tab

**Create Custom Prompts:**
1. Select analysis type
2. Click "Create New Prompt"
3. Enter:
   - Name (unique identifier)
   - Description (optional)
   - Template (use `{ticker}` and `{year}` placeholders)
4. Save and use in analyses

**Example Prompt:**
```
Analyze {ticker} for fiscal year {year} with a focus on:
- Competitive moat strength
- Management capital allocation
- Free cash flow generation
- Long-term sustainability

Be specific with numbers and provide evidence.
```

---

## 🎯 Example Workflow

**Analyze Apple with Buffett perspective for 5 years:**

1. Launch app: `streamlit run streamlit_app.py`
2. Click "📈 New Analysis"
3. Enter:
   - Ticker: `AAPL`
   - Analysis Type: `Buffett Lens (Value Investing)`
   - Filing Type: `10-K`
   - Years: Number of Years = `5`
4. Click "🚀 Run Analysis"
5. Wait for completion (5-10 minutes)
6. Click "📊 View Results"
7. Explore:
   - Investment Verdict (BUY/HOLD/PASS)
   - Economic Moat Assessment
   - Pricing Power
   - ROIC
   - Intrinsic Value Estimate
8. Export as Markdown for your notes

---

## 📂 File Structure

After running the app, you'll see:

```
fintel/
├── data/
│   ├── fintel.db           # SQLite database (auto-created)
│   ├── filings/            # Downloaded HTML (from SEC)
│   └── pdfs/               # Converted PDF files
├── cache/                  # API response cache
└── logs/                   # Application logs
```

---

## ⚙️ Configuration

**Required Environment Variables:**

Create/edit `.env` file in the fintel directory:

```bash
# Google Gemini API Keys (1-25 keys for parallel processing)
GOOGLE_API_KEY_1=your_first_key_here
GOOGLE_API_KEY_2=your_second_key_here
# ... up to GOOGLE_API_KEY_25

# SEC Edgar (required by SEC)
FINTEL_SEC_USER_EMAIL=your@email.com
FINTEL_SEC_COMPANY_NAME="Your Research Company"

# Optional
FINTEL_DATA_DIR=./data
FINTEL_CACHE_DIR=./cache
FINTEL_LOG_DIR=./logs
FINTEL_NUM_WORKERS=25
```

**Without API keys**, you'll see an error. Get Gemini API keys from:
https://aistudio.google.com/apikey

---

## 🐛 Troubleshooting

### App Won't Start

```bash
# Make sure you're in the fintel directory
cd /Users/gkg/PycharmProjects/stock_stuff_06042025/fintel

# Reinstall dependencies
/Users/gkg/PycharmProjects/stock_stuff_06042025/.venv/bin/python -m pip install -e .

# Try again
streamlit run streamlit_app.py
```

### Analysis Stuck at "Running"

1. Check terminal for errors
2. Verify API keys in `.env`
3. Check internet connection (needs to download from SEC)
4. Wait longer (10+ year analyses can take 20-30 minutes)

### Database Error

```bash
# Delete and recreate
rm data/fintel.db

# Restart app - it will recreate schema
streamlit run streamlit_app.py
```

### Import Errors

```bash
cd fintel
/Users/gkg/PycharmProjects/stock_stuff_06042025/.venv/bin/python -m pip install -e .
```

---

## 🎨 UI Pages Overview

### Home (📊 Dashboard)
- Quick metrics
- Recent analyses
- Quick action buttons

### Single Analysis (📊)
- Main analysis interface
- Configure and run new analyses
- Real-time progress tracking

### Analysis History (📈)
- View all past analyses
- Filter and search
- Manage analyses
- Statistics

### Results Viewer (🔍)
- Formatted analysis display
- JSON tree view
- Export functionality
- Multi-year comparison

### Settings (⚙️)
- Custom prompts library
- File cache management
- (Future: user preferences)

---

## 🔮 Next Steps

**Current Limitations (Phase 1):**
- ⏳ No real-time progress bar (shows spinner only)
- 📝 No batch CSV upload
- 📊 No data visualizations/charts
- 🔍 No comparative analysis (top 50 benchmark)
- 📧 No email notifications

**Coming in Phase 2:**
- Batch analysis with CSV upload
- Progress tracking with percentage completion
- Benchmark comparisons (Compounder DNA scoring)
- Contrarian scanner (6-dimension scoring)
- Data visualizations (Plotly charts)
- PDF report generation

---

## 💡 Tips & Best Practices

1. **Start Small**: Test with 1-2 years first before running 10+ year analyses
2. **Use Caching**: Re-analyzing same company/years uses cached PDFs (much faster)
3. **Custom Prompts**: Experiment with prompts to get exactly the insights you want
4. **Export Results**: Save important analyses as Markdown for your notes
5. **Multiple Keys**: Add more API keys to enable parallel processing
6. **10-K vs 10-Q**: Stick with 10-K (annual) for comprehensive analysis

---

## 📖 Learn More

- **Full Documentation**: `src/fintel/ui/README.md`
- **Implementation Plan**: `/Users/gkg/.claude/plans/dapper-dreaming-cat.md`
- **Main Fintel Docs**: `README.md`, `QUICK_START.md`

---

## 🎉 You're Ready!

Launch the app and start analyzing:

```bash
cd fintel
streamlit run streamlit_app.py
```

Happy analyzing! 📊
