# Fintel Web UI

Streamlit-based web interface for the Fintel financial analysis platform.

## Features

- **Single Company Analysis**: Analyze SEC filings through multiple AI-powered perspectives
- **Multiple Analysis Types**:
  - Fundamental (single year)
  - Excellent Company (multi-year, success-focused)
  - Objective Company (multi-year, unbiased)
  - Buffett Lens (value investing)
  - Taleb Lens (antifragility & risks)
  - Contrarian Lens (variant perception)
  - Multi-Perspective (all three lenses combined)
- **Custom Prompts**: Create and manage custom analysis prompts
- **Results Display**: View results in formatted markdown or raw JSON
- **Export**: Download results as JSON, CSV, or Markdown
- **Analysis History**: Track and manage past analyses
- **SQLite Database**: Persistent storage of analyses and results

## Getting Started

### Prerequisites

1. Install dependencies:
   ```bash
   cd fintel
   pip install -e .
   ```

2. Set up environment variables (create `.env` file):
   ```bash
   # Google API Keys (1-25 keys)
   GOOGLE_API_KEY_1=your_api_key_here
   GOOGLE_API_KEY_2=another_key_here

   # SEC Edgar (required)
   FINTEL_SEC_USER_EMAIL=your@email.com
   FINTEL_SEC_COMPANY_NAME="Your Company"

   # Optional
   FINTEL_DATA_DIR=./data
   FINTEL_CACHE_DIR=./cache
   FINTEL_LOG_DIR=./logs
   ```

### Running the Application

```bash
cd fintel
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### 1. Running an Analysis

1. Navigate to **Single Analysis** page
2. Enter ticker symbol (e.g., AAPL, MSFT)
3. Select analysis type
4. Choose filing type (10-K recommended)
5. Select years to analyze
6. Optionally select a custom prompt
7. Click "Run Analysis"
8. Wait for completion (1-5 minutes per year)
9. View results

### 2. Viewing Results

- From the completed analysis page, click "View Results"
- Or navigate to **Results Viewer** and select an analysis
- Switch between tabs:
  - **Formatted View**: Readable markdown with expanders
  - **JSON View**: Interactive JSON tree
  - **Export**: Download in multiple formats

### 3. Managing Custom Prompts

1. Navigate to **Settings** page
2. Select analysis type
3. Click "Create New Prompt"
4. Enter name, description, and template
5. Use `{ticker}` and `{year}` as placeholders
6. Save and use in analyses

### 4. Viewing History

1. Navigate to **Analysis History** page
2. Use filters to search (ticker, type, status, date)
3. Select an analysis to:
   - View results
   - Re-run
   - Delete

## Architecture

### Directory Structure

```
src/fintel/ui/
├── app.py                  # Home page
├── pages/
│   ├── 1_📊_Single_Analysis.py
│   ├── 2_📈_Analysis_History.py
│   ├── 3_🔍_Results_Viewer.py
│   └── 4_⚙️_Settings.py
├── components/
│   └── results_display.py
├── services/
│   └── analysis_service.py  # Wraps fintel analyzers
├── database/
│   ├── repository.py         # SQLite operations
│   └── migrations/
│       └── v001_initial_schema.sql
└── utils/
    ├── formatting.py
    └── validators.py
```

### Database Schema

**Tables:**
- `analysis_runs`: Tracks each analysis job
- `analysis_results`: Stores Pydantic model outputs (JSON)
- `custom_prompts`: User-created prompts
- `file_cache`: Downloaded PDF files
- `user_settings`: User preferences

### Service Layer

The `AnalysisService` class wraps existing fintel analyzers without modifying them:
- `FundamentalAnalyzer` → fundamental analysis
- `PerspectiveAnalyzer` → Buffett, Taleb, Contrarian, Multi-perspective
- Downloads/caches filings
- Stores results in database
- Tracks progress

## Troubleshooting

### Database Issues

If you encounter database errors:
```bash
# Delete and recreate database
rm data/fintel.db
# Restart the app - it will recreate the schema
```

### Analysis Stuck

If an analysis appears stuck:
1. Check the terminal for errors
2. Verify API keys are valid
3. Check internet connection (SEC Edgar requires network)
4. Long analyses (10+ years) can take 10-30 minutes

### Import Errors

If you see import errors:
```bash
# Reinstall in development mode
cd fintel
pip install -e .
```

## Development

### Adding a New Analysis Type

1. Implement analyzer in `src/fintel/analysis/`
2. Add method to `AnalysisService._run_<type>_analysis()`
3. Add formatting function to `utils/formatting.py`
4. Add display function to `components/results_display.py`
5. Add to analysis type selector in Single Analysis page

### Adding a New Page

1. Create file in `src/fintel/ui/pages/` with format: `N_<emoji>_<Name>.py`
2. Streamlit auto-discovers pages in alphabetical order
3. Use consistent session state initialization

## Future Enhancements

- Batch analysis with CSV upload
- Real-time progress tracking
- Comparative analysis (benchmark against top 50)
- Data visualizations (charts, trends)
- PDF report generation
- Email notifications
- User authentication

## Support

For issues or questions:
1. Check the logs in `./logs/`
2. Review database with SQLite browser
3. Consult the main Fintel documentation

---

Built with Streamlit, powered by Google Gemini AI.
