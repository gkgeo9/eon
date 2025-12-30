#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis History Page - View and manage past analyses.
"""

import streamlit as st
from datetime import date, timedelta
from fintel.ui.database import DatabaseRepository
from fintel.ui.theme import apply_theme

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
            ["All", "fundamental", "excellent", "objective", "buffett", "taleb", "contrarian", "multi"]
        )

    with col3:
        filter_status = st.selectbox(
            "Status",
            ["All", "completed", "running", "pending", "failed"]
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

    # Calculate duration
    def calculate_duration(row):
        if pd.notna(row['completed_at']) and pd.notna(row['created_at']):
            try:
                start = pd.to_datetime(row['created_at'])
                end = pd.to_datetime(row['completed_at'])
                duration = end - start
                total_seconds = int(duration.total_seconds())
                # Handle negative durations (shouldn't happen but be safe)
                if total_seconds < 60 and total_seconds >= 0:
                    return f"{total_seconds}s"
                elif total_seconds >= 60 and total_seconds < 3600:
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    return f"{minutes}m {seconds}s"
                elif total_seconds >= 3600:
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    return f"{hours}h {minutes}m"
                else:
                    # Negative duration - something's wrong
                    return '-'
            except:
                return '-'
        return '-'

    display_df['Duration'] = display_df.apply(calculate_duration, axis=1)

    # Enhanced status indicator with progress for running analyses
    def format_status(row):
        status = row['status']
        status_display = {
            'completed': ('✅', 'Completed'),
            'running': ('🔄', 'Running'),
            'pending': ('⏳', 'Queued'),
            'failed': ('❌', 'Failed')
        }

        emoji, label = status_display.get(status, ('❓', 'Unknown'))

        # For running analyses, add progress percentage if available
        if status == 'running' and 'progress_percent' in analyses_df.columns:
            progress = row.get('progress_percent', 0)
            if progress and progress > 0:
                return f"{emoji} {label} ({progress}%)"

        return f"{emoji} {label}"

    display_df['Status'] = analyses_df.apply(format_status, axis=1)

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
            "Status": st.column_config.TextColumn("Status", width="small"),
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

        for idx, row in running_analyses.iterrows():
            with st.expander(f"{row['ticker'].upper()} - {row['analysis_type'].capitalize()} (Running)", expanded=True):
                run_details = db.get_run_details(row['run_id'])
                if run_details:
                    progress_msg = run_details.get('progress_message', 'Processing...')
                    progress_pct = run_details.get('progress_percent', 0)
                    current_step = run_details.get('current_step')
                    total_steps = run_details.get('total_steps')

                    st.markdown(f"**Status:** {progress_msg}")

                    if progress_pct:
                        st.progress(progress_pct / 100.0)
                        st.caption(f"{progress_pct}% complete")

                    if current_step and total_steps:
                        st.caption(f"Current: {current_step} ({total_steps} year{'s' if total_steps > 1 else ''} total)")

                    st.caption(f"Started: {pd.to_datetime(run_details['started_at']).strftime('%Y-%m-%d %H:%M:%S') if run_details.get('started_at') else 'N/A'}")

        if st.button("🔄 Refresh Progress", width="stretch"):
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
        if '✅' in selected_status:  # Completed
            if st.button("📊 View Results", type="primary", width="stretch"):
                st.session_state.view_run_id = selected_run_id
                st.switch_page("pages/3_🔍_Results_Viewer.py")
        else:
            st.button("📊 View Results", disabled=True, width="stretch")

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
