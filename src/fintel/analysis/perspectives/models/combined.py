#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Combined multi-perspective analysis model.

Integrates all three investment lenses: Buffett, Taleb, and Contrarian.
"""

from typing import List
from pydantic import BaseModel, Field

from .buffett import BuffettAnalysis
from .taleb import TalebAnalysis
from .contrarian import ContrarianViewAnalysis


class MultiPerspectiveAnalysis(BaseModel):
    """
    Multi-Perspective Investment Analysis.

    Combines three investment philosophies:
    - Warren Buffett (value, moat, management)
    - Nassim Taleb (fragility, tail risks, antifragility)
    - Contrarian View (variant perception)
    """
    ticker: str = Field(description="Stock ticker symbol")
    company_name: str = Field(description="Company name")
    fiscal_year: int = Field(description="Fiscal year analyzed")

    # Three investment lenses
    buffett_lens: BuffettAnalysis = Field(
        description="Warren Buffett's value investing analysis"
    )
    taleb_lens: TalebAnalysis = Field(
        description="Nassim Taleb's antifragility analysis"
    )
    contrarian_lens: ContrarianViewAnalysis = Field(
        description="Contrarian variant perception analysis"
    )

    # Synthesis
    key_insights: List[str] = Field(
        description="Top 5-7 most important insights combining all three perspectives. Each insight should be one clear sentence with supporting evidence. These should be the 'so what' - the insights that actually matter for the investment decision."
    )
    final_verdict: str = Field(
        description="STRONG BUY / BUY / HOLD / SELL / STRONG SELL with conviction level (High/Medium/Low). Provide 3-4 paragraph synthesis: (1) What's the complete picture combining all lenses? (2) Key trade-offs and risks, (3) Time horizon and position sizing recommendation, (4) What would make you change your mind? Be decisive but honest about uncertainty."
    )


__all__ = ['MultiPerspectiveAnalysis']
