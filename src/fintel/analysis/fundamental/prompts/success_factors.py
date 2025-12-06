#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Multi-year success factor analysis prompt template.

RESTORED FROM: 10K_automator/analyze_30_outputs_for_random_companies.py

This comprehensive prompt guides AI analysis of multiple years of 10-K filings
to identify patterns, success factors, and strategic evolution.

Template uses .format() with {company_name} and {years_str} placeholders.
"""

# Complete multi-year success factors analysis prompt
# CRITICAL: This is the FULL original prompt from 10K_automator (110+ lines)
SUCCESS_FACTORS_PROMPT = """
# Multi-Year 10-K Analysis Consolidation

You are an expert business analyst examining 10-K filings for {company_name} across multiple years ({years_str}).
Your task is to consolidate these analyses into a comprehensive assessment.

Based on the 10-K analyses provided, create an objective analysis covering:
1. The company's business model and its evolution
2. Performance metrics and trends
3. Strategic decisions and their outcomes
4. Competitive positioning
5. Management actions and their impacts
6. Research and development activities
7. Risk factors and their development
8. Distinguishing characteristics of this company

Return ONLY a valid JSON object with your analysis, structured as follows:

{{
    "company_name": "{company_name}",
    "period_analyzed": [{years_str}],
    "business_model": {{
        "core_operations": "Detailed explanation of how the company generates revenue, its primary products/services, and key operational processes",
        "strategic_shifts": [
            {{
                "period": "Specific year or timeframe when the change occurred",
                "change": "Detailed description of the strategic or operational change that took place",
                "measured_outcome": "Quantifiable results that followed this shift, including relevant metrics and whether outcomes were positive, negative, or mixed"
            }}
        ],
        "operational_consistency": "Specific areas of the business model that remained consistent throughout the analyzed period, and why they did or did not change"
    }},
    "performance_factors": [
        {{
            "factor": "Specific business element that significantly influenced company performance",
            "business_impact": "Detailed explanation of how this factor affected financial results, operations, or market position with supporting metrics",
            "development": "How this factor changed or evolved throughout the analyzed timeframe, including key milestones or turning points"
        }}
    ],
    "financial_metrics": {{
        "revenue_analysis": "Comprehensive breakdown of revenue trends, including growth rates, revenue streams, and any significant patterns observed across the analyzed period",
        "profit_analysis": "Detailed assessment of profit/loss figures, margins, and profitability trends with supporting data points",
        "capital_decisions": "Thorough examination of how capital was allocated across divisions, projects, acquisitions, stock buybacks, or other purposes",
        "financial_position": ["Multiple specific aspects of the company's financial status, including debt levels, cash reserves, liquidity, and balance sheet characteristics"]
    }},
    "market_position": [
        {{
            "factor": "Specific element affecting the company's competitive standing in its industry",
            "durability": "Assessment of how sustainable this position factor is, based on market dynamics, barriers to entry, and competitive responses",
            "business_effect": "Detailed explanation of how this factor has affected market share, pricing power, customer acquisition, or other relevant metrics"
        }}
    ],
    "management_assessment": {{
        "key_decisions": ["Specific major management actions taken during the period and their documented outcomes"],
        "leadership_approach": ["Observable management characteristics and methodologies based on executive statements and actions"],
        "governance_structure": "Detailed description of board composition, executive compensation structures, voting rights, and other governance mechanisms"
    }},
    "research_development": {{
        "methodology": "Comprehensive explanation of R&D approach, investment levels as percentage of revenue, and focus areas",
        "notable_initiatives": ["Specific R&D projects, acquisitions, or partnerships undertaken in the analyzed period"],
        "outcomes": "Detailed assessment of R&D results, including products launched, patents secured, or technology advantages gained"
    }},
    "risk_assessment": {{
        "methodology": "Detailed explanation of how the company identifies, measures, and addresses various types of risk",
        "identified_risks": ["Specific major risks disclosed in filings, including market, operational, financial, and regulatory concerns"],
        "vulnerabilities": ["Particular areas where the company appears exposed based on disclosures and performance data"]
    }},
    "evolving_risk_factors": [
        {{
            "category": "Specific type of risk (e.g., regulatory, competitive, technological, financial)",
            "description": "Detailed explanation of the risk and its specific relevance to this company",
            "trajectory": "How this risk has changed in nature or severity throughout the analyzed period",
            "potential_consequences": "Specific business impacts that could result from this risk, based on disclosures and industry analysis",
            "mitigation_efforts": "Actions taken by the company to address or reduce this particular risk"
        }}
    ],
    "stakeholder_impacts": {{
        "customer_impact": "Detailed assessment of how company operations affect customer experiences, satisfaction metrics, and retention rates",
        "investor_outcomes": "Comprehensive analysis of shareholder returns, dividend policies, and investor communications",
        "broader_impacts": "Thorough examination of environmental practices, social responsibility initiatives, and governance matters"
    }},
    "distinguishing_characteristics": [
        "Specific factors that differentiate this company from others in its industry or market, whether in business model, operations, culture, or other areas"
    ],
    "forward_outlook": {{
        "positive_factors": ["Specific identified elements that could contribute to future growth or improved performance"],
        "challenges": ["Particular obstacles or difficulties the company faces moving forward"],
        "trajectory_assessment": "Data-driven evaluation of likely future direction based on current momentum, market conditions, and company positioning"
    }}
}}

Important guidelines:
- Base your analysis exclusively on the information provided in the 10-K filings
- Present a balanced assessment that includes both favorable and unfavorable aspects
- Support observations with specific data points and metrics whenever possible
- Do not assume the company is either successful or unsuccessful
- Avoid subjective judgments unless directly supported by evidence
- Identify both strengths and weaknesses with equal attention to detail

Don't include any explanatory text, just return valid JSON.
"""


__all__ = [
    'SUCCESS_FACTORS_PROMPT',
]
