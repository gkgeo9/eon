#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Viewer Page - View cached data and database contents.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from fintel.ui.database import DatabaseRepository

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

db = st.session_state.db

st.title("🗄️ Database Viewer")
st.markdown("Inspect cached data, analysis runs, and database statistics")

st.markdown("---")

# Tab selection
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Analysis Runs",
    "📄 Analysis Results",
    "📁 File Cache",
    "⚙️ Settings",
    "📈 Statistics"
])

# Tab 1: Analysis Runs
with tab1:
    st.subheader("Analysis Runs")
    st.markdown("View all analysis run records from the database")

    # Query the database
    query = """
    SELECT
        run_id,
        ticker,
        company_name,
        analysis_type,
        filing_type,
        status,
        years_analyzed,
        created_at,
        started_at,
        completed_at,
        error_message
    FROM analysis_runs
    ORDER BY created_at DESC
    LIMIT 100
    """

    runs_df = db._execute_query(query)

    if not runs_df.empty:
        st.markdown(f"**Total Runs**: {len(runs_df)}")

        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_ticker = st.text_input("Filter by Ticker", key="runs_ticker_filter")
        with col2:
            filter_status = st.selectbox(
                "Filter by Status",
                ["All", "completed", "running", "pending", "failed"],
                key="runs_status_filter"
            )
        with col3:
            filter_type = st.selectbox(
                "Filter by Type",
                ["All", "fundamental", "excellent", "objective", "buffett", "taleb", "contrarian", "multi", "scanner"],
                key="runs_type_filter"
            )

        # Apply filters
        filtered_df = runs_df.copy()
        if filter_ticker:
            filtered_df = filtered_df[filtered_df['ticker'].str.contains(filter_ticker.upper(), case=False, na=False)]
        if filter_status != "All":
            filtered_df = filtered_df[filtered_df['status'] == filter_status]
        if filter_type != "All":
            filtered_df = filtered_df[filtered_df['analysis_type'] == filter_type]

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "run_id": st.column_config.TextColumn("Run ID", width="small"),
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "company_name": st.column_config.TextColumn("Company", width="medium"),
                "analysis_type": st.column_config.TextColumn("Type", width="small"),
                "filing_type": st.column_config.TextColumn("Filing", width="small"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "years_analyzed": st.column_config.TextColumn("Years", width="medium"),
                "created_at": st.column_config.TextColumn("Created", width="medium"),
                "started_at": st.column_config.TextColumn("Started", width="medium"),
                "completed_at": st.column_config.TextColumn("Completed", width="medium"),
                "error_message": st.column_config.TextColumn("Error", width="large"),
            }
        )
    else:
        st.info("No analysis runs found in database")

# Tab 2: Analysis Results
with tab2:
    st.subheader("Analysis Results")
    st.markdown("View stored analysis results (Pydantic model outputs)")

    query = """
    SELECT
        id,
        run_id,
        ticker,
        fiscal_year,
        filing_type,
        result_type,
        created_at,
        LENGTH(result_json) as json_size
    FROM analysis_results
    ORDER BY created_at DESC
    LIMIT 100
    """

    results_df = db._execute_query(query)

    if not results_df.empty:
        st.markdown(f"**Total Results**: {len(results_df)}")

        # Add filters
        col1, col2 = st.columns(2)
        with col1:
            filter_ticker_res = st.text_input("Filter by Ticker", key="results_ticker_filter")
        with col2:
            filter_type_res = st.selectbox(
                "Filter by Result Type",
                ["All"] + list(results_df['result_type'].unique()),
                key="results_type_filter"
            )

        # Apply filters
        filtered_results = results_df.copy()
        if filter_ticker_res:
            filtered_results = filtered_results[filtered_results['ticker'].str.contains(filter_ticker_res.upper(), case=False, na=False)]
        if filter_type_res != "All":
            filtered_results = filtered_results[filtered_results['result_type'] == filter_type_res]

        st.dataframe(
            filtered_results,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "run_id": st.column_config.TextColumn("Run ID", width="small"),
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "fiscal_year": st.column_config.NumberColumn("Year", width="small"),
                "filing_type": st.column_config.TextColumn("Filing", width="small"),
                "result_type": st.column_config.TextColumn("Result Type", width="medium"),
                "created_at": st.column_config.TextColumn("Created", width="medium"),
                "json_size": st.column_config.NumberColumn("Size (bytes)", width="small"),
            }
        )

        # Option to view specific result
        st.markdown("---")
        st.subheader("View Specific Result JSON")
        result_id = st.number_input("Enter Result ID to view", min_value=1, step=1, key="view_result_id")

        if st.button("Load Result JSON", key="load_result"):
            query = f"SELECT result_json FROM analysis_results WHERE id = {result_id}"
            result_row = db._execute_query(query)
            if not result_row.empty:
                import json
                result_json = result_row.iloc[0]['result_json']
                result_dict = json.loads(result_json)
                st.json(result_dict)
            else:
                st.error(f"No result found with ID {result_id}")
    else:
        st.info("No analysis results found in database")

# Tab 3: File Cache
with tab3:
    st.subheader("File Cache")
    st.markdown("View cached PDF files and their locations")

    query = """
    SELECT
        id,
        ticker,
        fiscal_year,
        filing_type,
        file_path,
        file_hash,
        downloaded_at
    FROM file_cache
    ORDER BY downloaded_at DESC
    """

    cache_df = db._execute_query(query)

    if not cache_df.empty:
        st.markdown(f"**Total Cached Files**: {len(cache_df)}")

        # Check which files actually exist
        cache_df['exists'] = cache_df['file_path'].apply(lambda p: '✅' if Path(p).exists() else '❌')

        # Filter
        filter_ticker_cache = st.text_input("Filter by Ticker", key="cache_ticker_filter")

        filtered_cache = cache_df.copy()
        if filter_ticker_cache:
            filtered_cache = filtered_cache[filtered_cache['ticker'].str.contains(filter_ticker_cache.upper(), case=False, na=False)]

        st.dataframe(
            filtered_cache,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "fiscal_year": st.column_config.NumberColumn("Year", width="small"),
                "filing_type": st.column_config.TextColumn("Filing", width="small"),
                "file_path": st.column_config.TextColumn("Path", width="large"),
                "file_hash": st.column_config.TextColumn("Hash", width="small"),
                "downloaded_at": st.column_config.TextColumn("Downloaded", width="medium"),
                "exists": st.column_config.TextColumn("Exists", width="small"),
            }
        )

        # Summary
        st.markdown("---")
        st.subheader("Cache Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Files", len(cache_df))
        with col2:
            existing = len([p for p in cache_df['file_path'] if Path(p).exists()])
            st.metric("Existing Files", existing)
        with col3:
            missing = len(cache_df) - existing
            st.metric("Missing Files", missing)

        # Cleanup option
        if missing > 0:
            st.warning(f"⚠️ {missing} cached files are missing from disk")
            if st.button("🗑️ Clean Up Missing Cache Entries", key="cleanup_cache"):
                for idx, row in cache_df.iterrows():
                    if not Path(row['file_path']).exists():
                        # Delete from cache
                        delete_query = f"DELETE FROM file_cache WHERE id = {row['id']}"
                        db._execute_update(delete_query)
                st.success(f"Removed {missing} missing cache entries")
                st.rerun()
    else:
        st.info("No cached files found in database")

# Tab 4: Settings
with tab4:
    st.subheader("User Settings")
    st.markdown("View and modify user settings")

    query = "SELECT key, value, updated_at FROM user_settings"
    settings_df = db._execute_query(query)

    if not settings_df.empty:
        st.dataframe(
            settings_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "key": st.column_config.TextColumn("Key", width="medium"),
                "value": st.column_config.TextColumn("Value", width="large"),
                "updated_at": st.column_config.TextColumn("Updated", width="medium"),
            }
        )
    else:
        st.info("No user settings found in database")

# Tab 5: Statistics
with tab5:
    st.subheader("Database Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Analysis Runs by Status")
        status_query = """
        SELECT status, COUNT(*) as count
        FROM analysis_runs
        GROUP BY status
        """
        status_df = db._execute_query(status_query)
        if not status_df.empty:
            st.bar_chart(status_df.set_index('status'))
            st.dataframe(status_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        st.markdown("#### Analysis Runs by Type")
        type_query = """
        SELECT analysis_type, COUNT(*) as count
        FROM analysis_runs
        GROUP BY analysis_type
        """
        type_df = db._execute_query(type_query)
        if not type_df.empty:
            st.bar_chart(type_df.set_index('analysis_type'))
            st.dataframe(type_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("#### Top 10 Most Analyzed Tickers")
        ticker_query = """
        SELECT ticker, COUNT(*) as analysis_count
        FROM analysis_runs
        GROUP BY ticker
        ORDER BY analysis_count DESC
        LIMIT 10
        """
        ticker_df = db._execute_query(ticker_query)
        if not ticker_df.empty:
            st.bar_chart(ticker_df.set_index('ticker'))
            st.dataframe(ticker_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        st.markdown("#### Database Size")
        import os
        from fintel.core import get_config
        config = get_config()
        db_path = config.get_data_path("fintel.db")
        if db_path.exists():
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            st.metric("Database File Size", f"{db_size_mb:.2f} MB")

        # Table row counts
        st.markdown("#### Table Row Counts")
        tables = ['analysis_runs', 'analysis_results', 'file_cache', 'user_settings', 'custom_prompts']
        counts = {}
        for table in tables:
            count_query = f"SELECT COUNT(*) as count FROM {table}"
            count_df = db._execute_query(count_query)
            if not count_df.empty:
                counts[table] = count_df.iloc[0]['count']

        counts_df = pd.DataFrame(list(counts.items()), columns=['Table', 'Rows'])
        st.dataframe(counts_df, use_container_width=True, hide_index=True)

# Navigation
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("streamlit_app.py")

with col2:
    if st.button("📜 View History", use_container_width=True):
        st.switch_page("pages/3_📈_Analysis_History.py")
