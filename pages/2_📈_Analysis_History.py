#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis History Page - View and manage past analyses.
"""

import streamlit as st
import time
from datetime import date, timedelta
from fintel.ui.database import DatabaseRepository
from fintel.ui.theme import apply_theme
from fintel.core.formatting import format_duration, format_status as _fmt_status
from fintel.core.analysis_types import CLI_ANALYSIS_CHOICES

# Apply global theme
apply_theme()

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

db = st.session_state.db

st.title("📈 Analysis History")
st.markdown("View and manage your analysis history")

st.markdown("---")

# Filters
with st.expander("🔍 Filters", expanded=False):
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_ticker = st.text_input("Ticker", "").upper()

    with col2:
        filter_type = st.selectbox(
            "Analysis Type",
            ["All"] + CLI_ANALYSIS_CHOICES
        )

    with col3:
        filter_status = st.selectbox(
            "Status",
            ["All", "completed", "running", "pending", "failed", "cancelled"]
        )

    # Date range
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input(
            "From Date",
            value=date.today() - timedelta(days=30)
        )
    with col2:
        date_to = st.date_input(
            "To Date",
            value=date.today()
        )

# Apply filters
ticker_filter = filter_ticker if filter_ticker else None
type_filter = filter_type if filter_type != "All" else None
status_filter = filter_status if filter_status != "All" else None

# Get filtered analyses
analyses_df = db.search_analyses(
    ticker=ticker_filter,
    analysis_type=type_filter,
    status=status_filter,
    date_from=date_from,
    date_to=date_to,
    limit=100
)

st.markdown("---")

# Display results
st.subheader(f"Results ({len(analyses_df)} analyses)")

if analyses_df.empty:
    st.info("No analyses found matching filters.")
else:
    import pandas as pd

    # Format display
    display_df = analyses_df.copy()

    # Format timestamps
    display_df['Start Time'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
    display_df['End Time'] = pd.to_datetime(display_df['completed_at'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    display_df['End Time'] = display_df['End Time'].fillna('-')

    # Calculate duration using shared formatter
    display_df['Duration'] = display_df.apply(
        lambda row: format_duration(
            start=row['created_at'] if pd.notna(row.get('created_at')) else None,
            end=row['completed_at'] if pd.notna(row.get('completed_at')) else None,
        ).replace("N/A", "-"),
        axis=1,
    )

    # Status display using shared formatter, with running-progress enhancement
    def _status_with_progress(row):
        base = _fmt_status(row['status'])
        if row['status'] == 'running' and 'progress_percent' in analyses_df.columns:
            progress = row.get('progress_percent')
            if progress is not None and progress > 0:
                return f"{base} ({progress}%)"
            return f"{base}..."
        return base

    display_df['Status'] = analyses_df.apply(_status_with_progress, axis=1)

    # Clean up names
    display_df['Ticker'] = display_df['ticker'].str.upper()
    display_df['Analysis'] = display_df['analysis_type'].str.capitalize()

    # Display table
    st.dataframe(
        display_df[[
            'Ticker', 'Analysis', 'Status', 'Start Time', 'End Time', 'Duration'
        ]],
        width="stretch",
        hide_index=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Analysis": st.column_config.TextColumn("Analysis Type", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
            "Start Time": st.column_config.TextColumn("Started", width="medium"),
            "End Time": st.column_config.TextColumn("Completed", width="medium"),
            "Duration": st.column_config.TextColumn("Duration", width="small"),
        }
    )

    st.markdown("---")

    # Show detailed progress for running analyses
    running_analyses = analyses_df[analyses_df['status'] == 'running']
    if not running_analyses.empty:
        st.subheader("📊 Active Analyses")

        # Import analysis service for cancellation
        from fintel.ui.services.analysis_service import AnalysisService
        if 'analysis_service' not in st.session_state:
            st.session_state.analysis_service = AnalysisService(db)
        analysis_svc = st.session_state.analysis_service

        for idx, row in running_analyses.iterrows():
            with st.expander(f"{row['ticker'].upper()} - {row['analysis_type'].capitalize()} (Running)", expanded=True):
                run_details = db.get_run_details(row['run_id'])
                if run_details:
                    progress_msg = run_details.get('progress_message') or 'Initializing analysis...'
                    progress_pct = run_details.get('progress_percent') or 0
                    current_step = run_details.get('current_step')
                    total_steps = run_details.get('total_steps')

                    # Progress info column and cancel button column
                    col_info, col_cancel = st.columns([4, 1])

                    with col_info:
                        st.markdown(f"**Status:** {progress_msg}")

                        # Always show progress bar for running analyses
                        progress_value = (progress_pct or 0) / 100.0
                        st.progress(progress_value)
                        if progress_pct and progress_pct > 0:
                            st.caption(f"{progress_pct}% complete")
                        else:
                            st.caption("Starting...")

                        if current_step and total_steps:
                            st.caption(f"Current: {current_step} ({total_steps} year{'s' if total_steps > 1 else ''} total)")

                        st.caption(f"Started: {pd.to_datetime(run_details['started_at']).strftime('%Y-%m-%d %H:%M:%S') if run_details.get('started_at') else 'N/A'}")

                    with col_cancel:
                        cancel_key = f"cancel_running_{row['run_id']}"
                        if st.button("Cancel", key=cancel_key, type="secondary", help="Cancel this analysis"):
                            with st.spinner("Cancelling analysis..."):
                                success = analysis_svc.cancel_analysis(row['run_id'])
                                if success:
                                    st.success("Analysis cancelled")
                                else:
                                    st.warning("Could not cancel cleanly - marked as cancelled")
                                time.sleep(1)
                                st.rerun()
                else:
                    # Run details not found - show basic info
                    st.warning(f"Unable to fetch details for run {row['run_id']}")
                    st.caption("The analysis may still be initializing...")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Refresh Now", width="stretch"):
                st.rerun()
        with col2:
            auto_refresh = st.checkbox("Auto-refresh (5s)", value=True, key="auto_refresh_running")

        # Auto-refresh when running analyses exist
        if auto_refresh:
            time.sleep(5)
            st.rerun()

        st.markdown("---")

    # Check for interrupted runs
    from fintel.ui.services.analysis_service import AnalysisService
    import threading

    analysis_service = AnalysisService(db)
    interrupted_runs = analysis_service.get_interrupted_runs(stale_minutes=5)

    if interrupted_runs:
        st.subheader("⚠️ Interrupted Analyses")
        st.markdown("These analyses appear to have been interrupted and can be resumed.")

        for run in interrupted_runs:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    completed = len(run['completed_years'])
                    total = len(run['years_analyzed'])
                    remaining = len(run['remaining_years'])

                    st.markdown(f"""
                    **{run['ticker']}** - {run['analysis_type'].capitalize()} ({run['filing_type']})
                    - Progress: {completed}/{total} years completed
                    - Remaining: {run['remaining_years']}
                    - Last activity: {run['last_activity_at'] or 'Unknown'}
                    """)

                    if run['progress_percent']:
                        st.progress(run['progress_percent'] / 100.0)

                with col2:
                    resume_key = f"resume_{run['run_id']}"
                    if st.button("▶️ Resume", key=resume_key, type="primary"):
                        st.session_state[f'resuming_{run["run_id"]}'] = True
                        st.info(f"Resuming analysis for {run['ticker']}...")

                        # Run resume in background thread
                        def resume_in_background(run_id):
                            try:
                                analysis_service.resume_analysis(run_id)
                            except Exception as e:
                                print(f"Resume error: {e}")

                        thread = threading.Thread(
                            target=resume_in_background,
                            args=(run['run_id'],),
                            daemon=True
                        )
                        thread.start()
                        time.sleep(1)
                        st.rerun()

                with col3:
                    cancel_key = f"cancel_{run['run_id']}"
                    if st.button("❌ Cancel", key=cancel_key, type="secondary"):
                        db.mark_run_as_interrupted(run['run_id'])
                        db.update_run_status(run['run_id'], 'failed', 'Cancelled by user')
                        st.success("Analysis cancelled")
                        st.rerun()

                st.markdown("---")

    # Action selector
    st.subheader("Actions")

    selected_idx = st.selectbox(
        "Select analysis to manage",
        options=analyses_df.index.tolist(),
        format_func=lambda idx: (
            f"{analyses_df.loc[idx, 'ticker']} - "
            f"{analyses_df.loc[idx, 'analysis_type']} - "
            f"{analyses_df.loc[idx, 'created_at'][:19]}"
        )
    )

    selected_run_id = analyses_df.loc[selected_idx, 'run_id']
    selected_status = analyses_df.loc[selected_idx, 'status']

    col1, col2, col3 = st.columns(3)

    with col1:
        if selected_status == 'completed':
            if st.button("View Results", type="primary", width="stretch"):
                st.session_state.view_run_id = selected_run_id
                st.switch_page("pages/3_🔍_Results_Viewer.py")
        else:
            st.button("View Results", disabled=True, width="stretch")

    with col2:
        if st.button("🔄 Re-run", width="stretch"):
            # Get original config
            run_details = db.get_run_details(selected_run_id)
            if run_details:
                # Could populate analysis form with these settings
                st.info("Re-run feature: Navigate to Analysis page and configure manually for now")

    with col3:
        if st.button("🗑️ Delete", width="stretch", type="secondary"):
            try:
                db.delete_analysis_run(selected_run_id)
                st.success("Analysis deleted successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting analysis: {e}")

# Statistics
st.markdown("---")
st.subheader("Statistics")

stats_df = db.get_stats_by_type()

if not stats_df.empty:
    # Pivot for better display
    stats_pivot = stats_df.pivot(index='analysis_type', columns='status', values='count').fillna(0)
    st.dataframe(stats_pivot, width="stretch")

# Navigation
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🏠 Home", width="stretch"):
        st.switch_page("streamlit_app.py")

with col2:
    if st.button("📊 New Analysis", width="stretch"):
        st.switch_page("pages/1_📊_Analysis.py")
