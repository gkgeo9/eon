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


# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

if 'analysis_service' not in st.session_state:
    st.session_state.analysis_service = AnalysisService(st.session_state.db)

if 'current_run_id' not in st.session_state:
    st.session_state.current_run_id = None

if 'check_status' not in st.session_state:
    st.session_state.check_status = False


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
if st.session_state.check_status and st.session_state.current_run_id:
    run_id = st.session_state.current_run_id
    status = st.session_state.db.get_run_status(run_id)

    if status == 'completed':
        st.success("✅ Analysis completed successfully!")
        st.session_state.check_status = False

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 View Results", type="primary", use_container_width=True):
                st.session_state.view_run_id = run_id
                st.switch_page("pages/3_🔍_Results_Viewer.py")
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

    elif status == 'running':
        st.info("🔄 Analysis in progress... This may take a few minutes.")
        st.markdown("The analysis is running in the background. This page will refresh automatically.")

        # Progress indicator
        with st.spinner("Analyzing..."):
            time.sleep(2)
            st.rerun()
    else:
        st.warning(f"Unknown status: {status}")
        st.session_state.check_status = False

# Only show form if not currently checking status
if not st.session_state.check_status:
    # Analysis configuration form
    with st.form("analysis_form"):
        st.subheader("Analysis Configuration")

        # Ticker input
        col1, col2 = st.columns([2, 1])

        with col1:
            ticker = st.text_input(
                "Company Ticker",
                placeholder="e.g., AAPL, MSFT, GOOGL",
                help="Enter the stock ticker symbol"
            ).upper().strip()

        with col2:
            company_name = st.text_input(
                "Company Name (Optional)",
                placeholder="e.g., Apple Inc.",
                help="Optional - for display purposes"
            )

        # Analysis type selector
        analysis_type_display = st.selectbox(
            "Analysis Type",
            options=[
                "Fundamental (Single Year)",
                "Success Factors - Excellent Company (Multi-Year)",
                "Success Factors - Objective Analysis (Multi-Year)",
                "Buffett Lens (Value Investing)",
                "Taleb Lens (Antifragility & Risks)",
                "Contrarian Lens (Variant Perception)",
                "Multi-Perspective (All Three Lenses)",
                "Contrarian Scanner (Hidden Gems)"
            ],
            help="Select the type of analysis to perform"
        )

        # Map display name to internal type
        analysis_type_map = {
            "Fundamental (Single Year)": "fundamental",
            "Success Factors - Excellent Company (Multi-Year)": "excellent",
            "Success Factors - Objective Analysis (Multi-Year)": "objective",
            "Buffett Lens (Value Investing)": "buffett",
            "Taleb Lens (Antifragility & Risks)": "taleb",
            "Contrarian Lens (Variant Perception)": "contrarian",
            "Multi-Perspective (All Three Lenses)": "multi",
            "Contrarian Scanner (Hidden Gems)": "scanner"
        }
        analysis_type = analysis_type_map[analysis_type_display]

        # Show analysis type description
        analysis_descriptions = {
            "fundamental": "📋 Analyzes business model, financials, risks, and key strategies for a single year.",
            "excellent": "⭐ Multi-year analysis for proven winners - Identifies what made excellent companies succeed. Best for studying top performers (AAPL, MSFT, GOOGL). Requires multiple years.",
            "objective": "🎯 Multi-year unbiased analysis - Objective assessment of any company's distinguishing characteristics, strengths, and weaknesses. Best for screening unknown companies. Requires multiple years.",
            "buffett": "💰 Warren Buffett perspective - Economic moat, management quality, pricing power, and intrinsic value.",
            "taleb": "🛡️ Nassim Taleb perspective - Fragility assessment, tail risks, and antifragility.",
            "contrarian": "🔍 Contrarian perspective - Variant perception, hidden opportunities, market mispricings.",
            "multi": "🎭 Combined analysis through all three investment lenses (Buffett, Taleb, Contrarian).",
            "scanner": "💎 Contrarian Scanner - 6-dimension scoring (0-600) to identify companies with hidden compounder potential through strategic anomalies and asymmetric resources."
        }
        st.info(analysis_descriptions[analysis_type])

        # Filing type
        filing_type = st.selectbox(
            "Filing Type",
            options=["10-K"],
            index=0,
            help="Type of SEC filing to analyze (10-K is annual report)"
        )

        # Year selection
        st.subheader("Years to Analyze")

        # Check if multi-year analysis is required
        multi_year_required = analysis_type in ['excellent', 'objective', 'scanner']

        if multi_year_required:
            st.warning("⚠️ This analysis type requires multiple years of data for meaningful insights.")
            num_years = st.slider(
                "Number of recent years",
                min_value=3,
                max_value=15,
                value=5,
                help="Multi-year analyses require at least 3 years. 5-10 years recommended for best insights."
            )
            years = None
            st.info(f"Will analyze the last {num_years} {filing_type} filings")
        else:
            year_mode = st.radio(
                "Selection Method",
                options=["Most Recent Year", "Number of Years", "Specific Year"],
                horizontal=True
            )

            current_year = datetime.now().year

            if year_mode == "Most Recent Year":
                num_years = 1
                years = None
                st.info(f"Will analyze the most recent {filing_type} filing (likely {current_year} or {current_year-1})")
            elif year_mode == "Number of Years":
                num_years = st.slider(
                    "Number of recent years",
                    min_value=2,
                    max_value=10,
                    value=3,
                    help="Analyze this many most recent years"
                )
                years = None
                st.info(f"Will analyze the last {num_years} {filing_type} filings")
            else:  # Specific Year
                specific_year = st.number_input(
                    "Select Year",
                    min_value=1995,
                    max_value=current_year,
                    value=current_year,
                    step=1,
                    help="Select a specific fiscal year to analyze"
                )
                years = [specific_year]
                num_years = None
                st.info(f"Will analyze {filing_type} for fiscal year {specific_year}")

        # Custom prompt (basic version)
        st.subheader("Custom Prompt (Optional)")

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

        # Submit button
        submitted = st.form_submit_button(
            "🚀 Run Analysis",
            type="primary",
            use_container_width=True
        )

        if submitted:
            # Validation
            if not ticker:
                st.error("❌ Please enter a ticker symbol")
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

                # Small delay to let thread start
                time.sleep(0.5)

                # Rerun to show progress
                st.rerun()
