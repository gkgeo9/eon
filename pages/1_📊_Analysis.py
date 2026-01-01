#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis Page - Main interface for running single or batch analyses.
"""

import streamlit as st
import pandas as pd
import threading
import time
from datetime import datetime

from fintel.ui.database import DatabaseRepository
from fintel.ui.services import AnalysisService
from fintel.ui.theme import apply_theme
from fintel.ui.utils.validators import validate_ticker
from fintel.data.sources.sec import SECDownloader

# Filing type periodicities
ANNUAL_FILINGS = {'10-K', '20-F', 'DEF 14A', '40-F', 'N-CSR', 'N-CSRS', 'ARS'}
QUARTERLY_FILINGS = {'10-Q', '6-K'}
# Everything else is event-based

def get_filing_periodicity(filing_type: str) -> str:
    """Get the periodicity of a filing type."""
    ft = filing_type.upper().replace("/A", "")
    if ft in ANNUAL_FILINGS:
        return 'annual'
    elif ft in QUARTERLY_FILINGS:
        return 'quarterly'
    else:
        return 'event'

# Import custom workflows discovery
try:
    from custom_workflows import list_workflows, get_workflow
    CUSTOM_WORKFLOWS_AVAILABLE = True
except ImportError:
    CUSTOM_WORKFLOWS_AVAILABLE = False
    def list_workflows():
        return []
    def get_workflow(workflow_id):
        return None

# Apply global theme
apply_theme()

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

if 'analysis_service' not in st.session_state:
    st.session_state.analysis_service = AnalysisService(st.session_state.db)

if 'current_run_id' not in st.session_state:
    st.session_state.current_run_id = None

if 'check_status' not in st.session_state:
    st.session_state.check_status = False

if 'start_wait_count' not in st.session_state:
    st.session_state.start_wait_count = 0

if 'available_filing_types' not in st.session_state:
    st.session_state.available_filing_types = None

if 'last_queried_ticker' not in st.session_state:
    st.session_state.last_queried_ticker = None

if 'filing_types_loading' not in st.session_state:
    st.session_state.filing_types_loading = False

if 'ticker_last_changed' not in st.session_state:
    st.session_state.ticker_last_changed = 0.0

# Debounce delay for auto-querying filing types (seconds)
FILING_TYPES_DEBOUNCE_DELAY = 1.5

# Batch-specific session state
if 'batch_run_ids' not in st.session_state:
    st.session_state.batch_run_ids = []

if 'batch_monitoring' not in st.session_state:
    st.session_state.batch_monitoring = False

if 'batch_errors' not in st.session_state:
    st.session_state.batch_errors = {}


def get_available_filing_types(ticker: str, db: DatabaseRepository) -> list:
    """Get available filing types for a ticker, using cache when possible."""
    if not ticker:
        return ["10-K", "10-Q", "8-K", "4", "DEF 14A"]

    ticker = ticker.upper().strip()

    # Check cache first
    cached_types = db.get_cached_filing_types(ticker, max_age_hours=24)
    if cached_types:
        return cached_types

    # Query SEC API
    try:
        downloader = SECDownloader()
        filing_types = downloader.get_available_filing_types(ticker)

        if filing_types:
            db.cache_filing_types(ticker, filing_types)
            return filing_types
        else:
            return ["10-K", "10-Q", "8-K", "4", "DEF 14A"]
    except Exception as e:
        st.warning(f"Could not fetch filing types for {ticker}: {str(e)}")
        return ["10-K", "10-Q", "8-K", "4", "DEF 14A"]


def run_analysis_background(service, params, run_id_key='current_run_id'):
    """Run analysis in background thread and store run_id in session state."""
    try:
        run_id = service.run_analysis(**params)
        st.session_state[run_id_key] = run_id
    except Exception as e:
        st.session_state[f'{run_id_key}_error'] = str(e)
        st.session_state[run_id_key] = None


def run_single_analysis_thread(service, config, run_ids_list, run_ids_lock, ticker, errors_dict, errors_lock):
    """Run a single analysis in a thread (for batch processing)."""
    try:
        run_id = service.run_analysis(**config)
        with run_ids_lock:
            run_ids_list.append(run_id)
    except Exception as e:
        with errors_lock:
            errors_dict[ticker] = str(e)


def run_batch_analysis_background(service, ticker_configs):
    """Submit multiple analyses to run in parallel background threads."""
    run_ids = []
    run_ids_lock = threading.Lock()
    errors = {}
    errors_lock = threading.Lock()
    threads = []

    for config in ticker_configs:
        thread = threading.Thread(
            target=run_single_analysis_thread,
            args=(service, config, run_ids, run_ids_lock, config['ticker'], errors, errors_lock),
            daemon=True
        )
        thread.start()
        threads.append(thread)
        time.sleep(0.1)  # Small delay to avoid overwhelming the system

    # Wait for all threads to at least start their runs (give them a bit of time)
    for thread in threads:
        thread.join(timeout=2.0)

    # Copy to session state (thread-safe copy)
    with run_ids_lock:
        st.session_state.batch_run_ids = list(run_ids)
    with errors_lock:
        st.session_state.batch_errors = dict(errors)


# Page content
st.title("📊 Analysis")
st.markdown("Analyze SEC filings with AI-powered perspectives")

st.markdown("---")

# Mode toggle
analysis_mode = st.radio(
    "Analysis Mode",
    options=["Single Company", "Multiple Companies"],
    horizontal=True,
    key="analysis_mode_radio"
)

st.markdown("---")

# Check if batch was just submitted
if st.session_state.batch_monitoring:
    st.success("✅ Batch analysis submitted successfully!")
    st.info("Your analyses are running in parallel in the background. View progress in the Analysis History tab.")

    if len(st.session_state.batch_run_ids) > 0:
        st.markdown(f"**{len(st.session_state.batch_run_ids)} analyses submitted**")

    # Show any batch errors
    if st.session_state.batch_errors:
        with st.expander(f"⚠️ {len(st.session_state.batch_errors)} error(s) during submission", expanded=False):
            for ticker, error in st.session_state.batch_errors.items():
                st.error(f"**{ticker}:** {error}")

    st.session_state.batch_monitoring = False

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📜 View in History", type="primary", width="stretch", key="batch_view_history"):
            st.switch_page("pages/2_📈_Analysis_History.py")
    with col2:
        if st.button("➕ Start New Batch", width="stretch", key="batch_new"):
            st.session_state.batch_run_ids = []
            st.session_state.batch_errors = {}
            st.rerun()

# Check if we're monitoring a running analysis (single mode)
elif st.session_state.check_status:
    if st.session_state.current_run_id:
        run_id = st.session_state.current_run_id
        status = st.session_state.db.get_run_status(run_id)

        if status == 'completed':
            st.success("✅ Analysis completed successfully!")
            st.session_state.check_status = False

            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 View Results", type="primary", width="stretch"):
                    st.session_state.view_run_id = run_id
                    st.switch_page("pages/3_🔍_Results_Viewer.py")
            with col2:
                if st.button("🏠 Back to Home", width="stretch"):
                    st.session_state.current_run_id = None
                    st.rerun()

        elif status == 'failed':
            run_details = st.session_state.db.get_run_details(run_id)
            error_msg = run_details.get('error_message', 'Unknown error')
            st.error(f"❌ Analysis failed: {error_msg}")
            st.session_state.check_status = False

            if st.button("Try Again"):
                st.session_state.current_run_id = None
                st.rerun()

        elif status == 'running' or status == 'pending':
            st.success("✅ Analysis submitted successfully!")
            st.info("Your analysis is running in the background. View progress in the Analysis History tab.")

            run_details = st.session_state.db.get_run_details(run_id)
            if run_details:
                st.markdown(f"**Ticker:** {run_details['ticker'].upper()}")
                st.markdown(f"**Analysis Type:** {run_details['analysis_type'].capitalize()}")

            st.session_state.check_status = False

            col1, col2 = st.columns(2)
            with col1:
                if st.button("📜 View in History", type="primary", width="stretch"):
                    st.switch_page("pages/2_📈_Analysis_History.py")
            with col2:
                if st.button("➕ Start New Analysis", width="stretch"):
                    st.session_state.current_run_id = None
                    st.rerun()
        else:
            st.warning(f"Unknown status: {status}")
            st.session_state.check_status = False

    else:
        # Waiting for background thread to start and set run_id
        st.session_state.start_wait_count += 1

        if 'current_run_id_error' in st.session_state:
            st.error(f"❌ Failed to start analysis: {st.session_state.current_run_id_error}")
            st.session_state.check_status = False
            st.session_state.start_wait_count = 0
            del st.session_state['current_run_id_error']
            if st.button("Try Again"):
                st.rerun()
        elif st.session_state.start_wait_count > 10:
            st.error("❌ Analysis failed to start. Please try again.")
            st.session_state.check_status = False
            st.session_state.start_wait_count = 0
            if st.button("Try Again"):
                st.rerun()
        else:
            st.info("🚀 Starting analysis...")
            st.markdown("Initializing the analysis job...")

            with st.spinner("Starting..."):
                time.sleep(1)
                st.rerun()

# Show configuration form
else:
    # ============== SINGLE COMPANY MODE ==============
    if analysis_mode == "Single Company":
        st.subheader("Single Company Analysis")

        # Ticker input
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            ticker = st.text_input(
                "Company Ticker",
                placeholder="e.g., AAPL, MSFT, GOOGL",
                help="Enter the stock ticker symbol",
                key="ticker_input"
            ).upper().strip()

        with col2:
            company_name = st.text_input(
                "Company Name (Optional)",
                placeholder="e.g., Apple Inc.",
                help="Optional - for display purposes",
                key="company_name_input"
            )

        with col3:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("📋 Get Filing Types", help="Query SEC to find available filing types"):
                if ticker:
                    with st.spinner(f"Querying SEC for {ticker}..."):
                        filing_types = get_available_filing_types(ticker, st.session_state.db)
                        st.session_state.available_filing_types = filing_types
                        st.session_state.last_queried_ticker = ticker
                        st.success(f"Found {len(filing_types)} filing types")
                else:
                    st.warning("Please enter a ticker first")

        # Auto-query filing types if ticker changed (with debounce)
        if ticker and ticker != st.session_state.last_queried_ticker:
            # Track when ticker changed for debounce
            if st.session_state.get('pending_ticker') != ticker:
                st.session_state.pending_ticker = ticker
                st.session_state.ticker_last_changed = time.time()

            # Only query if enough time has passed since last change (debounce)
            time_since_change = time.time() - st.session_state.ticker_last_changed
            if time_since_change >= FILING_TYPES_DEBOUNCE_DELAY:
                with st.spinner(f"Fetching available filing types for {ticker}..."):
                    filing_types = get_available_filing_types(ticker, st.session_state.db)
                    st.session_state.available_filing_types = filing_types
                    st.session_state.last_queried_ticker = ticker
                    st.session_state.pending_ticker = None

        # Build analysis type options including custom workflows
        builtin_options = [
            ("📋 Fundamental Analysis", "fundamental"),
            ("⭐ Excellent Company Success Factors", "excellent"),
            ("🎯 Objective Company Analysis", "objective"),
            ("💰 Buffett Lens", "buffett"),
            ("🛡️ Taleb Lens", "taleb"),
            ("🔍 Contrarian Lens", "contrarian"),
            ("🎭 Multi-Perspective", "multi"),
            ("💎 Contrarian Scanner", "scanner"),
        ]

        # Get custom workflows
        custom_workflows = list_workflows()

        # Build options list
        analysis_options = [opt[0] for opt in builtin_options]

        # Add custom workflows if any exist
        if custom_workflows:
            analysis_options.append("───── Custom Workflows ─────")
            for wf in custom_workflows:
                analysis_options.append(f"{wf['icon']} {wf['name']}")

        # Analysis type selector
        analysis_type_display = st.selectbox(
            "Analysis Type",
            options=analysis_options,
            help="Select the type of analysis to perform",
            key="single_analysis_type"
        )

        # Determine if this is a custom workflow
        is_custom_workflow = False
        custom_workflow_id = None
        custom_workflow_min_years = 1

        # Map display name to internal type
        analysis_type_map = {opt[0]: opt[1] for opt in builtin_options}

        if analysis_type_display in analysis_type_map:
            analysis_type = analysis_type_map[analysis_type_display]
        elif analysis_type_display.startswith("─"):
            # This is the separator, default to fundamental
            analysis_type = "fundamental"
        else:
            # This is a custom workflow
            is_custom_workflow = True
            # Find the matching workflow
            for wf in custom_workflows:
                if f"{wf['icon']} {wf['name']}" == analysis_type_display:
                    custom_workflow_id = wf['id']
                    custom_workflow_min_years = wf['min_years']
                    break
            analysis_type = f"custom:{custom_workflow_id}"

        # Show analysis type description
        analysis_descriptions = {
            "fundamental": "📋 Analyzes business model, financials, risks, and key strategies.",
            "excellent": "⭐ Multi-year analysis for proven winners - identifies what made excellent companies succeed. **Requires at least 3 years**.",
            "objective": "🎯 Multi-year unbiased analysis - objective assessment of any company's strengths and weaknesses. **Requires at least 3 years**.",
            "buffett": "💰 Warren Buffett perspective: economic moat, management quality, pricing power, and intrinsic value.",
            "taleb": "🛡️ Nassim Taleb perspective: fragility assessment, tail risks, and antifragility.",
            "contrarian": "🔍 Contrarian perspective: variant perception, hidden opportunities, and market mispricings.",
            "multi": "🎭 Combined analysis through all three investment lenses: Buffett, Taleb, and Contrarian.",
            "scanner": "💎 Six-dimension scoring system (0-600 scale) to identify companies with hidden compounder potential. **Requires at least 3 years**."
        }

        if is_custom_workflow and custom_workflow_id:
            # Get description from custom workflow
            for wf in custom_workflows:
                if wf['id'] == custom_workflow_id:
                    min_years_note = f" **Requires at least {wf['min_years']} years**." if wf['min_years'] > 1 else ""
                    st.info(f"{wf['icon']} {wf['description']}{min_years_note}")
                    break
        else:
            if analysis_type in analysis_descriptions:
                st.info(analysis_descriptions[analysis_type])

        # Filing type
        if st.session_state.available_filing_types:
            filing_options = st.session_state.available_filing_types
            help_text = f"Available SEC filings for {st.session_state.last_queried_ticker or ticker}"
        else:
            filing_options = ["10-K", "10-Q", "8-K", "4", "DEF 14A"]
            help_text = "Common SEC filing types"

        filing_type = st.selectbox(
            "Filing Type",
            options=filing_options,
            index=0,
            help=help_text,
            key="single_filing_type"
        )

        # Period selection - adapts based on filing type periodicity
        st.subheader("Filing Period Selection")

        # Check if multi-year is required (builtin or custom workflow)
        multi_year_required = analysis_type in ['excellent', 'objective', 'scanner']
        if is_custom_workflow and custom_workflow_min_years >= 3:
            multi_year_required = True
        current_year = datetime.now().year

        years = None
        num_years = None
        quarters = None  # For quarterly filings
        filing_periodicity = get_filing_periodicity(filing_type)

        # Show filing type hint
        if filing_periodicity == 'quarterly':
            st.info(f"📊 **{filing_type}** is a quarterly filing (Q1, Q2, Q3 per fiscal year)")
        elif filing_periodicity == 'event':
            st.info(f"📊 **{filing_type}** is an event-based filing (filed when material events occur)")
        else:
            st.info(f"📊 **{filing_type}** is an annual filing (one per fiscal year)")

        if filing_periodicity == 'quarterly':
            # QUARTERLY FILING SELECTION
            if multi_year_required:
                st.warning("⚠️ This analysis type requires multiple periods (minimum 3).")

            quarter_mode = st.radio(
                "Selection Method",
                options=["Recent Quarters", "Specific Quarters"],
                horizontal=True,
                key="single_quarter_mode"
            )

            if quarter_mode == "Recent Quarters":
                min_quarters = 3 if multi_year_required else 1
                num_quarters = st.slider(
                    "Number of recent quarters",
                    min_value=min_quarters, max_value=12, value=max(4, min_quarters),
                    key="single_num_quarters"
                )
                num_years = num_quarters  # We'll use num_years to pass the count
                st.info(f"📅 Will analyze the {num_quarters} most recent {filing_type} filings")

            else:  # Specific Quarters
                st.markdown("Select specific fiscal year + quarter combinations:")
                col1, col2 = st.columns(2)
                with col1:
                    selected_years = st.multiselect(
                        "Fiscal Years",
                        options=list(range(current_year, current_year - 10, -1)),
                        default=[current_year, current_year - 1] if not multi_year_required else [current_year, current_year - 1, current_year - 2],
                        key="single_quarter_years"
                    )
                with col2:
                    selected_quarters = st.multiselect(
                        "Quarters",
                        options=["Q1", "Q2", "Q3"],
                        default=["Q1", "Q2", "Q3"],
                        key="single_quarter_quarters"
                    )

                # Build year-quarter combinations
                quarters = []
                for y in sorted(selected_years, reverse=True):
                    for q in ["Q3", "Q2", "Q1"]:  # Reverse order for recent first
                        if q in selected_quarters:
                            quarters.append(f"{y}-{q}")

                if multi_year_required and len(quarters) < 3:
                    st.error(f"❌ Please select at least 3 quarter periods. You selected {len(quarters)}.")
                    quarters = None
                elif len(quarters) == 0:
                    st.error("❌ Please select at least one year and quarter.")
                    quarters = None
                else:
                    st.info(f"📅 Will analyze {len(quarters)} quarters: {', '.join(quarters[:6])}{'...' if len(quarters) > 6 else ''}")
                    # Convert to years for now (backend will handle quarter logic)
                    years = sorted(set(selected_years), reverse=True)

        elif filing_periodicity == 'event':
            # EVENT-BASED FILING SELECTION (8-K, etc.)
            st.markdown("Event filings are filed when material events occur. Select how many recent filings to analyze.")

            if multi_year_required:
                st.warning("⚠️ This analysis type requires multiple filings (minimum 3).")

            min_filings = 3 if multi_year_required else 1
            num_filings = st.slider(
                "Number of recent filings",
                min_value=min_filings, max_value=20, value=max(5, min_filings),
                key="single_num_event_filings"
            )
            num_years = num_filings  # We'll use this to pass the count
            st.info(f"📅 Will analyze the {num_filings} most recent {filing_type} filings")

        else:
            # ANNUAL FILING SELECTION (10-K, 20-F, etc.)
            if multi_year_required:
                st.warning("⚠️ This analysis type requires multiple years of data (minimum 3 years).")

                year_mode = st.radio(
                    "Selection Method",
                    options=["Last N Years", "Specific Years", "Year Range"],
                    horizontal=True,
                    key="single_multi_year_mode"
                )

                if year_mode == "Last N Years":
                    num_years = st.slider("Number of recent years", min_value=3, max_value=15, value=5, key="single_num_years")
                    preview_years = list(range(current_year, current_year - num_years, -1))
                    st.info(f"📅 Will analyze: {', '.join(map(str, preview_years))}")

                elif year_mode == "Specific Years":
                    years_input = st.text_input(
                        "Enter years (comma-separated)",
                        value=f"{current_year}, {current_year-1}, {current_year-2}, {current_year-3}, {current_year-4}",
                        key="single_specific_years"
                    )
                    try:
                        years = [int(y.strip()) for y in years_input.split(',') if y.strip()]
                        years = sorted(years, reverse=True)
                        if len(years) < 3:
                            st.error(f"❌ Please enter at least 3 years. You entered {len(years)}.")
                            years = None
                        else:
                            st.info(f"📅 Will analyze {len(years)} years: {', '.join(map(str, years))}")
                    except ValueError:
                        st.error("❌ Invalid year format.")
                        years = None

                else:  # Year Range
                    col1, col2 = st.columns(2)
                    with col1:
                        start_year = st.number_input("From Year", min_value=1995, max_value=current_year, value=current_year - 4, key="single_start_year")
                    with col2:
                        end_year = st.number_input("To Year", min_value=1995, max_value=current_year, value=current_year, key="single_end_year")

                    if end_year < start_year:
                        st.error("❌ End year must be greater than or equal to start year.")
                    elif (end_year - start_year + 1) < 3:
                        st.error(f"❌ Range must include at least 3 years.")
                    else:
                        years = list(range(end_year, start_year - 1, -1))
                        st.info(f"📅 Will analyze {len(years)} years: {start_year} to {end_year}")

            else:
                year_mode = st.radio(
                    "Selection Method",
                    options=["Single Year", "Last N Years", "Specific Years", "Year Range"],
                    horizontal=True,
                    key="single_flex_year_mode"
                )

                if year_mode == "Single Year":
                    specific_year = st.number_input("Select Year", min_value=1995, max_value=current_year, value=current_year, key="single_year")
                    years = [specific_year]
                    st.info(f"📅 Will analyze fiscal year {specific_year}")

                elif year_mode == "Last N Years":
                    num_years = st.slider("Number of recent years", min_value=1, max_value=15, value=3, key="single_flex_num_years")
                    preview_years = list(range(current_year, current_year - num_years, -1))
                    st.info(f"📅 Will analyze: {', '.join(map(str, preview_years))}")

                elif year_mode == "Specific Years":
                    years_input = st.text_input(
                        "Enter years (comma-separated)",
                        value=f"{current_year}, {current_year-1}, {current_year-2}",
                        key="single_flex_specific_years"
                    )
                    try:
                        years = [int(y.strip()) for y in years_input.split(',') if y.strip()]
                        years = sorted(years, reverse=True)
                        if len(years) == 0:
                            st.error("❌ Please enter at least 1 year.")
                            years = None
                        else:
                            st.info(f"📅 Will analyze {len(years)} year{'s' if len(years) > 1 else ''}: {', '.join(map(str, years))}")
                    except ValueError:
                        st.error("❌ Invalid year format.")
                        years = None

                else:  # Year Range
                    col1, col2 = st.columns(2)
                    with col1:
                        start_year = st.number_input("From Year", min_value=1995, max_value=current_year, value=current_year - 2, key="single_flex_start_year")
                    with col2:
                        end_year = st.number_input("To Year", min_value=1995, max_value=current_year, value=current_year, key="single_flex_end_year")

                    if end_year < start_year:
                        st.error("❌ End year must be greater than or equal to start year.")
                    else:
                        years = list(range(end_year, start_year - 1, -1))
                        st.info(f"📅 Will analyze {len(years)} years: {start_year} to {end_year}")

        # Advanced options
        with st.expander("⚙️ Advanced Options", expanded=False):
            use_custom_prompt = st.checkbox("Use custom prompt", key="single_use_custom")

            custom_prompt_template = None
            if use_custom_prompt:
                db = st.session_state.db
                prompts = db.get_prompts_by_type(analysis_type)

                if prompts:
                    prompt_names = [p['name'] for p in prompts]
                    selected_prompt_name = st.selectbox("Select custom prompt", options=[""] + prompt_names, key="single_custom_prompt")

                    if selected_prompt_name:
                        prompt_data = db.get_prompt_by_name(selected_prompt_name)
                        if prompt_data:
                            custom_prompt_template = prompt_data['prompt_template']
                            st.text_area("Prompt Preview", value=custom_prompt_template, height=200, disabled=True)
                else:
                    st.info("No custom prompts saved for this analysis type. Go to Settings to create one.")

        # Submit button
        if st.button("🚀 Run Analysis", type="primary", width="stretch", key="single_submit"):
            if not ticker:
                st.error("❌ Please enter a ticker symbol")
            else:
                is_valid, error_msg = validate_ticker(ticker)
                if not is_valid:
                    st.error(f"❌ Invalid ticker: {error_msg}")
                elif years is None and num_years is None:
                    st.error("❌ Please select a valid time period")
                else:
                    params = {
                        'ticker': ticker,
                        'analysis_type': analysis_type,
                        'filing_type': filing_type,
                        'years': years,
                        'num_years': num_years,
                        'custom_prompt': custom_prompt_template,
                        'company_name': company_name if company_name else None
                    }

                    thread = threading.Thread(
                        target=run_analysis_background,
                        args=(st.session_state.analysis_service, params),
                        daemon=True
                    )
                    thread.start()

                    st.session_state.check_status = True
                    st.session_state.start_wait_count = 0

                    time.sleep(0.5)
                    st.rerun()

    # ============== MULTIPLE COMPANIES MODE ==============
    else:
        st.subheader("Multiple Companies Analysis")
        st.markdown("Analyze multiple companies in parallel")

        # Input method tabs
        input_tab1, input_tab2 = st.tabs(["📁 CSV Upload", "✍️ Manual Entry"])

        with input_tab1:
            st.markdown("""
            Upload a CSV file with the following columns:
            - **ticker** (required): Stock ticker symbol
            - **analysis_type** (optional): fundamental, excellent, objective, buffett, taleb, contrarian, multi, scanner
            - **filing_type** (optional): 10-K, 10-Q, etc.
            - **company_name** (optional): Company name for display
            """)

            with st.expander("📄 View Example CSV Template"):
                example_df = pd.DataFrame({
                    'ticker': ['AAPL', 'MSFT', 'GOOGL'],
                    'analysis_type': ['fundamental', 'buffett', 'taleb'],
                    'filing_type': ['10-K', '10-K', '10-K'],
                    'company_name': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.']
                })
                st.dataframe(example_df, width="stretch", hide_index=True)

                csv_template = example_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Template",
                    data=csv_template,
                    file_name="fintel_batch_template.csv",
                    mime="text/csv",
                    width="stretch"
                )

            uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'], key="batch_csv_upload")

            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    st.success(f"✅ Loaded {len(df)} companies from CSV")

                    if 'ticker' not in df.columns:
                        st.error("❌ CSV must have a 'ticker' column")
                    else:
                        st.dataframe(df.head(10), width="stretch")
                        st.session_state['batch_csv_df'] = df
                except Exception as e:
                    st.error(f"Error reading CSV: {e}")

        with input_tab2:
            st.markdown("Enter multiple ticker symbols (comma or newline separated)")

            ticker_input = st.text_area(
                "Ticker Symbols",
                placeholder="AAPL, MSFT, GOOGL\nor one per line",
                height=100,
                key="batch_manual_tickers"
            )

        st.markdown("---")

        # Default settings for batch
        st.subheader("Batch Settings")

        col1, col2 = st.columns(2)

        with col1:
            batch_analysis_type = st.selectbox(
                "Analysis Type (applies to all)",
                options=["fundamental", "excellent", "objective", "buffett", "taleb", "contrarian", "multi", "scanner"],
                index=0,
                key="batch_analysis_type"
            )

        with col2:
            batch_filing_type = st.selectbox(
                "Filing Type (applies to all)",
                options=["10-K", "10-Q", "8-K", "4", "DEF 14A"],
                index=0,
                key="batch_filing_type"
            )

        # Year selection for batch
        st.subheader("Time Period (applies to all)")

        batch_multi_year_required = batch_analysis_type in ['excellent', 'objective', 'scanner']
        current_year = datetime.now().year

        batch_years = None
        batch_num_years = None

        if batch_multi_year_required:
            st.warning("⚠️ This analysis type requires at least 3 years.")
            batch_num_years = st.slider("Number of recent years", min_value=3, max_value=15, value=5, key="batch_num_years")
            preview_years = list(range(current_year, current_year - batch_num_years, -1))
            st.info(f"📅 Will analyze: {', '.join(map(str, preview_years))}")
        else:
            batch_year_mode = st.radio(
                "Selection Method",
                options=["Single Year", "Last N Years"],
                horizontal=True,
                key="batch_year_mode"
            )

            if batch_year_mode == "Single Year":
                batch_year = st.number_input("Year", min_value=1995, max_value=current_year, value=current_year, key="batch_single_year")
                batch_years = [batch_year]
                st.info(f"📅 Will analyze fiscal year {batch_year}")
            else:
                batch_num_years = st.slider("Number of recent years", min_value=1, max_value=15, value=3, key="batch_flex_num_years")
                preview_years = list(range(current_year, current_year - batch_num_years, -1))
                st.info(f"📅 Will analyze: {', '.join(map(str, preview_years))}")

        # Submit batch
        if st.button("🚀 Run Batch Analysis", type="primary", width="stretch", key="batch_submit"):
            configs = []
            invalid_tickers = []

            # Check for CSV data first
            if 'batch_csv_df' in st.session_state and st.session_state.batch_csv_df is not None:
                df = st.session_state.batch_csv_df

                for idx, row in df.iterrows():
                    ticker = str(row['ticker']).strip().upper()

                    if not ticker:
                        continue

                    is_valid, error_msg = validate_ticker(ticker)
                    if not is_valid:
                        invalid_tickers.append((ticker, error_msg))
                        continue

                    # Get analysis type (from CSV or default)
                    analysis_type = batch_analysis_type
                    if 'analysis_type' in df.columns and pd.notna(row['analysis_type']):
                        analysis_type = str(row['analysis_type']).strip().lower()

                    # Get company name if provided
                    company_name = None
                    if 'company_name' in df.columns and pd.notna(row['company_name']):
                        company_name = str(row['company_name']).strip()

                    # Get filing type (from CSV or default)
                    filing_type = batch_filing_type
                    if 'filing_type' in df.columns and pd.notna(row['filing_type']):
                        filing_type = str(row['filing_type']).strip()

                    config = {
                        'ticker': ticker,
                        'analysis_type': analysis_type,
                        'filing_type': filing_type,
                        'years': batch_years,
                        'num_years': batch_num_years,
                        'custom_prompt': None,
                        'company_name': company_name
                    }
                    configs.append(config)

            # Check for manual entry
            elif ticker_input.strip():
                tickers = [t.strip().upper() for t in ticker_input.replace(',', '\n').split('\n') if t.strip()]

                for ticker in tickers:
                    is_valid, error_msg = validate_ticker(ticker)
                    if is_valid:
                        config = {
                            'ticker': ticker,
                            'analysis_type': batch_analysis_type,
                            'filing_type': batch_filing_type,
                            'years': batch_years,
                            'num_years': batch_num_years,
                            'custom_prompt': None,
                            'company_name': None
                        }
                        configs.append(config)
                    else:
                        invalid_tickers.append((ticker, error_msg))

            # Show validation warnings
            if invalid_tickers:
                st.warning(f"⚠️ Skipped {len(invalid_tickers)} invalid ticker(s):")
                for ticker, msg in invalid_tickers[:10]:
                    st.caption(f"  - {ticker}: {msg}")

            if not configs:
                st.error("❌ No valid companies found. Please enter tickers or upload a CSV.")
            else:
                st.info(f"Starting batch analysis for {len(configs)} companies...")

                thread = threading.Thread(
                    target=run_batch_analysis_background,
                    args=(st.session_state.analysis_service, configs),
                    daemon=True
                )
                thread.start()

                st.session_state.batch_monitoring = True

                time.sleep(1)
                st.rerun()
