#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main Streamlit application - Home page with dashboard.
"""

import streamlit as st
from fintel.ui.database import DatabaseRepository
from fintel.ui.services import AnalysisService

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
        # Format the dataframe for display
        recent_df['started_at'] = recent_df['started_at'].str[:19]  # Trim timestamp

        # Add status indicator
        status_emojis = {
            'completed': '✅',
            'running': '🔄',
            'pending': '⏳',
            'failed': '❌'
        }
        recent_df['status'] = recent_df['status'].apply(
            lambda x: f"{status_emojis.get(x, '❓')} {x.capitalize()}"
        )

        st.dataframe(
            recent_df[[
                'ticker', 'analysis_type', 'status', 'started_at', 'completed_at'
            ]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No analyses yet. Start your first analysis!")

    st.markdown("---")

    # Quick actions
    st.subheader("Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 Single Analysis", use_container_width=True, type="primary"):
            st.switch_page("pages/1_📊_Single_Analysis.py")

    with col2:
        if st.button("📦 Batch Analysis", use_container_width=True, type="primary"):
            st.switch_page("pages/5_📦_Batch_Analysis.py")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📜 View History", use_container_width=True):
            st.switch_page("pages/2_📈_Analysis_History.py")

    with col2:
        if st.button("🔍 View Results", use_container_width=True):
            st.switch_page("pages/3_🔍_Results_Viewer.py")

    with col3:
        if st.button("⚙️ Settings", use_container_width=True):
            st.switch_page("pages/4_⚙️_Settings.py")

    # Footer
    st.markdown("---")
    st.caption("Fintel v0.1.0 - Powered by Google Gemini AI")


if __name__ == "__main__":
    main()
