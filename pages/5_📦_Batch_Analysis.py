#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch Analysis Page - Analyze multiple companies at once.
"""

import streamlit as st
import pandas as pd
import threading
import time
import io
from datetime import datetime

from fintel.ui.database import DatabaseRepository
from fintel.ui.services import AnalysisService


# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

if 'analysis_service' not in st.session_state:
    st.session_state.analysis_service = AnalysisService(st.session_state.db)

if 'batch_run_ids' not in st.session_state:
    st.session_state.batch_run_ids = []

if 'batch_monitoring' not in st.session_state:
    st.session_state.batch_monitoring = False


def run_batch_analysis_background(service, ticker_configs):
    """Run multiple analyses in background threads."""
    run_ids = []
    for config in ticker_configs:
        try:
            run_id = service.run_analysis(**config)
            run_ids.append(run_id)
            time.sleep(0.5)  # Small delay between submissions
        except Exception as e:
            st.session_state[f'batch_error_{config["ticker"]}'] = str(e)

    st.session_state.batch_run_ids = run_ids


# Page content
st.title("📦 Batch Company Analysis")
st.markdown("Analyze multiple companies at once by uploading a CSV file")

st.markdown("---")

# Check if we're monitoring a batch
if st.session_state.batch_monitoring and st.session_state.batch_run_ids:
    st.subheader("📊 Batch Progress")

    # Get status for all runs
    statuses = []
    for run_id in st.session_state.batch_run_ids:
        details = st.session_state.db.get_run_details(run_id)
        if details:
            statuses.append({
                'run_id': run_id,
                'ticker': details['ticker'],
                'analysis_type': details['analysis_type'],
                'status': details['status'],
                'started': details.get('started_at', 'N/A')
            })

    # Create progress dataframe
    df = pd.DataFrame(statuses)

    # Count statuses
    total = len(statuses)
    completed = len(df[df['status'] == 'completed'])
    running = len(df[df['status'] == 'running'])
    failed = len(df[df['status'] == 'failed'])

    # Progress metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", total)
    with col2:
        st.metric("Completed", completed, delta=f"{(completed/total*100):.0f}%" if total > 0 else "0%")
    with col3:
        st.metric("Running", running)
    with col4:
        st.metric("Failed", failed)

    # Status indicator
    status_emojis = {
        'completed': '✅',
        'running': '🔄',
        'pending': '⏳',
        'failed': '❌'
    }
    df['status_display'] = df['status'].apply(
        lambda x: f"{status_emojis.get(x, '❓')} {x.capitalize()}"
    )

    # Display table
    st.dataframe(
        df[['ticker', 'analysis_type', 'status_display', 'started']],
        use_container_width=True,
        hide_index=True
    )

    # Auto-refresh if any are still running
    if running > 0:
        st.info(f"🔄 {running} analyses still running... Auto-refreshing every 5 seconds")
        time.sleep(5)
        st.rerun()
    else:
        st.success("✅ All batch analyses complete!")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 View Results in History", type="primary", use_container_width=True):
                st.switch_page("pages/2_📈_Analysis_History.py")
        with col2:
            if st.button("🔄 New Batch", use_container_width=True):
                st.session_state.batch_monitoring = False
                st.session_state.batch_run_ids = []
                st.rerun()

# Only show form if not monitoring
if not st.session_state.batch_monitoring:
    # CSV Upload Section
    st.subheader("📁 Upload CSV File")

    st.markdown("""
    Upload a CSV file with the following columns:
    - **ticker** (required): Stock ticker symbol (e.g., AAPL, MSFT)
    - **analysis_type** (optional): Type of analysis (defaults to fundamental)
      - Options: fundamental, excellent, objective, buffett, taleb, contrarian, multi, scanner
    - **company_name** (optional): Company name for display
    - **num_years** (optional): Number of years to analyze (default: 1 for single-year, 5 for multi-year)
    """)

    # Example CSV template
    with st.expander("📄 View Example CSV Template"):
        example_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL', 'TSLA'],
            'analysis_type': ['fundamental', 'excellent', 'objective', 'scanner'],
            'company_name': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.', 'Tesla Inc.'],
            'num_years': [1, 5, 5, 5]
        })
        st.dataframe(example_df, use_container_width=True, hide_index=True)

        csv_template = example_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Template",
            data=csv_template,
            file_name="fintel_batch_template.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("---")

    # File upload
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=['csv'],
        help="Upload a CSV with ticker symbols and optional configuration"
    )

    if uploaded_file is not None:
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file)

            st.success(f"✅ Loaded {len(df)} companies from CSV")

            # Validate required columns
            if 'ticker' not in df.columns:
                st.error("❌ CSV must have a 'ticker' column")
            else:
                # Show preview
                st.subheader("Preview")
                st.dataframe(df.head(10), use_container_width=True)

                # Default settings for all
                st.subheader("Default Settings")

                col1, col2 = st.columns(2)

                with col1:
                    default_analysis_type = st.selectbox(
                        "Default Analysis Type (if not specified in CSV)",
                        options=["fundamental", "excellent", "objective", "buffett", "taleb", "contrarian", "multi", "scanner"],
                        index=0,
                        help="This will be used for rows without an analysis_type column"
                    )

                with col2:
                    default_filing_type = st.selectbox(
                        "Filing Type",
                        options=["10-K"],
                        index=0,
                        help="Type of SEC filing to analyze"
                    )

                # Process and validate
                st.markdown("---")

                if st.button("🚀 Start Batch Analysis", type="primary", use_container_width=True):
                    # Prepare configs
                    configs = []

                    for idx, row in df.iterrows():
                        ticker = str(row['ticker']).strip().upper()

                        if not ticker:
                            continue

                        # Get analysis type (from CSV or default)
                        analysis_type = default_analysis_type
                        if 'analysis_type' in df.columns and pd.notna(row['analysis_type']):
                            analysis_type = str(row['analysis_type']).strip().lower()

                        # Get company name if provided
                        company_name = None
                        if 'company_name' in df.columns and pd.notna(row['company_name']):
                            company_name = str(row['company_name']).strip()

                        # Get num_years if provided, otherwise use defaults
                        num_years = None
                        if 'num_years' in df.columns and pd.notna(row['num_years']):
                            num_years = int(row['num_years'])
                        else:
                            # Set defaults based on analysis type
                            if analysis_type in ['excellent', 'objective', 'scanner']:
                                num_years = 5  # Multi-year analyses need more data
                            else:
                                num_years = 1

                        config = {
                            'ticker': ticker,
                            'analysis_type': analysis_type,
                            'filing_type': default_filing_type,
                            'years': None,
                            'num_years': num_years,
                            'custom_prompt': None,
                            'company_name': company_name
                        }

                        configs.append(config)

                    if configs:
                        st.info(f"Starting batch analysis for {len(configs)} companies...")

                        # Start batch in background
                        thread = threading.Thread(
                            target=run_batch_analysis_background,
                            args=(st.session_state.analysis_service, configs),
                            daemon=True
                        )
                        thread.start()

                        # Mark that we should monitor
                        st.session_state.batch_monitoring = True

                        # Small delay to let thread start
                        time.sleep(1)

                        # Rerun to show progress
                        st.rerun()
                    else:
                        st.error("No valid companies found in CSV")

        except Exception as e:
            st.error(f"Error reading CSV: {e}")

# Manual entry section
st.markdown("---")
st.subheader("✍️ Manual Entry (Alternative)")

with st.expander("Enter Tickers Manually"):
    st.markdown("Enter multiple ticker symbols separated by commas or new lines")

    ticker_input = st.text_area(
        "Ticker Symbols",
        placeholder="AAPL, MSFT, GOOGL\nor one per line",
        height=100
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        manual_analysis_type = st.selectbox(
            "Analysis Type",
            options=["fundamental", "excellent", "objective", "buffett", "taleb", "contrarian", "multi", "scanner"],
            index=0,
            key="manual_analysis_type"
        )

    with col2:
        manual_num_years = st.number_input(
            "Number of Years",
            min_value=1,
            max_value=15,
            value=5 if manual_analysis_type in ['excellent', 'objective', 'scanner'] else 1,
            key="manual_num_years"
        )

    with col3:
        manual_filing_type = st.selectbox(
            "Filing Type",
            options=["10-K"],
            index=0,
            key="manual_filing_type"
        )

    if st.button("🚀 Start Manual Batch", use_container_width=True):
        if not ticker_input.strip():
            st.error("Please enter at least one ticker symbol")
        else:
            # Parse tickers
            tickers = [t.strip().upper() for t in ticker_input.replace(',', '\n').split('\n') if t.strip()]

            if tickers:
                # Prepare configs
                configs = []
                for ticker in tickers:
                    config = {
                        'ticker': ticker,
                        'analysis_type': manual_analysis_type,
                        'filing_type': manual_filing_type,
                        'years': None,
                        'num_years': manual_num_years,
                        'custom_prompt': None,
                        'company_name': None
                    }
                    configs.append(config)

                st.info(f"Starting batch analysis for {len(configs)} companies...")

                # Start batch in background
                thread = threading.Thread(
                    target=run_batch_analysis_background,
                    args=(st.session_state.analysis_service, configs),
                    daemon=True
                )
                thread.start()

                # Mark that we should monitor
                st.session_state.batch_monitoring = True

                # Small delay to let thread start
                time.sleep(1)

                # Rerun to show progress
                st.rerun()

# Navigation
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("app.py")

with col2:
    if st.button("📊 Single Analysis", use_container_width=True):
        st.switch_page("pages/1_📊_Single_Analysis.py")

with col3:
    if st.button("📜 View History", use_container_width=True):
        st.switch_page("pages/2_📈_Analysis_History.py")
