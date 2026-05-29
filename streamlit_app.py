#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main Streamlit application - Home page with dashboard.
"""

import streamlit as st
from eon.core import setup_logging, get_logger
from eon.core.formatting import format_duration
from eon.ui.database import DatabaseRepository
from eon.ui.services import AnalysisService
from eon.ui.theme import apply_theme
from eon.ui.skin import topbar, components as C

# Initialize logging with timestamps
setup_logging(level=20)  # INFO level
logger = get_logger(__name__)

# Configure page (must run before any other Streamlit command)
st.set_page_config(
    page_title="Erebus Observatory Network",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global theme / skin (renders sidebar chrome, so runs after page config)
apply_theme()


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

    # ── Top bar + page header ────────────────────────────────────────────────
    topbar(["Workspace", "Observatory"])
    C.page_header(
        title="Welcome back",
        eyebrow="EON.00 — Observatory",
        desc="AI-powered SEC filing analysis with multiple investment perspectives — "
        "Buffett value, Taleb antifragility, and contrarian lenses, all traced to source filings.",
    )

    # ── KPI strip (real data) ────────────────────────────────────────────────
    total = db.get_total_analyses()
    running = db.get_running_analyses_count()
    today = db.get_analyses_today()
    tickers = db.get_unique_tickers_count()
    C.kpi_grid([
        {"label": "Total analyses", "value": f"{total:,}"},
        {"label": "Running now", "value": running,
         "delta": "live" if running else "idle", "delta_dir": "up" if running else ""},
        {"label": "Today", "value": today},
        {"label": "Companies analyzed", "value": f"{tickers:,}"},
    ])

    # ── Recent activity ──────────────────────────────────────────────────────
    C.section_h("Recent activity", num="01",
                right_html='<span class="dim mono" style="font-size:11px">last 10 runs</span>')

    recent_df = db.get_recent_analyses(limit=10)
    if not recent_df.empty:
        import pandas as pd

        rows = []
        for _, row in recent_df.iterrows():
            started = pd.to_datetime(row.get("started_at"), errors="coerce")
            started_str = started.strftime("%Y-%m-%d %H:%M") if pd.notna(started) else "—"
            duration = format_duration(
                start=row["started_at"] if pd.notna(row.get("started_at")) else None,
                end=row["completed_at"] if pd.notna(row.get("completed_at")) else None,
            ).replace("N/A", "—")
            rows.append([
                C.tick(str(row.get("ticker", "")).upper()),
                str(row.get("analysis_type", "")).capitalize(),
                C.status_pill(row.get("status", "")),
                f'<span class="tnum dim" style="font-size:11.5px">{started_str}</span>',
                f'<span class="tnum" style="font-size:12.5px">{duration}</span>',
            ])
        C.html_table(
            [("Ticker", 100), "Analysis", ("Status", 130), ("Started", 160), ("Runtime", 100)],
            rows,
        )
    else:
        st.info("No analyses yet. Start your first analysis below.")

    st.write("")

    # ── Quick actions ────────────────────────────────────────────────────────
    C.section_h("Quick actions", num="02")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📊  New analysis", width="stretch", type="primary"):
            st.switch_page("pages/1_📊_Analysis.py")
    with col2:
        if st.button("📈  History", width="stretch"):
            st.switch_page("pages/2_📈_Analysis_History.py")
    with col3:
        if st.button("🔍  Results", width="stretch"):
            st.switch_page("pages/3_🔍_Results_Viewer.py")
    with col4:
        if st.button("🌙  Batch queue", width="stretch"):
            st.switch_page("pages/4_🌙_Batch_Queue.py")


if __name__ == "__main__":
    main()
