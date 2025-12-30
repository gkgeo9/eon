#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Results Viewer Page - View analysis results.
"""

import streamlit as st
from fintel.ui.database import DatabaseRepository
from fintel.ui.components.results_display import display_results
from fintel.ui.theme import apply_theme

# Apply global theme
apply_theme()


# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

db = st.session_state.db

st.title("🔍 Results Viewer")
st.markdown("View and export analysis results")

st.markdown("---")

# Get run_id from session state or selection
run_id = st.session_state.get('view_run_id', None)

# If no run_id, show selector
if not run_id:
    # Get all completed analyses
    completed_analyses = db.search_analyses(status='completed', limit=100)

    if completed_analyses.empty:
        st.info("No completed analyses found. Run an analysis first!")
        if st.button("➕ New Analysis"):
            st.switch_page("pages/1_📊_Analysis.py")
    else:
        # Group by ticker for selection
        completed_analyses['display_name'] = (
            completed_analyses['ticker'] + " - " +
            completed_analyses['analysis_type'] + " (" +
            completed_analyses['completed_at'].str[:10] + ")"
        )

        selected = st.selectbox(
            "Select Analysis to View",
            options=completed_analyses.index.tolist(),
            format_func=lambda idx: completed_analyses.loc[idx, 'display_name']
        )

        if st.button("View Results", type="primary"):
            run_id = completed_analyses.loc[selected, 'run_id']
            st.session_state.view_run_id = run_id
            st.rerun()

# Display results if run_id is available
if run_id:
    # Get run details
    run_details = db.get_run_details(run_id)

    if not run_details:
        st.error("Analysis not found!")
        if st.button("Back"):
            st.session_state.view_run_id = None
            st.rerun()
    else:
        # Get results
        results = db.get_analysis_results(run_id)

        if not results:
            st.warning("No results available for this analysis.")
        else:
            # Display results
            display_results(run_details, results)

            st.markdown("---")

            # Navigation buttons
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("🏠 Home"):
                    st.session_state.view_run_id = None
                    st.switch_page("streamlit_app.py")

            with col2:
                if st.button("📜 View History"):
                    st.session_state.view_run_id = None
                    st.switch_page("pages/2_📈_Analysis_History.py")

            with col3:
                if st.button("📊 New Analysis"):
                    st.session_state.view_run_id = None
                    st.switch_page("pages/1_📊_Analysis.py")
