#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Benchmark comparison Pydantic models.

RESTORED FROM: 10K_automator/compare_excellent_to_top_50.py
and compare_random_to_top_50.py

Defines the comprehensive scoring framework for comparing companies
against top 50 proven winners.
"""

from typing import List
from pydantic import BaseModel, Field


class CompounderPotential(BaseModel):
    """Overall compounder potential assessment"""
    score: int = Field(
        ge=0, le=100,
        description="Overall potential score (0-100)"
    )
    category: str = Field(
        description="Category: Future Compounder/Strong Potential/Developing Contender/Partial Alignment/Limited Alignment/Misaligned"
    )
    summary: str = Field(
        description="3-4 sentence summary of the company's potential as a long-term compounder"
    )
    distinctive_strengths: List[str] = Field(
        description="3-5 most compelling characteristics that could drive long-term outperformance"
    )
    critical_gaps: List[str] = Field(
        description="3-5 most concerning weaknesses that could limit long-term compounding"
    )
    stage_context: str = Field(
        description="Assessment of the company's current business stage and how it affects the evaluation"
    )


class SuccessFactorAlignment(BaseModel):
    """Alignment with a specific universal success factor"""
    factor: str = Field(description="Name of universal success factor")
    alignment: str = Field(description="Strong/Moderate/Weak/Absent")
    score: int = Field(ge=0, le=100, description="Score for this specific factor")
    pattern_assessment: str = Field(
        description="Description of how the company's approach compares to top performers in this area"
    )
    maturity_level: str = Field(
        description="Assessment of how developed and embedded this pattern is within the company"
    )
    competitive_advantage: str = Field(
        description="Analysis of whether this factor contributes to sustainable differentiation"
    )


class LeadershipAssessment(BaseModel):
    """Leadership alignment with top performers"""
    alignment: str = Field(description="Strong/Moderate/Weak")
    score: int = Field(ge=0, le=100, description="Leadership alignment score")
    patterns_present: List[str] = Field(
        description="Leadership patterns from top performers that appear present"
    )
    patterns_missing: List[str] = Field(
        description="Leadership patterns from top performers that appear absent"
    )
    long_term_orientation: str = Field(
        description="Assessment of leadership's focus on long-term value creation versus short-term results"
    )


class StrategicPositioningAssessment(BaseModel):
    """Strategic positioning alignment"""
    alignment: str = Field(description="Strong/Moderate/Weak")
    score: int = Field(ge=0, le=100, description="Strategic alignment score")
    approaches_present: List[str] = Field(
        description="Strategic positioning approaches from top 50 that appear present"
    )
    approaches_missing: List[str] = Field(
        description="Strategic positioning approaches from top 50 that appear absent"
    )
    defensibility: str = Field(
        description="Assessment of how defensible the company's strategic position appears over a multi-decade horizon"
    )


class FinancialPatternsAssessment(BaseModel):
    """Financial patterns alignment"""
    alignment: str = Field(description="Strong/Moderate/Weak")
    score: int = Field(ge=0, le=100, description="Financial patterns alignment score")
    patterns_present: List[str] = Field(
        description="Financial patterns from top performers that appear present"
    )
    patterns_missing: List[str] = Field(
        description="Financial patterns from top performers that appear missing"
    )
    capital_allocation_quality: str = Field(
        description="Specific assessment of the company's capital allocation approach and its potential to drive compounding"
    )


class InnovationSystemsAssessment(BaseModel):
    """Innovation systems alignment"""
    alignment: str = Field(description="Strong/Moderate/Weak")
    score: int = Field(ge=0, le=100, description="Innovation systems alignment score")
    systems_present: List[str] = Field(
        description="Innovation systems from top performers that appear present"
    )
    systems_missing: List[str] = Field(
        description="Innovation systems from top performers that appear missing"
    )
    adaptability_assessment: str = Field(
        description="Evaluation of the company's ability to innovate within its core model rather than requiring fundamental pivots"
    )


class OperationalExcellenceAssessment(BaseModel):
    """Operational excellence alignment"""
    alignment: str = Field(description="Strong/Moderate/Weak")
    score: int = Field(ge=0, le=100, description="Operational excellence alignment score")
    factors_present: List[str] = Field(
        description="Operational excellence factors from top performers that appear present"
    )
    factors_missing: List[str] = Field(
        description="Operational excellence factors from top performers that appear missing"
    )
    execution_quality: str = Field(
        description="Assessment of the company's operational execution capabilities and its impact on competitive advantage"
    )


class CustomerRelationshipAssessment(BaseModel):
    """Customer relationship alignment"""
    alignment: str = Field(description="Strong/Moderate/Weak")
    score: int = Field(ge=0, le=100, description="Customer relationship alignment score")
    models_present: List[str] = Field(
        description="Customer relationship models from top performers that appear present"
    )
    models_missing: List[str] = Field(
        description="Customer relationship models from top performers that appear missing"
    )
    durability_assessment: str = Field(
        description="Evaluation of how sticky and durable customer relationships appear to be"
    )


class CrossPatternRelationshipAssessment(BaseModel):
    """Cross-pattern relationship alignment"""
    alignment: str = Field(description="Strong/Moderate/Weak")
    score: int = Field(ge=0, le=100, description="Cross-pattern relationship alignment score")
    relationships_present: List[str] = Field(
        description="Cross-pattern relationships from top performers that appear present"
    )
    relationships_missing: List[str] = Field(
        description="Cross-pattern relationships from top performers that appear missing"
    )
    system_coherence: str = Field(
        description="Assessment of how well the company's various success elements work together as a coherent system"
    )


class PredictiveIndicatorsAssessment(BaseModel):
    """Predictive indicators alignment"""
    alignment: str = Field(description="Strong/Moderate/Weak")
    score: int = Field(ge=0, le=100, description="Predictive indicators alignment score")
    indicators_present: List[str] = Field(
        description="Predictive indicators from top performers that appear present"
    )
    indicators_missing: List[str] = Field(
        description="Predictive indicators from top performers that appear missing"
    )
    forward_indicators: str = Field(
        description="Identification of leading indicators that suggest future compounding potential"
    )


class FinalAssessment(BaseModel):
    """Final assessment and verdict"""
    verdict: str = Field(description="Assessment of likelihood to be a multi-decade compounder")
    probability_of_outperformance: str = Field(description="High/Medium/Low")
    reasoning: str = Field(description="Explanation of why this probability was assigned")
    key_areas_to_monitor: List[str] = Field(
        description="3-5 specific areas to watch that could confirm or challenge the compounding thesis"
    )
    meta_conclusions_alignment: str = Field(
        description="Assessment of how the company aligns with the meta_conclusions from the top 50 analysis"
    )


class InvestorConsiderations(BaseModel):
    """Investor considerations and next steps"""
    research_priorities: List[str] = Field(
        description="Suggested areas for deeper investigation based on this initial screening"
    )
    potential_catalysts: List[str] = Field(
        description="Possible events or developments that could accelerate or reveal compounding potential"
    )
    key_risks: List[str] = Field(
        description="Specific risks to the compounding thesis that deserve particular attention"
    )


class BenchmarkComparison(BaseModel):
    """
    Complete benchmark comparison against top 50 proven winners.

    RESTORED FROM: 10K_automator/compare_excellent_to_top_50.py

    Uses the COMPOUNDER DNA SCORING SYSTEM:
    - 90-100: Future Compounder - Clear, comprehensive pattern strongly resembling top performers
    - 75-89: Strong Potential - Significant alignment with intentional design
    - 60-74: Developing Contender - Meaningful elements with room for improvement
    - 40-59: Partial Alignment - Some positive elements but lacking cohesive pattern
    - 20-39: Limited Alignment - Minimal resemblance to top performers
    - 0-19: Misaligned - Approach runs counter to top performer patterns
    """
    company_name: str = Field(description="Name of the company being analyzed")
    analysis_date: str = Field(description="Current date")
    compounder_potential: CompounderPotential = Field(
        description="Overall compounder potential assessment"
    )
    success_factor_alignment: List[SuccessFactorAlignment] = Field(
        description="Alignment with each universal success factor from top 50"
    )
    leadership_assessment: LeadershipAssessment = Field(
        description="Leadership alignment with top performers"
    )
    strategic_positioning_assessment: StrategicPositioningAssessment = Field(
        description="Strategic positioning alignment"
    )
    financial_patterns_assessment: FinancialPatternsAssessment = Field(
        description="Financial patterns alignment"
    )
    innovation_systems_assessment: InnovationSystemsAssessment = Field(
        description="Innovation systems alignment"
    )
    operational_excellence_assessment: OperationalExcellenceAssessment = Field(
        description="Operational excellence alignment"
    )
    customer_relationship_assessment: CustomerRelationshipAssessment = Field(
        description="Customer relationship alignment"
    )
    cross_pattern_relationship_assessment: CrossPatternRelationshipAssessment = Field(
        description="Cross-pattern relationship alignment"
    )
    predictive_indicators_assessment: PredictiveIndicatorsAssessment = Field(
        description="Predictive indicators alignment"
    )
    final_assessment: FinalAssessment = Field(
        description="Final verdict and probability assessment"
    )
    investor_considerations: InvestorConsiderations = Field(
        description="Research priorities, catalysts, and risks"
    )


__all__ = [
    'CompounderPotential',
    'SuccessFactorAlignment',
    'LeadershipAssessment',
    'StrategicPositioningAssessment',
    'FinancialPatternsAssessment',
    'InnovationSystemsAssessment',
    'OperationalExcellenceAssessment',
    'CustomerRelationshipAssessment',
    'CrossPatternRelationshipAssessment',
    'PredictiveIndicatorsAssessment',
    'FinalAssessment',
    'InvestorConsiderations',
    'BenchmarkComparison',
]
