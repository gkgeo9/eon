#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Results display components for Streamlit.
"""

import streamlit as st
import json
from typing import Dict, Any, List
from fintel.ui.utils.formatting import generate_markdown_report, flatten_for_csv


def display_results(run_details: Dict[str, Any], results: List[Dict[str, Any]]):
    """
    Display analysis results with multiple views.

    Args:
        run_details: Analysis run metadata
        results: List of result dictionaries with year, type, and data
    """
    ticker = run_details['ticker']
    analysis_type = run_details['analysis_type']

    st.title(f"📊 Analysis Results: {ticker}")
    st.caption(f"Analysis Type: {analysis_type.capitalize()}")

    # Show basic info
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Ticker", ticker)

    with col2:
        st.metric("Years Analyzed", len(results))

    with col3:
        status = run_details.get('status', 'unknown')
        status_emoji = {'completed': '✅', 'failed': '❌', 'running': '🔄'}.get(status, '❓')
        st.metric("Status", f"{status_emoji} {status.capitalize()}")

    st.markdown("---")

    # Year selector if multiple years
    if len(results) > 1:
        years = [r['year'] for r in results]
        selected_year = st.selectbox("Select Year", years, index=0)
        result_data = next(r for r in results if r['year'] == selected_year)
    else:
        result_data = results[0]
        selected_year = result_data['year']

    st.subheader(f"Year: {selected_year}")

    result_type = result_data['type']
    data = result_data['data']

    # Tabbed interface for different views
    tab1, tab2, tab3 = st.tabs(["📄 Formatted View", "🔍 JSON View", "📥 Export"])

    with tab1:
        # Formatted markdown view
        display_formatted_view(data, result_type)

    with tab2:
        # JSON tree view
        display_json_view(data)

    with tab3:
        # Export options
        display_export_options(data, result_type, ticker, selected_year)


def display_formatted_view(data: Dict[str, Any], result_type: str):
    """Display formatted markdown view of results."""
    st.subheader("Formatted Analysis")

    if result_type == "TenKAnalysis":
        _display_tenk_formatted(data)
    elif result_type == "BuffettAnalysis":
        _display_buffett_formatted(data)
    elif result_type == "TalebAnalysis":
        _display_taleb_formatted(data)
    elif result_type == "ContrarianAnalysis":
        _display_contrarian_formatted(data)
    elif result_type == "SimplifiedAnalysis":
        _display_multi_perspective_formatted(data)
    else:
        # Generic display
        st.write(data)


def _display_tenk_formatted(data: Dict):
    """Display TenKAnalysis in formatted style."""

    # Key Takeaways (prominent)
    st.markdown("### 🎯 Key Takeaways")
    for takeaway in data.get('key_takeaways', []):
        st.markdown(f"- {takeaway}")

    # Business sections
    with st.expander("📋 Business Model", expanded=True):
        st.markdown(data.get('business_model', 'N/A'))

    with st.expander("💎 Unique Value Proposition"):
        st.markdown(data.get('unique_value', 'N/A'))

    with st.expander("🎯 Key Strategies"):
        st.markdown(data.get('key_strategies', 'N/A'))

    with st.expander("💰 Financial Highlights"):
        st.markdown(data.get('financial_highlights', 'N/A'))

    with st.expander("🏆 Competitive Position"):
        st.markdown(data.get('competitive_position', 'N/A'))

    with st.expander("⚠️ Key Risks"):
        st.markdown(data.get('risks', 'N/A'))

    with st.expander("👔 Management Quality"):
        st.markdown(data.get('management_quality', 'N/A'))

    with st.expander("🔬 Innovation & R&D"):
        st.markdown(data.get('innovation', 'N/A'))

    with st.expander("🌱 ESG Factors"):
        st.markdown(data.get('esg_factors', 'N/A'))


def _display_buffett_formatted(data: Dict):
    """Display BuffettAnalysis in formatted style."""

    # Verdict (prominent)
    verdict = data.get('buffett_verdict', 'HOLD')
    verdict_colors = {'BUY': 'green', 'HOLD': 'orange', 'PASS': 'red'}
    color = verdict_colors.get(verdict, 'gray')

    st.markdown(f"### Investment Verdict: :{color}[{verdict}]")

    # Metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Moat Strength", data.get('moat_strength', 'N/A'))
    with col2:
        st.metric("Management Quality", data.get('management_rating', 'N/A'))

    # Details
    with st.expander("🏰 Economic Moat", expanded=True):
        st.markdown(data.get('economic_moat', 'N/A'))

    with st.expander("💵 Pricing Power"):
        st.markdown(data.get('pricing_power', 'N/A'))

    with st.expander("📈 Return on Invested Capital"):
        st.markdown(data.get('return_on_invested_capital', 'N/A'))

    with st.expander("💰 Free Cash Flow Quality"):
        st.markdown(data.get('free_cash_flow_quality', 'N/A'))

    with st.expander("👔 Management & Capital Allocation"):
        st.markdown(data.get('management_quality', 'N/A'))

    with st.expander("🎯 Intrinsic Value Estimate"):
        st.markdown(data.get('intrinsic_value_estimate', 'N/A'))

    with st.expander("⚠️ Margin of Safety"):
        st.markdown(data.get('margin_of_safety', 'N/A'))


def _display_taleb_formatted(data: Dict):
    """Display TalebAnalysis in formatted style."""

    st.markdown(f"### 🛡️ Antifragility Rating: **{data.get('antifragile_rating', 'N/A')}**")

    with st.expander("🔍 Fragility Assessment", expanded=True):
        st.markdown(data.get('fragility_assessment', 'N/A'))

    with st.expander("⚠️ Tail Risk Exposure"):
        st.markdown(data.get('tail_risk_exposure', 'N/A'))

    with st.expander("💎 Optionality & Convexity"):
        st.markdown(data.get('optionality', 'N/A'))

    with st.expander("🎲 Black Swan Vulnerability"):
        st.markdown(data.get('black_swan_vulnerability', 'N/A'))

    with st.expander("🎯 Skin in the Game"):
        st.markdown(data.get('skin_in_the_game', 'N/A'))


def _display_contrarian_formatted(data: Dict):
    """Display ContrarianAnalysis in formatted style."""

    with st.expander("🔍 Market Consensus", expanded=True):
        st.markdown(data.get('market_consensus', 'N/A'))

    with st.expander("💎 Variant Perception"):
        st.markdown(data.get('variant_perception', 'N/A'))

    with st.expander("🎁 Hidden Strengths"):
        st.markdown(data.get('hidden_strengths', 'N/A'))

    with st.expander("⚠️ Hidden Weaknesses"):
        st.markdown(data.get('hidden_weaknesses', 'N/A'))

    with st.expander("🎯 Investment Thesis"):
        st.markdown(data.get('investment_thesis', 'N/A'))

    with st.expander("📈 Catalyst Timeline"):
        st.markdown(data.get('catalyst_timeline', 'N/A'))


def _display_multi_perspective_formatted(data: Dict):
    """Display SimplifiedAnalysis (multi-perspective) formatted."""

    st.subheader("💰 Buffett Lens")
    buffett_data = data.get('buffett_analysis', {})
    if buffett_data:
        _display_buffett_formatted(buffett_data)
    else:
        st.info("No Buffett analysis available")

    st.markdown("---")

    st.subheader("🛡️ Taleb Lens")
    taleb_data = data.get('taleb_analysis', {})
    if taleb_data:
        _display_taleb_formatted(taleb_data)
    else:
        st.info("No Taleb analysis available")

    st.markdown("---")

    st.subheader("🔍 Contrarian Lens")
    contrarian_data = data.get('contrarian_analysis', {})
    if contrarian_data:
        _display_contrarian_formatted(contrarian_data)
    else:
        st.info("No Contrarian analysis available")


def display_json_view(data: Dict[str, Any]):
    """Display interactive JSON tree view."""
    st.subheader("Raw JSON Data")

    # Pretty print with syntax highlighting
    st.json(data)

    # Code block for copying
    with st.expander("Copy JSON"):
        st.code(json.dumps(data, indent=2), language='json')


def display_export_options(data: Dict[str, Any], result_type: str, ticker: str, year: int):
    """Display export options."""
    st.subheader("Export Options")

    col1, col2, col3 = st.columns(3)

    with col1:
        # JSON download
        json_str = json.dumps(data, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"{ticker}_{year}_{result_type}.json",
            mime="application/json",
            use_container_width=True
        )

    with col2:
        # CSV download
        df = flatten_for_csv(data)
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"{ticker}_{year}_{result_type}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col3:
        # Markdown download
        md = generate_markdown_report(data, result_type)
        st.download_button(
            label="📥 Download Markdown",
            data=md,
            file_name=f"{ticker}_{year}_{result_type}.md",
            mime="text/markdown",
            use_container_width=True
        )
