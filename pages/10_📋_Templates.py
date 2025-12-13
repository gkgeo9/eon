#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Templates & Presets Page - Quick-start templates for common analysis scenarios.
Helps users get started quickly with pre-configured analysis workflows and prompts.
"""

import streamlit as st
import json
from pathlib import Path
from fintel.ui.theme import apply_theme
from fintel.ui.session import init_session_state, init_page_state
from fintel.ui.components.navigation import render_page_navigation

# Apply global theme
apply_theme()

# Initialize session state
db = init_session_state()
init_page_state("templates", {
    "selected_template": None,
    "show_template_details": False
})

st.title("📋 Templates & Presets")
st.markdown("Quick-start templates for common analysis scenarios")

st.markdown("---")

# Create tabs for different template types
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Analysis Presets",
    "🔗 Workflow Templates",
    "💬 Custom Prompts",
    "📝 Saved Configurations"
])

with tab1:
    st.subheader("Analysis Presets")
    st.info("💡 Pre-configured analysis setups for common investment strategies")

    # Define analysis presets
    presets = {
        "Deep Value Analysis": {
            "description": "Warren Buffett style deep value analysis focusing on moats, management quality, and intrinsic value",
            "analysis_types": ["fundamental", "buffett"],
            "years": 10,
            "icon": "💰"
        },
        "Growth Stock Scan": {
            "description": "Identify high-growth companies with strong revenue expansion and market positioning",
            "analysis_types": ["fundamental", "objective"],
            "years": 5,
            "icon": "📈"
        },
        "Contrarian Opportunities": {
            "description": "Find undervalued companies with hidden strengths and asymmetric upside potential",
            "analysis_types": ["contrarian", "scanner"],
            "years": 10,
            "icon": "🔍"
        },
        "Antifragility Assessment": {
            "description": "Nassim Taleb inspired analysis focusing on resilience, optionality, and tail risk protection",
            "analysis_types": ["taleb", "fundamental"],
            "years": 10,
            "icon": "🛡️"
        },
        "Compounder DNA Check": {
            "description": "Compare companies against top 50 proven winners to identify compounder potential",
            "analysis_types": ["excellent", "scanner"],
            "years": 10,
            "icon": "⭐"
        },
        "Quick Overview": {
            "description": "Fast 3-year snapshot for initial screening",
            "analysis_types": ["fundamental"],
            "years": 3,
            "icon": "⚡"
        }
    }

    # Display presets in grid
    cols = st.columns(2)

    for i, (name, config) in enumerate(presets.items()):
        with cols[i % 2]:
            with st.container():
                st.markdown(
                    f'<div style="padding: 1rem; border: 1px solid #e0e0e0; border-radius: 0.5rem; margin-bottom: 1rem;">'
                    f'<h4>{config["icon"]} {name}</h4>'
                    f'<p style="color: #666;">{config["description"]}</p>'
                    f'<p><strong>Analysis Types:</strong> {", ".join(config["analysis_types"])}</p>'
                    f'<p><strong>Years:</strong> {config["years"]}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                if st.button(f"Use {name}", key=f"preset_{name}"):
                    st.session_state.selected_template = config
                    st.success(f"✅ {name} preset selected! Navigate to Single Analysis to use it.")

with tab2:
    st.subheader("Workflow Templates")
    st.info("💡 Pre-built multi-step workflows for complex analysis tasks")

    # Define workflow templates
    workflows = {
        "Top 50 Compounder Analysis": {
            "description": "Comprehensive analysis comparing companies against top 50 proven winners",
            "steps": [
                "Load ticker list from CSV",
                "Run fundamental analysis (10 years)",
                "Run excellent company analysis",
                "Calculate compounder DNA score",
                "Filter top scorers (90+)",
                "Export results to Excel"
            ],
            "estimated_time": "2-4 hours (for 50 companies)",
            "icon": "🏆"
        },
        "Sector Comparison": {
            "description": "Compare multiple companies within the same sector",
            "steps": [
                "Load sector tickers",
                "Run multi-perspective analysis",
                "Aggregate key metrics",
                "Create comparison table",
                "Export to CSV"
            ],
            "estimated_time": "30-60 minutes",
            "icon": "📊"
        },
        "Hidden Gems Scanner": {
            "description": "Scan for undervalued companies with contrarian potential",
            "steps": [
                "Load universe of tickers",
                "Run objective company analysis",
                "Run contrarian scanner",
                "Filter by contrarian score (400+)",
                "Rank by total score",
                "Export top 20"
            ],
            "estimated_time": "3-5 hours (for 100+ companies)",
            "icon": "💎"
        },
        "Quarterly Update": {
            "description": "Quick quarterly re-analysis of your existing portfolio",
            "steps": [
                "Load saved ticker list",
                "Run fundamental analysis (1 year)",
                "Compare vs previous quarter",
                "Flag significant changes",
                "Export summary report"
            ],
            "estimated_time": "15-30 minutes",
            "icon": "🔄"
        }
    }

    for name, config in workflows.items():
        with st.expander(f"{config['icon']} {name}"):
            st.markdown(f"**Description:** {config['description']}")
            st.markdown(f"**Estimated Time:** {config['estimated_time']}")

            st.markdown("**Steps:**")
            for i, step in enumerate(config['steps'], 1):
                st.markdown(f"{i}. {step}")

            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("Create Workflow", key=f"workflow_{name}"):
                    st.info("💡 Navigate to Workflow Builder to create this workflow")

with tab3:
    st.subheader("Custom Prompt Library")
    st.info("💡 Browse and use custom analysis prompts created by the community")

    # Get custom prompts from database
    try:
        prompts = db.get_all_prompts()

        if prompts:
            # Filter by analysis type
            analysis_types = list(set(p['analysis_type'] for p in prompts))
            selected_type = st.selectbox(
                "Filter by Analysis Type",
                ["All"] + analysis_types,
                key="prompt_filter"
            )

            # Display prompts
            for prompt in prompts:
                if selected_type != "All" and prompt['analysis_type'] != selected_type:
                    continue

                with st.expander(f"📝 {prompt['name']} ({prompt['analysis_type']})"):
                    if prompt.get('description'):
                        st.markdown(f"**Description:** {prompt['description']}")

                    st.text_area(
                        "Prompt Template",
                        value=prompt.get('prompt_template', prompt.get('template', '')),
                        height=150,
                        disabled=True,
                        key=f"view_prompt_{prompt['id']}"
                    )

                    st.caption(f"Created: {prompt['created_at']}")

                    if st.button("Use This Prompt", key=f"use_prompt_{prompt['id']}"):
                        st.success("✅ Prompt selected! Use it in your next analysis.")
        else:
            st.info("No custom prompts available yet. Create your first one in Settings!")

    except Exception as e:
        st.error(f"Error loading prompts: {e}")

    st.markdown("---")

    # Link to create new prompts
    st.markdown("### Create New Prompts")
    st.markdown("Navigate to **Settings → Custom Prompts** to create your own analysis prompts")

    if st.button("Go to Settings"):
        st.switch_page("pages/5_⚙️_Settings.py")

with tab4:
    st.subheader("Saved Configurations")
    st.info("💡 Save and load your favorite ticker lists and configuration profiles")

    # Ticker Lists section
    st.markdown("### 📋 Ticker Lists")

    # Sample ticker lists
    ticker_lists = {
        "S&P 500 Tech Giants": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
        "Warren Buffett Portfolio": ["AAPL", "BAC", "AXP", "KO", "CVX", "OXY"],
        "Dividend Aristocrats Sample": ["JNJ", "PG", "KO", "PEP", "WMT", "T"],
        "My Watchlist": []  # User can customize
    }

    selected_list = st.selectbox(
        "Select Ticker List",
        list(ticker_lists.keys()),
        key="ticker_list_select"
    )

    if selected_list:
        tickers = ticker_lists[selected_list]
        if tickers:
            st.markdown(f"**Tickers:** {', '.join(tickers)}")
            st.caption(f"Total: {len(tickers)} companies")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Use in Single Analysis"):
                    st.info("Navigate to Single Analysis and enter ticker")

            with col2:
                if st.button("Use in Batch Analysis"):
                    st.info("Navigate to Batch Analysis to analyze all tickers")

            with col3:
                if st.button("Export as CSV"):
                    import io
                    csv_buffer = io.StringIO()
                    csv_buffer.write("ticker\n")
                    for ticker in tickers:
                        csv_buffer.write(f"{ticker}\n")

                    st.download_button(
                        "Download CSV",
                        csv_buffer.getvalue(),
                        file_name=f"{selected_list.replace(' ', '_')}.csv",
                        mime="text/csv"
                    )
        else:
            st.info("This is an empty list. Add tickers below.")

    st.markdown("---")

    # Add new ticker list
    with st.expander("➕ Create New Ticker List"):
        list_name = st.text_input("List Name", key="new_list_name")
        tickers_input = st.text_area(
            "Tickers (one per line)",
            placeholder="AAPL\nMSFT\nGOOGL",
            key="new_list_tickers"
        )

        if st.button("Save List"):
            if list_name and tickers_input:
                st.success(f"✅ List '{list_name}' saved!")
            else:
                st.error("Please provide both name and tickers")

# Navigation
render_page_navigation()
