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

    # Display year header (or "Multi-Year" if year is 0)
    if selected_year == 0:
        st.subheader("Multi-Year Analysis")
    else:
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
        # Check if it's the scanner version (has overall_alpha_score) or perspectives version
        if 'overall_alpha_score' in data:
            _display_scanner_formatted(data)
        else:
            _display_contrarian_formatted(data)
    elif result_type == "SimplifiedAnalysis":
        _display_multi_perspective_formatted(data)
    elif result_type == "ExcellentCompanyFactors":
        _display_excellent_factors_formatted(data)
    elif result_type == "CompanySuccessFactors":
        _display_success_factors_formatted(data)
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


def _display_excellent_factors_formatted(data: Dict):
    """Display ExcellentCompanyFactors in formatted style."""

    st.markdown(f"### ⭐ Excellent Company Analysis: {data.get('company_name', 'N/A')}")
    st.caption(f"Years Analyzed: {', '.join(data.get('years_analyzed', []))}")

    # Unique attributes (prominent)
    st.markdown("### 💎 Unique Attributes")
    for attr in data.get('unique_attributes', []):
        st.markdown(f"- {attr}")

    # Success factors
    with st.expander("🎯 Success Factors", expanded=True):
        success_factors = data.get('success_factors', [])
        for i, factor in enumerate(success_factors, 1):
            st.markdown(f"**{i}. {factor.get('factor', 'N/A')}**")
            st.markdown(f"- **Importance:** {factor.get('importance', 'N/A')}")
            st.markdown(f"- **Evolution:** {factor.get('evolution', 'N/A')}")
            st.markdown("")

    # Business Evolution
    with st.expander("📈 Business Evolution"):
        biz_evo = data.get('business_evolution', {})
        st.markdown(f"**Core Model:** {biz_evo.get('core_model', 'N/A')}")
        st.markdown(f"**Strategic Consistency:** {biz_evo.get('strategic_consistency', 'N/A')}")

        key_changes = biz_evo.get('key_changes', [])
        if key_changes:
            st.markdown("**Key Changes:**")
            for change in key_changes:
                st.markdown(f"- **{change.get('year', 'N/A')}**: {change.get('change', 'N/A')}")
                st.markdown(f"  - Impact: {change.get('impact', 'N/A')}")

    # Financial Performance
    with st.expander("💰 Financial Performance"):
        fin = data.get('financial_performance', {})
        st.markdown(f"**Revenue Trends:** {fin.get('revenue_trends', 'N/A')}")
        st.markdown(f"**Profitability:** {fin.get('profitability', 'N/A')}")
        st.markdown(f"**Capital Allocation:** {fin.get('capital_allocation', 'N/A')}")
        st.markdown("**Financial Strengths:**")
        for strength in fin.get('financial_strengths', []):
            st.markdown(f"- {strength}")

    # Competitive Advantages
    with st.expander("🏆 Competitive Advantages"):
        for adv in data.get('competitive_advantages', []):
            st.markdown(f"**{adv.get('advantage', 'N/A')}**")
            st.markdown(f"- Sustainability: {adv.get('sustainability', 'N/A')}")
            st.markdown(f"- Impact: {adv.get('impact', 'N/A')}")
            st.markdown("")

    # Management Excellence
    with st.expander("👔 Management Excellence"):
        mgmt = data.get('management_excellence', {})
        st.markdown("**Key Decisions:**")
        for decision in mgmt.get('key_decisions', []):
            st.markdown(f"- {decision}")
        st.markdown("**Leadership Qualities:**")
        for quality in mgmt.get('leadership_qualities', []):
            st.markdown(f"- {quality}")
        st.markdown(f"**Governance:** {mgmt.get('governance', 'N/A')}")

    # Future Outlook
    with st.expander("🔮 Future Outlook"):
        outlook = data.get('future_outlook', {})
        st.markdown("**Strengths to Leverage:**")
        for strength in outlook.get('strengths_to_leverage', []):
            st.markdown(f"- {strength}")
        st.markdown("**Challenges to Address:**")
        for challenge in outlook.get('challenges_to_address', []):
            st.markdown(f"- {challenge}")
        st.markdown(f"**Growth Potential:** {outlook.get('growth_potential', 'N/A')}")


def _display_success_factors_formatted(data: Dict):
    """Display CompanySuccessFactors (objective) in formatted style."""

    st.markdown(f"### 🎯 Objective Company Analysis: {data.get('company_name', 'N/A')}")
    st.caption(f"Period Analyzed: {', '.join(data.get('period_analyzed', []))}")

    # Distinguishing characteristics (prominent)
    st.markdown("### 💡 Distinguishing Characteristics")
    for char in data.get('distinguishing_characteristics', []):
        st.markdown(f"- {char}")

    # Performance factors
    with st.expander("📊 Performance Factors", expanded=True):
        for i, factor in enumerate(data.get('performance_factors', []), 1):
            st.markdown(f"**{i}. {factor.get('factor', 'N/A')}**")
            st.markdown(f"- **Business Impact:** {factor.get('business_impact', 'N/A')}")
            st.markdown(f"- **Development:** {factor.get('development', 'N/A')}")
            st.markdown("")

    # Business Model
    with st.expander("🏢 Business Model"):
        biz = data.get('business_model', {})
        st.markdown(f"**Core Operations:** {biz.get('core_operations', 'N/A')}")
        st.markdown(f"**Operational Consistency:** {biz.get('operational_consistency', 'N/A')}")

        shifts = biz.get('strategic_shifts', [])
        if shifts:
            st.markdown("**Strategic Shifts:**")
            for shift in shifts:
                st.markdown(f"- **{shift.get('period', 'N/A')}**: {shift.get('change', 'N/A')}")
                st.markdown(f"  - Outcome: {shift.get('measured_outcome', 'N/A')}")

    # Financial Metrics
    with st.expander("💵 Financial Metrics"):
        fin = data.get('financial_metrics', {})
        st.markdown(f"**Revenue Analysis:** {fin.get('revenue_analysis', 'N/A')}")
        st.markdown(f"**Profit Analysis:** {fin.get('profit_analysis', 'N/A')}")
        st.markdown(f"**Capital Decisions:** {fin.get('capital_decisions', 'N/A')}")
        st.markdown("**Financial Position:**")
        for pos in fin.get('financial_position', []):
            st.markdown(f"- {pos}")

    # Market Position
    with st.expander("🎯 Market Position"):
        for pos in data.get('market_position', []):
            st.markdown(f"**{pos.get('factor', 'N/A')}**")
            st.markdown(f"- Durability: {pos.get('durability', 'N/A')}")
            st.markdown(f"- Business Effect: {pos.get('business_effect', 'N/A')}")
            st.markdown("")

    # Risk Assessment
    with st.expander("⚠️ Risk Assessment"):
        risk = data.get('risk_assessment', {})
        st.markdown(f"**Methodology:** {risk.get('methodology', 'N/A')}")
        st.markdown("**Identified Risks:**")
        for r in risk.get('identified_risks', []):
            st.markdown(f"- {r}")
        st.markdown("**Vulnerabilities:**")
        for v in risk.get('vulnerabilities', []):
            st.markdown(f"- {v}")

    # Forward Outlook
    with st.expander("🔮 Forward Outlook"):
        outlook = data.get('forward_outlook', {})
        st.markdown("**Positive Factors:**")
        for factor in outlook.get('positive_factors', []):
            st.markdown(f"- {factor}")
        st.markdown("**Challenges:**")
        for challenge in outlook.get('challenges', []):
            st.markdown(f"- {challenge}")
        st.markdown(f"**Trajectory Assessment:** {outlook.get('trajectory_assessment', 'N/A')}")


def _display_scanner_formatted(data: Dict):
    """Display Contrarian Scanner results in formatted style."""

    st.markdown(f"### 💎 Contrarian Scanner: {data.get('company_name', 'N/A')}")

    # Overall score (prominent)
    alpha_score = data.get('overall_alpha_score', 0)
    confidence = data.get('confidence_level', 'N/A')

    # Color code based on score
    if alpha_score >= 70:
        score_color = 'green'
    elif alpha_score >= 50:
        score_color = 'orange'
    else:
        score_color = 'red'

    st.markdown(f"### Overall Alpha Score: :{score_color}[{alpha_score}/100]")
    st.markdown(f"**Confidence Level:** {confidence}")

    # Dimension scores
    st.markdown("### 📊 Dimension Scores")
    scores = data.get('scores', {})

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Strategic Anomaly", f"{scores.get('strategic_anomaly', 0)}/100")
        st.metric("Asymmetric Resources", f"{scores.get('asymmetric_resources', 0)}/100")
        st.metric("Contrarian Positioning", f"{scores.get('contrarian_positioning', 0)}/100")
    with col2:
        st.metric("Cross-Industry DNA", f"{scores.get('cross_industry_dna', 0)}/100")
        st.metric("Early Infrastructure", f"{scores.get('early_infrastructure', 0)}/100")
        st.metric("Intellectual Capital", f"{scores.get('intellectual_capital', 0)}/100")

    # Key Insights
    with st.expander("💡 Key Insights", expanded=True):
        for insight in data.get('key_insights', []):
            st.markdown(f"- {insight}")

    # Investment Thesis
    with st.expander("📝 Investment Thesis", expanded=True):
        st.markdown(data.get('investment_thesis', 'N/A'))

    # Risk Factors
    with st.expander("⚠️ Risk Factors"):
        for risk in data.get('risk_factors', []):
            st.markdown(f"- {risk}")

    # Catalyst Timeline
    with st.expander("⏰ Catalyst Timeline"):
        st.markdown(data.get('catalyst_timeline', 'N/A'))


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
