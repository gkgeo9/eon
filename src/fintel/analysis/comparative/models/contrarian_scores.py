#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contrarian scanner Pydantic models.

Scores companies on hidden gem / contrarian investment potential.
"""

from typing import List
from pydantic import BaseModel, Field


class ContrarianScores(BaseModel):
    """Individual contrarian scoring dimensions."""

    strategic_anomaly: int = Field(..., ge=0, le=100, description="Bold, counterintuitive strategic moves")
    asymmetric_resources: int = Field(..., ge=0, le=100, description="Concentrated resource allocation")
    contrarian_positioning: int = Field(..., ge=0, le=100, description="Inverse to industry orthodoxy")
    cross_industry_dna: int = Field(..., ge=0, le=100, description="Leadership importing foreign practices")
    early_infrastructure: int = Field(..., ge=0, le=100, description="Building for future markets")
    intellectual_capital: int = Field(..., ge=0, le=100, description="Undervalued IP/capabilities")


class ContrarianAnalysis(BaseModel):
    """
    Contrarian investment analysis result.

    Scores companies on six dimensions of contrarian/hidden gem potential.
    Overall "alpha score" represents composite opportunity assessment.
    """

    ticker: str
    company_name: str
    overall_alpha_score: int = Field(..., ge=0, le=100, description="Composite contrarian opportunity score")
    scores: ContrarianScores
    key_insights: List[str] = Field(default_factory=list, description="Factual observations about strategy")
    investment_thesis: str = Field(description="Objective assessment based on evidence")
    risk_factors: List[str] = Field(default_factory=list, description="Primary execution/market risks")
    catalyst_timeline: str = Field(description="Timeframe for thesis validation")
    confidence_level: str = Field(description="HIGH/MEDIUM/LOW based on evidence strength")


__all__ = [
    'ContrarianScores',
    'ContrarianAnalysis',
]
