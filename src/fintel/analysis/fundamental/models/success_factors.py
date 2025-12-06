#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Multi-year success factor analysis Pydantic models.

Enhanced with detailed Field descriptions from 10K_automator to guide AI analysis.
Follows standardized_sec_ai pattern of using Field descriptions as prompt guidance.
"""

from typing import List
from pydantic import BaseModel, Field


class StrategicShift(BaseModel):
    """A significant strategic or operational change over time"""
    period: str = Field(
        description="Specific year or timeframe when the change occurred"
    )
    change: str = Field(
        description="Detailed description of the strategic or operational change that took place"
    )
    measured_outcome: str = Field(
        description="Quantifiable results that followed this shift, including relevant metrics and whether outcomes were positive, negative, or mixed"
    )


class BusinessModel(BaseModel):
    """Core business model and its evolution"""
    core_operations: str = Field(
        description="Detailed explanation of how the company generates revenue, its primary products/services, and key operational processes"
    )
    strategic_shifts: List[StrategicShift] = Field(
        description="Major strategic or operational changes that occurred during the analyzed period, with measured outcomes"
    )
    operational_consistency: str = Field(
        description="Specific areas of the business model that remained consistent throughout the analyzed period, and why they did or did not change"
    )


class PerformanceFactor(BaseModel):
    """A key factor that significantly influenced company performance"""
    factor: str = Field(
        description="Specific business element that significantly influenced company performance"
    )
    business_impact: str = Field(
        description="Detailed explanation of how this factor affected financial results, operations, or market position with supporting metrics"
    )
    development: str = Field(
        description="How this factor changed or evolved throughout the analyzed timeframe, including key milestones or turning points"
    )


class FinancialMetrics(BaseModel):
    """Comprehensive financial performance analysis"""
    revenue_analysis: str = Field(
        description="Comprehensive breakdown of revenue trends, including growth rates, revenue streams, and any significant patterns observed across the analyzed period"
    )
    profit_analysis: str = Field(
        description="Detailed assessment of profit/loss figures, margins, and profitability trends with supporting data points"
    )
    capital_decisions: str = Field(
        description="Thorough examination of how capital was allocated across divisions, projects, acquisitions, stock buybacks, or other purposes"
    )
    financial_position: List[str] = Field(
        description="Multiple specific aspects of the company's financial status, including debt levels, cash reserves, liquidity, and balance sheet characteristics"
    )


class MarketPosition(BaseModel):
    """Competitive market positioning factor"""
    factor: str = Field(
        description="Specific element affecting the company's competitive standing in its industry"
    )
    durability: str = Field(
        description="Assessment of how sustainable this position factor is, based on market dynamics, barriers to entry, and competitive responses"
    )
    business_effect: str = Field(
        description="Detailed explanation of how this factor has affected market share, pricing power, customer acquisition, or other relevant metrics"
    )


class ManagementAssessment(BaseModel):
    """Leadership and governance evaluation"""
    key_decisions: List[str] = Field(
        description="Specific major management actions taken during the period and their documented outcomes"
    )
    leadership_approach: List[str] = Field(
        description="Observable management characteristics and methodologies based on executive statements and actions"
    )
    governance_structure: str = Field(
        description="Detailed description of board composition, executive compensation structures, voting rights, and other governance mechanisms"
    )


class ResearchDevelopment(BaseModel):
    """R&D strategy and outcomes"""
    methodology: str = Field(
        description="Comprehensive explanation of R&D approach, investment levels as percentage of revenue, and focus areas"
    )
    notable_initiatives: List[str] = Field(
        description="Specific R&D projects, acquisitions, or partnerships undertaken in the analyzed period"
    )
    outcomes: str = Field(
        description="Detailed assessment of R&D results, including products launched, patents secured, or technology advantages gained"
    )


class RiskMethodology(BaseModel):
    """Risk management approach and assessment"""
    methodology: str = Field(
        description="Detailed explanation of how the company identifies, measures, and addresses various types of risk"
    )
    identified_risks: List[str] = Field(
        description="Specific major risks disclosed in filings, including market, operational, financial, and regulatory concerns"
    )
    vulnerabilities: List[str] = Field(
        description="Particular areas where the company appears exposed based on disclosures and performance data"
    )


class EvolvingRiskFactor(BaseModel):
    """A risk factor and how it evolved over time"""
    category: str = Field(
        description="Specific type of risk (e.g., regulatory, competitive, technological, financial)"
    )
    description: str = Field(
        description="Detailed explanation of the risk and its specific relevance to this company"
    )
    trajectory: str = Field(
        description="How this risk has changed in nature or severity throughout the analyzed period"
    )
    potential_consequences: str = Field(
        description="Specific business impacts that could result from this risk, based on disclosures and industry analysis"
    )
    mitigation_efforts: str = Field(
        description="Actions taken by the company to address or reduce this particular risk"
    )


class StakeholderImpacts(BaseModel):
    """Impact on various stakeholders"""
    customer_impact: str = Field(
        description="Detailed assessment of how company operations affect customer experiences, satisfaction metrics, and retention rates"
    )
    investor_outcomes: str = Field(
        description="Comprehensive analysis of shareholder returns, dividend policies, and investor communications"
    )
    broader_impacts: str = Field(
        description="Thorough examination of environmental practices, social responsibility initiatives, and governance matters"
    )


class ForwardOutlook(BaseModel):
    """Forward-looking assessment based on historical patterns"""
    positive_factors: List[str] = Field(
        description="Specific identified elements that could contribute to future growth or improved performance"
    )
    challenges: List[str] = Field(
        description="Particular obstacles or difficulties the company faces moving forward"
    )
    trajectory_assessment: str = Field(
        description="Data-driven evaluation of likely future direction based on current momentum, market conditions, and company positioning"
    )


class CompanySuccessFactors(BaseModel):
    """
    Multi-year success factor analysis.

    Synthesizes patterns across multiple 10-K filings to identify:
    - Business model evolution and strategic pivots
    - Core success factors that drove performance
    - Financial performance trends and capital allocation
    - Competitive advantages and market positioning
    - Management quality and decision-making
    - Innovation approaches and R&D effectiveness
    - Risk management and vulnerabilities
    - Value creation for stakeholders

    This model follows standardized_sec_ai pattern: Field descriptions
    provide detailed guidance to the AI for comprehensive analysis.
    """
    company_name: str = Field(
        description="Company name or ticker symbol"
    )
    period_analyzed: List[str] = Field(
        description="List of fiscal years included in this analysis (e.g., ['2020', '2021', '2022'])"
    )
    business_model: BusinessModel = Field(
        description="Evolution of the company's core business model, including strategic shifts and areas of consistency"
    )
    performance_factors: List[PerformanceFactor] = Field(
        description="Key factors that significantly influenced company performance, with detailed impact analysis and evolution over time"
    )
    financial_metrics: FinancialMetrics = Field(
        description="Comprehensive financial performance analysis including revenue, profitability, capital allocation, and balance sheet strength"
    )
    market_position: List[MarketPosition] = Field(
        description="Factors affecting competitive standing, their sustainability, and business impact"
    )
    management_assessment: ManagementAssessment = Field(
        description="Evaluation of leadership quality, key decisions, and governance structure"
    )
    research_development: ResearchDevelopment = Field(
        description="R&D strategy, investment levels, notable initiatives, and outcomes"
    )
    risk_assessment: RiskMethodology = Field(
        description="Risk management methodology, identified risks, and vulnerabilities"
    )
    evolving_risk_factors: List[EvolvingRiskFactor] = Field(
        description="Major risks and how they evolved over the analyzed period, with mitigation efforts"
    )
    stakeholder_impacts: StakeholderImpacts = Field(
        description="Impact on customers, investors, and broader society"
    )
    distinguishing_characteristics: List[str] = Field(
        description="Specific factors that differentiate this company from others in its industry or market, whether in business model, operations, culture, or other areas"
    )
    forward_outlook: ForwardOutlook = Field(
        description="Forward-looking assessment based on historical patterns, strengths to leverage, and challenges to address"
    )


__all__ = [
    'StrategicShift',
    'BusinessModel',
    'PerformanceFactor',
    'FinancialMetrics',
    'MarketPosition',
    'ManagementAssessment',
    'ResearchDevelopment',
    'RiskMethodology',
    'EvolvingRiskFactor',
    'StakeholderImpacts',
    'ForwardOutlook',
    'CompanySuccessFactors',
]
