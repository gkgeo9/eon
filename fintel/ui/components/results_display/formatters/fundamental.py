#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Formatter for Fundamental Analysis (10-K) results.
"""

import streamlit as st
from .base import BaseFormatter
from typing import Dict, Any


class FundamentalFormatter(BaseFormatter):
    """Formatter for TenKAnalysis results."""

    def render(self):
        """Render fundamental analysis results with enhanced UX."""
        if not self.result_data:
            self.render_empty_state("No fundamental analysis data available")
            return

        # Create tabbed interface for better organization
        self.render_tabs({
            "📋 Overview": self._render_overview,
            "💼 Business Model": self._render_business_model,
            "🏆 Competitive Position": self._render_competitive_position,
            "⚠️ Risks": self._render_risks,
            "📊 Financials": self._render_financials
        })

    def _render_overview(self):
        """Render overview section."""
        st.markdown("### Company Overview")

        # Key highlights in metric cards
        if 'business_summary' in self.result_data:
            st.markdown(self.result_data.get('business_summary', 'N/A'))

        # Key insights
        insights = []
        if 'key_products' in self.result_data:
            products = self.result_data['key_products']
            if products:
                insights.append(f"Key Products: {', '.join(products[:3])}")

        if 'competitive_advantages' in self.result_data:
            advantages = self.result_data['competitive_advantages']
            if advantages:
                insights.append(f"Main Advantages: {', '.join(advantages[:2])}")

        if insights:
            self.render_key_insights(insights)

    def _render_business_model(self):
        """Render business model section."""
        st.markdown("### Business Model Analysis")

        # Revenue streams
        if 'revenue_streams' in self.result_data:
            streams = self.result_data['revenue_streams']
            if streams:
                st.markdown("**Revenue Streams:**")
                for stream in streams:
                    st.markdown(f"- {stream}")
            else:
                st.info("No revenue stream information available")

        st.markdown("---")

        # Key products/services
        if 'key_products' in self.result_data:
            products = self.result_data['key_products']
            if products:
                st.markdown("**Key Products & Services:**")
                for product in products:
                    st.markdown(f"- {product}")

        st.markdown("---")

        # Target markets
        if 'target_markets' in self.result_data:
            markets = self.result_data['target_markets']
            if markets:
                st.markdown("**Target Markets:**")
                for market in markets:
                    st.markdown(f"- {market}")

    def _render_competitive_position(self):
        """Render competitive position section."""
        st.markdown("### Competitive Position")

        # Competitive advantages
        if 'competitive_advantages' in self.result_data:
            advantages = self.result_data['competitive_advantages']
            if advantages:
                st.success("**Competitive Advantages:**")
                for adv in advantages:
                    st.markdown(f"✓ {adv}")

        st.markdown("---")

        # Main competitors
        if 'main_competitors' in self.result_data:
            competitors = self.result_data['main_competitors']
            if competitors:
                st.markdown("**Main Competitors:**")
                for comp in competitors:
                    st.markdown(f"- {comp}")

        st.markdown("---")

        # Market position
        if 'market_position' in self.result_data:
            st.markdown("**Market Position:**")
            st.markdown(self.result_data['market_position'])

    def _render_risks(self):
        """Render risks section."""
        st.markdown("### Risk Factors")

        if 'key_risks' in self.result_data:
            risks = self.result_data['key_risks']
            if risks:
                for i, risk in enumerate(risks, 1):
                    st.warning(f"**Risk {i}:** {risk}")
            else:
                st.info("No specific risk factors identified")
        else:
            st.info("Risk information not available")

    def _render_financials(self):
        """Render financial metrics section."""
        st.markdown("### Financial Highlights")

        # Create metric cards for financial data
        col1, col2, col3 = st.columns(3)

        with col1:
            if 'revenue_growth' in self.result_data:
                growth = self.result_data['revenue_growth']
                self.render_metric_card(
                    "Revenue Growth",
                    growth,
                    help_text="Year-over-year revenue growth"
                )

        with col2:
            if 'profit_margin' in self.result_data:
                margin = self.result_data['profit_margin']
                self.render_metric_card(
                    "Profit Margin",
                    margin,
                    help_text="Net profit margin"
                )

        with col3:
            if 'debt_to_equity' in self.result_data:
                ratio = self.result_data['debt_to_equity']
                self.render_metric_card(
                    "Debt/Equity",
                    ratio,
                    help_text="Debt to equity ratio"
                )

        st.markdown("---")

        # Additional financial commentary
        if 'financial_health_summary' in self.result_data:
            st.markdown("**Financial Health Summary:**")
            st.markdown(self.result_data['financial_health_summary'])
