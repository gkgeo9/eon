#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis History Page - View and manage past analyses.
"""

import streamlit as st
from datetime import date, timedelta
from fintel.ui.database import DatabaseRepository


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
    # Format display
    display_df = analyses_df[[
        'ticker', 'analysis_type', 'status', 'created_at', 'completed_at', 'run_id'
    ]].copy()

    # Add status emoji
    status_emojis = {
        'completed': '✅',
        'running': '🔄',
        'pending': '⏳',
        'failed': '❌'
    }
    display_df['status'] = display_df['status'].apply(
        lambda x: f"{status_emojis.get(x, '❓')} {x.capitalize()}"
    )

    # Truncate timestamps
    display_df['created_at'] = display_df['created_at'].str[:19]
    display_df['completed_at'] = display_df['completed_at'].fillna('').str[:19]

    # Display table
    st.dataframe(
        display_df[[
            'ticker', 'analysis_type', 'status', 'created_at', 'completed_at'
        ]],
        use_container_width=True,
        hide_index=True
    )

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
            if st.button("📊 View Results", type="primary", use_container_width=True):
                st.session_state.view_run_id = selected_run_id
                st.switch_page("pages/3_🔍_Results_Viewer.py")
        else:
            st.button("📊 View Results", disabled=True, use_container_width=True)

    with col2:
        if st.button("🔄 Re-run", use_container_width=True):
            # Get original config
            run_details = db.get_run_details(selected_run_id)
            if run_details:
                # Could populate analysis form with these settings
                st.info("Re-run feature: Navigate to Analysis page and configure manually for now")

    with col3:
        if st.button("🗑️ Delete", use_container_width=True, type="secondary"):
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
    st.dataframe(stats_pivot, use_container_width=True)

# Navigation
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("app.py")

with col2:
    if st.button("📊 New Analysis", use_container_width=True):
        st.switch_page("pages/1_📊_Single_Analysis.py")
