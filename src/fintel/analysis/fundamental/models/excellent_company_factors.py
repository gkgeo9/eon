#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excellent company success factor analysis Pydantic models.

RESTORED FROM: 10K_automator/analyze_30_outputs_for_excellent_companies.py

Different structure from objective analysis - focuses on SUCCESS identification.
"""

from typing import List
from pydantic import BaseModel, Field


class KeyChange(BaseModel):
    """A strategic change that improved performance"""
    year: str = Field(description="Year of change")
    change: str = Field(description="Description of strategic change")
    impact: str = Field(description="How this affected the company")


class BusinessEvolution(BaseModel):
    """Evolution of business model over time"""
    core_model: str = Field(description="Description of the fundamental business model")
    key_changes: List[KeyChange] = Field(description="Strategic changes that improved performance")
    strategic_consistency: str = Field(description="Areas where strategy remained consistent")


class SuccessFactor(BaseModel):
    """A key factor that drove success"""
    factor: str = Field(description="Key success factor")
    importance: str = Field(description="Why this factor was crucial")
    evolution: str = Field(description="How this factor evolved over time")


class FinancialPerformance(BaseModel):
    """Financial performance and trends"""
    revenue_trends: str = Field(description="Analysis of revenue growth patterns")
    profitability: str = Field(description="Analysis of profit margin trends")
    capital_allocation: str = Field(description="How the company allocated capital")
    financial_strengths: List[str] = Field(description="List of financial competitive advantages")


class CompetitiveAdvantage(BaseModel):
    """A specific competitive advantage"""
    advantage: str = Field(description="Specific competitive advantage")
    sustainability: str = Field(description="How sustainable this advantage is")
    impact: str = Field(description="How this created value")


class ManagementExcellence(BaseModel):
    """Management quality and decisions"""
    key_decisions: List[str] = Field(description="Important management decisions")
    leadership_qualities: List[str] = Field(description="Leadership attributes that drove success")
    governance: str = Field(description="Assessment of corporate governance")


class InnovationStrategy(BaseModel):
    """Innovation approach and results"""
    approach: str = Field(description="Overall approach to innovation")
    key_innovations: List[str] = Field(description="Significant innovations or R&D investments")
    results: str = Field(description="Outcomes of innovation efforts")


class RiskManagement(BaseModel):
    """Risk management approach"""
    approach: str = Field(description="Overall approach to risk")
    key_risks_addressed: List[str] = Field(description="Major risks the company successfully managed")
    vulnerabilities: List[str] = Field(description="Remaining areas of vulnerability")


class ValueCreation(BaseModel):
    """Value creation for stakeholders"""
    customer_value: str = Field(description="How the company created value for customers")
    shareholder_value: str = Field(description="How the company created value for shareholders")
    societal_value: str = Field(description="Broader impact and ESG contributions")


class FutureOutlook(BaseModel):
    """Forward-looking assessment"""
    strengths_to_leverage: List[str] = Field(description="Key strengths for future growth")
    challenges_to_address: List[str] = Field(description="Challenges that need attention")
    growth_potential: str = Field(description="Assessment of future growth potential")


class ExcellentCompanyFactors(BaseModel):
    """
    Success factor analysis for KNOWN excellent companies.

    Different from objective analysis - assumes company was successful
    and focuses on identifying WHY it succeeded.

    Used for analyzing top performers like the top 50 compounders.
    """
    company_name: str = Field(description="Company name or ticker")
    years_analyzed: List[str] = Field(description="Fiscal years analyzed")
    business_evolution: BusinessEvolution = Field(description="How the business model evolved over time")
    success_factors: List[SuccessFactor] = Field(description="Key factors that drove success")
    financial_performance: FinancialPerformance = Field(description="Financial performance trends and strengths")
    competitive_advantages: List[CompetitiveAdvantage] = Field(description="Competitive advantages that created value")
    management_excellence: ManagementExcellence = Field(description="Leadership quality and key decisions")
    innovation_strategy: InnovationStrategy = Field(description="Innovation approach and outcomes")
    risk_management: RiskManagement = Field(description="Risk management approach and results")
    value_creation: ValueCreation = Field(description="Value created for all stakeholders")
    unique_attributes: List[str] = Field(description="Top 5-7 attributes that made this company unique and valuable")
    future_outlook: FutureOutlook = Field(description="Forward-looking assessment")


__all__ = [
    'KeyChange',
    'BusinessEvolution',
    'SuccessFactor',
    'FinancialPerformance',
    'CompetitiveAdvantage',
    'ManagementExcellence',
    'InnovationStrategy',
    'RiskManagement',
    'ValueCreation',
    'FutureOutlook',
    'ExcellentCompanyFactors',
]
