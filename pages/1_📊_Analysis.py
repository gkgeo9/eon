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
from fintel.core import get_filing_category
from fintel.core.analysis_types import (
    ANALYSIS_TYPES,
    DEFAULT_FILING_TYPES,
    get_analysis_type,
    get_ui_options,
    requires_multi_year,
)

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


def get_available_filing_types(ticker: str, service: AnalysisService, input_mode: str = "ticker") -> list:
    """Get available filing types via the shared AnalysisService."""
    try:
        return service.get_available_filing_types(ticker, input_mode=input_mode)
    except Exception as e:
        st.warning(f"Could not fetch filing types for {ticker}: {str(e)}")
        return list(DEFAULT_FILING_TYPES)


def run_analysis_background(service, params, result_container):
    """
    Run analysis in background thread and store result in container.

    Args:
        service: AnalysisService instance
        params: Analysis parameters
        result_container: Dict to store {'run_id': str, 'error': str or None}
    """
    try:
        run_id = service.run_analysis(**params)
        result_container['run_id'] = run_id
        result_container['error'] = None
    except Exception as e:
        result_container['run_id'] = None
        result_container['error'] = str(e)


def run_single_analysis_thread(service, config, run_ids_list, run_ids_lock, ticker, errors_dict, errors_lock):
    """Run a single analysis in a thread (for batch processing)."""
    try:
        run_id = service.run_analysis(**config)
        with run_ids_lock:
            run_ids_list.append(run_id)
    except Exception as e:
        with errors_lock:
            errors_dict[ticker] = str(e)


def run_batch_analysis_background(service, ticker_configs, result_container):
    """
    Submit multiple analyses to run in parallel background threads.

    Args:
        service: AnalysisService instance
        ticker_configs: List of analysis config dicts
        result_container: Dict to store {'run_ids': list, 'errors': dict}
    """
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

    # Store results in container (no st.session_state access from thread)
    with run_ids_lock:
        result_container['run_ids'] = list(run_ids)
    with errors_lock:
        result_container['errors'] = dict(errors)


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

        # Input mode toggle (Ticker vs CIK)
        input_mode = st.radio(
            "Input Mode",
            options=["Ticker", "CIK"],
            horizontal=True,
            key="input_mode_radio",
            help="Ticker: Stock symbol (e.g., AAPL). CIK: SEC's 10-digit company ID (e.g., 0001018724 for Enron)"
        )

        # Ticker/CIK input - adapts based on mode
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            if input_mode == "Ticker":
                ticker = st.text_input(
                    "Company Ticker",
                    placeholder="e.g., AAPL, MSFT, GOOGL",
                    help="Enter the stock ticker symbol",
                    key="ticker_input"
                ).upper().strip()
            else:
                ticker = st.text_input(
                    "CIK Number",
                    placeholder="e.g., 0001018724 (Enron)",
                    help="Enter the SEC Central Index Key (10 digits, leading zeros optional)",
                    key="cik_input"
                ).strip()

        with col2:
            company_name = st.text_input(
                "Company Name (Optional)",
                placeholder="e.g., Apple Inc.",
                help="Optional - for display purposes. Auto-filled for CIK lookups.",
                key="company_name_input"
            )

        with col3:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("📋 Get Filing Types", help="Query SEC to find available filing types"):
                if ticker:
                    with st.spinner(f"Querying SEC for {ticker}..."):
                        mode = "cik" if input_mode == "CIK" else "ticker"
                        filing_types = get_available_filing_types(
                            ticker, st.session_state.analysis_service, input_mode=mode
                        )
                        st.session_state.available_filing_types = filing_types
                        st.session_state.last_queried_ticker = ticker
                        st.success(f"Found {len(filing_types)} filing types")
                else:
                    st.warning("Please enter a ticker or CIK first")

        # Show company info preview for CIK mode
        if input_mode == "CIK" and ticker and len(ticker) >= 1:
            # Check cache first
            cached = st.session_state.db.get_cached_cik_company(ticker)
            if cached:
                st.info(f"**Company:** {cached['company_name']}")
                if cached.get('former_names'):
                    former_names = cached['former_names']
                    if isinstance(former_names, list) and former_names:
                        names = [n.get('name', str(n)) if isinstance(n, dict) else str(n) for n in former_names[:3]]
                        st.caption(f"Former names: {', '.join(names)}")

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
                    mode = "cik" if input_mode == "CIK" else "ticker"
                    filing_types = get_available_filing_types(
                        ticker, st.session_state.analysis_service, input_mode=mode
                    )
                    st.session_state.available_filing_types = filing_types
                    st.session_state.last_queried_ticker = ticker
                    st.session_state.pending_ticker = None

        # Build analysis type options from shared registry + custom workflows
        custom_workflows = list_workflows()
        analysis_options, analysis_type_map = get_ui_options(
            include_custom_workflows=True,
            custom_workflows=custom_workflows,
        )

        # Analysis type selector
        analysis_type_display = st.selectbox(
            "Analysis Type",
            options=analysis_options,
            help="Select the type of analysis to perform",
            key="single_analysis_type"
        )

        # Map display name to internal type (from shared registry)
        if analysis_type_display.startswith("─"):
            # Separator line, default to fundamental
            analysis_type = "fundamental"
        else:
            analysis_type = analysis_type_map.get(analysis_type_display, "fundamental")

        is_custom_workflow = analysis_type.startswith("custom:")
        custom_workflow_id = analysis_type.split(":", 1)[1] if is_custom_workflow else None
        custom_workflow_min_years = 1
        if is_custom_workflow and custom_workflow_id:
            for wf in custom_workflows:
                if wf['id'] == custom_workflow_id:
                    custom_workflow_min_years = wf.get('min_years', 1)
                    break

        # Show analysis type description (from shared registry)
        if is_custom_workflow and custom_workflow_id:
            for wf in custom_workflows:
                if wf['id'] == custom_workflow_id:
                    min_years_note = f" **Requires at least {wf['min_years']} years**." if wf['min_years'] > 1 else ""
                    st.info(f"{wf['icon']} {wf['description']}{min_years_note}")
                    break
        else:
            type_info = get_analysis_type(analysis_type)
            if type_info:
                min_note = f" **Requires at least {type_info.min_years} years**." if type_info.min_years > 1 else ""
                st.info(f"{type_info.icon} {type_info.description}{min_note}")

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

        # Check if multi-year is required (from shared registry or custom workflow)
        multi_year_required = requires_multi_year(analysis_type)
        if is_custom_workflow and custom_workflow_min_years >= 3:
            multi_year_required = True
        current_year = datetime.now().year

        years = None
        num_years = None
        quarters = None  # For quarterly filings
        filing_periodicity = get_filing_category(filing_type)

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
            st.markdown(f"""
**Event filings ({filing_type})** are filed when material events occur, not on a fixed schedule.
They can occur multiple times per year. Fintel will fetch the N most recent filings automatically.
            """)

            if multi_year_required:
                st.warning("⚠️ This analysis type requires multiple filings (minimum 3).")

            min_filings = 3 if multi_year_required else 1
            num_filings = st.slider(
                "Number of recent filings to analyze",
                min_value=min_filings, max_value=20, value=max(5, min_filings),
                key="single_num_event_filings",
                help="Fetches this many most recent filings, regardless of year/date"
            )
            num_years = num_filings  # We'll use this to pass the count
            st.info(f"📋 Will analyze the {num_filings} most recent {filing_type} filings available")

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
                    # Show preview but note that actual years may differ based on availability
                    preview_years = list(range(current_year - 1, current_year - 1 - num_years, -1))
                    st.info(f"📅 Will analyze up to {num_years} most recent available years (e.g., {', '.join(map(str, preview_years[:3]))}...)")

                elif year_mode == "Specific Years":
                    # Default to previous years (current year often not available in early months)
                    years_input = st.text_input(
                        "Enter years (comma-separated)",
                        value=f"{current_year-1}, {current_year-2}, {current_year-3}, {current_year-4}, {current_year-5}",
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
                    # Default to previous year (current year often not available in early months)
                    specific_year = st.number_input("Select Year", min_value=1995, max_value=current_year, value=current_year - 1, key="single_year")
                    years = [specific_year]
                    st.info(f"📅 Will analyze fiscal year {specific_year}")

                elif year_mode == "Last N Years":
                    num_years = st.slider("Number of recent years", min_value=1, max_value=15, value=3, key="single_flex_num_years")
                    # Show preview but note actual years depend on availability
                    preview_years = list(range(current_year - 1, current_year - 1 - num_years, -1))
                    st.info(f"📅 Will analyze up to {num_years} most recent available years")

                elif year_mode == "Specific Years":
                    # Default to previous years (current year often not available in early months)
                    years_input = st.text_input(
                        "Enter years (comma-separated)",
                        value=f"{current_year-1}, {current_year-2}, {current_year-3}",
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
                st.error("❌ Please enter a ticker symbol or CIK")
            else:
                # Use mode-aware validation
                from fintel.ui.utils.validators import validate_company_identifier
                is_valid, error_msg = validate_company_identifier(
                    ticker,
                    mode='cik' if input_mode == "CIK" else 'ticker'
                )
                if not is_valid:
                    st.error(f"❌ Invalid {'CIK' if input_mode == 'CIK' else 'ticker'}: {error_msg}")
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
                        'company_name': company_name if company_name else None,
                        'input_mode': 'cik' if input_mode == "CIK" else 'ticker'
                    }

                    # Use a result container to avoid st.session_state access from thread
                    result_container = {}
                    thread = threading.Thread(
                        target=run_analysis_background,
                        args=(st.session_state.analysis_service, params, result_container),
                        daemon=True
                    )
                    thread.start()

                    # Wait for thread to populate result_container (with timeout)
                    # The DB record is created immediately, so we wait for that
                    max_wait = 10  # seconds
                    waited = 0
                    while waited < max_wait and 'run_id' not in result_container and 'error' not in result_container:
                        time.sleep(0.1)
                        waited += 0.1

                    # Copy results to session state (main thread)
                    st.session_state.current_run_id = result_container.get('run_id')
                    if result_container.get('error'):
                        st.session_state.current_run_id_error = result_container['error']

                    st.session_state.check_status = True
                    st.session_state.start_wait_count = 0

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

        # Build analysis type options from shared registry (same as single mode)
        batch_custom_workflows = list_workflows()
        batch_analysis_options, batch_analysis_type_map = get_ui_options(
            include_custom_workflows=True,
            custom_workflows=batch_custom_workflows,
        )

        col1, col2 = st.columns(2)

        with col1:
            batch_analysis_type_display = st.selectbox(
                "Analysis Type (applies to all)",
                options=batch_analysis_options,
                index=0,
                key="batch_analysis_type"
            )

            # Map display name to internal type (from shared registry)
            if batch_analysis_type_display.startswith("─"):
                batch_analysis_type = "fundamental"
            else:
                batch_analysis_type = batch_analysis_type_map.get(
                    batch_analysis_type_display, "fundamental"
                )

            batch_is_custom_workflow = batch_analysis_type.startswith("custom:")
            batch_custom_workflow_id = (
                batch_analysis_type.split(":", 1)[1] if batch_is_custom_workflow else None
            )
            batch_custom_workflow_min_years = 1
            if batch_is_custom_workflow and batch_custom_workflow_id:
                for wf in batch_custom_workflows:
                    if wf['id'] == batch_custom_workflow_id:
                        batch_custom_workflow_min_years = wf.get('min_years', 1)
                        break

        with col2:
            batch_filing_type = st.selectbox(
                "Filing Type (applies to all)",
                options=["10-K", "10-Q", "8-K", "4", "DEF 14A"],
                index=0,
                key="batch_filing_type"
            )

        # Show analysis type description (from shared registry)
        if batch_is_custom_workflow and batch_custom_workflow_id:
            for wf in batch_custom_workflows:
                if wf['id'] == batch_custom_workflow_id:
                    min_years_note = f" **Requires at least {wf['min_years']} years**." if wf['min_years'] > 1 else ""
                    st.info(f"{wf['icon']} {wf['description']}{min_years_note}")
                    break
        else:
            batch_type_info = get_analysis_type(batch_analysis_type)
            if batch_type_info:
                min_note = f" **Requires at least {batch_type_info.min_years} years**." if batch_type_info.min_years > 1 else ""
                st.info(f"{batch_type_info.icon} {batch_type_info.description}{min_note}")

        # Year selection for batch
        st.subheader("Time Period (applies to all)")

        batch_multi_year_required = requires_multi_year(batch_analysis_type)
        if batch_is_custom_workflow and batch_custom_workflow_min_years >= 3:
            batch_multi_year_required = True
        current_year = datetime.now().year

        batch_years = None
        batch_num_years = None

        if batch_multi_year_required:
            st.warning("⚠️ This analysis type requires at least 3 years.")
            batch_num_years = st.slider("Number of recent years", min_value=3, max_value=15, value=5, key="batch_num_years")
            preview_years = list(range(current_year - 1, current_year - 1 - batch_num_years, -1))
            st.info(f"📅 Will analyze up to {batch_num_years} most recent available years (e.g., {', '.join(map(str, preview_years[:3]))}...)")
        else:
            batch_year_mode = st.radio(
                "Selection Method",
                options=["Single Year", "Last N Years"],
                horizontal=True,
                key="batch_year_mode"
            )

            if batch_year_mode == "Single Year":
                # Default to previous year (current year often not available in early months)
                batch_year = st.number_input("Year", min_value=1995, max_value=current_year, value=current_year - 1, key="batch_single_year")
                batch_years = [batch_year]
                st.info(f"📅 Will analyze fiscal year {batch_year}")
            else:
                batch_num_years = st.slider("Number of recent years", min_value=1, max_value=15, value=3, key="batch_flex_num_years")
                st.info(f"📅 Will analyze up to {batch_num_years} most recent available years")

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

                # Use a result container to avoid st.session_state access from thread
                result_container = {}
                thread = threading.Thread(
                    target=run_batch_analysis_background,
                    args=(st.session_state.analysis_service, configs, result_container),
                    daemon=True
                )
                thread.start()

                # Wait for threads to start
                time.sleep(1)

                # Copy results to session state (main thread)
                st.session_state.batch_run_ids = result_container.get('run_ids', [])
                st.session_state.batch_errors = result_container.get('errors', {})

                st.session_state.batch_monitoring = True
                st.rerun()
