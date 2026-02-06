#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main Streamlit application - Home page with dashboard.
"""

import streamlit as st
from fintel.core import setup_logging, get_logger
from fintel.ui.database import DatabaseRepository
from fintel.ui.services import AnalysisService
from fintel.ui.theme import apply_theme

# Initialize logging with timestamps
setup_logging(level=20)  # INFO level
logger = get_logger(__name__)

# Apply global theme
apply_theme()

# Configure page
st.set_page_config(
    page_title="Fintel - Financial Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize Streamlit session state."""
    if 'db' not in st.session_state:
        st.session_state.db = DatabaseRepository()

    if 'analysis_service' not in st.session_state:
        st.session_state.analysis_service = AnalysisService(st.session_state.db)


def main():
    """Main Streamlit application entry point - Home page."""

    # Initialize session state
    init_session_state()

    db = st.session_state.db

    # Header
    st.title("📊 Fintel Financial Intelligence Platform")
    st.markdown(
        "AI-powered SEC filing analysis with multiple investment perspectives"
    )

    st.markdown("---")

    # Dashboard metrics
    st.subheader("Dashboard")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total = db.get_total_analyses()
        st.metric("Total Analyses", total)

    with col2:
        running = db.get_running_analyses_count()
        st.metric("Running", running, delta=None if running == 0 else f"+{running}")

    with col3:
        today = db.get_analyses_today()
        st.metric("Today", today)

    with col4:
        tickers = db.get_unique_tickers_count()
        st.metric("Companies Analyzed", tickers)

    st.markdown("---")

    # Recent analyses
    st.subheader("Recent Analyses")

    recent_df = db.get_recent_analyses(limit=10)

    if not recent_df.empty:
        import pandas as pd

        # Create display dataframe
        display_df = recent_df.copy()

        # Format timestamps
        display_df['Start Time'] = pd.to_datetime(display_df['started_at'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        display_df['Start Time'] = display_df['Start Time'].fillna('-')
        display_df['End Time'] = pd.to_datetime(display_df['completed_at'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        display_df['End Time'] = display_df['End Time'].fillna('-')

        # Calculate duration for completed analyses
        def calculate_duration(row):
            if pd.notna(row['completed_at']) and pd.notna(row['started_at']):
                try:
                    start = pd.to_datetime(row['started_at'])
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

        # Enhanced status indicator with better labels
        status_display = {
            'completed': ('✅', 'Completed', '#28a745'),
            'running': ('🔄', 'Running', '#17a2b8'),
            'pending': ('⏳', 'Queued', '#ffc107'),
            'failed': ('❌', 'Failed', '#dc3545')
        }

        display_df['Status'] = display_df['status'].apply(
            lambda x: f"{status_display.get(x, ('❓', 'Unknown', '#6c757d'))[0]} {status_display.get(x, ('❓', 'Unknown', '#6c757d'))[1]}"
        )

        # Clean up analysis type names
        display_df['Analysis'] = display_df['analysis_type'].str.capitalize()
        display_df['Ticker'] = display_df['ticker'].str.upper()

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
    else:
        st.info("No analyses yet. Start your first analysis!")

    st.markdown("---")

    # Quick actions
    st.subheader("Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 New Analysis", width="stretch", type="primary"):
            st.switch_page("pages/1_📊_Analysis.py")

    with col2:
        if st.button("📜 View History", width="stretch", type="primary"):
            st.switch_page("pages/2_📈_Analysis_History.py")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 View Results", width="stretch"):
            st.switch_page("pages/3_🔍_Results_Viewer.py")

    with col2:
        if st.button("⚙️ Settings", width="stretch"):
            st.switch_page("pages/5_⚙️_Settings.py")

    # Footer
    st.markdown("---")
    st.caption("Fintel v0.1.0")


if __name__ == "__main__":
    main()
