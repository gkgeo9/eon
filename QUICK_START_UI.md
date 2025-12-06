# Fintel Streamlit UI - Quick Start Guide

## 🚀 Launch the Application

```bash
cd /Users/gkg/PycharmProjects/stock_stuff_06042025/fintel
streamlit run streamlit_app.py
```

The app will automatically open in your browser at `http://localhost:8501`

---

## 📊 Run Your First Analysis

### Step-by-Step:

1. **Navigate to "Single Analysis"** (first page)

2. **Enter a ticker** (e.g., AAPL, MSFT, GOOGL)

3. **Choose analysis type**:
   - **Fundamental**: Business model, financials, risks, key takeaways
   - **Buffett Lens**: Economic moat, management quality, intrinsic value
   - **Taleb Lens**: Antifragility, tail risks, optionality
   - **Contrarian Lens**: Variant perception, hidden opportunities
   - **Multi-Perspective**: All three lenses combined

4. **Select filing type**: 10-K (recommended)

5. **Choose years**: Start with "Most Recent Year"

6. **Click "🚀 Run Analysis"**

7. **Wait for completion** (1-5 minutes)
   - The page will auto-refresh to show progress
   - You'll see a success message when done

8. **Click "📊 View Results"** to see the analysis

---

## 🔍 View Results

Results are displayed in 3 tabs:

### Formatted View (Markdown)
- Easy-to-read sections with expandable content
- Key metrics highlighted
- Perfect for quick review

### JSON View
- Interactive JSON tree viewer
- Full Pydantic model output
- Great for developers

### Export
- Download as JSON
- Download as CSV (flattened data)
- Download as Markdown report

---

## 📈 View Analysis History

1. Navigate to "Analysis History"
2. See all past analyses
3. Filter by:
   - Ticker symbol
   - Analysis type
   - Status (completed/failed)
   - Date range
4. Actions:
   - **View**: See results again
   - **Re-run**: Run same analysis again
   - **Delete**: Remove from database

---

## ⚙️ Create Custom Prompts

1. Navigate to "Settings"
2. Select analysis type
3. Click "Create New Prompt"
4. Fill in:
   - **Name**: Short identifier (e.g., "Tech Focus")
   - **Description**: What makes it unique
   - **Template**: Your custom prompt (use `{ticker}` and `{year}`)
5. Save and use in analyses

**Example Custom Prompt**:
```
Analyze {ticker}'s {year} 10-K with special focus on:
- R&D spending trends
- Technology moat
- Product innovation pipeline
- Competition in tech sector

Provide detailed assessment of long-term competitive advantage.
```

---

## 💡 Tips

### For Best Results:
- Start with 1 year to test (faster)
- Use 10-K filings (most comprehensive)
- Try Buffett lens for value stocks
- Try Taleb lens for risk assessment
- Try Contrarian lens for overlooked opportunities
- Use Multi-Perspective for complete view

### Analysis Times:
- Fundamental: ~1.5 min
- Single Perspective: ~2 min
- Multi-Perspective: ~4-5 min

### If Analysis Fails:
- Check ticker is valid
- Verify internet connection
- Check logs in terminal
- Error message will show in UI

---

## 🗂️ Database Location

All analyses are stored in:
```
/Users/gkg/PycharmProjects/stock_stuff_06042025/fintel/data/fintel.db
```

You can browse with any SQLite viewer if needed.

---

## 📁 Where Files Are Stored

```
data/
├── fintel.db                    # Analysis database
├── raw/sec_filings/             # Downloaded filings
│   └── sec-edgar-filings/
│       └── AAPL/10-K/...
└── pdfs/                        # Converted PDFs
    └── AAPL_10-K_2025.pdf
```

---

## 🎯 Example Use Cases

### Value Investing Analysis
1. Ticker: BRK-B (Berkshire Hathaway)
2. Type: Buffett Lens
3. Years: 3
4. Review: Economic moat, pricing power, intrinsic value

### Risk Assessment
1. Ticker: TSLA (Tesla)
2. Type: Taleb Lens
3. Years: 1
4. Review: Fragility, tail risks, dependency chains

### Finding Undervalued Stocks
1. Ticker: Any mid-cap stock
2. Type: Contrarian Lens
3. Years: 1
4. Review: Variant perception, hidden strengths, market mispricing

### Complete Due Diligence
1. Ticker: Any company you're researching
2. Type: Multi-Perspective
3. Years: 3
4. Review: All three lenses + synthesis + final verdict

---

## 🛑 Stopping the App

Press `Ctrl+C` in the terminal to stop the Streamlit server.

---

## 📚 More Information

- **Full Testing Report**: See [TESTING_COMPLETE.md](TESTING_COMPLETE.md)
- **UI Documentation**: See [src/fintel/ui/README.md](src/fintel/ui/README.md)
- **Main Fintel Docs**: See main README files

---

## ✅ Verified Features

All features have been tested with real API calls:

- ✅ Download SEC 10-K filings
- ✅ Convert to PDF
- ✅ Fundamental analysis
- ✅ Buffett perspective
- ✅ Taleb perspective
- ✅ Contrarian perspective
- ✅ Multi-perspective analysis
- ✅ Database persistence
- ✅ File caching
- ✅ Custom prompts
- ✅ Results export
- ✅ Analysis history

**Ready to use!** 🎉
