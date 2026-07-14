#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis History Page - View and manage past analyses.
"""

import streamlit as st
import time
from datetime import date, timedelta
from eon.ui.database import DatabaseRepository
from eon.ui.theme import apply_theme
from eon.ui.skin import topbar, components as C
from eon.core.formatting import format_duration, format_status as _fmt_status
from eon.core.analysis_types import CLI_ANALYSIS_CHOICES

# Apply global theme
apply_theme()

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

db = st.session_state.db

topbar(["Workspace", "Analysis History"])
C.page_header(
    title="Analysis history",
    eyebrow="EON.02 — Run Ledger",
    desc="Every analysis run is logged with its source citations, status, and runtime. "
    "Filter the ledger, resume interrupted runs, or re-open completed results.",
)

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

    # Date range. Off by default: a fixed default window silently hides the whole
    # ledger whenever the most recent run is older than it.
    use_dates = st.checkbox("Filter by date range", value=False)
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input(
            "From Date",
            value=date.today() - timedelta(days=30),
            disabled=not use_dates,
        )
    with col2:
        date_to = st.date_input(
            "To Date",
            value=date.today(),
            disabled=not use_dates,
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
    date_from=date_from if use_dates else None,
    date_to=date_to if use_dates else None,
)

# ── KPI strip (real, from the filtered ledger) ──────────────────────────────
import pandas as pd

_n = len(analyses_df)
if _n:
    _counts = analyses_df['status'].value_counts()
    _completed = int(_counts.get('completed', 0))
    _running = int(_counts.get('running', 0))
    _failed = int(_counts.get('failed', 0))
    _rate = f"{(_completed / _n * 100):.1f}" if _n else "0.0"
else:
    _completed = _running = _failed = 0
    _rate = "0.0"

C.kpi_grid([
    {"label": "Runs in view", "value": f"{_n:,}"},
    {"label": "Success rate", "value": _rate, "suffix": "%"},
    {"label": "Running", "value": _running, "delta": "live" if _running else None,
     "delta_dir": "up" if _running else ""},
    {"label": "Failed", "value": _failed, "delta_dir": "down" if _failed else ""},
])
st.write("")

# Display results
C.section_h(
    f"Results — {_n} {'analysis' if _n == 1 else 'analyses'}", num="01",
    right_html='<span class="dim mono" style="font-size:11px">click an action below to manage a run</span>',
)

if analyses_df.empty:
    st.info("No analyses found matching filters.")
else:
    has_progress = 'progress_percent' in analyses_df.columns

    rows = []
    for _, row in analyses_df.iterrows():
        started = pd.to_datetime(row.get('created_at'), errors='coerce')
        started_str = started.strftime('%Y-%m-%d %H:%M') if pd.notna(started) else '—'
        duration = format_duration(
            start=row['created_at'] if pd.notna(row.get('created_at')) else None,
            end=row['completed_at'] if pd.notna(row.get('completed_at')) else None,
        ).replace("N/A", "—")

        status_cell = C.status_pill(row['status'])
        if row['status'] == 'running' and has_progress:
            pct = row.get('progress_percent') or 0
            status_cell += (
                f'<div style="width:96px;height:3px;background:var(--bg-3);border-radius:2px;'
                f'margin-top:5px;overflow:hidden"><div style="width:{pct}%;height:100%;'
                f'background:var(--accent)"></div></div>'
            )

        rows.append([
            C.tick(str(row.get('ticker', '')).upper()),
            str(row.get('analysis_type', '')).capitalize(),
            status_cell,
            f'<span class="tnum dim" style="font-size:11.5px">{started_str}</span>',
            f'<span class="tnum" style="font-size:12.5px">{duration}</span>',
        ])

    C.html_table(
        [("Ticker", 100), "Analysis", ("Status", 150), ("Started", 170), ("Runtime", 100)],
        rows,
    )

    st.write("")

    # Show detailed progress for running analyses
    running_analyses = analyses_df[analyses_df['status'] == 'running']
    if not running_analyses.empty:
        st.subheader("📊 Active Analyses")

        # Import analysis service for cancellation
        from eon.ui.services.analysis_service import AnalysisService
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
    from eon.ui.services.analysis_service import AnalysisService
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
st.write("")
C.section_h("Statistics by type", num="02")

stats_df = db.get_stats_by_type()

if not stats_df.empty:
    # Pivot for better display
    stats_pivot = stats_df.pivot(index='analysis_type', columns='status', values='count').fillna(0)
    _status_cols = list(stats_pivot.columns)
    _rows = []
    for _atype, _r in stats_pivot.iterrows():
        _cells = [f'<span style="font-weight:500">{str(_atype).capitalize()}</span>']
        for _c in _status_cols:
            _cells.append(f'<span class="tnum">{int(_r[_c])}</span>')
        _rows.append(_cells)
    C.html_table(
        ["Analysis type"] + [str(c).capitalize() for c in _status_cols],
        _rows,
    )
else:
    st.info("No statistics yet.")

# Navigation
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🏠 Home", width="stretch"):
        st.switch_page("streamlit_app.py")

with col2:
    if st.button("📊 New Analysis", width="stretch"):
        st.switch_page("pages/1_📊_Analysis.py")
