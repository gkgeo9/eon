#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch Queue Page - Manage large-scale multi-day analysis jobs.

This page allows users to:
- Create batch jobs with 1000+ tickers
- Monitor progress over multiple days
- Handle automatic rate limit waiting
- Resume after crashes
- Export batch results as summary tables
"""

import streamlit as st
import pandas as pd
import time
import io
from datetime import datetime

from fintel.ui.database import DatabaseRepository
from fintel.ui.services.batch_queue import BatchQueueService, BatchJobConfig
from fintel.ui.theme import apply_theme

# Import custom workflows discovery
try:
    from custom_workflows import list_workflows, get_workflow
    CUSTOM_WORKFLOWS_AVAILABLE = True
except ImportError:
    CUSTOM_WORKFLOWS_AVAILABLE = False
    def list_workflows():
        return []
    def get_workflow(workflow_id):
        return None

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

# Check for stale running batches (crashed but still showing as running)
stale_batches = queue.get_stale_running_batches(stale_minutes=5)
for stale in stale_batches:
    queue.mark_batch_as_crashed(stale['batch_id'])
    st.info(f"Detected crashed batch '{stale['name']}' - marked for resume")

# Check for interrupted batches that need attention
all_batches = queue.get_all_batches()
interrupted_batches = [
    b for b in all_batches
    if b['status'] in ['stopped', 'failed'] and b['completed_tickers'] > 0 and b['completed_tickers'] < b['total_tickers']
]

if interrupted_batches:
    st.warning(f"**{len(interrupted_batches)} batch(es) were interrupted and can be resumed**")
    for batch in interrupted_batches:
        pending = batch['total_tickers'] - batch['completed_tickers'] - batch['failed_tickers']
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.markdown(f"**{batch['name']}** - {batch['completed_tickers']}/{batch['total_tickers']} completed")
        with col2:
            st.caption(f"{pending} companies remaining")
        with col3:
            if st.button("Resume", key=f"quick_resume_{batch['batch_id']}", type="primary"):
                queue.start_batch_job(batch['batch_id'])
                st.success(f"Resumed from company {batch['completed_tickers'] + 1}")
                time.sleep(1)
                st.rerun()
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

    # Ticker input methods
    input_method = st.radio(
        "Input Method",
        ["Manual Entry", "CSV Upload"],
        horizontal=True,
        key="batch_input_method"
    )

    tickers = []
    company_names_dict = {}

    if input_method == "Manual Entry":
        ticker_input = st.text_area(
            "Tickers (comma or newline separated)",
            placeholder="AAPL, MSFT, GOOGL, AMZN, META...\nor one per line",
            height=150
        )

        if ticker_input:
            tickers = [t.strip().upper() for t in ticker_input.replace(',', '\n').split('\n') if t.strip()]
            st.caption(f"Parsed {len(tickers)} tickers")
    else:
        st.markdown("""
        Upload a CSV with columns:
        - **ticker** (required): Stock ticker symbol
        - **company_name** (optional): Company name for display
        """)

        uploaded_file = st.file_uploader("Choose CSV", type=['csv'], key="batch_csv")
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                if 'ticker' in df.columns:
                    tickers = [str(t).strip().upper() for t in df['ticker'].dropna() if str(t).strip()]
                    if 'company_name' in df.columns:
                        for _, row in df.iterrows():
                            if pd.notna(row['ticker']) and pd.notna(row.get('company_name')):
                                company_names_dict[str(row['ticker']).upper()] = str(row['company_name'])
                    st.success(f"Loaded {len(tickers)} tickers from CSV")
                    st.dataframe(df.head(10), use_container_width=True)
                else:
                    st.error("CSV must have a 'ticker' column")
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

    # Build analysis type options including custom workflows
    builtin_options = [
        ("Fundamental Analysis", "fundamental"),
        ("Excellent Company Success Factors", "excellent"),
        ("Objective Company Analysis", "objective"),
        ("Buffett Lens", "buffett"),
        ("Taleb Lens", "taleb"),
        ("Contrarian Lens", "contrarian"),
        ("Multi-Perspective", "multi"),
        ("Contrarian Scanner", "scanner"),
    ]

    # Get custom workflows
    custom_workflows = list_workflows()

    # Build options list
    analysis_options = [opt[0] for opt in builtin_options]
    analysis_type_map = {opt[0]: opt[1] for opt in builtin_options}

    # Add custom workflows if any exist
    if custom_workflows:
        analysis_options.append("--- Custom Workflows ---")
        for wf in custom_workflows:
            display_name = f"{wf['icon']} {wf['name']}"
            analysis_options.append(display_name)
            analysis_type_map[display_name] = f"custom:{wf['id']}"

    col1, col2 = st.columns(2)
    with col1:
        analysis_type_display = st.selectbox(
            "Analysis Type",
            analysis_options,
            key="batch_analysis_type"
        )

        # Handle separator selection
        if analysis_type_display.startswith("---"):
            analysis_type = "fundamental"
        else:
            analysis_type = analysis_type_map.get(analysis_type_display, "fundamental")

    with col2:
        filing_type = st.selectbox(
            "Filing Type",
            ["10-K", "10-Q", "8-K", "4", "DEF 14A", "20-F", "6-K"],
            key="batch_filing_type"
        )

    # Analysis type descriptions
    analysis_descriptions = {
        "fundamental": "Analyzes business model, financials, risks, and key strategies.",
        "excellent": "Multi-year analysis for proven winners - identifies what made excellent companies succeed. Requires 3+ years.",
        "objective": "Multi-year unbiased analysis - objective assessment of strengths and weaknesses. Requires 3+ years.",
        "buffett": "Warren Buffett perspective: economic moat, management quality, pricing power.",
        "taleb": "Nassim Taleb perspective: fragility assessment, tail risks, and antifragility.",
        "contrarian": "Contrarian perspective: variant perception, hidden opportunities.",
        "multi": "Combined analysis through all three investment lenses.",
        "scanner": "Six-dimension scoring system (0-600) for hidden compounder potential. Requires 3+ years."
    }

    if analysis_type in analysis_descriptions:
        st.info(analysis_descriptions[analysis_type])

    # Check multi-year requirement
    multi_year_required = analysis_type in ['excellent', 'objective', 'scanner']
    if analysis_type.startswith('custom:'):
        for wf in custom_workflows:
            if f"custom:{wf['id']}" == analysis_type and wf.get('min_years', 1) >= 3:
                multi_year_required = True
                break

    col1, col2 = st.columns(2)
    with col1:
        min_years = 3 if multi_year_required else 1
        num_years = st.slider("Number of Years", min_years, 10, max(5, min_years), key="batch_num_years")

    with col2:
        max_retries = st.slider("Max Retries per Ticker", 1, 5, 2, key="batch_max_retries")

    # Custom prompt option
    with st.expander("Advanced Options"):
        use_custom_prompt = st.checkbox("Use custom prompt", key="batch_use_custom")
        custom_prompt = None
        if use_custom_prompt:
            prompts = db.get_prompts_by_type(analysis_type)
            if prompts:
                prompt_names = [p['name'] for p in prompts]
                selected_prompt_name = st.selectbox("Select custom prompt", options=[""] + prompt_names)
                if selected_prompt_name:
                    prompt_data = db.get_prompt_by_name(selected_prompt_name)
                    if prompt_data:
                        custom_prompt = prompt_data['prompt_template']
                        st.text_area("Prompt Preview", value=custom_prompt, height=150, disabled=True)
            else:
                st.info("No custom prompts saved for this analysis type.")

    # Estimate time
    if tickers:
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
        elif not tickers:
            st.error("Please enter at least one ticker")
        else:
            batch_config = BatchJobConfig(
                name=batch_name,
                tickers=tickers,
                analysis_type=analysis_type,
                filing_type=filing_type,
                num_years=num_years,
                company_names=company_names_dict if company_names_dict else None,
                custom_prompt=custom_prompt if use_custom_prompt else None,
                max_retries=max_retries
            )
            batch_id = queue.create_batch_job(batch_config)
            st.success(f"Created batch job with {len(tickers)} tickers")
            st.session_state.new_batch_id = batch_id
            time.sleep(1)
            st.rerun()

st.markdown("---")

# Show existing batches
st.subheader("Batch Jobs")

# Reuse all_batches from interrupted check above
batches = all_batches

if not batches:
    st.info("No batch jobs yet. Create one above.")
else:
    for batch in batches:
        status_text = {
            'pending': 'Pending',
            'running': 'Running',
            'paused': 'Paused',
            'waiting_reset': 'Waiting for Reset',
            'completed': 'Completed',
            'failed': 'Failed',
            'stopped': 'Stopped'
        }.get(batch['status'], 'Unknown')

        status_icon = {
            'pending': ':hourglass:',
            'running': ':arrows_counterclockwise:',
            'paused': ':pause_button:',
            'waiting_reset': ':crescent_moon:',
            'completed': ':white_check_mark:',
            'failed': ':x:',
            'stopped': ':stop_sign:'
        }.get(batch['status'], ':question:')

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
            elif batch['status'] == 'stopped':
                batch_details = queue.get_batch_status(batch['batch_id'])
                if batch['completed_tickers'] > 0:
                    pending_count = batch['total_tickers'] - batch['completed_tickers'] - batch['failed_tickers']
                    st.info(
                        f"Batch was interrupted. **{batch['completed_tickers']} companies completed**, "
                        f"**{pending_count} remaining**. Click Resume to continue from where it left off."
                    )
                if batch_details and batch_details.get('error_message'):
                    st.caption(f"Reason: {batch_details['error_message']}")
            elif batch['status'] == 'failed':
                batch_details = queue.get_batch_status(batch['batch_id'])
                if batch['completed_tickers'] > 0:
                    pending_count = batch['total_tickers'] - batch['completed_tickers'] - batch['failed_tickers']
                    st.info(
                        f"Batch failed but **{batch['completed_tickers']} companies are saved**. "
                        f"Resume will continue from company {batch['completed_tickers'] + 1}."
                    )
                if batch_details and batch_details.get('error_message'):
                    st.error(f"Error: {batch_details['error_message']}")

            # Actions row 1
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
                    # Calculate remaining items for clearer messaging
                    pending_count = batch['total_tickers'] - batch['completed_tickers'] - batch['failed_tickers']
                    resume_label = "Resume" if batch['completed_tickers'] > 0 else "Start"
                    if st.button(resume_label, key=f"restart_{batch['batch_id']}", type="primary"):
                        queue.start_batch_job(batch['batch_id'])
                        if batch['completed_tickers'] > 0:
                            st.success(f"Resumed - continuing from company {batch['completed_tickers'] + 1} ({pending_count} remaining)")
                        else:
                            st.success("Started")
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

            # Export, Synthesis, and delete row
            col1, col2, col3 = st.columns(3)

            with col1:
                # Export results for completed batches
                if batch['completed_tickers'] > 0:
                    if st.button("Export", key=f"export_{batch['batch_id']}"):
                        st.session_state.export_batch_id = batch['batch_id']
                        st.rerun()

            with col2:
                # Synthesis analysis for completed batches with 2+ results
                if batch['completed_tickers'] >= 2:
                    num_years = batch.get('num_years', 1)
                    if num_years >= 2:
                        # Multi-year batch: per-company longitudinal synthesis
                        synth_help = "Create per-company multi-year synthesis (one per company)"
                        synth_label = "Synthesize"
                    else:
                        # Single-year batch: cross-company comparison
                        synth_help = "Create cross-company comparative synthesis"
                        synth_label = "Synthesize"

                    if st.button(synth_label, key=f"synth_{batch['batch_id']}", help=synth_help):
                        st.session_state.synthesis_batch_id = batch['batch_id']
                        st.rerun()

            with col3:
                # Delete option (only for completed/stopped/failed/pending)
                if batch['status'] in ['completed', 'stopped', 'failed', 'pending']:
                    if st.button("Delete", key=f"delete_{batch['batch_id']}", type="secondary"):
                        queue.delete_batch(batch['batch_id'])
                        st.success("Deleted")
                        time.sleep(1)
                        st.rerun()

# Export batch results
if 'export_batch_id' in st.session_state:
    st.markdown("---")
    st.subheader("Export Batch Results")

    batch_id = st.session_state.export_batch_id
    batch = queue.get_batch_status(batch_id)

    if batch:
        st.markdown(f"**Batch:** {batch['name']}")
        st.markdown(f"**Analysis Type:** {batch['analysis_type']}")
        st.markdown(f"**Completed:** {batch['completed_tickers']}/{batch['total_tickers']}")

        # Get all completed items with their run_ids
        completed_items = queue.get_batch_items(batch_id, status='completed', limit=5000)

        if completed_items:
            # Build summary dataframe
            summary_data = []

            for item in completed_items:
                run_id = item.get('run_id')
                row = {
                    'ticker': item['ticker'],
                    'company_name': item.get('company_name', ''),
                    'status': 'Completed',
                    'completed_at': item.get('completed_at', ''),
                    'run_id': run_id
                }

                # Try to get analysis results summary
                if run_id:
                    try:
                        run_details = db.get_run_details(run_id)
                        if run_details:
                            row['analysis_type'] = run_details.get('analysis_type', batch['analysis_type'])
                            row['filing_type'] = run_details.get('filing_type', batch['filing_type'])
                            row['years_analyzed'] = run_details.get('years_analyzed', '')

                            # Get brief result summary if available
                            year_analyses = db.get_analysis_results(run_id)
                            if year_analyses:
                                row['years_completed'] = len(year_analyses)
                    except:
                        pass

                summary_data.append(row)

            # Also add failed items
            failed_items = queue.get_batch_items(batch_id, status='failed', limit=5000)
            for item in failed_items:
                summary_data.append({
                    'ticker': item['ticker'],
                    'company_name': item.get('company_name', ''),
                    'status': 'Failed',
                    'error_message': item.get('error_message', ''),
                    'attempts': item.get('attempts', 0)
                })

            summary_df = pd.DataFrame(summary_data)

            # Display summary
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

            # Export options
            col1, col2 = st.columns(2)

            with col1:
                # CSV export
                csv_buffer = io.StringIO()
                summary_df.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()

                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"batch_{batch['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="download_csv"
                )

            with col2:
                # JSON export with more details
                import json
                json_data = json.dumps({
                    'batch_name': batch['name'],
                    'batch_id': batch_id,
                    'analysis_type': batch['analysis_type'],
                    'filing_type': batch['filing_type'],
                    'total_tickers': batch['total_tickers'],
                    'completed_tickers': batch['completed_tickers'],
                    'failed_tickers': batch['failed_tickers'],
                    'created_at': batch.get('created_at', ''),
                    'completed_at': batch.get('completed_at', ''),
                    'results': summary_data
                }, indent=2, default=str)

                st.download_button(
                    label="Download JSON",
                    data=json_data,
                    file_name=f"batch_{batch['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    key="download_json"
                )

        else:
            st.info("No completed items to export yet.")

    if st.button("Close Export"):
        del st.session_state.export_batch_id
        st.rerun()

# Synthesis analysis creation
if 'synthesis_batch_id' in st.session_state:
    st.markdown("---")
    st.subheader("Create Synthesis Analysis")

    batch_id = st.session_state.synthesis_batch_id
    batch = queue.get_batch_status(batch_id)

    if batch:
        num_years = batch.get('num_years', 1)
        is_multi_year = num_years >= 2

        st.markdown(f"""
        **Batch:** {batch['name']}
        **Completed Analyses:** {batch['completed_tickers']}
        **Years Per Company:** {num_years}
        """)

        if is_multi_year:
            # Multi-year batch: per-company longitudinal synthesis
            st.info(f"""
            **Per-Company Multi-Year Synthesis**

            This will create a separate synthesis document for EACH company, analyzing their
            longitudinal trends across all {num_years} years:

            - Trajectory and evolution over time
            - Key turning points and pivotal moments
            - Consistent strengths and weaknesses
            - Risk evolution and forward outlook
            - Year-over-year trend analysis

            **Output:** One synthesis document per company (e.g., 3 companies = 3 synthesis documents)
            """)
        else:
            # Single-year batch: cross-company comparison
            st.info("""
            **Cross-Company Comparative Synthesis**

            This will combine all completed analyses into a single comprehensive
            report comparing companies:

            - Executive summary across all companies
            - Common themes and patterns
            - Outliers and standout companies
            - Investment insights and recommendations
            - Company rankings
            """)

        # Custom synthesis prompt option
        use_custom_synthesis = st.checkbox("Use custom synthesis prompt", key="use_custom_synthesis")
        custom_synthesis_prompt = None

        if use_custom_synthesis:
            custom_synthesis_prompt = st.text_area(
                "Custom Synthesis Prompt",
                placeholder="Enter your custom instructions for the synthesis analysis...",
                height=200,
                key="custom_synthesis_prompt"
            )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Create Synthesis", type="primary", key="create_synthesis"):
                if is_multi_year:
                    # Per-company multi-year synthesis
                    with st.spinner(f"Creating per-company synthesis for {batch['completed_tickers']} companies... This may take a few minutes."):
                        run_ids = queue.create_per_company_synthesis(
                            batch_id,
                            synthesis_prompt=custom_synthesis_prompt if use_custom_synthesis else None
                        )
                        if run_ids:
                            st.success(f"Created {len(run_ids)} synthesis documents!")
                            del st.session_state.synthesis_batch_id
                            time.sleep(1)
                            # Go to results viewer
                            st.switch_page("pages/3_🔍_Results_Viewer.py")
                        else:
                            st.error("Failed to create synthesis. Each company needs 2+ years of data.")
                else:
                    # Single cross-company synthesis
                    with st.spinner("Creating cross-company synthesis... This may take a minute."):
                        run_id = queue.create_synthesis_analysis(
                            batch_id,
                            synthesis_prompt=custom_synthesis_prompt if use_custom_synthesis else None
                        )
                        if run_id:
                            st.success(f"Synthesis created successfully!")
                            st.session_state.synthesis_run_id = run_id
                            del st.session_state.synthesis_batch_id
                            time.sleep(1)
                            # Option to view results
                            st.session_state.view_run_id = run_id
                            st.switch_page("pages/3_🔍_Results_Viewer.py")
                        else:
                            st.error("Failed to create synthesis. Check logs for details.")

        with col2:
            if st.button("Cancel", key="cancel_synthesis"):
                del st.session_state.synthesis_batch_id
                st.rerun()

# Show batch details if selected
if 'view_batch_id' in st.session_state:
    st.markdown("---")
    st.subheader("Batch Details")

    batch_id = st.session_state.view_batch_id
    batch = queue.get_batch_status(batch_id)

    if batch:
        # Summary
        st.markdown(f"**{batch['name']}**")
        st.markdown(f"Analysis: {batch['analysis_type']} | Filing: {batch['filing_type']} | Years: {batch['num_years']}")

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
            items = queue.get_batch_items(batch_id, limit=100)
            if items:
                df = pd.DataFrame(items)
                cols_to_show = ['ticker', 'status', 'attempts']
                if 'error_message' in df.columns:
                    cols_to_show.append('error_message')
                st.dataframe(
                    df[cols_to_show],
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No items")

        with tab_completed:
            items = queue.get_batch_items(batch_id, status='completed', limit=100)
            if items:
                df = pd.DataFrame(items)
                st.dataframe(
                    df[['ticker', 'run_id', 'completed_at']],
                    hide_index=True,
                    use_container_width=True
                )

                # Link to view results
                st.markdown("**View Results:**")
                for item in items[:10]:
                    if item.get('run_id'):
                        if st.button(f"View {item['ticker']}", key=f"view_result_{item['run_id']}"):
                            st.session_state.view_run_id = item['run_id']
                            st.switch_page("pages/3_🔍_Results_Viewer.py")
            else:
                st.info("No completed items")

        with tab_failed:
            items = queue.get_batch_items(batch_id, status='failed', limit=100)
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
            items = queue.get_batch_items(batch_id, status='pending', limit=100)
            if items:
                df = pd.DataFrame(items)
                cols = ['ticker']
                if 'company_name' in df.columns:
                    cols.append('company_name')
                st.dataframe(
                    df[cols],
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
