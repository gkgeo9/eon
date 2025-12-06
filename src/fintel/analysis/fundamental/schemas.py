#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pydantic models for fundamental 10-K analysis.

BACKWARD COMPATIBILITY LAYER
This file now imports from models/ subdirectory.
Existing code will continue to work without changes.

Extracted from standardized_sec_ai/tenk_models.py
"""

# Import everything from models for backward compatibility
from .models.basic import (
    FinancialHighlights,
    TenKAnalysis,
    RevenueSegment,
    GeographicBreakdown,
    CustomDeepDiveAnalysis,
    BusinessModelSustainability,
    CompetitivePositioning,
    FinancialHealth,
    RiskAssessment,
    FocusedAnalysis,
    EVManufacturerMetrics,
)

from .models.success_factors import (
    StrategicShift,
    BusinessModel,
    PerformanceFactor,
    FinancialMetrics,
    MarketPosition,
    ManagementAssessment,
    ResearchDevelopment,
    RiskMethodology,
    EvolvingRiskFactor,
    StakeholderImpacts,
    ForwardOutlook,
    CompanySuccessFactors,
)

# Export all models (maintains backward compatibility)
__all__ = [
    # Basic models
    'TenKAnalysis',
    'FinancialHighlights',
    'CustomDeepDiveAnalysis',
    'FocusedAnalysis',
    'EVManufacturerMetrics',
    'RevenueSegment',
    'GeographicBreakdown',
    'BusinessModelSustainability',
    'CompetitivePositioning',
    'FinancialHealth',
    'RiskAssessment',
    # Multi-year success factors schemas
    'CompanySuccessFactors',
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
    'StrategicShift',
]
