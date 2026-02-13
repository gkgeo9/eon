#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Results Viewer Page - View and export analysis results.
"""

import json
import streamlit as st
from eon.ui.database import DatabaseRepository
from eon.ui.components.results_display import display_results
from eon.ui.theme import apply_theme

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
    completed_analyses = db.search_analyses(status='completed')

    if completed_analyses.empty:
        st.info("No completed analyses found. Run an analysis first!")
        if st.button("New Analysis"):
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
            # Quick info bar
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Ticker", run_details.get('ticker', 'N/A'))
            with col2:
                st.metric("Type", run_details.get('analysis_type', 'N/A').title())
            with col3:
                years = run_details.get('years', [])
                if years:
                    year_range = f"{min(years)}-{max(years)}" if len(years) > 1 else str(years[0])
                else:
                    year_range = "N/A"
                st.metric("Years", year_range)
            with col4:
                st.metric("Results", len(results))

            st.markdown("---")

            # Display results
            display_results(run_details, results)

            st.markdown("---")

            # Actions section - Synthesize and Export
            st.subheader("Actions")

            # Show synthesize button for multi-year analyses (2+ years)
            # Don't show for synthesis results themselves
            analysis_type = run_details.get('analysis_type', '')
            is_synthesis = analysis_type in ['multi_year_synthesis', 'synthesis']
            if len(results) >= 2 and not is_synthesis:
                st.markdown("**Synthesize Years**")
                st.caption(
                    f"Combine all {len(results)} year analyses into a comprehensive longitudinal assessment"
                )

                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button("Create Multi-Year Synthesis", type="primary", key="create_synthesis"):
                        from eon.ui.services.analysis_service import AnalysisService
                        import time

                        with st.spinner("Creating synthesis analysis... This may take a minute."):
                            analysis_service = AnalysisService(db)
                            synthesis_run_id = analysis_service.create_multi_year_synthesis(run_id)

                            if synthesis_run_id:
                                st.success("Multi-year synthesis created!")
                                time.sleep(1)
                                st.session_state.view_run_id = synthesis_run_id
                                st.rerun()
                            else:
                                st.error("Failed to create synthesis. Check logs for details.")

                st.markdown("---")

            # Export section
            st.markdown("**Export**")
            col1, col2 = st.columns(2)

            with col1:
                # Export as JSON
                export_data = {
                    "run_id": run_id,
                    "ticker": run_details.get('ticker'),
                    "analysis_type": run_details.get('analysis_type'),
                    "years": run_details.get('years'),
                    "completed_at": run_details.get('completed_at'),
                    "results": results
                }
                json_str = json.dumps(export_data, indent=2, default=str)
                st.download_button(
                    "Download JSON",
                    data=json_str,
                    file_name=f"{run_details.get('ticker', 'analysis')}_{run_details.get('analysis_type', 'results')}.json",
                    mime="application/json"
                )

            with col2:
                # Re-run same analysis
                if st.button("Re-run Analysis", type="secondary"):
                    # Store config for re-run
                    st.session_state.rerun_config = {
                        'ticker': run_details.get('ticker'),
                        'analysis_type': run_details.get('analysis_type'),
                        'years': run_details.get('years'),
                        'filing_type': run_details.get('filing_type', '10-K')
                    }
                    st.session_state.view_run_id = None
                    st.switch_page("pages/1_📊_Analysis.py")

            st.markdown("---")

            # Navigation buttons
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Home"):
                    st.session_state.view_run_id = None
                    st.switch_page("streamlit_app.py")

            with col2:
                if st.button("View History"):
                    st.session_state.view_run_id = None
                    st.switch_page("pages/2_📈_Analysis_History.py")

            with col3:
                if st.button("New Analysis"):
                    st.session_state.view_run_id = None
                    st.switch_page("pages/1_📊_Analysis.py")
