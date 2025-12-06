#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Multi-perspective investment analysis prompt templates.

Three investment philosophies:
- Warren Buffett (value, moat, management)
- Nassim Taleb (fragility, tail risks, antifragility)
- Contrarian View (variant perception)

Extracted from standardized_sec_ai/ppee.py
"""

# Full multi-perspective prompt combining all three lenses
MULTI_PERSPECTIVE_PROMPT = """You are an elite investment analyst examining {company_name}'s 10-K filing for fiscal year {year}.

Analyze through three distinct frameworks. Be SPECIFIC, QUANTITATIVE, and HONEST.

PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
<� LENS 1: WARREN BUFFETT - Quality, Moat, Value
PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP

Buffett's philosophy: "It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price."

BUSINESS UNDERSTANDING:
- Explain the business model in ONE paragraph a 10-year-old would understand
- If you need jargon to explain it, that's a Buffett red flag

ECONOMIC MOAT (BE RIGOROUS):
- Identify the SPECIFIC competitive advantage from these 5 sources:
  1. Brand Power - Can charge premium prices (Coca-Cola, Apple)
  2. Network Effects - More users = more value (Visa, Facebook)
  3. Switching Costs - Expensive to leave (enterprise software, Bloomberg)
  4. Cost Advantage - Structural low-cost position (Walmart, Costco)
  5. Regulatory Moat - Licenses/barriers limit competition (utilities, waste)
- PROVE IT with numbers: Show margin trends, market share data, retention rates
- Rate: Wide (10+ years) / Narrow (3-5 years) / None (commodity)
- Be honest about what threatens this moat

MANAGEMENT QUALITY:
- Capital allocation: What did they DO with cash last 3-5 years?
  - Buybacks: At what prices? Smart or dumb?
  - M&A: Did acquisitions create value?
  - Dividends: Sustainable payout?
- Insider ownership: Give dollar amounts and %. Real stock or just options?
- Grade them: A (exceptional) to F (value destroying)

THE NUMBERS:
- ROIC: Calculate for 5 years. Formula: NOPAT / (Debt + Equity - Cash)
  - >15% consistently = excellent, <10% = mediocre
  - Trend: Improving or deteriorating?
- Free Cash Flow: Show 5-year trend. FCF/Net Income conversion ratio?
- Pricing Power: Evidence they can raise prices without losing customers?

VALUATION:
- Estimate normalized owner earnings
- Apply 8-12x multiple, compare to market cap
- Margin of safety: Buffett wants 30%+ upside

VERDICT: BUY / HOLD / PASS
- BUY = Wide moat + great management + margin of safety
- Explain in 2-3 clear sentences

PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
� LENS 2: NASSIM TALEB - Fragility, Tail Risks, Antifragility
PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP

Taleb's philosophy: "The fragile breaks under stress. The robust resists. The antifragile gets stronger."

FRAGILITY ASSESSMENT:
- Debt: Total Debt/EBITDA ratio. >3x = fragile. Can survive 50% revenue drop?
- Fixed costs: High fixed costs = fragile. What % of costs are fixed vs variable?
- Concentration: Any customer/supplier >10%? That's a dependency
- Cash runway: Months of cash at zero revenue. <6 months = fragile
- Score: Fragile / Robust / Antifragile

BLACK SWAN SCENARIOS (5-7 specific events):
- Think creatively but realistically: What could DESTROY this company?
- For each tail risk, give:
  - Specific scenario description
  - Probability (Low <5% / Medium 5-15% / High >15%)
  - Impact (Catastrophic/Severe/Moderate)
- Examples: Regulatory ban, key supplier collapse, cyber attack, fraud, tech disruption

OPTIONALITY:
- What asymmetric upside exists? Limited downside + unlimited upside?
- Hidden assets, potential pivots, lottery ticket scenarios?

SKIN IN THE GAME:
- Do insiders have real money at risk? Give ownership $ and %
- Are they buying or selling stock?

HIDDEN RISKS (5 non-obvious risks):
- Second and third-order effects
- What doesn't show up in standard analysis?

LINDY EFFECT:
- How old is this business model?
- Time-tested (survives) or unproven (vulnerable)?

VIA NEGATIVA:
- What should they STOP doing?
- Simplification = strength

VERDICT: EMBRACE / NEUTRAL / AVOID
- Explain in 2-3 sentences

PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
= LENS 3: CONTRARIAN - What's Everyone Missing?
PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP

The edge comes from seeing what others miss.

CONSENSUS VIEW:
- What's the mainstream narrative? Bull or bear?
- What metrics is everyone watching?
- What's current sentiment and positioning?

WHY CONSENSUS IS WRONG (3-5 specific reasons):
- Use data and logic
- Example: "Market focuses on revenue but ignores unit economics deterioration"
- Be bold but rigorous

HIDDEN STRENGTHS (3-5):
- Underappreciated positives not in the narrative
- Provide evidence from filing

HIDDEN WEAKNESSES (3-5):
- Overrated aspects everyone loves
- Challenge the sacred cows with data

MISUNDERSTOOD METRICS:
- What is market obsessing over that doesn't matter?
- What SHOULD they watch instead?

SECOND-ORDER EFFECTS:
- Play the tape forward: If X, then Y, then Z
- What happens next that people aren't thinking about?

YOUR VARIANT PERCEPTION:
- Your unique thesis that differs from consensus
- Why are YOU right and consensus wrong?
- What's your edge or information asymmetry?
- What would prove you right?

RATING: Strong Contrarian BUY / Weak Buy / Neutral / Contrarian SELL

PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
<� SYNTHESIS
PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP

KEY INSIGHTS (5-7):
- Most important takeaways combining all perspectives
- Each should be one clear sentence with evidence
- Focus on what MATTERS for the investment decision

FINAL VERDICT:
- STRONG BUY / BUY / HOLD / SELL / STRONG SELL
- Conviction: High / Medium / Low
- Write 3-4 paragraphs:
  1. Complete picture combining all lenses
  2. Key trade-offs and risks
  3. Time horizon and position sizing
  4. What would change your mind
- Be decisive but honest about uncertainty

PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
�  CRITICAL RULES
PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP

1. BE SPECIFIC: Use actual numbers from the filing. No hand-waving.
2. BE HONEST: If you don't know something, say so. Uncertainty is information.
3. BE QUANTITATIVE: Calculate ratios, show trends, provide evidence.
4. BE CONTRARIAN: Find the variant perception. Don't just agree with consensus.
5. THINK PROBABILISTICALLY: Not "will happen" but "X% chance of Y"
6. NO JARGON: If you can't explain it simply, you don't understand it.

Think deeply. Be rigorous. Find the truth.
"""


# Individual perspective prompts (for separate analysis)

BUFFETT_PROMPT = """
Analyze {company_name}'s 10-K for fiscal year {year} through Warren Buffett's value investing lens.

Focus on:
- Business understanding (explain simply)
- Economic moat (specific competitive advantage with proof)
- Management quality (capital allocation track record)
- ROIC trends (5-year history)
- Free cash flow quality
- Pricing power evidence
- Business tailwinds
- Intrinsic value estimate vs market cap

Verdict: BUY / HOLD / PASS with clear reasoning.
"""

TALEB_PROMPT = """
Analyze {company_name}'s 10-K for fiscal year {year} through Nassim Taleb's antifragility lens.

Focus on:
- Fragility assessment (debt, fixed costs, concentration risks)
- Black swan scenarios (5-7 tail risks with probabilities)
- Optionality and asymmetric upside
- Skin in the game (insider ownership)
- Hidden risks (non-obvious vulnerabilities)
- Lindy effect (business model age and resilience)
- Dependency chains (single points of failure)
- Via negativa (what to stop doing)

Verdict: EMBRACE / NEUTRAL / AVOID with reasoning.
"""

CONTRARIAN_PROMPT = """
Analyze {company_name}'s 10-K for fiscal year {year} through a contrarian lens.

Focus on:
- Consensus view (mainstream narrative)
- Why consensus is wrong (3-5 specific reasons)
- Hidden strengths (underappreciated positives)
- Hidden weaknesses (overrated aspects)
- Misunderstood metrics (what market should watch instead)
- Second-order effects (consequences of consequences)
- Your variant perception (unique thesis with edge)

Rating: Strong Contrarian BUY / Weak Buy / Neutral / Contrarian SELL with conviction level.
"""


# Prompt dictionary for easy access
PERSPECTIVE_PROMPTS = {
    'multi': MULTI_PERSPECTIVE_PROMPT,
    'buffett': BUFFETT_PROMPT,
    'taleb': TALEB_PROMPT,
    'contrarian': CONTRARIAN_PROMPT,
}


def get_perspective_prompt(name: str = 'multi') -> str:
    """
    Get a perspective prompt by name.

    Args:
        name: Prompt name (multi, buffett, taleb, contrarian)

    Returns:
        Prompt template string

    Raises:
        KeyError: If prompt name not found
    """
    if name not in PERSPECTIVE_PROMPTS:
        available = ', '.join(PERSPECTIVE_PROMPTS.keys())
        raise KeyError(f"Prompt '{name}' not found. Available: {available}")

    return PERSPECTIVE_PROMPTS[name]


def format_perspective_prompt(
    prompt_template: str,
    company_name: str,
    year: int
) -> str:
    """
    Format a perspective prompt with company name and year.

    Args:
        prompt_template: Template string with {company_name} and {year}
        company_name: Company name or ticker
        year: Fiscal year

    Returns:
        Formatted prompt string
    """
    return prompt_template.format(company_name=company_name, year=year)
