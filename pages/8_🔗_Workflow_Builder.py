#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Workflow Builder - Create custom multi-step analysis pipelines.

Build complex analysis workflows by chaining steps together:
1. Define inputs (companies, years, prompts)
2. Chain analysis steps
3. Apply custom transformations
4. Export results

Example workflows:
- Compare 3 companies → Success factors → Custom ranking → Export
- Deep dive one company → All 3 lenses → Synthesis → Report
- Batch scan 50 companies → Filter by score → Detailed analysis of top 10
"""

import streamlit as st
import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
import time
from fintel.ui.theme import apply_theme
from fintel.ui.database import DatabaseRepository
from fintel.ui.services.analysis_service import AnalysisService
from fintel.ui.services.workflow_service import WorkflowService

# Apply global theme
apply_theme()

# Initialize services
@st.cache_resource
def get_services():
    db = DatabaseRepository()
    analysis_service = AnalysisService(db)
    workflow_service = WorkflowService(db, analysis_service)
    return db, analysis_service, workflow_service

db, analysis_service, workflow_service = get_services()

# Initialize session state
if 'workflow_steps' not in st.session_state:
    st.session_state.workflow_steps = []

if 'workflow_name' not in st.session_state:
    st.session_state.workflow_name = ""

if 'workflow_description' not in st.session_state:
    st.session_state.workflow_description = ""

if 'monitoring_run_id' not in st.session_state:
    st.session_state.monitoring_run_id = None

if 'current_workflow_id' not in st.session_state:
    st.session_state.current_workflow_id = None

st.set_page_config(page_title="Workflow Builder", layout="wide")

st.title("🔗 Workflow Builder")
st.markdown("Create custom multi-step analysis pipelines")

st.markdown("---")

# Workflow metadata
col1, col2 = st.columns([2, 1])

with col1:
    workflow_name = st.text_input(
        "Workflow Name",
        value=st.session_state.workflow_name,
        placeholder="e.g., Tech Giants Comparison",
        help="Give your workflow a descriptive name"
    )
    st.session_state.workflow_name = workflow_name

with col2:
    st.metric("Steps", len(st.session_state.workflow_steps))

workflow_description = st.text_area(
    "Description",
    value=st.session_state.workflow_description,
    placeholder="What does this workflow do?",
    height=80,
    help="Describe the purpose of this workflow"
)
st.session_state.workflow_description = workflow_description

st.markdown("---")

# Workflow visualization
if st.session_state.workflow_steps:
    st.subheader("📊 Workflow Pipeline")

    # Calculate shapes for each step
    def calculate_shape(step, prev_shape):
        """Calculate output shape based on step type and config."""
        step_type = step.get('type', '')
        config = step.get('config', {})

        if step_type == 'input':
            num_tickers = len(config.get('tickers', []))
            if 'years' in config:
                num_years = len(config.get('years', []))
            else:
                num_years = config.get('num_years', 1)
            return (num_tickers, num_years)

        elif step_type == 'fundamental_analysis' or step_type == 'perspective_analysis':
            return prev_shape  # Same shape

        elif step_type == 'success_factors':
            agg_by = config.get('aggregate_by', 'company')
            if agg_by == 'company':
                return (prev_shape[0], 1) if prev_shape else (0, 1)
            elif agg_by == 'year':
                return (1, prev_shape[1]) if prev_shape else (1, 0)
            else:
                return prev_shape

        elif step_type == 'aggregate':
            operation = config.get('operation', 'merge_all')
            if operation == 'merge_all':
                return (1, 1)
            elif 'company' in operation:
                return (prev_shape[0], 1) if prev_shape else (0, 1)
            elif 'year' in operation:
                return (1, prev_shape[1]) if prev_shape else (1, 0)
            elif operation == 'top_n':
                n = config.get('n', 10)
                return (min(n, prev_shape[0]), prev_shape[1]) if prev_shape else (n, 0)
            else:
                return prev_shape

        elif step_type == 'filter':
            return prev_shape  # Unknown reduction

        elif step_type == 'custom_analysis':
            return (1, 1)  # Usually aggregates to single result

        elif step_type == 'export':
            return prev_shape  # Pass-through

        return prev_shape

    # Step type colors and icons
    step_styles = {
        'input': {'color': '#4CAF50', 'icon': '📥', 'label': 'Input'},
        'fundamental_analysis': {'color': '#2196F3', 'icon': '📊', 'label': 'Analysis'},
        'success_factors': {'color': '#9C27B0', 'icon': '⭐', 'label': 'Success Factors'},
        'perspective_analysis': {'color': '#FF9800', 'icon': '🔍', 'label': 'Perspective'},
        'custom_analysis': {'color': '#E91E63', 'icon': '✨', 'label': 'Custom'},
        'filter': {'color': '#F44336', 'icon': '🔎', 'label': 'Filter'},
        'aggregate': {'color': '#00BCD4', 'icon': '📦', 'label': 'Aggregate'},
        'export': {'color': '#795548', 'icon': '💾', 'label': 'Export'}
    }

    # Build visual pipeline with shapes
    current_shape = None
    pipeline_html = '<div style="display: flex; flex-direction: column; gap: 15px; margin: 20px 0;">'

    for i, step in enumerate(st.session_state.workflow_steps):
        step_type = step.get('type', 'unknown')
        style = step_styles.get(step_type, {'color': '#757575', 'icon': '❓', 'label': 'Unknown'})

        # Calculate shape
        new_shape = calculate_shape(step, current_shape)

        # Create step card with shape visualization
        shape_str = f"({new_shape[0]} × {new_shape[1]})" if new_shape else "(? × ?)"

        pipeline_html += f'''
        <div style="
            background: linear-gradient(135deg, {style['color']}22 0%, {style['color']}11 100%);
            border-left: 4px solid {style['color']};
            border-radius: 8px;
            padding: 15px;
            position: relative;
        ">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 24px;">{style['icon']}</span>
                    <div>
                        <div style="font-weight: 600; font-size: 14px; color: #333;">
                            Step {i+1}: {step['name']}
                        </div>
                        <div style="font-size: 12px; color: #666; margin-top: 2px;">
                            {style['label']}
                        </div>
                    </div>
                </div>
                <div style="
                    background: {style['color']};
                    color: white;
                    padding: 6px 16px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 13px;
                    font-family: monospace;
                ">
                    {shape_str}
                </div>
            </div>
        '''

        # Show shape transformation if changed
        if current_shape and current_shape != new_shape:
            old_shape_str = f"({current_shape[0]} × {current_shape[1]})"
            pipeline_html += f'''
            <div style="
                margin-top: 8px;
                padding: 8px 12px;
                background: rgba(0,0,0,0.03);
                border-radius: 4px;
                font-size: 11px;
                color: #666;
                font-family: monospace;
            ">
                ⚡ Shape change: {old_shape_str} → {shape_str}
            </div>
            '''

        pipeline_html += '</div>'

        # Add arrow between steps
        if i < len(st.session_state.workflow_steps) - 1:
            pipeline_html += '''
            <div style="text-align: center; color: #999; font-size: 20px; margin: -5px 0;">
                ↓
            </div>
            '''

        current_shape = new_shape

    pipeline_html += '</div>'

    # Display the pipeline
    st.markdown(pipeline_html, unsafe_allow_html=True)

    # Show final output summary
    if current_shape:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Final Companies", current_shape[0])
        with col2:
            st.metric("Final Years/Items", current_shape[1])
        with col3:
            st.metric("Total Items", current_shape[0] * current_shape[1])

    st.markdown("---")

# Step builder
st.subheader("➕ Add Step")

# Step type selector
step_type = st.selectbox(
    "Step Type",
    options=[
        "Input (Companies & Years)",
        "Fundamental Analysis",
        "Success Factors Extraction",
        "Perspective Analysis (Buffett/Taleb/Contrarian)",
        "Custom Prompt Analysis",
        "Filter Results",
        "Aggregate/Combine",
        "Export"
    ],
    help="Select the type of step to add to your workflow"
)

# Step configuration based on type
step_config = {}

if step_type == "Input (Companies & Years)":
    st.markdown("### Configure Input")

    col1, col2 = st.columns(2)

    with col1:
        input_mode = st.radio(
            "Input Mode",
            options=["Manual Entry", "CSV Upload", "Load from Previous Analysis"],
            help="How do you want to provide company inputs?"
        )

    with col2:
        filing_type = st.selectbox(
            "Filing Type",
            options=["10-K", "10-Q", "8-K", "4", "DEF 14A"],
            help="Type of SEC filing"
        )

    if input_mode == "Manual Entry":
        tickers = st.text_input(
            "Tickers (comma-separated)",
            placeholder="e.g., AAPL, MSFT, GOOGL",
            help="Enter stock ticker symbols"
        )

        year_mode = st.radio(
            "Year Selection",
            options=["Last N Years", "Specific Years", "Year Range"],
            horizontal=True
        )

        if year_mode == "Last N Years":
            num_years = st.slider("Number of years", 1, 15, 5)
            step_config = {
                "type": "input",
                "tickers": [t.strip().upper() for t in tickers.split(',') if t.strip()],
                "num_years": num_years,
                "filing_type": filing_type
            }
        elif year_mode == "Specific Years":
            years_input = st.text_input("Years (comma-separated)", "2024, 2023, 2022")
            years = [int(y.strip()) for y in years_input.split(',') if y.strip()]
            step_config = {
                "type": "input",
                "tickers": [t.strip().upper() for t in tickers.split(',') if t.strip()],
                "years": years,
                "filing_type": filing_type
            }
        else:  # Year Range
            col1, col2 = st.columns(2)
            with col1:
                start_year = st.number_input("From", 2015, 2024, 2020)
            with col2:
                end_year = st.number_input("To", 2015, 2024, 2024)
            years = list(range(end_year, start_year - 1, -1))
            step_config = {
                "type": "input",
                "tickers": [t.strip().upper() for t in tickers.split(',') if t.strip()],
                "years": years,
                "filing_type": filing_type
            }

elif step_type == "Fundamental Analysis":
    st.markdown("### Configure Fundamental Analysis")

    run_mode = st.radio(
        "Run Mode",
        options=["Per Filing (separate analysis for each year)", "Aggregated (combine all years)"],
        help="How to process multiple years"
    )

    custom_prompt = st.text_area(
        "Custom Prompt (Optional)",
        placeholder="Leave blank to use default fundamental analysis prompt",
        height=150
    )

    step_config = {
        "type": "fundamental_analysis",
        "run_mode": "per_filing" if "Per Filing" in run_mode else "aggregated",
        "custom_prompt": custom_prompt if custom_prompt else None
    }

elif step_type == "Success Factors Extraction":
    st.markdown("### Configure Success Factors")

    analyzer_type = st.radio(
        "Analyzer Type",
        options=[
            "Objective (balanced assessment)",
            "Excellent (success-focused for known winners)"
        ],
        help="Objective for unknown companies, Excellent for proven winners"
    )

    aggregate_by = st.radio(
        "Aggregate By",
        options=["Company", "Year", "None"],
        help="How to group results before extraction"
    )

    step_config = {
        "type": "success_factors",
        "analyzer_type": "objective" if "Objective" in analyzer_type else "excellent",
        "aggregate_by": aggregate_by.lower()
    }

elif step_type == "Perspective Analysis (Buffett/Taleb/Contrarian)":
    st.markdown("### Configure Perspective")

    perspectives = st.multiselect(
        "Select Perspectives",
        options=["Buffett (Value Investing)", "Taleb (Antifragility)", "Contrarian (Variant Perception)"],
        default=["Buffett (Value Investing)"],
        help="Choose one or more investment perspectives"
    )

    run_parallel = st.checkbox(
        "Run in Parallel",
        value=True,
        help="Run all perspectives simultaneously (faster)"
    )

    step_config = {
        "type": "perspective_analysis",
        "perspectives": [p.split(" ")[0].lower() for p in perspectives],
        "run_parallel": run_parallel
    }

elif step_type == "Custom Prompt Analysis":
    st.markdown("### Configure Custom Analysis")

    st.info("💡 **Tip:** This step takes output from previous steps and applies a custom prompt")

    custom_prompt = st.text_area(
        "Custom Prompt",
        placeholder="""Example:
Analyze the provided company data and:
1. Identify the top 3 competitive advantages
2. Rank the companies by investment potential
3. Provide a buy/hold/pass recommendation for each

Use the {company_data} placeholder to reference previous step outputs.""",
        height=200,
        help="Write a prompt to analyze previous step results"
    )

    output_format = st.selectbox(
        "Expected Output",
        options=["Structured JSON", "Free Text", "Comparison Table"],
        help="What format should the AI return?"
    )

    step_config = {
        "type": "custom_analysis",
        "prompt": custom_prompt,
        "output_format": output_format.lower().replace(" ", "_")
    }

elif step_type == "Filter Results":
    st.markdown("### Configure Filter")

    filter_field = st.text_input(
        "Filter Field",
        placeholder="e.g., moat_rating, success_score, revenue_growth",
        help="Field to filter on"
    )

    filter_operator = st.selectbox(
        "Operator",
        options=[">", ">=", "<", "<=", "==", "!=", "contains"],
        help="Comparison operator"
    )

    filter_value = st.text_input(
        "Value",
        placeholder="e.g., 80, 'wide', 15%",
        help="Value to compare against"
    )

    step_config = {
        "type": "filter",
        "field": filter_field,
        "operator": filter_operator,
        "value": filter_value
    }

elif step_type == "Aggregate/Combine":
    st.markdown("### Configure Aggregation")

    agg_operation = st.selectbox(
        "Operation",
        options=[
            "Merge All (combine into single dataset)",
            "Group By Company",
            "Group By Year",
            "Take Top N by Score",
            "Average Metrics"
        ],
        help="How to aggregate results"
    )

    if "Top N" in agg_operation:
        top_n = st.number_input("N (number of top results)", 1, 100, 10)
        score_field = st.text_input("Score Field", "total_score")
        step_config = {
            "type": "aggregate",
            "operation": "top_n",
            "n": top_n,
            "score_field": score_field
        }
    else:
        # Map display names to operation values
        operation_map = {
            "Merge All (combine into single dataset)": "merge_all",
            "Group By Company": "group_by_company",
            "Group By Year": "group_by_year",
            "Average Metrics": "average_metrics"
        }
        step_config = {
            "type": "aggregate",
            "operation": operation_map.get(agg_operation, "merge_all")
        }

elif step_type == "Export":
    st.markdown("### Configure Export")

    export_formats = st.multiselect(
        "Export Formats",
        options=["JSON", "CSV", "Excel", "PDF Report"],
        default=["JSON"],
        help="Select one or more export formats"
    )

    include_metadata = st.checkbox("Include Metadata", value=True)
    include_raw_data = st.checkbox("Include Raw Data", value=True)

    step_config = {
        "type": "export",
        "formats": [f.lower() for f in export_formats],
        "include_metadata": include_metadata,
        "include_raw_data": include_raw_data
    }

# Add step button
st.markdown("---")

col1, col2 = st.columns([3, 1])

with col1:
    step_name = st.text_input(
        "Step Name",
        placeholder=f"Step {len(st.session_state.workflow_steps) + 1}",
        help="Give this step a descriptive name"
    )

with col2:
    if st.button("➕ Add Step", type="primary", use_container_width=True):
        if step_config:
            # Map display names to internal step types
            step_type_map = {
                "Input (Companies & Years)": "input",
                "Fundamental Analysis": "fundamental_analysis",
                "Success Factors Extraction": "success_factors",
                "Perspective Analysis (Buffett/Taleb/Contrarian)": "perspective_analysis",
                "Custom Prompt Analysis": "custom_analysis",
                "Filter Results": "filter",
                "Aggregate/Combine": "aggregate",
                "Export": "export"
            }

            internal_type = step_type_map.get(step_type, step_config.get('type', 'unknown'))

            new_step = {
                "step_id": f"step_{len(st.session_state.workflow_steps) + 1}",
                "name": step_name or f"Step {len(st.session_state.workflow_steps) + 1}",
                "type": internal_type,
                "config": step_config
            }
            st.session_state.workflow_steps.append(new_step)
            st.success(f"✅ Added: {new_step['name']}")
            st.rerun()
        else:
            st.error("Please configure the step first")

st.markdown("---")

# Display current steps with controls
if st.session_state.workflow_steps:
    st.subheader("📋 Step Configuration Details")

    # Step type colors and icons (reuse from above)
    step_styles = {
        'input': {'color': '#4CAF50', 'icon': '📥', 'label': 'Input'},
        'fundamental_analysis': {'color': '#2196F3', 'icon': '📊', 'label': 'Analysis'},
        'success_factors': {'color': '#9C27B0', 'icon': '⭐', 'label': 'Success Factors'},
        'perspective_analysis': {'color': '#FF9800', 'icon': '🔍', 'label': 'Perspective'},
        'custom_analysis': {'color': '#E91E63', 'icon': '✨', 'label': 'Custom'},
        'filter': {'color': '#F44336', 'icon': '🔎', 'label': 'Filter'},
        'aggregate': {'color': '#00BCD4', 'icon': '📦', 'label': 'Aggregate'},
        'export': {'color': '#795548', 'icon': '💾', 'label': 'Export'}
    }

    for i, step in enumerate(st.session_state.workflow_steps):
        step_type = step.get('type', 'unknown')
        style = step_styles.get(step_type, {'color': '#757575', 'icon': '❓', 'label': 'Unknown'})

        # Create colored header for expander
        header = f"{style['icon']} Step {i+1}: {step['name']} - {style['label']}"

        with st.expander(header, expanded=False):
            # Show configuration in a nice format
            st.markdown("**Configuration:**")
            config = step.get('config', {})

            # Format config nicely
            if step_type == 'input':
                st.write(f"• **Tickers:** {', '.join(config.get('tickers', []))}")
                if 'years' in config:
                    st.write(f"• **Years:** {', '.join(map(str, config.get('years', [])))}")
                else:
                    st.write(f"• **Number of Years:** {config.get('num_years', 1)}")
                st.write(f"• **Filing Type:** {config.get('filing_type', '10-K')}")

            elif step_type == 'fundamental_analysis':
                st.write(f"• **Run Mode:** {config.get('run_mode', 'per_filing')}")
                if config.get('custom_prompt'):
                    st.write(f"• **Custom Prompt:** Yes ({len(config.get('custom_prompt', ''))} characters)")

            elif step_type == 'success_factors':
                st.write(f"• **Analyzer Type:** {config.get('analyzer_type', 'objective')}")
                st.write(f"• **Aggregate By:** {config.get('aggregate_by', 'company')}")

            elif step_type == 'perspective_analysis':
                st.write(f"• **Perspectives:** {', '.join(config.get('perspectives', []))}")
                st.write(f"• **Run Parallel:** {config.get('run_parallel', True)}")

            elif step_type == 'custom_analysis':
                st.write(f"• **Output Format:** {config.get('output_format', 'free_text')}")
                if config.get('prompt'):
                    st.write(f"• **Prompt Length:** {len(config.get('prompt', ''))} characters")

            elif step_type == 'filter':
                st.write(f"• **Field:** {config.get('field', '')}")
                st.write(f"• **Operator:** {config.get('operator', '==')}")
                st.write(f"• **Value:** {config.get('value', '')}")

            elif step_type == 'aggregate':
                st.write(f"• **Operation:** {config.get('operation', 'merge_all')}")
                if config.get('n'):
                    st.write(f"• **Top N:** {config.get('n')}")
                if config.get('score_field'):
                    st.write(f"• **Score Field:** {config.get('score_field')}")

            elif step_type == 'export':
                st.write(f"• **Formats:** {', '.join(config.get('formats', []))}")
                st.write(f"• **Include Metadata:** {config.get('include_metadata', True)}")
                st.write(f"• **Include Raw Data:** {config.get('include_raw_data', True)}")

            # Show raw JSON in collapsed section
            with st.expander("🔧 View Raw JSON", expanded=False):
                st.json(step['config'])

            # Action buttons
            st.markdown("---")
            col1, col2, col3 = st.columns(3)

            with col1:
                if i > 0:
                    if st.button(f"⬆️ Move Up", key=f"up_{i}", use_container_width=True):
                        st.session_state.workflow_steps[i], st.session_state.workflow_steps[i-1] = \
                            st.session_state.workflow_steps[i-1], st.session_state.workflow_steps[i]
                        st.rerun()

            with col2:
                if i < len(st.session_state.workflow_steps) - 1:
                    if st.button(f"⬇️ Move Down", key=f"down_{i}", use_container_width=True):
                        st.session_state.workflow_steps[i], st.session_state.workflow_steps[i+1] = \
                            st.session_state.workflow_steps[i+1], st.session_state.workflow_steps[i]
                        st.rerun()

            with col3:
                if st.button(f"🗑️ Remove", key=f"remove_{i}", type="secondary", use_container_width=True):
                    st.session_state.workflow_steps.pop(i)
                    st.rerun()

    st.markdown("---")

    # Workflow actions
    st.subheader("🚀 Workflow Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💾 Save Workflow", use_container_width=True, type="primary"):
            if workflow_name:
                workflow_data = {
                    "steps": st.session_state.workflow_steps
                }

                # Save to database
                try:
                    workflow_id = workflow_service.save_workflow(
                        name=workflow_name,
                        description=workflow_description,
                        workflow_definition=workflow_data
                    )
                    st.session_state.current_workflow_id = workflow_id
                    st.success(f"✅ Saved workflow to database (ID: {workflow_id})")

                    # Also save to file
                    workflows_dir = Path("workflows")
                    workflows_dir.mkdir(exist_ok=True)

                    filename = f"{workflow_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    filepath = workflows_dir / filename

                    full_workflow = {
                        "name": workflow_name,
                        "description": workflow_description,
                        "steps": st.session_state.workflow_steps,
                        "created_at": datetime.now().isoformat()
                    }

                    with open(filepath, 'w') as f:
                        json.dump(full_workflow, f, indent=2)

                    # Offer download
                    st.download_button(
                        label="📥 Download Workflow JSON",
                        data=json.dumps(full_workflow, indent=2),
                        file_name=f"{workflow_name.replace(' ', '_')}.json",
                        mime="application/json"
                    )

                except Exception as e:
                    st.error(f"Failed to save workflow: {e}")
            else:
                st.error("Please enter a workflow name")

    with col2:
        # Run Workflow button
        run_disabled = not (workflow_name and st.session_state.workflow_steps)
        if st.button("▶️ Run Workflow", use_container_width=True, type="primary", disabled=run_disabled):
            # Save workflow first if not saved
            if not st.session_state.current_workflow_id:
                workflow_data = {
                    "steps": st.session_state.workflow_steps
                }
                try:
                    workflow_id = workflow_service.save_workflow(
                        name=workflow_name,
                        description=workflow_description,
                        workflow_definition=workflow_data
                    )
                    st.session_state.current_workflow_id = workflow_id
                except Exception as e:
                    st.error(f"Failed to save workflow: {e}")
                    st.stop()

            # Start execution
            try:
                with st.spinner("Starting workflow execution..."):
                    run_id = workflow_service.execute_workflow(
                        workflow_id=st.session_state.current_workflow_id
                    )
                    st.session_state.monitoring_run_id = run_id
                    st.success(f"✅ Workflow started! Run ID: {run_id}")
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to start workflow: {e}")

    with col3:
        if st.button("🗑️ Clear All Steps", use_container_width=True, type="secondary"):
            if st.session_state.get('confirm_clear_workflow', False):
                st.session_state.workflow_steps = []
                st.session_state.workflow_name = ""
                st.session_state.workflow_description = ""
                st.session_state.confirm_clear_workflow = False
                st.success("✅ Workflow cleared")
                st.rerun()
            else:
                st.session_state.confirm_clear_workflow = True
                st.warning("⚠️ Click again to confirm")

st.markdown("---")

# Workflow Execution Monitoring
if st.session_state.monitoring_run_id:
    st.subheader("🔄 Workflow Execution Monitor")

    run_id = st.session_state.monitoring_run_id

    # Get current status
    try:
        status = workflow_service.get_run_status(run_id)

        if status:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Status", status['status'].upper())

            with col2:
                st.metric("Progress", f"{status['progress_percent']}%")

            with col3:
                st.metric("Step", f"{status['current_step']}/{status['total_steps']}")

            with col4:
                if status['status'] in ['running', 'pending']:
                    if st.button("🔄 Refresh", key="refresh_status"):
                        st.rerun()

            # Progress bar
            st.progress(status['progress_percent'] / 100)

            # Show current step
            if status['last_successful_step']:
                st.write(f"**Last completed step:** {status['last_successful_step']}")

            # Show logs
            with st.expander("📋 Execution Logs", expanded=False):
                logs = workflow_service.get_step_logs(run_id)
                if logs:
                    for log in logs[-20:]:  # Show last 20 logs
                        level_icon = {
                            'INFO': '  ℹ️',
                            'WARNING': '⚠️',
                            'ERROR': '❌'
                        }.get(log['log_level'], '📝')

                        st.text(f"{level_icon} [{log['step_id']}] {log['message']}")
                else:
                    st.info("No logs yet")

            # Show errors if any
            if status.get('errors'):
                st.error(f"**Errors:** {len(status['errors'])}")
                for error in status['errors']:
                    with st.expander(f"❌ Error in {error.get('step_id', 'unknown')}", expanded=False):
                        st.code(error.get('message', 'Unknown error'))

            # Show results if completed
            if status['status'] == 'completed':
                st.success("✅ Workflow completed successfully!")

                try:
                    results = workflow_service.get_run_results(run_id)
                    if results:
                        st.write(f"**Final Results:** Shape={results.shape}, Items={results.total_items}")

                        # Show exported files if available
                        if 'exported_files' in results.metadata:
                            st.write("**Exported Files:**")
                            for file in results.metadata['exported_files']:
                                st.write(f"- {file}")

                        # Show results data
                        with st.expander("📊 View Results", expanded=False):
                            st.json(results.to_dict())

                except Exception as e:
                    st.error(f"Failed to load results: {e}")

                # Clear monitoring
                if st.button("Clear Monitoring"):
                    st.session_state.monitoring_run_id = None
                    st.rerun()

            elif status['status'] == 'failed':
                st.error("❌ Workflow execution failed")

                # Clear monitoring
                if st.button("Clear Monitoring"):
                    st.session_state.monitoring_run_id = None
                    st.rerun()

            # Auto-refresh for running workflows
            if status['status'] in ['running', 'pending']:
                time.sleep(3)
                st.rerun()

        else:
            st.warning(f"Run {run_id} not found")
            st.session_state.monitoring_run_id = None

    except Exception as e:
        st.error(f"Failed to get workflow status: {e}")
        if st.button("Clear Monitoring"):
            st.session_state.monitoring_run_id = None
            st.rerun()

    st.markdown("---")

# Load saved workflows
st.subheader("📁 Saved Workflows")

workflows_dir = Path("workflows")
if workflows_dir.exists():
    workflow_files = list(workflows_dir.glob("*.json"))

    if workflow_files:
        st.markdown(f"**Found {len(workflow_files)} saved workflows**")

        for wf_file in sorted(workflow_files, reverse=True)[:10]:  # Show last 10
            with st.expander(f"📄 {wf_file.stem}"):
                try:
                    with open(wf_file, 'r') as f:
                        wf_data = json.load(f)

                    st.markdown(f"**Name:** {wf_data.get('name', 'Unnamed')}")
                    st.markdown(f"**Description:** {wf_data.get('description', 'No description')}")
                    st.markdown(f"**Steps:** {len(wf_data.get('steps', []))}")
                    st.markdown(f"**Created:** {wf_data.get('created_at', 'Unknown')}")

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(f"📂 Load", key=f"load_{wf_file.stem}"):
                            st.session_state.workflow_name = wf_data.get('name', '')
                            st.session_state.workflow_description = wf_data.get('description', '')
                            st.session_state.workflow_steps = wf_data.get('steps', [])
                            st.success(f"✅ Loaded: {wf_data.get('name')}")
                            st.rerun()

                    with col2:
                        if st.button(f"🗑️ Delete", key=f"delete_{wf_file.stem}", type="secondary"):
                            wf_file.unlink()
                            st.success("✅ Deleted workflow")
                            st.rerun()

                except Exception as e:
                    st.error(f"Error loading workflow: {e}")
    else:
        st.info("No saved workflows yet. Create one above!")
else:
    st.info("No workflows directory found. Save a workflow to create it.")

# Navigation
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("streamlit_app.py")

with col2:
    if st.button("📤 Export", use_container_width=True):
        st.switch_page("pages/7_📤_Export.py")
