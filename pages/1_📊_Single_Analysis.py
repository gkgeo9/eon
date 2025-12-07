#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Single Analysis Page - Main interface for running analyses.
"""

import streamlit as st
import threading
import time
from datetime import datetime

from fintel.ui.database import DatabaseRepository
from fintel.ui.services import AnalysisService
from fintel.ui.theme import apply_theme

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


def run_analysis_background(service, params, run_id_key='current_run_id'):
    """Run analysis in background thread and store run_id in session state."""
    try:
        run_id = service.run_analysis(**params)
        st.session_state[run_id_key] = run_id
    except Exception as e:
        st.session_state[f'{run_id_key}_error'] = str(e)
        st.session_state[run_id_key] = None


# Page content
st.title("📊 Single Company Analysis")
st.markdown("Analyze SEC filings with AI-powered perspectives")

st.markdown("---")

# Check if we're monitoring a running analysis
if st.session_state.check_status:
    if st.session_state.current_run_id:
        run_id = st.session_state.current_run_id
        status = st.session_state.db.get_run_status(run_id)

        if status == 'completed':
            st.success("✅ Analysis completed successfully!")
            st.session_state.check_status = False

            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 View Results", type="primary", use_container_width=True):
                    st.session_state.view_run_id = run_id
                    st.switch_page("pages/4_🔍_Results_Viewer.py")
            with col2:
                if st.button("🏠 Back to Home", use_container_width=True):
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
                if st.button("📜 View in History", type="primary", use_container_width=True):
                    st.switch_page("pages/3_📈_Analysis_History.py")
            with col2:
                if st.button("➕ Start New Analysis", use_container_width=True):
                    st.session_state.current_run_id = None
                    st.rerun()
        else:
            st.warning(f"Unknown status: {status}")
            st.session_state.check_status = False

    else:
        # Waiting for background thread to start and set run_id
        st.session_state.start_wait_count += 1

        # Check for errors from background thread
        if 'current_run_id_error' in st.session_state:
            st.error(f"❌ Failed to start analysis: {st.session_state.current_run_id_error}")
            st.session_state.check_status = False
            st.session_state.start_wait_count = 0
            del st.session_state['current_run_id_error']
            if st.button("Try Again"):
                st.rerun()
        # Timeout after 10 attempts (10 seconds)
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

# Only show configuration if not currently checking status
if not st.session_state.check_status:
    # Analysis configuration (no form - fully reactive)
    st.subheader("Analysis Configuration")

    # Ticker input
    col1, col2 = st.columns([2, 1])

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

    # Analysis type selector - Clean names without single/multi labels
    analysis_type_display = st.selectbox(
        "Analysis Type",
        options=[
            "Fundamental Analysis",
            "Excellent Company Success Factors",
            "Objective Company Analysis",
            "Buffett Lens",
            "Taleb Lens",
            "Contrarian Lens",
            "Multi-Perspective (Buffett + Taleb + Contrarian)",
            "Contrarian Scanner"
        ],
        help="Select the type of analysis to perform"
    )

    # Map display name to internal type
    analysis_type_map = {
        "Fundamental Analysis": "fundamental",
        "Excellent Company Success Factors": "excellent",
        "Objective Company Analysis": "objective",
        "Buffett Lens": "buffett",
        "Taleb Lens": "taleb",
        "Contrarian Lens": "contrarian",
        "Multi-Perspective (Buffett + Taleb + Contrarian)": "multi",
        "Contrarian Scanner": "scanner"
    }
    analysis_type = analysis_type_map[analysis_type_display]

    # Show analysis type description
    analysis_descriptions = {
        "fundamental": "📋 Analyzes business model, financials, risks, and key strategies. Works with single or multiple years.",
        "excellent": "⭐ Multi-year analysis for proven winners - identifies what made excellent companies succeed. Best for studying top performers like AAPL, MSFT, GOOGL. **Requires at least 3 years**.",
        "objective": "🎯 Multi-year unbiased analysis - objective assessment of any company's strengths and weaknesses. Best for screening unknown companies. **Requires at least 3 years**.",
        "buffett": "💰 Warren Buffett perspective: economic moat, management quality, pricing power, and intrinsic value. Works with single or multiple years.",
        "taleb": "🛡️ Nassim Taleb perspective: fragility assessment, tail risks, and antifragility. Works with single or multiple years.",
        "contrarian": "🔍 Contrarian perspective: variant perception, hidden opportunities, and market mispricings. Works with single or multiple years.",
        "multi": "🎭 Combined analysis through all three investment lenses: Buffett (value investing), Taleb (antifragility), and Contrarian (variant perception). Works with single or multiple years.",
        "scanner": "💎 Six-dimension scoring system (0-600 scale) to identify companies with hidden compounder potential through strategic anomalies and asymmetric resources. **Requires at least 3 years**."
    }
    st.info(analysis_descriptions[analysis_type])

    # Filing type
    filing_type = st.selectbox(
        "Filing Type",
        options=["10-K", "10-Q", "8-K", "4", "DEF 14A"],
        index=0,
        help="""Type of SEC filing to analyze:
• 10-K: Annual report (comprehensive)
• 10-Q: Quarterly report (3x per year)
• 8-K: Current report (material events)
• 4: Insider trading report
• DEF 14A: Proxy statement (voting/governance)"""
    )

    # Year selection
    st.subheader("Time Period Selection")

    # Check if multi-year analysis is required
    multi_year_required = analysis_type in ['excellent', 'objective', 'scanner']
    current_year = datetime.now().year

    # Initialize years variables
    years = None
    num_years = None

    if multi_year_required:
        st.warning("⚠️ This analysis type requires multiple years of data (minimum 3 years).")

        year_mode = st.radio(
            "Selection Method",
            options=["Last N Years", "Specific Years", "Year Range"],
            horizontal=True,
            key="multi_year_mode"
        )

        if year_mode == "Last N Years":
            num_years = st.slider(
                "Number of recent years",
                min_value=3,
                max_value=15,
                value=5,
                help="5-10 years recommended for best insights"
            )
            years = None
            preview_years = list(range(current_year, current_year - num_years, -1))
            st.info(f"📅 Will analyze: {', '.join(map(str, preview_years))}")

        elif year_mode == "Specific Years":
            years_input = st.text_input(
                "Enter years (comma-separated)",
                value=f"{current_year}, {current_year-1}, {current_year-2}, {current_year-3}, {current_year-4}",
                help="Example: 2023, 2022, 2021, 2020, 2019",
                key="multi_specific_years_input"
            )
            try:
                years = [int(y.strip()) for y in years_input.split(',') if y.strip()]
                years = sorted(years, reverse=True)
                if len(years) < 3:
                    st.error(f"❌ Please enter at least 3 years. You entered {len(years)}.")
                    years = None
                    num_years = None
                else:
                    num_years = None
                    st.info(f"📅 Will analyze {len(years)} years: {', '.join(map(str, years))}")
            except ValueError:
                st.error("❌ Invalid year format. Please enter years as numbers separated by commas.")
                years = None
                num_years = None

        else:  # Year Range
            col1, col2 = st.columns(2)
            with col1:
                start_year = st.number_input(
                    "From Year",
                    min_value=1995,
                    max_value=current_year,
                    value=current_year - 4,
                    step=1,
                    key="multi_start_year"
                )
            with col2:
                end_year = st.number_input(
                    "To Year",
                    min_value=1995,
                    max_value=current_year,
                    value=current_year,
                    step=1,
                    key="multi_end_year"
                )

            if end_year < start_year:
                st.error("❌ End year must be greater than or equal to start year.")
                years = None
                num_years = None
            elif (end_year - start_year + 1) < 3:
                st.error(f"❌ Range must include at least 3 years. Current range: {end_year - start_year + 1} years.")
                years = None
                num_years = None
            else:
                years = list(range(end_year, start_year - 1, -1))
                num_years = None
                st.info(f"📅 Will analyze {len(years)} years: {start_year} to {end_year}")

    else:
        # Flexible analyses - support single or multiple years
        year_mode = st.radio(
            "Selection Method",
            options=["Single Year", "Last N Years", "Specific Years", "Year Range"],
            horizontal=True,
            key="flexible_year_mode"
        )

        if year_mode == "Single Year":
            specific_year = st.number_input(
                "Select Year",
                min_value=1995,
                max_value=current_year,
                value=current_year,
                step=1,
                help="Select a specific fiscal year to analyze",
                key="single_year_input"
            )
            years = [specific_year]
            num_years = None
            st.info(f"📅 Will analyze fiscal year {specific_year}")

        elif year_mode == "Last N Years":
            num_years = st.slider(
                "Number of recent years",
                min_value=1,
                max_value=15,
                value=3,
                help="Analyze this many most recent years",
                key="flex_num_years"
            )
            years = None
            preview_years = list(range(current_year, current_year - num_years, -1))
            st.info(f"📅 Will analyze: {', '.join(map(str, preview_years))}")

        elif year_mode == "Specific Years":
            years_input = st.text_input(
                "Enter years (comma-separated)",
                value=f"{current_year}, {current_year-1}, {current_year-2}",
                help="Example: 2023, 2021, 2019 (can be non-contiguous)",
                key="flex_specific_years_input"
            )
            try:
                years = [int(y.strip()) for y in years_input.split(',') if y.strip()]
                years = sorted(years, reverse=True)
                if len(years) == 0:
                    st.error("❌ Please enter at least 1 year.")
                    years = None
                    num_years = None
                else:
                    num_years = None
                    st.info(f"📅 Will analyze {len(years)} year{'s' if len(years) > 1 else ''}: {', '.join(map(str, years))}")
            except ValueError:
                st.error("❌ Invalid year format. Please enter years as numbers separated by commas.")
                years = None
                num_years = None

        else:  # Year Range
            col1, col2 = st.columns(2)
            with col1:
                start_year = st.number_input(
                    "From Year",
                    min_value=1995,
                    max_value=current_year,
                    value=current_year - 2,
                    step=1,
                    key="flex_start_year"
                )
            with col2:
                end_year = st.number_input(
                    "To Year",
                    min_value=1995,
                    max_value=current_year,
                    value=current_year,
                    step=1,
                    key="flex_end_year"
                )

            if end_year < start_year:
                st.error("❌ End year must be greater than or equal to start year.")
                years = None
                num_years = None
            else:
                years = list(range(end_year, start_year - 1, -1))
                num_years = None
                st.info(f"📅 Will analyze {len(years)} years: {start_year} to {end_year}")

    # Advanced options - collapsible
    with st.expander("⚙️ Advanced Options", expanded=False):
        use_custom_prompt = st.checkbox("Use custom prompt")

        custom_prompt_template = None
        if use_custom_prompt:
            # Get available prompts for this analysis type
            db = st.session_state.db
            prompts = db.get_prompts_by_type(analysis_type)

            if prompts:
                prompt_names = [p['name'] for p in prompts]
                selected_prompt_name = st.selectbox(
                    "Select custom prompt",
                    options=[""] + prompt_names
                )

                if selected_prompt_name:
                    prompt_data = db.get_prompt_by_name(selected_prompt_name)
                    if prompt_data:
                        custom_prompt_template = prompt_data['prompt_template']
                        with st.expander("Preview Prompt"):
                            st.text_area(
                                "Prompt Template",
                                value=custom_prompt_template,
                                height=200,
                                disabled=True
                            )
            else:
                st.info("No custom prompts saved for this analysis type. Go to Settings to create one.")

    # Submit button (now a regular button, not form_submit_button)
    if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
        # Validation
        if not ticker:
            st.error("❌ Please enter a ticker symbol")
        elif years is None and num_years is None:
            st.error("❌ Please select a valid time period")
        else:
            # Prepare parameters
            params = {
                'ticker': ticker,
                'analysis_type': analysis_type,
                'filing_type': filing_type,
                'years': years,
                'num_years': num_years,
                'custom_prompt': custom_prompt_template,
                'company_name': company_name if company_name else None
            }

            # Start analysis in background thread
            thread = threading.Thread(
                target=run_analysis_background,
                args=(st.session_state.analysis_service, params),
                daemon=True
            )
            thread.start()

            # Mark that we should check status
            st.session_state.check_status = True
            st.session_state.start_wait_count = 0

            # Small delay to let thread start
            time.sleep(0.5)

            # Rerun to show progress
            st.rerun()
