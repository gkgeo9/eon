#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Viewer - View cached data, analysis runs, and database statistics.
"""

import os
import json
import streamlit as st
import pandas as pd
from pathlib import Path
from fintel.ui.database import DatabaseRepository
from fintel.ui.utils.validators import validate_prompt_template, validate_prompt_name
from fintel.ui.theme import apply_theme
from fintel.core.analysis_types import CLI_ANALYSIS_CHOICES

# Apply global theme
apply_theme()

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseRepository()

if 'show_prompt_editor' not in st.session_state:
    st.session_state.show_prompt_editor = False

if 'edit_prompt_id' not in st.session_state:
    st.session_state.edit_prompt_id = None

db = st.session_state.db

st.title("🗄️ Database Viewer")
st.markdown("Inspect cached data, analysis runs, and database statistics")

st.markdown("---")

# Tab selection
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Analysis Runs",
    "📄 Analysis Results",
    "📁 File Cache",
    "📝 Custom Prompts",
    "📈 Statistics",
    "🔑 API Usage"
])

# Tab 1: Analysis Runs
with tab1:
    st.subheader("Analysis Runs")
    st.markdown("View all analysis run records. **Select a run to view its results.**")

    query = """
    SELECT
        run_id,
        ticker,
        company_name,
        analysis_type,
        filing_type,
        status,
        years_analyzed,
        created_at,
        started_at,
        completed_at,
        error_message
    FROM analysis_runs
    ORDER BY created_at DESC
    LIMIT 100
    """

    runs_df = db._execute_query(query)

    if not runs_df.empty:
        st.markdown(f"**Total Runs**: {len(runs_df)}")

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_ticker = st.text_input("Filter by Ticker", key="runs_ticker_filter")
        with col2:
            filter_status = st.selectbox(
                "Filter by Status",
                ["All", "completed", "running", "pending", "failed"],
                key="runs_status_filter"
            )
        with col3:
            filter_type = st.selectbox(
                "Filter by Type",
                ["All"] + CLI_ANALYSIS_CHOICES,
                key="runs_type_filter"
            )

        # Apply filters
        filtered_df = runs_df.copy()
        if filter_ticker:
            filtered_df = filtered_df[filtered_df['ticker'].str.contains(filter_ticker.upper(), case=False, na=False)]
        if filter_status != "All":
            filtered_df = filtered_df[filtered_df['status'] == filter_status]
        if filter_type != "All":
            filtered_df = filtered_df[filtered_df['analysis_type'] == filter_type]

        # Create display labels for selection
        filtered_df['display'] = (
            filtered_df['ticker'] + " | " +
            filtered_df['analysis_type'] + " | " +
            filtered_df['status'] + " | " +
            filtered_df['created_at'].str[:10]
        )

        if len(filtered_df) > 0:
            # Selectable dropdown
            selected_run_idx = st.selectbox(
                "Select a run to inspect",
                options=filtered_df.index.tolist(),
                format_func=lambda idx: filtered_df.loc[idx, 'display'],
                key="runs_selector"
            )

            selected_run = filtered_df.loc[selected_run_idx]

            # Show run details
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Ticker", selected_run['ticker'])
            with col2:
                st.metric("Type", selected_run['analysis_type'])
            with col3:
                status_emoji = {"completed": "✅", "failed": "❌", "running": "🔄", "pending": "⏳"}.get(selected_run['status'], "❓")
                st.metric("Status", f"{status_emoji} {selected_run['status']}")
            with col4:
                st.metric("Years", selected_run['years_analyzed'] or "N/A")

            # Show error if failed
            if selected_run['status'] == 'failed' and selected_run['error_message']:
                st.error(f"**Error:** {selected_run['error_message']}")

            # Get results for this run
            results_query = """
            SELECT id, fiscal_year, result_type, LENGTH(result_json) as json_size
            FROM analysis_results
            WHERE run_id = ?
            ORDER BY fiscal_year DESC
            """
            run_results = db._execute_query(results_query, params=(selected_run['run_id'],))

            if not run_results.empty:
                st.markdown(f"**{len(run_results)} result(s) for this run:**")

                # Let user select which result to view
                run_results['display'] = (
                    "FY" + run_results['fiscal_year'].astype(str) + " | " +
                    run_results['result_type'] + " | " +
                    run_results['json_size'].astype(str) + " bytes"
                )

                selected_result_idx = st.selectbox(
                    "Select result to view JSON",
                    options=run_results.index.tolist(),
                    format_func=lambda idx: run_results.loc[idx, 'display'],
                    key="run_results_selector"
                )

                if st.button("📄 View JSON for Selected Result", type="primary", key="view_run_result_json"):
                    st.session_state.viewing_run_result_id = int(run_results.loc[selected_result_idx, 'id'])

                # Show JSON if viewing
                if st.session_state.get('viewing_run_result_id') == int(run_results.loc[selected_result_idx, 'id']):
                    result_id = int(run_results.loc[selected_result_idx, 'id'])
                    json_query = "SELECT result_json FROM analysis_results WHERE id = ?"
                    result_row = db._execute_query(json_query, params=(result_id,))

                    if not result_row.empty:
                        result_json = result_row.iloc[0]['result_json']
                        result_dict = json.loads(result_json)

                        st.markdown("---")
                        fiscal_year = int(run_results.loc[selected_result_idx, 'fiscal_year'])
                        result_type = run_results.loc[selected_result_idx, 'result_type']
                        st.subheader(f"JSON: {selected_run['ticker']} FY{fiscal_year} - {result_type}")

                        # Download button
                        st.download_button(
                            "📥 Download JSON",
                            data=json.dumps(result_dict, indent=2),
                            file_name=f"{selected_run['ticker']}_{fiscal_year}_{result_type}.json",
                            mime="application/json"
                        )

                        st.json(result_dict)
            else:
                if selected_run['status'] == 'completed':
                    st.warning("No results stored for this completed run. The analysis may have failed silently.")
                else:
                    st.info("No results yet for this run.")

        # Also show the table
        st.markdown("---")
        st.markdown("**All Runs (filtered)**")
        st.dataframe(
            filtered_df[['run_id', 'ticker', 'analysis_type', 'filing_type', 'status', 'years_analyzed', 'created_at', 'error_message']],
            width="stretch",
            hide_index=True,
            column_config={
                "run_id": st.column_config.TextColumn("Run ID", width="small"),
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "analysis_type": st.column_config.TextColumn("Type", width="small"),
                "filing_type": st.column_config.TextColumn("Filing", width="small"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "years_analyzed": st.column_config.TextColumn("Years", width="medium"),
                "created_at": st.column_config.TextColumn("Created", width="medium"),
                "error_message": st.column_config.TextColumn("Error", width="large"),
            }
        )
    else:
        st.info("No analysis runs found in database")

# Tab 2: Analysis Results
with tab2:
    st.subheader("Analysis Results")
    st.markdown("View stored analysis results (Pydantic model outputs). **Click a row to view its JSON.**")

    query = """
    SELECT
        id,
        run_id,
        ticker,
        fiscal_year,
        filing_type,
        result_type,
        created_at,
        LENGTH(result_json) as json_size
    FROM analysis_results
    ORDER BY created_at DESC
    LIMIT 100
    """

    results_df = db._execute_query(query)

    if not results_df.empty:
        st.markdown(f"**Total Results**: {len(results_df)}")

        # Filters
        col1, col2 = st.columns(2)
        with col1:
            filter_ticker_res = st.text_input("Filter by Ticker", key="results_ticker_filter")
        with col2:
            filter_type_res = st.selectbox(
                "Filter by Result Type",
                ["All"] + list(results_df['result_type'].unique()),
                key="results_type_filter"
            )

        # Apply filters
        filtered_results = results_df.copy()
        if filter_ticker_res:
            filtered_results = filtered_results[filtered_results['ticker'].str.contains(filter_ticker_res.upper(), case=False, na=False)]
        if filter_type_res != "All":
            filtered_results = filtered_results[filtered_results['result_type'] == filter_type_res]

        # Create display labels for selection
        filtered_results['display'] = (
            filtered_results['ticker'] + " | FY" +
            filtered_results['fiscal_year'].astype(str) + " | " +
            filtered_results['result_type'] + " | " +
            filtered_results['created_at'].str[:10]
        )

        # Selectable list
        if len(filtered_results) > 0:
            selected_idx = st.selectbox(
                "Select a result to view",
                options=filtered_results.index.tolist(),
                format_func=lambda idx: filtered_results.loc[idx, 'display'],
                key="results_selector"
            )

            selected_result = filtered_results.loc[selected_idx]

            # Show selected result details
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Ticker", selected_result['ticker'])
            with col2:
                st.metric("Year", int(selected_result['fiscal_year']))
            with col3:
                st.metric("Type", selected_result['result_type'])
            with col4:
                st.metric("Size", f"{selected_result['json_size']:,} bytes")

            # View JSON button
            if st.button("📄 View Full JSON", type="primary", key="view_selected_json"):
                st.session_state.viewing_result_id = int(selected_result['id'])

            # Show JSON if viewing
            if st.session_state.get('viewing_result_id') == int(selected_result['id']):
                query = "SELECT result_json FROM analysis_results WHERE id = ?"
                result_row = db._execute_query(query, params=(int(selected_result['id']),))
                if not result_row.empty:
                    result_json = result_row.iloc[0]['result_json']
                    result_dict = json.loads(result_json)

                    st.markdown("---")
                    st.subheader(f"JSON: {selected_result['ticker']} FY{int(selected_result['fiscal_year'])} - {selected_result['result_type']}")

                    # Download button
                    st.download_button(
                        "📥 Download JSON",
                        data=json.dumps(result_dict, indent=2),
                        file_name=f"{selected_result['ticker']}_{int(selected_result['fiscal_year'])}_{selected_result['result_type']}.json",
                        mime="application/json"
                    )

                    # Display JSON
                    st.json(result_dict)

        # Also show the table for reference
        st.markdown("---")
        st.markdown("**All Results (filtered)**")
        st.dataframe(
            filtered_results[['id', 'ticker', 'fiscal_year', 'filing_type', 'result_type', 'created_at', 'json_size']],
            width="stretch",
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "fiscal_year": st.column_config.NumberColumn("Year", width="small"),
                "filing_type": st.column_config.TextColumn("Filing", width="small"),
                "result_type": st.column_config.TextColumn("Result Type", width="medium"),
                "created_at": st.column_config.TextColumn("Created", width="medium"),
                "json_size": st.column_config.NumberColumn("Size (bytes)", width="small"),
            }
        )
    else:
        st.info("No analysis results found in database")

# Tab 3: File Cache
with tab3:
    st.subheader("File Cache")
    st.markdown("View cached PDF files and their locations")

    query = """
    SELECT
        id,
        ticker,
        fiscal_year,
        filing_type,
        file_path,
        file_hash,
        downloaded_at
    FROM file_cache
    ORDER BY downloaded_at DESC
    """

    cache_df = db._execute_query(query)

    if not cache_df.empty:
        st.markdown(f"**Total Cached Files**: {len(cache_df)}")

        # Check which files actually exist
        cache_df['exists'] = cache_df['file_path'].apply(lambda p: '✅' if Path(p).exists() else '❌')

        # Filter
        filter_ticker_cache = st.text_input("Filter by Ticker", key="cache_ticker_filter")

        filtered_cache = cache_df.copy()
        if filter_ticker_cache:
            filtered_cache = filtered_cache[filtered_cache['ticker'].str.contains(filter_ticker_cache.upper(), case=False, na=False)]

        st.dataframe(
            filtered_cache,
            width="stretch",
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "fiscal_year": st.column_config.NumberColumn("Year", width="small"),
                "filing_type": st.column_config.TextColumn("Filing", width="small"),
                "file_path": st.column_config.TextColumn("Path", width="large"),
                "file_hash": st.column_config.TextColumn("Hash", width="small"),
                "downloaded_at": st.column_config.TextColumn("Downloaded", width="medium"),
                "exists": st.column_config.TextColumn("Exists", width="small"),
            }
        )

        # Summary
        st.markdown("---")
        st.subheader("Cache Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Files", len(cache_df))
        with col2:
            existing = len([p for p in cache_df['file_path'] if Path(p).exists()])
            st.metric("Existing Files", existing)
        with col3:
            missing = len(cache_df) - existing
            st.metric("Missing Files", missing)

        # Cache actions
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Clear All Cache", type="secondary", width="stretch"):
                if st.session_state.get('confirm_clear_cache', False):
                    deleted = db.clear_file_cache()
                    st.success(f"Cleared {deleted} cached files")
                    st.session_state.confirm_clear_cache = False
                    st.rerun()
                else:
                    st.session_state.confirm_clear_cache = True
                    st.warning("Click again to confirm")

        with col2:
            if missing > 0:
                if st.button("Clean Up Missing Entries", width="stretch"):
                    for idx, row in cache_df.iterrows():
                        if not Path(row['file_path']).exists():
                            delete_query = "DELETE FROM file_cache WHERE id = ?"
                            db._execute_update(delete_query, params=(int(row['id']),))
                    st.success(f"Removed {missing} missing cache entries")
                    st.rerun()
    else:
        st.info("No cached files found in database")

# Tab 4: Custom Prompts
with tab4:
    st.subheader("Custom Prompts")
    st.markdown("Create and manage custom analysis prompts")

    # Show existing prompts as a table first
    prompts_df = db._execute_query("SELECT id, name, analysis_type, description, created_at FROM custom_prompts ORDER BY created_at DESC")

    if not prompts_df.empty:
        st.markdown(f"**Total Prompts**: {len(prompts_df)}")

        st.dataframe(
            prompts_df,
            width="stretch",
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "name": st.column_config.TextColumn("Name", width="medium"),
                "analysis_type": st.column_config.TextColumn("Type", width="small"),
                "description": st.column_config.TextColumn("Description", width="large"),
                "created_at": st.column_config.TextColumn("Created", width="medium"),
            }
        )
    else:
        st.info("No custom prompts found")

    st.markdown("---")

    # Prompt management section
    st.subheader("Manage Prompts")

    analysis_type = st.selectbox(
        "Analysis Type",
        options=["fundamental", "buffett", "taleb", "contrarian"],
        help="Select analysis type for prompts"
    )

    prompts = db.get_prompts_by_type(analysis_type)

    if prompts:
        for prompt in prompts:
            with st.expander(f"📄 {prompt['name']}"):
                st.caption(f"Created: {prompt['created_at']}")

                if prompt.get('description'):
                    st.markdown(f"**Description:** {prompt['description']}")

                st.text_area(
                    "Template",
                    value=prompt['template'],
                    height=150,
                    disabled=True,
                    key=f"view_{prompt['id']}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Edit", key=f"edit_{prompt['id']}"):
                        st.session_state.edit_prompt_id = prompt['id']
                        st.session_state.show_prompt_editor = True
                        st.rerun()
                with col2:
                    if st.button("Delete", key=f"delete_{prompt['id']}", type="secondary"):
                        db.delete_prompt(prompt['id'])
                        st.success(f"Deleted: {prompt['name']}")
                        st.rerun()

    # Create new prompt
    if st.button("Create New Prompt", type="primary"):
        st.session_state.show_prompt_editor = True
        st.session_state.edit_prompt_id = None

    if st.session_state.show_prompt_editor:
        st.markdown("---")

        edit_mode = st.session_state.edit_prompt_id is not None
        existing_prompt = None

        if edit_mode:
            matching = [p for p in prompts if p['id'] == st.session_state.edit_prompt_id]
            if matching:
                existing_prompt = db.get_prompt_by_name(matching[0]['name'])

        with st.form("prompt_form"):
            name = st.text_input("Name", value=existing_prompt['name'] if existing_prompt else "")
            description = st.text_area("Description", value=existing_prompt.get('description', '') if existing_prompt else "", height=80)
            template = st.text_area(
                "Template",
                value=existing_prompt.get('prompt_template', existing_prompt.get('template', '')) if existing_prompt else "",
                height=200,
                help="Use {ticker} and {year} as placeholders"
            )

            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Save", type="primary", width="stretch")
            with col2:
                cancelled = st.form_submit_button("Cancel", width="stretch")

            if cancelled:
                st.session_state.show_prompt_editor = False
                st.session_state.edit_prompt_id = None
                st.rerun()

            if submitted and name and template:
                try:
                    if edit_mode and existing_prompt:
                        db.update_prompt(st.session_state.edit_prompt_id, name=name, description=description, prompt_template=template)
                        st.success(f"Updated: {name}")
                    else:
                        db.save_prompt(name=name, description=description, prompt_template=template, analysis_type=analysis_type)
                        st.success(f"Created: {name}")
                    st.session_state.show_prompt_editor = False
                    st.session_state.edit_prompt_id = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# Tab 5: Statistics
with tab5:
    st.subheader("Database Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Analysis Runs by Status")
        status_query = """
        SELECT status, COUNT(*) as count
        FROM analysis_runs
        GROUP BY status
        """
        status_df = db._execute_query(status_query)
        if not status_df.empty:
            st.bar_chart(status_df.set_index('status'))
            st.dataframe(status_df, width="stretch", hide_index=True)

        st.markdown("---")

        st.markdown("#### Analysis Runs by Type")
        type_query = """
        SELECT analysis_type, COUNT(*) as count
        FROM analysis_runs
        GROUP BY analysis_type
        """
        type_df = db._execute_query(type_query)
        if not type_df.empty:
            st.bar_chart(type_df.set_index('analysis_type'))
            st.dataframe(type_df, width="stretch", hide_index=True)

    with col2:
        st.markdown("#### Top 10 Most Analyzed Tickers")
        ticker_query = """
        SELECT ticker, COUNT(*) as analysis_count
        FROM analysis_runs
        GROUP BY ticker
        ORDER BY analysis_count DESC
        LIMIT 10
        """
        ticker_df = db._execute_query(ticker_query)
        if not ticker_df.empty:
            st.bar_chart(ticker_df.set_index('ticker'))
            st.dataframe(ticker_df, width="stretch", hide_index=True)

        st.markdown("---")

        st.markdown("#### Database Size")
        from fintel.core import get_config
        config = get_config()
        db_path = config.get_data_path("fintel.db")
        if db_path.exists():
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            st.metric("Database File Size", f"{db_size_mb:.2f} MB")

        # Table row counts
        st.markdown("#### Table Row Counts")
        tables = ['analysis_runs', 'analysis_results', 'file_cache', 'user_settings', 'custom_prompts']
        counts = {}
        for table in tables:
            count_query = f"SELECT COUNT(*) as count FROM {table}"
            count_df = db._execute_query(count_query)
            if not count_df.empty:
                counts[table] = count_df.iloc[0]['count']

        counts_df = pd.DataFrame(list(counts.items()), columns=['Table', 'Rows'])
        st.dataframe(counts_df, width="stretch", hide_index=True)

# Tab 6: API Usage
with tab6:
    st.subheader("API Usage Tracking")
    st.markdown("Monitor API usage across all configured keys (persistent JSON-based tracking)")

    # Import the new API usage tracking system
    from fintel.core import get_config
    from fintel.ai import get_api_limits, get_usage_tracker, APIKeyManager

    config = get_config()
    limits = get_api_limits()
    tracker = get_usage_tracker()

    # Configuration info
    st.markdown("#### Configuration")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Daily Limit/Key", limits.DAILY_LIMIT_PER_KEY)
    with col2:
        st.metric("Sleep After Request", f"{limits.SLEEP_AFTER_REQUEST}s")
    with col3:
        st.metric("Warning Threshold", f"{int(limits.WARNING_THRESHOLD * 100)}%")
    with col4:
        st.metric("Total API Keys", len(config.google_api_keys))

    st.caption(f"*Edit limits in: `fintel/ai/api_config.py`*")
    st.markdown("---")

    # Get usage for all configured keys
    if config.google_api_keys:
        api_key_manager = APIKeyManager(config.google_api_keys)
        usage_stats = api_key_manager.get_usage_stats()
        summary = api_key_manager.get_summary()

        # Summary metrics
        st.markdown("#### Today's Summary")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Used Today", summary['total_used_today'])
        with col2:
            st.metric("Total Remaining", summary['total_remaining_today'])
        with col3:
            st.metric("Keys Available", f"{summary['available_keys']}/{summary['total_keys']}")
        with col4:
            st.metric("Utilization", f"{summary['utilization_percent']}%")

        if summary['exhausted_keys'] > 0:
            st.warning(f"{summary['exhausted_keys']} API key(s) have reached their daily limit!")

        if summary['keys_near_limit'] > 0:
            st.info(f"{summary['keys_near_limit']} API key(s) are approaching their daily limit (>{int(limits.WARNING_THRESHOLD * 100)}%)")

        st.markdown("---")

        # Per-key usage table
        st.markdown("#### Usage by API Key")

        if usage_stats:
            # Convert to DataFrame for display
            usage_data = []
            for key_id, stats in usage_stats.items():
                status = "Exhausted" if not stats['can_make_request'] else ("Near Limit" if stats['near_limit'] else "Available")
                status_emoji = {"Exhausted": "🔴", "Near Limit": "🟡", "Available": "🟢"}[status]
                usage_data.append({
                    'Key': key_id,
                    'Status': f"{status_emoji} {status}",
                    'Used Today': stats['used_today'],
                    'Remaining': stats['remaining_today'],
                    'Limit': stats['daily_limit'],
                    'Usage %': f"{stats['percentage_used']}%",
                    'Errors Today': stats['errors_today'],
                    'Total Requests': stats['total_requests'],
                    'Last Used': stats['last_used'][:19] if stats['last_used'] else 'Never',
                })

            usage_df = pd.DataFrame(usage_data)
            st.dataframe(
                usage_df,
                width="stretch",
                hide_index=True,
                column_config={
                    "Key": st.column_config.TextColumn("Key (last 4)", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Used Today": st.column_config.NumberColumn("Used Today", width="small"),
                    "Remaining": st.column_config.NumberColumn("Remaining", width="small"),
                    "Limit": st.column_config.NumberColumn("Limit", width="small"),
                    "Usage %": st.column_config.TextColumn("Usage %", width="small"),
                    "Errors Today": st.column_config.NumberColumn("Errors", width="small"),
                    "Total Requests": st.column_config.NumberColumn("All-Time", width="small"),
                    "Last Used": st.column_config.TextColumn("Last Used", width="medium"),
                }
            )

        st.markdown("---")

        # Visual progress bars for each key
        st.markdown("#### Key Status (Visual)")

        for key_id, stats in usage_stats.items():
            pct = stats['percentage_used'] / 100.0
            col1, col2 = st.columns([3, 1])
            with col1:
                st.progress(min(pct, 1.0), text=f"{key_id}: {stats['used_today']}/{stats['daily_limit']}")
            with col2:
                if not stats['can_make_request']:
                    st.markdown("**🔴 Exhausted**")
                elif stats['near_limit']:
                    st.markdown("**🟡 Near Limit**")
                else:
                    st.markdown("**🟢 Available**")

        st.markdown("---")

        # Usage history for individual keys
        st.markdown("#### Usage History (Last 7 Days)")

        # Let user select a key to view history
        key_options = list(usage_stats.keys())
        if key_options:
            selected_key_display = st.selectbox("Select Key", options=key_options, key="history_key_select")

            # Find the actual key
            selected_key = None
            for key in config.google_api_keys:
                if f"...{key[-4:]}" == selected_key_display:
                    selected_key = key
                    break

            if selected_key:
                history = tracker.get_usage_history(selected_key, days=7)
                if history:
                    history_df = pd.DataFrame(history)
                    st.bar_chart(history_df.set_index('date')['request_count'])

                    with st.expander("View Raw History Data"):
                        st.dataframe(history_df, width="stretch", hide_index=True)

        st.markdown("---")

        # Actions
        st.markdown("#### Actions")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Refresh Usage Data", width="stretch"):
                st.rerun()

        with col2:
            if st.button("Reset All Usage Data", type="secondary", width="stretch"):
                if st.session_state.get('confirm_reset_usage', False):
                    tracker.reset_all_usage()
                    st.success("All usage data has been reset!")
                    st.session_state.confirm_reset_usage = False
                    st.rerun()
                else:
                    st.session_state.confirm_reset_usage = True
                    st.warning("Click again to confirm reset")

        # Data location info
        st.markdown("---")
        st.caption(f"**Usage data location:** `{tracker.usage_dir}`")
        st.caption("Each API key's usage is stored in a separate JSON file for parallel-safe tracking.")

    else:
        st.warning("No API keys configured. Add keys to your `.env` file:")
        st.code("""
GOOGLE_API_KEY_1=your_first_key
GOOGLE_API_KEY_2=your_second_key
GOOGLE_API_KEY_3=your_third_key
# ... up to unlimited keys
        """)

        st.markdown("---")
        st.markdown("""
        **How API usage tracking works:**
        - Each API key has its own JSON file for usage data
        - Usage is tracked per key per day with timestamps
        - File locking ensures safe parallel access
        - Daily limits are enforced (configurable in `fintel/ai/api_config.py`)
        - Least-used key is automatically selected for each request
        """)

# Navigation
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("Home", width="stretch"):
        st.switch_page("streamlit_app.py")

with col2:
    if st.button("View History", width="stretch"):
        st.switch_page("pages/2_📈_Analysis_History.py")
