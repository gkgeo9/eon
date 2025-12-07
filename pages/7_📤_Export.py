#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Export Page - Bulk export analyses to various formats.
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from fintel.ui.database import DatabaseRepository
from fintel.ui.theme import apply_theme

# Apply global theme
apply_theme()

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

db = st.session_state.db

st.title("📤 Export Data")
st.markdown("Export analysis results to JSON, CSV, or Excel")

st.markdown("---")

# Export mode selector
export_mode = st.radio(
    "Export Mode",
    options=["Single Analysis", "Bulk Export", "Time Series", "Comparison Table"],
    horizontal=True,
    help="Choose what type of export you want"
)

st.markdown("---")

if export_mode == "Single Analysis":
    st.subheader("📄 Export Single Analysis")

    # Get all completed analyses
    all_analyses = db.search_analyses(status="completed", limit=1000)

    if all_analyses.empty:
        st.info("No completed analyses found.")
    else:
        # Create selection dropdown
        analyses_list = []
        for idx, row in all_analyses.iterrows():
            label = f"{row['ticker']} - {row['analysis_type']} - {row['created_at'][:10]}"
            analyses_list.append((label, row['run_id']))

        selected = st.selectbox(
            "Select Analysis",
            options=range(len(analyses_list)),
            format_func=lambda i: analyses_list[i][0]
        )

        run_id = analyses_list[selected][1]

        # Get results for this run
        results = db.get_results_by_run(run_id)

        st.markdown("---")
        st.subheader("Export Options")

        col1, col2 = st.columns(2)

        with col1:
            export_format = st.radio(
                "Format",
                options=["JSON", "CSV"],
                help="JSON preserves full structure, CSV is more readable"
            )

        with col2:
            include_metadata = st.checkbox("Include Metadata", value=True)

        if st.button("📥 Export", type="primary", use_container_width=True):
            if results:
                # Prepare export data
                export_data = []
                for result in results:
                    data = json.loads(result['result_json'])
                    if include_metadata:
                        data['_metadata'] = {
                            'ticker': result['ticker'],
                            'fiscal_year': result['fiscal_year'],
                            'result_type': result['result_type'],
                            'created_at': result['created_at']
                        }
                    export_data.append(data)

                if export_format == "JSON":
                    # Export as JSON
                    json_str = json.dumps(export_data, indent=2)
                    filename = f"{results[0]['ticker']}_analysis_{datetime.now().strftime('%Y%m%d')}.json"

                    st.download_button(
                        label="💾 Download JSON",
                        data=json_str,
                        file_name=filename,
                        mime="application/json"
                    )
                else:
                    # Export as CSV (flattened)
                    df = pd.json_normalize(export_data)
                    csv = df.to_csv(index=False)
                    filename = f"{results[0]['ticker']}_analysis_{datetime.now().strftime('%Y%m%d')}.csv"

                    st.download_button(
                        label="💾 Download CSV",
                        data=csv,
                        file_name=filename,
                        mime="text/csv"
                    )

                    st.success(f"✅ Ready to download! ({len(results)} results)")
            else:
                st.warning("No results found for this analysis.")

elif export_mode == "Bulk Export":
    st.subheader("📦 Bulk Export")
    st.markdown("Export multiple analyses at once")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_ticker = st.text_input("Filter by Ticker", "").upper()

    with col2:
        filter_type = st.selectbox(
            "Analysis Type",
            ["All", "fundamental", "excellent", "objective", "buffett", "taleb", "contrarian", "multi", "scanner"]
        )

    with col3:
        filter_status = st.selectbox("Status", ["completed", "All", "failed"])

    # Date range
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("From Date", value=date.today() - timedelta(days=90))
    with col2:
        date_to = st.date_input("To Date", value=date.today())

    # Apply filters
    analyses_df = db.search_analyses(
        ticker=filter_ticker if filter_ticker else None,
        analysis_type=filter_type if filter_type != "All" else None,
        status=filter_status if filter_status != "All" else None,
        date_from=date_from,
        date_to=date_to,
        limit=1000
    )

    st.markdown(f"**Found {len(analyses_df)} analyses**")

    if not analyses_df.empty:
        # Preview
        st.dataframe(
            analyses_df[['ticker', 'analysis_type', 'status', 'created_at']].head(10),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")

        export_format = st.radio(
            "Export Format",
            options=["JSON (all results)", "CSV (flattened)", "Summary CSV (metadata only)"],
            help="JSON includes all data, CSV is easier to analyze"
        )

        if st.button("📥 Export All", type="primary", use_container_width=True):
            all_results = []

            for run_id in analyses_df['run_id']:
                results = db.get_results_by_run(run_id)
                for result in results:
                    data = json.loads(result['result_json'])
                    data['_metadata'] = {
                        'run_id': run_id,
                        'ticker': result['ticker'],
                        'fiscal_year': result['fiscal_year'],
                        'result_type': result['result_type'],
                        'created_at': result['created_at']
                    }
                    all_results.append(data)

            if export_format == "JSON (all results)":
                json_str = json.dumps(all_results, indent=2)
                filename = f"bulk_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

                st.download_button(
                    label="💾 Download Bulk JSON",
                    data=json_str,
                    file_name=filename,
                    mime="application/json"
                )
            elif export_format == "CSV (flattened)":
                df = pd.json_normalize(all_results)
                csv = df.to_csv(index=False)
                filename = f"bulk_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

                st.download_button(
                    label="💾 Download Bulk CSV",
                    data=csv,
                    file_name=filename,
                    mime="text/csv"
                )
            else:  # Summary CSV
                summary_df = analyses_df[['run_id', 'ticker', 'analysis_type', 'filing_type', 'status', 'created_at', 'completed_at']]
                csv = summary_df.to_csv(index=False)
                filename = f"summary_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

                st.download_button(
                    label="💾 Download Summary CSV",
                    data=csv,
                    file_name=filename,
                    mime="text/csv"
                )

            st.success(f"✅ Ready! Exporting {len(all_results)} results from {len(analyses_df)} analyses")
    else:
        st.info("No analyses match your filters.")

elif export_mode == "Time Series":
    st.subheader("📈 Time Series Export")
    st.markdown("Export metrics over time for tracking trends")

    ticker = st.text_input("Ticker", placeholder="e.g., AAPL").upper().strip()

    if ticker:
        # Get all analyses for this ticker
        ticker_analyses = db.search_analyses(ticker=ticker, status="completed", limit=100)

        if not ticker_analyses.empty:
            st.markdown(f"**Found {len(ticker_analyses)} completed analyses for {ticker}**")

            # Group by year
            results_by_year = {}

            for run_id in ticker_analyses['run_id']:
                results = db.get_results_by_run(run_id)
                for result in results:
                    year = result['fiscal_year']
                    if year not in results_by_year:
                        results_by_year[year] = []
                    results_by_year[year].append(json.loads(result['result_json']))

            st.markdown(f"**Years available:** {', '.join(map(str, sorted(results_by_year.keys())))}")

            if st.button("📥 Export Time Series", type="primary"):
                # Create time series data
                time_series = {
                    'ticker': ticker,
                    'years': sorted(results_by_year.keys()),
                    'data_by_year': results_by_year
                }

                json_str = json.dumps(time_series, indent=2)
                filename = f"{ticker}_timeseries_{datetime.now().strftime('%Y%m%d')}.json"

                st.download_button(
                    label="💾 Download Time Series JSON",
                    data=json_str,
                    file_name=filename,
                    mime="application/json"
                )

                st.success(f"✅ Ready! {len(results_by_year)} years of data")
        else:
            st.info(f"No completed analyses found for {ticker}")

elif export_mode == "Comparison Table":
    st.subheader("🔍 Comparison Table Export")
    st.markdown("Compare multiple companies side-by-side")

    tickers_input = st.text_input(
        "Tickers (comma-separated)",
        placeholder="e.g., AAPL, MSFT, GOOGL"
    )

    if tickers_input:
        tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]

        year = st.number_input("Select Year", min_value=2015, max_value=2024, value=2023)

        if st.button("📥 Generate Comparison", type="primary"):
            comparison_data = []

            for ticker in tickers:
                # Get analysis for this ticker and year
                ticker_analyses = db.search_analyses(ticker=ticker, status="completed", limit=10)

                if not ticker_analyses.empty:
                    for run_id in ticker_analyses['run_id']:
                        results = db.get_results_by_run(run_id)
                        for result in results:
                            if result['fiscal_year'] == year:
                                data = json.loads(result['result_json'])
                                data['ticker'] = ticker
                                data['year'] = year
                                comparison_data.append(data)
                                break

            if comparison_data:
                df = pd.json_normalize(comparison_data)
                csv = df.to_csv(index=False)
                filename = f"comparison_{'-'.join(tickers)}_{year}.csv"

                st.download_button(
                    label="💾 Download Comparison CSV",
                    data=csv,
                    file_name=filename,
                    mime="text/csv"
                )

                st.success(f"✅ Comparison ready! ({len(comparison_data)} companies)")
            else:
                st.warning(f"No data found for {year}. Try a different year.")

# Navigation
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("streamlit_app.py")

with col2:
    if st.button("📜 View History", use_container_width=True):
        st.switch_page("pages/3_📈_Analysis_History.py")
