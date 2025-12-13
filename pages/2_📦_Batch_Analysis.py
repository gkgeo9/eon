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
from fintel.ui.theme import apply_theme
from fintel.ui.utils.validators import validate_ticker

# Apply global theme
apply_theme()


# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

if 'analysis_service' not in st.session_state:
    st.session_state.analysis_service = AnalysisService(st.session_state.db)

if 'batch_run_ids' not in st.session_state:
    st.session_state.batch_run_ids = []

if 'batch_monitoring' not in st.session_state:
    st.session_state.batch_monitoring = False


def run_single_analysis_thread(service, config, run_ids_list, ticker):
    """Run a single analysis in a thread."""
    try:
        run_id = service.run_analysis(**config)
        run_ids_list.append(run_id)
    except Exception as e:
        st.session_state[f'batch_error_{ticker}'] = str(e)


def run_batch_analysis_background(service, ticker_configs):
    """Submit multiple analyses to run in parallel background threads."""
    run_ids = []
    threads = []

    # Start a thread for each analysis
    for config in ticker_configs:
        thread = threading.Thread(
            target=run_single_analysis_thread,
            args=(service, config, run_ids, config['ticker']),
            daemon=True
        )
        thread.start()
        threads.append(thread)
        time.sleep(0.1)  # Small delay to avoid overwhelming the system

    # Store the run_ids list reference (it will be populated as threads complete)
    st.session_state.batch_run_ids = run_ids


# Page content
st.title("📦 Batch Company Analysis")
st.markdown("Analyze multiple companies at once by uploading a CSV file")

st.markdown("---")

# Check if batch was just submitted
if st.session_state.batch_monitoring:
    st.success("✅ Batch analysis submitted successfully!")
    st.info("Your analyses are running in parallel in the background. View progress in the Analysis History tab.")

    # Wait briefly for run_ids to be populated
    if len(st.session_state.batch_run_ids) > 0:
        st.markdown(f"**{len(st.session_state.batch_run_ids)} analyses submitted**")

    st.session_state.batch_monitoring = False

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📜 View in History", type="primary", use_container_width=True):
            st.switch_page("pages/3_📈_Analysis_History.py")
    with col2:
        if st.button("➕ Start New Batch", use_container_width=True):
            st.session_state.batch_run_ids = []
            st.rerun()

elif False:  # Removed old monitoring code
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
                st.switch_page("pages/3_📈_Analysis_History.py")
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
    - **filing_type** (optional): SEC filing type (defaults to selection below)
      - Common: 10-K, 10-Q, 8-K, 4, DEF 14A, or any SEC filing type
    - **company_name** (optional): Company name for display
    - **year_mode** (optional): How to select years (defaults to last_n)
      - Options: last_n, specific_years, year_range, single_year
    - **years_value** (optional): Value depends on year_mode:
      - For last_n: number (e.g., 5)
      - For specific_years: comma-separated years (e.g., "2023,2022,2020")
      - For year_range: range format (e.g., "2018-2023")
      - For single_year: single year (e.g., 2023)
    """)

    # Example CSV template
    with st.expander("📄 View Example CSV Template"):
        example_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'],
            'analysis_type': ['fundamental', 'excellent', 'objective', 'scanner', 'buffett'],
            'filing_type': ['10-K', '10-Q', '10-K', '8-K', '10-K'],
            'company_name': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.', 'Tesla Inc.', 'NVIDIA Corp.'],
            'year_mode': ['single_year', 'last_n', 'specific_years', 'year_range', 'last_n'],
            'years_value': ['2023', '10', '2023,2022,2020,2019', '2018-2023', '5']
        })
        st.dataframe(example_df, use_container_width=True, hide_index=True)

        csv_template = example_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Enhanced Template",
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
                        options=["10-K", "10-Q", "8-K", "4", "DEF 14A"],
                        index=0,
                        help="""Default filing type for all companies (unless overridden in CSV).
• 10-K: Annual | • 10-Q: Quarterly | • 8-K: Events | • 4: Insider | • DEF 14A: Proxy
Optional: Add 'filing_type' column to CSV to specify per company"""
                    )

                # Process and validate
                st.markdown("---")

                if st.button("🚀 Start Batch Analysis", type="primary", use_container_width=True):
                    # Prepare configs
                    configs = []
                    invalid_tickers = []
                    current_year = datetime.now().year

                    for idx, row in df.iterrows():
                        ticker = str(row['ticker']).strip().upper()

                        if not ticker:
                            continue

                        # Validate ticker format
                        is_valid, error_msg = validate_ticker(ticker)
                        if not is_valid:
                            invalid_tickers.append((ticker, error_msg))
                            continue

                        # Get analysis type (from CSV or default)
                        analysis_type = default_analysis_type
                        if 'analysis_type' in df.columns and pd.notna(row['analysis_type']):
                            analysis_type = str(row['analysis_type']).strip().lower()

                        # Get company name if provided
                        company_name = None
                        if 'company_name' in df.columns and pd.notna(row['company_name']):
                            company_name = str(row['company_name']).strip()

                        # Get filing type (from CSV or default)
                        filing_type = default_filing_type
                        if 'filing_type' in df.columns and pd.notna(row['filing_type']):
                            filing_type = str(row['filing_type']).strip()

                        # Process year selection
                        years = None
                        num_years = None

                        # Check if new year_mode column exists
                        if 'year_mode' in df.columns and pd.notna(row['year_mode']):
                            year_mode = str(row['year_mode']).strip().lower()
                            years_value = str(row.get('years_value', '')).strip() if 'years_value' in df.columns and pd.notna(row.get('years_value')) else None

                            if year_mode == 'last_n' and years_value:
                                num_years = int(years_value)
                                years = None
                            elif year_mode == 'specific_years' and years_value:
                                years = [int(y.strip()) for y in years_value.split(',') if y.strip()]
                                years = sorted(years, reverse=True)
                                num_years = None
                            elif year_mode == 'year_range' and years_value:
                                if '-' in years_value:
                                    start, end = years_value.split('-')
                                    years = list(range(int(end.strip()), int(start.strip()) - 1, -1))
                                    num_years = None
                            elif year_mode == 'single_year' and years_value:
                                years = [int(years_value)]
                                num_years = None
                        # Legacy support: check for old num_years column
                        elif 'num_years' in df.columns and pd.notna(row['num_years']):
                            num_years = int(row['num_years'])
                            years = None

                        # If still not set, use defaults based on analysis type
                        if years is None and num_years is None:
                            if analysis_type in ['excellent', 'objective', 'scanner']:
                                num_years = 5  # Multi-year analyses need more data
                            else:
                                num_years = 1

                        config = {
                            'ticker': ticker,
                            'analysis_type': analysis_type,
                            'filing_type': filing_type,
                            'years': years,
                            'num_years': num_years,
                            'custom_prompt': None,  # Batch doesn't support custom prompts
                            'company_name': company_name
                        }

                        configs.append(config)

                    # Show validation warnings
                    if invalid_tickers:
                        st.warning(f"⚠️ Skipped {len(invalid_tickers)} invalid ticker(s):")
                        for ticker, msg in invalid_tickers[:10]:  # Show first 10
                            st.caption(f"  - {ticker}: {msg}")
                        if len(invalid_tickers) > 10:
                            st.caption(f"  ... and {len(invalid_tickers) - 10} more")

                    if not configs:
                        st.error("❌ No valid companies found in CSV. Please correct the ticker symbols.")
                    else:
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
                    
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

# Manual entry section
st.markdown("---")
st.subheader("✍️ Manual Entry (Alternative)")

with st.expander("Enter Tickers Manually", expanded=False):
    st.markdown("Enter multiple ticker symbols and apply the same settings to all")

    ticker_input = st.text_area(
        "Ticker Symbols",
        placeholder="AAPL, MSFT, GOOGL\nor one per line",
        height=100
    )

    # Analysis type
    manual_analysis_type = st.selectbox(
        "Analysis Type (applies to all)",
        options=["fundamental", "excellent", "objective", "buffett", "taleb", "contrarian", "multi", "scanner"],
        index=0,
        key="manual_analysis_type"
    )

    # Filing type
    manual_filing_type = st.selectbox(
        "Filing Type",
        options=["10-K", "10-Q", "8-K", "4", "DEF 14A"],
        index=0,
        help="• 10-K: Annual | • 10-Q: Quarterly | • 8-K: Events | • 4: Insider | • DEF 14A: Proxy",
        key="manual_filing_type"
    )

    # Year selection
    st.markdown("**Time Period Selection (applies to all)**")

    # Determine if multi-year is required
    multi_year_required = manual_analysis_type in ['excellent', 'objective', 'scanner']
    current_year = datetime.now().year

    if multi_year_required:
        year_mode_options = ["Last N Years", "Specific Years", "Year Range"]
        default_mode = 0
    else:
        year_mode_options = ["Single Year", "Last N Years", "Specific Years", "Year Range"]
        default_mode = 1

    manual_year_mode = st.radio(
        "Selection Method",
        options=year_mode_options,
        horizontal=True,
        key="manual_year_mode"
    )

    manual_years = None
    manual_num_years = None

    if manual_year_mode == "Single Year":
        manual_specific_year = st.number_input(
            "Year",
            min_value=1995,
            max_value=current_year,
            value=current_year,
            step=1,
            key="manual_single_year"
        )
        manual_years = [manual_specific_year]
        st.info(f"📅 Will analyze fiscal year {manual_specific_year} for all companies")

    elif manual_year_mode == "Last N Years":
        min_years = 3 if multi_year_required else 1
        default_years = 5 if multi_year_required else 3

        manual_num_years = st.slider(
            "Number of recent years",
            min_value=min_years,
            max_value=15,
            value=default_years,
            key="manual_last_n"
        )
        preview_years = list(range(current_year, current_year - manual_num_years, -1))
        st.info(f"📅 Will analyze: {', '.join(map(str, preview_years))} for all companies")

    elif manual_year_mode == "Specific Years":
        default_value = f"{current_year}, {current_year-1}, {current_year-2}, {current_year-3}, {current_year-4}" if multi_year_required else f"{current_year}, {current_year-1}, {current_year-2}"

        manual_years_input = st.text_input(
            "Enter years (comma-separated)",
            value=default_value,
            help="Example: 2023, 2022, 2020, 2019",
            key="manual_specific_years"
        )
        try:
            manual_years = [int(y.strip()) for y in manual_years_input.split(',') if y.strip()]
            manual_years = sorted(manual_years, reverse=True)

            min_count = 3 if multi_year_required else 1
            if len(manual_years) < min_count:
                st.error(f"❌ Please enter at least {min_count} year(s). You entered {len(manual_years)}.")
                manual_years = None
            else:
                st.info(f"📅 Will analyze {len(manual_years)} year(s): {', '.join(map(str, manual_years))} for all companies")
        except ValueError:
            st.error("❌ Invalid year format. Please enter years as numbers separated by commas.")
            manual_years = None

    else:  # Year Range
        col1, col2 = st.columns(2)
        with col1:
            manual_start_year = st.number_input(
                "From Year",
                min_value=1995,
                max_value=current_year,
                value=current_year - (4 if multi_year_required else 2),
                step=1,
                key="manual_range_start"
            )
        with col2:
            manual_end_year = st.number_input(
                "To Year",
                min_value=1995,
                max_value=current_year,
                value=current_year,
                step=1,
                key="manual_range_end"
            )

        if manual_end_year < manual_start_year:
            st.error("❌ End year must be greater than or equal to start year.")
            manual_years = None
        else:
            min_range = 3 if multi_year_required else 1
            if (manual_end_year - manual_start_year + 1) < min_range:
                st.error(f"❌ Range must include at least {min_range} year(s).")
                manual_years = None
            else:
                manual_years = list(range(manual_end_year, manual_start_year - 1, -1))
                st.info(f"📅 Will analyze {len(manual_years)} years: {manual_start_year} to {manual_end_year} for all companies")

    if st.button("🚀 Start Manual Batch", use_container_width=True, type="primary"):
        if not ticker_input.strip():
            st.error("Please enter at least one ticker symbol")
        elif manual_years is None and manual_num_years is None:
            st.error("Please configure a valid time period")
        else:
            # Parse tickers
            tickers = [t.strip().upper() for t in ticker_input.replace(',', '\n').split('\n') if t.strip()]

            if tickers:
                # Validate all tickers first
                invalid_tickers = []
                valid_tickers = []
                for ticker in tickers:
                    is_valid, error_msg = validate_ticker(ticker)
                    if is_valid:
                        valid_tickers.append(ticker)
                    else:
                        invalid_tickers.append((ticker, error_msg))

                # Show validation warnings
                if invalid_tickers:
                    st.warning(f"⚠️ Found {len(invalid_tickers)} invalid ticker(s):")
                    for ticker, msg in invalid_tickers[:10]:  # Show first 10
                        st.caption(f"  - {ticker}: {msg}")
                    if len(invalid_tickers) > 10:
                        st.caption(f"  ... and {len(invalid_tickers) - 10} more")

                if not valid_tickers:
                    st.error("❌ No valid tickers found. Please correct the ticker symbols.")
                else:
                    # Prepare configs for valid tickers only
                    configs = []
                    for ticker in valid_tickers:
                        config = {
                            'ticker': ticker,
                            'analysis_type': manual_analysis_type,
                            'filing_type': manual_filing_type,
                            'years': manual_years,
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
        st.switch_page("streamlit_app.py")

with col2:
    if st.button("📊 Single Analysis", use_container_width=True):
        st.switch_page("pages/1_📊_Single_Analysis.py")

with col3:
    if st.button("📜 View History", use_container_width=True):
        st.switch_page("pages/3_📈_Analysis_History.py")
