#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Formatting utilities for displaying analysis results.
"""

import json
from typing import Dict, Any
import pandas as pd


def generate_markdown_report(data: Dict[str, Any], result_type: str) -> str:
    """
    Generate markdown report from analysis data.

    Args:
        data: Analysis result as dictionary
        result_type: Type of result (TenKAnalysis, BuffettAnalysis, etc.)

    Returns:
        Markdown formatted report
    """
    ticker = data.get('ticker', 'Company')

    if result_type == "TenKAnalysis":
        return _format_tenk_analysis(data, ticker)
    elif result_type == "BuffettAnalysis":
        return _format_buffett_analysis(data, ticker)
    elif result_type == "TalebAnalysis":
        return _format_taleb_analysis(data, ticker)
    elif result_type == "ContrarianAnalysis":
        return _format_contrarian_analysis(data, ticker)
    elif result_type == "SimplifiedAnalysis":
        return _format_multi_perspective(data, ticker)
    else:
        # Generic format
        return f"# Analysis Report: {ticker}\n\n```json\n{json.dumps(data, indent=2)}\n```"


def _format_tenk_analysis(data: Dict, ticker: str) -> str:
    """Format TenKAnalysis result."""
    md = f"""# Fundamental Analysis: {ticker}

## 🎯 Key Takeaways
"""
    for takeaway in data.get('key_takeaways', []):
        md += f"- {takeaway}\n"

    md += f"""
## 📋 Business Model
{data.get('business_model', 'N/A')}

## 💎 Unique Value Proposition
{data.get('unique_value', 'N/A')}

## 🎯 Key Strategies
{data.get('key_strategies', 'N/A')}

## 💰 Financial Highlights
{data.get('financial_highlights', 'N/A')}

## 🏆 Competitive Position
{data.get('competitive_position', 'N/A')}

## ⚠️ Key Risks
{data.get('risks', 'N/A')}

## 👔 Management Quality
{data.get('management_quality', 'N/A')}

## 🔬 Innovation & R&D
{data.get('innovation', 'N/A')}

## 🌱 ESG Factors
{data.get('esg_factors', 'N/A')}
"""
    return md


def _format_buffett_analysis(data: Dict, ticker: str) -> str:
    """Format BuffettAnalysis result."""
    md = f"""# Warren Buffett Perspective: {ticker}

## 📊 Investment Verdict
**{data.get('buffett_verdict', 'N/A')}**

## 🏰 Economic Moat Assessment
{data.get('economic_moat', 'N/A')}

## 💵 Pricing Power
{data.get('pricing_power', 'N/A')}

## 📈 Return on Invested Capital (ROIC)
{data.get('return_on_invested_capital', 'N/A')}

## 💰 Free Cash Flow Quality
{data.get('free_cash_flow_quality', 'N/A')}

## 👔 Management Quality & Capital Allocation
{data.get('management_quality', 'N/A')}

## 🎯 Intrinsic Value Estimate
{data.get('intrinsic_value_estimate', 'N/A')}

## ⚠️ Margin of Safety
{data.get('margin_of_safety', 'N/A')}
"""
    return md


def _format_taleb_analysis(data: Dict, ticker: str) -> str:
    """Format TalebAnalysis result."""
    md = f"""# Nassim Taleb Perspective: {ticker}

## 🛡️ Antifragility Rating
**{data.get('antifragile_rating', 'N/A')}**

## 🔍 Fragility Assessment
{data.get('fragility_assessment', 'N/A')}

## ⚠️ Tail Risk Exposure
{data.get('tail_risk_exposure', 'N/A')}

## 💎 Optionality & Convexity
{data.get('optionality', 'N/A')}

## 🎲 Black Swan Vulnerability
{data.get('black_swan_vulnerability', 'N/A')}

## 🎯 Skin in the Game
{data.get('skin_in_the_game', 'N/A')}

## 📊 Overall Antifragility Score
{data.get('overall_score', 'N/A')}
"""
    return md


def _format_contrarian_analysis(data: Dict, ticker: str) -> str:
    """Format ContrarianAnalysis result."""
    md = f"""# Contrarian Perspective: {ticker}

## 🔍 Market Consensus
{data.get('market_consensus', 'N/A')}

## 💎 Variant Perception
{data.get('variant_perception', 'N/A')}

## 🎁 Hidden Strengths
{data.get('hidden_strengths', 'N/A')}

## ⚠️ Hidden Weaknesses
{data.get('hidden_weaknesses', 'N/A')}

## 🎯 Contrarian Investment Thesis
{data.get('investment_thesis', 'N/A')}

## 📈 Catalyst Timeline
{data.get('catalyst_timeline', 'N/A')}

## ⚡ Key Risks to Thesis
{data.get('thesis_risks', 'N/A')}
"""
    return md


def _format_multi_perspective(data: Dict, ticker: str) -> str:
    """Format SimplifiedAnalysis (multi-perspective) result."""
    md = f"""# Multi-Perspective Analysis: {ticker}

## 💰 Buffett Lens (Value Investing)
{json.dumps(data.get('buffett_analysis', {}), indent=2)}

---

## 🛡️ Taleb Lens (Antifragility)
{json.dumps(data.get('taleb_analysis', {}), indent=2)}

---

## 🔍 Contrarian Lens (Variant Perception)
{json.dumps(data.get('contrarian_analysis', {}), indent=2)}
"""
    return md


def flatten_for_csv(data: Dict[str, Any]) -> pd.DataFrame:
    """
    Flatten nested JSON for CSV export.

    Args:
        data: Analysis result dictionary

    Returns:
        Flattened DataFrame
    """
    return pd.json_normalize(data)
