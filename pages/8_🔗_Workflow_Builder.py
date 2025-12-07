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
from fintel.ui.theme import apply_theme

# Apply global theme
apply_theme()

# Initialize session state
if 'workflow_steps' not in st.session_state:
    st.session_state.workflow_steps = []

if 'workflow_name' not in st.session_state:
    st.session_state.workflow_name = ""

if 'workflow_description' not in st.session_state:
    st.session_state.workflow_description = ""

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

    # Create visual flowchart
    workflow_viz = " → ".join([
        f"**{i+1}. {step['name']}**"
        for i, step in enumerate(st.session_state.workflow_steps)
    ])

    st.info(workflow_viz)

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
        step_config = {
            "type": "aggregate",
            "operation": agg_operation.split(" ")[0].lower().replace("by", "by_")
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
            new_step = {
                "step_id": f"step_{len(st.session_state.workflow_steps) + 1}",
                "name": step_name or f"Step {len(st.session_state.workflow_steps) + 1}",
                "type": step_type,
                "config": step_config
            }
            st.session_state.workflow_steps.append(new_step)
            st.success(f"✅ Added: {new_step['name']}")
            st.rerun()
        else:
            st.error("Please configure the step first")

st.markdown("---")

# Display current steps
if st.session_state.workflow_steps:
    st.subheader("📋 Current Steps")

    for i, step in enumerate(st.session_state.workflow_steps):
        with st.expander(f"{i+1}. {step['name']} ({step['type']})", expanded=False):
            st.json(step['config'])

            col1, col2, col3 = st.columns(3)

            with col1:
                if i > 0 and st.button(f"⬆️ Move Up", key=f"up_{i}"):
                    st.session_state.workflow_steps[i], st.session_state.workflow_steps[i-1] = \
                        st.session_state.workflow_steps[i-1], st.session_state.workflow_steps[i]
                    st.rerun()

            with col2:
                if i < len(st.session_state.workflow_steps) - 1 and st.button(f"⬇️ Move Down", key=f"down_{i}"):
                    st.session_state.workflow_steps[i], st.session_state.workflow_steps[i+1] = \
                        st.session_state.workflow_steps[i+1], st.session_state.workflow_steps[i]
                    st.rerun()

            with col3:
                if st.button(f"🗑️ Remove", key=f"remove_{i}", type="secondary"):
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
                    "name": workflow_name,
                    "description": workflow_description,
                    "steps": st.session_state.workflow_steps,
                    "created_at": datetime.now().isoformat()
                }

                # Save to file
                workflows_dir = Path("workflows")
                workflows_dir.mkdir(exist_ok=True)

                filename = f"{workflow_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = workflows_dir / filename

                with open(filepath, 'w') as f:
                    json.dump(workflow_data, f, indent=2)

                st.success(f"✅ Saved workflow to: {filepath}")

                # Also offer download
                st.download_button(
                    label="📥 Download Workflow JSON",
                    data=json.dumps(workflow_data, indent=2),
                    file_name=f"{workflow_name.replace(' ', '_')}.json",
                    mime="application/json"
                )
            else:
                st.error("Please enter a workflow name")

    with col2:
        if st.button("▶️ Run Workflow", use_container_width=True, type="primary"):
            st.info("🚧 **Workflow Execution Coming Soon!**\n\nFor now, workflows are saved as templates. Execution engine will be added in the next update.")

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
