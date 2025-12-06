#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Nassim Taleb's antifragility lens - Pydantic models.

EXACT Field descriptions from standardized_sec_ai/ppee.py
Following the pattern: Field descriptions ARE the prompt guidance.
"""

from typing import List
from pydantic import BaseModel, Field


class TalebAnalysis(BaseModel):
    """
    Nassim Taleb's Anti-Fragile Framework.

    Focus on: Fragility assessment, tail risks, optionality, skin in the game,
    and building antifragile systems.
    """
    fragility_assessment: str = Field(
        description="Debt fragility: Total Debt/EBITDA ratio (>3x is concerning). Can they survive 50% revenue drop for 12 months? Operational leverage: Fixed vs variable costs. Concentration risk: Top customers/suppliers >10%? Calculate cash runway at zero revenue (months). Be quantitative."
    )
    tail_risk_exposure: List[str] = Field(
        description="5-7 specific BLACK SWAN events that could destroy this company. Think creatively: regulatory changes, technological disruption, key supplier collapse, cyber attack, fraud, geopolitical risk. For each: describe the scenario and estimate probability (low <5%, medium 5-15%, high >15%) and impact (catastrophic/severe/moderate)."
    )
    optionality_and_asymmetry: str = Field(
        description="What asymmetric upside exists? Hidden assets, potential pivots, undervalued optionality. Look for: limited downside + unlimited upside scenarios. Does this have 'lottery ticket' characteristics where small probability events could 10x the value? Or is it capped upside?"
    )
    skin_in_the_game: str = Field(
        description="Do insiders have REAL money at risk? CEO and top execs: actual stock ownership in dollars and % (not unvested options). Are they buying or selling on open market? Do they personally suffer if company fails? Red flag: <1% ownership or constant selling."
    )
    hidden_risks: List[str] = Field(
        description="5 non-obvious risks that don't show up in standard analysis. Think second-order and third-order effects. Examples: customer concentration risk, key person dependency, technological obsolescence, regulatory capture, accounting red flags, supplier power shifts."
    )
    lindy_effect: str = Field(
        description="How old is this business model? 100+ years (lindy) vs <10 years (unproven). Older business models that survived have revealed resilience. Does this get stronger with age or weaker? Is it disruption-resistant or vulnerable?"
    )
    dependency_chains: str = Field(
        description="Map the single points of failure. Critical suppliers? Key customers? Essential personnel? Regulatory dependencies? Geographic concentration? What ONE thing, if it broke, would cripple the business?"
    )
    via_negativa: List[str] = Field(
        description="What should they STOP doing? Addition by subtraction. Identify complexity, low-ROIC businesses, or distractions they should eliminate. Simplification = anti-fragility."
    )
    antifragile_rating: str = Field(
        description="Fragile (breaks under stress) / Robust (resists stress) / Antifragile (benefits from volatility and stress). Be specific about why."
    )
    taleb_verdict: str = Field(
        description="EMBRACE (antifragile + asymmetric upside) / NEUTRAL (robust, no edge) / AVOID (fragile + tail risk). Explain reasoning in 2-3 sentences."
    )


__all__ = ['TalebAnalysis']
