#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excellent company success factor analysis prompt template.

RESTORED FROM: 10K_automator/analyze_30_outputs_for_excellent_companies.py

This SUCCESS-FOCUSED prompt guides AI analysis of known successful companies
to identify what made them succeed.

CRITICAL DIFFERENCE from objective analysis:
- This assumes the company WAS successful
- Focuses on identifying success factors and value creation
- Used for analyzing known high performers like top 50 compounders

Template uses .format() with {company_name} and {years_str} placeholders.
"""

# Success-focused prompt for analyzing EXCELLENT companies
# CRITICAL: This is for companies we KNOW are successful
EXCELLENT_COMPANY_PROMPT = """
# Company Success Factors Analysis

You are an expert business analyst examining 10-K filings analyses for {company_name} across multiple years ({years_str}).
Your task is to identify the key factors that made this company successful.

Based on the 10-K analyses provided, identify:
1. Evolution of the company's business model and strategy over time
2. Core success factors that remained consistent
3. Strategic pivots or changes that improved performance
4. Financial performance trends and drivers
5. Competitive advantages that strengthened or weakened
6. Management decisions that created value
7. Innovation approaches that drove growth
8. Risk management techniques that protected value
9. What truly made this company valuable and unique

Return ONLY a valid JSON object with your analysis, structured as follows:

{{
    "company_name": "{company_name}",
    "years_analyzed": [{years_str}],
    "business_evolution": {{
        "core_model": "Description of the fundamental business model",
        "key_changes": [
            {{
                "year": "Year of change",
                "change": "Description of strategic change",
                "impact": "How this affected the company"
            }}
        ],
        "strategic_consistency": "Areas where strategy remained consistent"
    }},
    "success_factors": [
        {{
            "factor": "Key success factor",
            "importance": "Why this factor was crucial",
            "evolution": "How this factor evolved over time"
        }}
    ],
    "financial_performance": {{
        "revenue_trends": "Analysis of revenue growth patterns",
        "profitability": "Analysis of profit margin trends",
        "capital_allocation": "How the company allocated capital",
        "financial_strengths": ["List of financial competitive advantages"]
    }},
    "competitive_advantages": [
        {{
            "advantage": "Specific competitive advantage",
            "sustainability": "How sustainable this advantage is",
            "impact": "How this created value"
        }}
    ],
    "management_excellence": {{
        "key_decisions": ["Important management decisions"],
        "leadership_qualities": ["Leadership attributes that drove success"],
        "governance": "Assessment of corporate governance"
    }},
    "innovation_strategy": {{
        "approach": "Overall approach to innovation",
        "key_innovations": ["Significant innovations or R&D investments"],
        "results": "Outcomes of innovation efforts"
    }},
    "risk_management": {{
        "approach": "Overall approach to risk",
        "key_risks_addressed": ["Major risks the company successfully managed"],
        "vulnerabilities": ["Remaining areas of vulnerability"]
    }},
    "value_creation": {{
        "customer_value": "How the company created value for customers",
        "shareholder_value": "How the company created value for shareholders",
        "societal_value": "Broader impact and ESG contributions"
    }},
    "unique_attributes": [
        "Top 5-7 attributes that truly made this company unique and valuable"
    ],
    "future_outlook": {{
        "strengths_to_leverage": ["Key strengths for future growth"],
        "challenges_to_address": ["Challenges that need attention"],
        "growth_potential": "Assessment of future growth potential"
    }}
}}

Don't include any explanatory text, just return valid JSON.
"""


__all__ = [
    'EXCELLENT_COMPANY_PROMPT',
]
