#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch Queue Page - Manage large-scale multi-day analysis jobs.

This page allows users to:
- Create batch jobs with 1000+ tickers
- Monitor progress over multiple days
- Handle automatic rate limit waiting
- Resume after crashes
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime

from fintel.ui.database import DatabaseRepository
from fintel.ui.services.batch_queue import BatchQueueService, BatchJobConfig
from fintel.ui.theme import apply_theme

apply_theme()

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

if 'batch_queue' not in st.session_state:
    st.session_state.batch_queue = BatchQueueService(st.session_state.db)

db = st.session_state.db
queue = st.session_state.batch_queue

st.title("Batch Queue")
st.markdown("Manage large-scale analysis jobs that run overnight or over multiple days")

st.markdown("---")

# Queue status overview
queue_state = queue.get_queue_state()

col1, col2, col3 = st.columns(3)

with col1:
    status_text = "Running" if queue_state.get('is_running') else "Idle"
    st.metric("Queue Status", status_text)

with col2:
    if queue_state.get('next_run_at'):
        try:
            next_run = datetime.fromisoformat(queue_state['next_run_at'])
            st.metric("Next Run", next_run.strftime("%b %d, %H:%M"))
        except:
            st.metric("Next Run", "-")
    else:
        st.metric("Next Run", "-")

with col3:
    daily_requests = queue_state.get('daily_requests_made', 0)
    st.metric("Daily Requests", daily_requests)

st.markdown("---")

# Create new batch job
st.subheader("Create New Batch Job")

with st.expander("New Batch", expanded=False):
    batch_name = st.text_input("Job Name", placeholder="e.g., S&P 500 Analysis - January 2024")

    # Ticker input
    ticker_input = st.text_area(
        "Tickers (comma or newline separated)",
        placeholder="AAPL, MSFT, GOOGL, AMZN, META...\nor one per line",
        height=150
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        analysis_type = st.selectbox(
            "Analysis Type",
            ["fundamental", "objective", "buffett", "taleb", "contrarian", "excellent"]
        )
    with col2:
        filing_type = st.selectbox(
            "Filing Type",
            ["10-K", "10-Q", "8-K"]
        )
    with col3:
        num_years = st.slider("Years", 1, 10, 5)

    # Parse tickers
    if ticker_input:
        tickers = [t.strip().upper() for t in ticker_input.replace(',', '\n').split('\n') if t.strip()]
        st.caption(f"Parsed {len(tickers)} tickers")

        # Estimate time
        if len(tickers) > 0:
            from fintel.core import get_config
            config = get_config()
            keys_count = len(config.google_api_keys)
            requests_per_day = keys_count * 20

            days_estimate = len(tickers) / max(requests_per_day, 1)
            if days_estimate < 1:
                time_estimate = f"~{int(days_estimate * 24)} hours"
            else:
                time_estimate = f"~{days_estimate:.1f} days"

            st.info(f"Estimated time: {time_estimate} ({requests_per_day} analyses/day with {keys_count} API keys)")

    if st.button("Create Batch Job", type="primary"):
        if not batch_name:
            st.error("Please enter a job name")
        elif not ticker_input:
            st.error("Please enter at least one ticker")
        else:
            tickers = [t.strip().upper() for t in ticker_input.replace(',', '\n').split('\n') if t.strip()]
            if not tickers:
                st.error("No valid tickers found")
            else:
                config = BatchJobConfig(
                    name=batch_name,
                    tickers=tickers,
                    analysis_type=analysis_type,
                    filing_type=filing_type,
                    num_years=num_years
                )
                batch_id = queue.create_batch_job(config)
                st.success(f"Created batch job with {len(tickers)} tickers")
                st.session_state.new_batch_id = batch_id
                time.sleep(1)
                st.rerun()

st.markdown("---")

# Show existing batches
st.subheader("Batch Jobs")

batches = queue.get_all_batches()

if not batches:
    st.info("No batch jobs yet. Create one above.")
else:
    for batch in batches:
        status_emoji = {
            'pending': '&#x23F3;',      # hourglass
            'running': '&#x1F504;',     # refresh
            'paused': '&#x23F8;',       # pause
            'waiting_reset': '&#x1F319;', # moon
            'completed': '&#x2705;',    # checkmark
            'failed': '&#x274C;',       # X
            'stopped': '&#x1F6D1;'      # stop sign
        }.get(batch['status'], '&#x2753;')  # question mark

        # Use markdown for emoji to avoid streamlit issues
        status_text = {
            'pending': 'Pending',
            'running': 'Running',
            'paused': 'Paused',
            'waiting_reset': 'Waiting for Reset',
            'completed': 'Completed',
            'failed': 'Failed',
            'stopped': 'Stopped'
        }.get(batch['status'], 'Unknown')

        with st.expander(
            f"{status_text} - {batch['name']} ({batch['progress_percent']}%)",
            expanded=batch['status'] in ['running', 'waiting_reset']
        ):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Completed", f"{batch['completed_tickers']}/{batch['total_tickers']}")
            with col2:
                st.metric("Failed", batch['failed_tickers'])
            with col3:
                pending = batch['total_tickers'] - batch['completed_tickers'] - batch['failed_tickers']
                st.metric("Pending", pending)
            with col4:
                if batch['estimated_completion']:
                    try:
                        est = datetime.fromisoformat(batch['estimated_completion'])
                        st.metric("Est. Done", est.strftime("%b %d"))
                    except:
                        st.metric("Est. Done", "-")
                else:
                    st.metric("Est. Done", "-")

            # Progress bar
            st.progress(batch['progress_percent'] / 100)

            # Status-specific info
            if batch['status'] == 'waiting_reset':
                st.info("Waiting for midnight PST rate limit reset...")
            elif batch['status'] == 'failed':
                batch_details = queue.get_batch_status(batch['batch_id'])
                if batch_details and batch_details.get('error_message'):
                    st.error(f"Error: {batch_details['error_message']}")

            # Actions
            st.markdown("**Actions:**")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if batch['status'] == 'pending':
                    if st.button("Start", key=f"start_{batch['batch_id']}", type="primary"):
                        queue.start_batch_job(batch['batch_id'])
                        st.success("Started")
                        time.sleep(1)
                        st.rerun()
                elif batch['status'] == 'paused':
                    if st.button("Resume", key=f"resume_{batch['batch_id']}", type="primary"):
                        queue.resume_batch(batch['batch_id'])
                        st.success("Resumed")
                        time.sleep(1)
                        st.rerun()
                elif batch['status'] in ['stopped', 'failed']:
                    if st.button("Restart", key=f"restart_{batch['batch_id']}", type="primary"):
                        queue.start_batch_job(batch['batch_id'])
                        st.success("Restarted")
                        time.sleep(1)
                        st.rerun()

            with col2:
                if batch['status'] in ['running', 'waiting_reset']:
                    if st.button("Pause", key=f"pause_{batch['batch_id']}"):
                        queue.pause_batch(batch['batch_id'])
                        st.success("Paused")
                        time.sleep(1)
                        st.rerun()

            with col3:
                if batch['status'] in ['running', 'paused', 'waiting_reset']:
                    if st.button("Stop", key=f"stop_{batch['batch_id']}", type="secondary"):
                        queue.stop_batch(batch['batch_id'])
                        st.success("Stopped")
                        time.sleep(1)
                        st.rerun()

            with col4:
                if st.button("Details", key=f"details_{batch['batch_id']}"):
                    st.session_state.view_batch_id = batch['batch_id']
                    st.rerun()

            # Delete option (only for completed/stopped/failed)
            if batch['status'] in ['completed', 'stopped', 'failed', 'pending']:
                if st.button("Delete", key=f"delete_{batch['batch_id']}", type="secondary"):
                    queue.delete_batch(batch['batch_id'])
                    st.success("Deleted")
                    time.sleep(1)
                    st.rerun()

# Show batch details if selected
if 'view_batch_id' in st.session_state:
    st.markdown("---")
    st.subheader("Batch Details")

    batch_id = st.session_state.view_batch_id
    batch = queue.get_batch_status(batch_id)

    if batch:
        # Summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", batch['total_tickers'])
        with col2:
            st.metric("Completed", batch['completed_tickers'])
        with col3:
            st.metric("Failed", batch['failed_tickers'])
        with col4:
            st.metric("Pending", batch['pending_tickers'])

        # Tabs for different item statuses
        tab_all, tab_completed, tab_failed, tab_pending = st.tabs(["All", "Completed", "Failed", "Pending"])

        with tab_all:
            items = queue.get_batch_items(batch_id, limit=50)
            if items:
                df = pd.DataFrame(items)
                st.dataframe(
                    df[['ticker', 'status', 'attempts', 'error_message']],
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No items")

        with tab_completed:
            items = queue.get_batch_items(batch_id, status='completed', limit=50)
            if items:
                df = pd.DataFrame(items)
                st.dataframe(
                    df[['ticker', 'run_id', 'completed_at']],
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No completed items")

        with tab_failed:
            items = queue.get_batch_items(batch_id, status='failed', limit=50)
            if items:
                df = pd.DataFrame(items)
                st.dataframe(
                    df[['ticker', 'attempts', 'error_message']],
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No failed items")

        with tab_pending:
            items = queue.get_batch_items(batch_id, status='pending', limit=50)
            if items:
                df = pd.DataFrame(items)
                st.dataframe(
                    df[['ticker', 'company_name']],
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No pending items")

    if st.button("Close Details"):
        del st.session_state.view_batch_id
        st.rerun()

# Auto-refresh for running batches
running_batches = [b for b in batches if b['status'] in ['running', 'waiting_reset']]
if running_batches:
    st.markdown("---")
    auto_refresh = st.checkbox("Auto-refresh (30s)", value=True)
    if auto_refresh:
        time.sleep(30)
        st.rerun()

# Navigation
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("Home", use_container_width=True):
        st.switch_page("streamlit_app.py")

with col2:
    if st.button("Analysis History", use_container_width=True):
        st.switch_page("pages/2_📈_Analysis_History.py")
