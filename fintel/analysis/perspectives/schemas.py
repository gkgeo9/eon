#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pydantic models for multi-perspective investment analysis.
Extracted from standardized_sec_ai/ppee.py

Three investment lenses:
- Warren Buffett (value, moat, management)
- Nassim Taleb (fragility, tail risks, optionality)
- Contrarian View (what everyone's missing)
"""

from typing import List
from pydantic import BaseModel, Field


class BuffettAnalysis(BaseModel):
    """Warren Buffett's Investment Philosophy"""
    business_understanding: str = Field(
        description="Explain this business in one simple paragraph. What do they actually sell? How do they make money? If you can't explain it simply, that's a red flag."
    )
    economic_moat: str = Field(
        description="What is their SPECIFIC competitive advantage? Choose from: Brand Power (pricing premium), Network Effects (more users = more value), Switching Costs (expensive to leave), Cost Advantage (structural), Regulatory Moat (licenses/barriers). PROVE it with numbers: margins vs competitors, market share trends, customer retention rates. Don't be vague."
    )
    moat_rating: str = Field(
        description="Wide (10+ years sustainable) / Narrow (3-5 years) / None (commodity). Be honest about durability."
    )
    management_quality: str = Field(
        description="Capital allocation track record over 3-5 years: What did they do with excess cash (buybacks, M&A, dividends)? Did those decisions create value? Insider ownership: Do executives have meaningful stock ownership (not just options)? Give dollar amounts and percentages. Grade them A-F."
    )
    pricing_power: str = Field(
        description="The ultimate test: Can they raise prices 10% without losing 10% of customers? Show evidence from the filing - have they raised prices? What happened to volume? Look for pricing strategy mentions, competitive dynamics, margin trends."
    )
    return_on_invested_capital: str = Field(
        description="Calculate ROIC = NOPAT / (Debt + Equity - Cash) for last 5 years if possible. Compare to 10% benchmark. Is it improving (compounding machine) or declining (value destruction)? Show the trend with numbers."
    )
    free_cash_flow_quality: str = Field(
        description="FCF = Operating Cash Flow - Capex. Show 5-year growth rate. Calculate FCF conversion ratio (FCF/Net Income - should be >80%). Is FCF growing faster than revenue? That's operating leverage. Be specific with dollars."
    )
    business_tailwinds: List[str] = Field(
        description="3-5 secular trends (10+ year duration) that benefit this business. Be specific - not 'digitalization' but 'enterprise cloud migration driving 20%+ annual SaaS spending growth'. Show how THIS company benefits."
    )
    intrinsic_value_estimate: str = Field(
        description="Estimate normalized owner earnings (Net Income + D&A - Maintenance Capex). Apply 8-12x multiple. Compare to current market cap. Calculate margin of safety: (Intrinsic Value - Market Cap) / Market Cap. Buffett wants 30%+ upside."
    )
    buffett_verdict: str = Field(
        description="BUY (wide moat + great management + 30% margin of safety) / HOLD (good business, fair price) / PASS (no moat, bad management, or overvalued). Explain in 2-3 sentences with clear logic."
    )


class TalebAnalysis(BaseModel):
    """Nassim Taleb's Anti-Fragile Framework"""
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


class ContrarianAnalysis(BaseModel):
    """The Contrarian View - What's Everyone Missing?"""
    consensus_view: str = Field(
        description="What is the mainstream Wall Street narrative on this company? Bull consensus (everyone loves it) or bear consensus (everyone hates it)? What's the prevailing story? What metrics is everyone watching? Be specific about current sentiment and positioning."
    )
    consensus_wrong_because: List[str] = Field(
        description="3-5 SPECIFIC reasons why consensus is wrong. Use data and logic. Examples: 'Market focuses on revenue growth but ignores deteriorating unit economics' or 'Everyone assumes competition but moat is actually widening - here's proof'. Be bold but rigorous."
    )
    hidden_strengths: List[str] = Field(
        description="3-5 underappreciated positives not in the mainstream narrative. What are people missing? Hidden assets, undervalued segments, management changes, strategic pivots, etc. Provide evidence from the filing."
    )
    hidden_weaknesses: List[str] = Field(
        description="3-5 overlooked negatives. What risks is the market ignoring? Be honest - contrarian doesn't mean blindly optimistic. What could go wrong that others aren't pricing in?"
    )
    variant_perception: str = Field(
        description="What is YOUR unique insight that differs from consensus? Not just 'I disagree' but 'Here's what I see that others don't, and here's the evidence'. This is your investment edge. Be specific and data-driven."
    )
    market_pricing: str = Field(
        description="What is the market currently pricing in? Use forward P/E, EV/EBITDA, growth assumptions. Compare to historical multiples and peers. Is the market pricing in perfection or disaster? What would need to happen to justify current price?"
    )
    catalyst_timeline: List[str] = Field(
        description="3-5 specific events/catalysts that could prove your thesis right (or wrong) within 6-24 months. Be specific: earnings beats, product launches, management changes, regulatory decisions, etc. What would make you change your mind?"
    )
    positioning: str = Field(
        description="What's the crowded trade? Is everyone long or short? Institutional ownership levels? Recent fund flows? Contrarian opportunities exist when positioning is extreme. Describe current positioning and how it creates opportunity or risk."
    )
    contrarian_verdict: str = Field(
        description="STRONG BUY (high conviction contrarian), BUY (lean contrarian), NEUTRAL (no edge), AVOID (consensus is right). Explain your conviction level and why in 2-3 sentences."
    )
    conviction_level: str = Field(
        description="Low / Medium / High. How confident are you in this contrarian thesis? What's your edge? What could prove you wrong?"
    )


class SimplifiedAnalysis(BaseModel):
    """
    Synthesized multi-perspective analysis combining all three lenses.
    """
    buffett: BuffettAnalysis = Field(description="Value investing perspective")
    taleb: TalebAnalysis = Field(description="Antifragility perspective")
    contrarian: ContrarianAnalysis = Field(description="Contrarian perspective")
    synthesis: str = Field(
        description="5-7 key insights synthesizing all three perspectives. What are the most important takeaways?"
    )
    final_verdict: str = Field(
        description="Overall investment recommendation based on all three perspectives. Include conviction level (High/Medium/Low) and reasoning."
    )


# Export all models
__all__ = [
    'BuffettAnalysis',
    'TalebAnalysis',
    'ContrarianAnalysis',
    'SimplifiedAnalysis',
]
