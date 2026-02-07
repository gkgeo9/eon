# EON Web UI

Streamlit-based web interface for the Erebus Observatory Network (EON) financial analysis platform.

## Features

### 🎯 Analysis Capabilities

- **Single Company Analysis**: Analyze SEC filings through multiple AI-powered perspectives
- **Batch Analysis**: Analyze multiple companies at once via CSV upload or manual entry
- **Multiple Analysis Types**:
  - **Fundamental** (single year) - Business model, financials, risks, and strategies
  - **Success Factors - Excellent Company** (multi-year) - Identifies what made proven winners succeed. Best for studying top performers (AAPL, MSFT, GOOGL)
  - **Success Factors - Objective Analysis** (multi-year) - Unbiased assessment of any company's characteristics, strengths, and weaknesses. Best for screening unknown companies
  - **Buffett Lens** - Warren Buffett perspective: Economic moat, management quality, pricing power, intrinsic value
  - **Taleb Lens** - Nassim Taleb perspective: Fragility assessment, tail risks, antifragility
  - **Contrarian Lens** - Variant perception, hidden opportunities, market mispricings
  - **Multi-Perspective** - All three investment lenses combined (Buffett + Taleb + Contrarian)
  - **Contrarian Scanner** - 6-dimension scoring (0-600) to identify hidden compounder potential through strategic anomalies and asymmetric resources

### 📊 Year Selection Options

- **Most Recent Year**: Analyze the latest available filing
- **Number of Years**: Analyze multiple consecutive years (2-10 for single analyses, 3-15 for multi-year analyses)
- **Specific Year**: Select a particular fiscal year (1995-present)

### 💼 User Interface

- **Custom Prompts**: Create and manage custom analysis prompts for each analysis type
- **Results Display**: View results in formatted markdown or raw JSON with interactive expanders
- **Export Options**: Download results as JSON, CSV, or Markdown
- **Analysis History**: Search, filter, and manage past analyses with comprehensive statistics
- **Batch Monitoring**: Real-time progress tracking for multiple running analyses
- **SQLite Database**: Persistent storage of analyses, results, and settings

## Getting Started

### Prerequisites

1. Install dependencies:

   ```bash
   cd eon
   pip install -e .
   ```

2. Set up environment variables (create `.env` file):

   ```bash
   # Google API Keys (1-25 keys)
   GOOGLE_API_KEY_1=your_api_key_here
   GOOGLE_API_KEY_2=another_key_here

   # SEC Edgar (required)
   EON_SEC_USER_EMAIL=your@email.com
   EON_SEC_COMPANY_NAME="Your Company"

   # Optional
   EON_DATA_DIR=./data
   EON_CACHE_DIR=./cache
   EON_LOG_DIR=./logs
   ```

### Running the Application

```bash
cd eon
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### 1. Running a Single Analysis

1. Navigate to **📊 Single Analysis** page
2. Enter ticker symbol (e.g., AAPL, MSFT)
3. Optionally enter company name for display
4. Select analysis type from dropdown:
   - For studying successful companies: Choose "Success Factors - Excellent Company"
   - For screening unknown companies: Choose "Success Factors - Objective Analysis"
   - For identifying hidden gems: Choose "Contrarian Scanner"
   - For traditional analyses: Choose Fundamental, Buffett, Taleb, Contrarian, or Multi-Perspective
5. Choose filing type (10-K recommended)
6. Select year option:
   - **Most Recent Year**: Latest filing only
   - **Number of Years**: Multiple consecutive years (note: multi-year analyses automatically require 3-15 years)
   - **Specific Year**: Pick a particular fiscal year
7. Optionally select a custom prompt
8. Click "🚀 Run Analysis"
9. Wait for completion (timing varies):
   - Single year: 1-5 minutes
   - Multi-year (5 years): 10-30 minutes
   - Scanner: 15-40 minutes (includes objective analysis + scanning)
10. View results when complete

### 2. Running Batch Analysis

#### Via CSV Upload:

1. Navigate to **📦 Batch Analysis** page
2. Download the CSV template
3. Fill in your tickers and optional settings:
   - `ticker` (required): Stock symbols
   - `analysis_type` (optional): Analysis type for each company
   - `company_name` (optional): Display names
   - `num_years` (optional): Years to analyze
4. Upload the completed CSV
5. Review the preview
6. Set default settings for any missing fields
7. Click "🚀 Start Batch Analysis"
8. Monitor real-time progress with auto-refresh
9. View results in History when complete

#### Manual Entry:

1. Navigate to **📦 Batch Analysis** page
2. Scroll to "Manual Entry" section
3. Enter tickers (comma or newline separated)
4. Select analysis type and settings
5. Click "🚀 Start Manual Batch"
6. Monitor progress

### 3. Viewing Results

- From the completed analysis page, click "📊 View Results"
- Or navigate to **🔍 Results Viewer** and select an analysis
- Switch between tabs:
  - **📄 Formatted View**: Beautiful markdown with interactive expanders, organized by section
  - **🔍 JSON View**: Interactive JSON tree for developers
  - **📥 Export**: Download as JSON, CSV, or Markdown
- For multi-year analyses: Results are shown as "Multi-Year Analysis"
- For scanner results: See 6-dimension scores with color coding

### 4. Managing Custom Prompts

1. Navigate to **⚙️ Settings** page
2. Select the "Custom Prompts" tab
3. Choose analysis type
4. Click "Create New Prompt"
5. Enter:
   - **Name**: Descriptive name for the prompt
   - **Description**: What this prompt does
   - **Template**: Your custom prompt (use `{ticker}` and `{year}` as placeholders)
6. Save and use in future analyses

### 5. Viewing History

1. Navigate to **📈 Analysis History** page
2. Use filters to search:
   - **Ticker**: Filter by stock symbol
   - **Analysis Type**: Filter by type (fundamental, excellent, objective, scanner, etc.)
   - **Status**: Filter by completion status
   - **Date Range**: Filter by creation date
3. View results table with status indicators:
   - ✅ Completed
   - 🔄 Running
   - ⏳ Pending
   - ❌ Failed
4. Select an analysis to:
   - **📊 View Results**: See the analysis
   - **🔄 Re-run**: Run again with same settings
   - **🗑️ Delete**: Remove from history
5. View statistics by type and status at the bottom

## Architecture

### Directory Structure

```
src/eon/ui/
├── app.py                          # Home page with dashboard
├── pages/
│   ├── 1_📊_Single_Analysis.py    # Single company analysis
│   ├── 2_📈_Analysis_History.py   # Search and filter past analyses
│   ├── 3_🔍_Results_Viewer.py     # View analysis results
│   ├── 5_⚙️_Settings.py           # Custom prompts and cache management
│   └── 5_📦_Batch_Analysis.py     # Batch analysis via CSV or manual entry
├── components/
│   └── results_display.py          # Display formatters for all analysis types
├── services/
│   └── analysis_service.py         # Service layer wrapping eon analyzers
├── database/
│   ├── repository.py               # SQLite database operations
│   └── migrations/
│       └── v001_initial_schema.sql
└── utils/
    ├── formatting.py               # Markdown and export formatting
    └── validators.py               # Input validation
```

### Database Schema

**Tables:**

- `analysis_runs`: Tracks each analysis job
- `analysis_results`: Stores Pydantic model outputs (JSON)
- `custom_prompts`: User-created prompts
- `file_cache`: Downloaded PDF files
- `user_settings`: User preferences

### Service Layer

The `AnalysisService` class wraps existing eon analyzers without modifying them:

- `FundamentalAnalyzer` → fundamental analysis (single year)
- `ExcellentCompanyAnalyzer` → success factors for proven winners (multi-year, success-focused)
- `ObjectiveCompanyAnalyzer` → success factors for unknown companies (multi-year, unbiased)
- `PerspectiveAnalyzer` → Buffett, Taleb, Contrarian, Multi-perspective
- `ContrarianScanner` → 6-dimension hidden gem detection
- Downloads/caches filings from SEC Edgar
- Stores results in database with year tracking (year=0 for multi-year aggregated)
- Tracks progress and handles background threading

## Troubleshooting

### Database Issues

If you encounter database errors:

```bash
# Delete and recreate database
rm data/eon.db
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
cd eon
pip install -e .
```

## Development

### Adding a New Analysis Type

1. **Implement analyzer** in `src/eon/analysis/`:

   - Create analyzer class with appropriate methods
   - Define Pydantic models for output
   - Create prompts if using AI

2. **Add to AnalysisService** (`src/eon/ui/services/analysis_service.py`):

   - Add new method `_run_<type>_analysis(ticker, pdf_paths)`
   - Add case to `run_analysis()` switch statement
   - Handle multi-year vs single-year logic

3. **Add display formatting** (`src/eon/ui/components/results_display.py`):

   - Create `_display_<type>_formatted(data)` function
   - Add case to `display_formatted_view()` switch
   - Use expanders and markdown for clean layout

4. **Update UI selectors**:

   - Add to analysis type dropdown in `1_📊_Single_Analysis.py`
   - Add description to `analysis_descriptions` dict
   - Add to analysis type map
   - Update Analysis History filters if needed

5. **Test thoroughly**:
   - Single analysis
   - Batch analysis
   - Result display
   - Export functionality

### Adding a New Page

1. Create file in `src/eon/ui/pages/` with format: `N_<emoji>_<Name>.py`

   - N is a number determining order (1-9)
   - Use an appropriate emoji
   - Name should be descriptive

2. Use consistent session state initialization:

   ```python
   if 'db' not in st.session_state:
       st.session_state.db = DatabaseRepository()

   if 'analysis_service' not in st.session_state:
       st.session_state.analysis_service = AnalysisService(st.session_state.db)
   ```

3. Follow navigation pattern with footer buttons

4. Streamlit auto-discovers pages in alphabetical order

## Analysis Type Reference

| Type        | Years       | Purpose                     | Output Model                       | Time         |
| ----------- | ----------- | --------------------------- | ---------------------------------- | ------------ |
| fundamental | 1 (or more) | Basic 10-K analysis         | `TenKAnalysis`                     | 1-5 min/year |
| excellent   | 3-15        | Success factors for winners | `ExcellentCompanyFactors`          | 10-30 min    |
| objective   | 3-15        | Unbiased success factors    | `CompanySuccessFactors`            | 10-30 min    |
| buffett     | 1           | Value investing lens        | `BuffettAnalysis`                  | 1-5 min      |
| taleb       | 1           | Antifragility lens          | `TalebAnalysis`                    | 1-5 min      |
| contrarian  | 1           | Variant perception          | `ContrarianAnalysis`               | 1-5 min      |
| multi       | 1           | All three lenses            | `SimplifiedAnalysis`               | 3-10 min     |
| scanner     | 3-15        | Hidden gem detection        | `ContrarianAnalysis` (with scores) | 15-40 min    |

## Future Enhancements

### Planned

- **Benchmark Comparison**: Compare against top 50 baseline (requires baseline file)
- **Data Visualizations**: Charts for trends, financial metrics, score distributions
- **Comparative Analysis**: Side-by-side company comparisons
- **PDF Report Generation**: Professional reports for presentations

### Under Consideration

- Email notifications for completed analyses
- User authentication and multi-user support
- API endpoint for programmatic access
- Real-time SEC filing alerts
- Portfolio-level analysis
- Integration with market data providers

## Support

For issues or questions:

1. Check the logs in `./logs/`
2. Review database with SQLite browser
3. Consult the main EON documentation

---

Built with Streamlit.
