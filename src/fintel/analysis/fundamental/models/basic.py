#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic Pydantic models for fundamental 10-K analysis.

Extracted from standardized_sec_ai/tenk_models.py
"""

from typing import List, Dict
from pydantic import BaseModel, Field


class FinancialHighlights(BaseModel):
    """Financial highlights from the 10-K"""
    revenue: str = Field(description="Total revenue with growth/decline rate")
    profit: str = Field(description="Net income/loss and margin details")
    cash_position: str = Field(description="Cash and debt information, objectively assessed")


class TenKAnalysis(BaseModel):
    """
    Default structured output for 10-K analysis.
    Use this model for consistent, validated AI responses.
    """
    business_model: str = Field(
        description="Objective explanation of the company's business model and how it generates revenue"
    )
    unique_value: str = Field(
        description="Objective assessment of what differentiates this company, whether positively or negatively"
    )
    key_strategies: List[str] = Field(
        description="List of key strategic initiatives or focus areas"
    )
    financial_highlights: FinancialHighlights = Field(
        description="Key financial metrics and trends"
    )
    risks: List[str] = Field(
        description="Major risks and challenges the company faces"
    )
    management_quality: str = Field(
        description="Balanced assessment of leadership and governance strengths and weaknesses"
    )
    innovation: str = Field(
        description="Objective analysis of the company's R&D and innovation approach, whether effective or not"
    )
    competitive_position: str = Field(
        description="Realistic assessment of market position and competitive landscape"
    )
    esg_factors: str = Field(
        description="Environmental, social and governance considerations, both positive and negative"
    )
    key_takeaways: List[str] = Field(
        description="3-5 balanced insights highlighting both strengths and weaknesses"
    )


class RevenueSegment(BaseModel):
    """Revenue breakdown by segment"""
    segment_name: str
    revenue: str
    percentage_of_total: str
    growth_rate: str


class GeographicBreakdown(BaseModel):
    """Geographic revenue distribution"""
    region: str
    revenue: str
    percentage_of_total: str


class CustomDeepDiveAnalysis(BaseModel):
    """
    Custom deep-dive analysis model.
    Provides detailed revenue and operational breakdowns.
    """
    revenue_segments: List[RevenueSegment] = Field(
        description="Revenue composition by business segment"
    )
    geographic_breakdown: List[GeographicBreakdown] = Field(
        description="Geographic distribution of sales"
    )
    capex_trends: str = Field(
        description="Capital expenditure trends and analysis"
    )
    rd_intensity: str = Field(
        description="R&D spending as percentage of revenue and trends"
    )
    competitive_moats: List[str] = Field(
        description="Key competitive advantages and their sustainability"
    )


class BusinessModelSustainability(BaseModel):
    """Business model assessment"""
    is_defensible: bool
    unit_economics: str
    revenue_model: str


class CompetitivePositioning(BaseModel):
    """Competitive analysis"""
    main_competitors: List[str]
    competitive_advantage: str
    moat_sustainability: str


class FinancialHealth(BaseModel):
    """Financial health metrics"""
    cash_burn_rate: str
    path_to_profitability: str
    capital_allocation_strategy: str


class RiskAssessment(BaseModel):
    """Risk analysis"""
    top_risks: List[str] = Field(description="Top 3 existential risks")
    mitigation_strategies: List[str]


class FocusedAnalysis(BaseModel):
    """
    Focused deep dive analysis.
    Emphasizes business model sustainability and competitive positioning.
    """
    business_model_sustainability: BusinessModelSustainability
    competitive_positioning: CompetitivePositioning
    financial_health: FinancialHealth
    risk_assessment: RiskAssessment


class EVManufacturerMetrics(BaseModel):
    """
    Industry-specific analysis for EV manufacturers.
    """
    vehicle_production_capacity: str = Field(
        description="Current and projected production capacity"
    )
    battery_technology: str = Field(
        description="Battery technology, costs, and supply chain"
    )
    charging_infrastructure: str = Field(
        description="Charging network and infrastructure strategy"
    )
    rd_spending: str = Field(
        description="R&D spending and focus areas"
    )
    government_incentives: str = Field(
        description="Dependencies on government incentives and policies"
    )
    key_metrics: Dict[str, str] = Field(
        description="Key operational and financial metrics"
    )


__all__ = [
    'FinancialHighlights',
    'TenKAnalysis',
    'RevenueSegment',
    'GeographicBreakdown',
    'CustomDeepDiveAnalysis',
    'BusinessModelSustainability',
    'CompetitivePositioning',
    'FinancialHealth',
    'RiskAssessment',
    'FocusedAnalysis',
    'EVManufacturerMetrics',
]
