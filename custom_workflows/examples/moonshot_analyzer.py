#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Moonshot & Asymmetric Opportunity Finder Workflow.

Identifies high-conviction asymmetric opportunities: novel business models,
contrarian setups, and 10x potential hidden in SEC filings.

Designed to surface companies attempting the "impossible" that traditional
screens would filter out (like ASTS before its breakout).
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow


class AsymmetryAnalysis(BaseModel):
    """Quantified risk/reward asymmetry assessment."""
    
    bull_case_multiple: str = Field(
        description="If the thesis works, what's the realistic upside? "
        "Be specific: '10x in 3-5 years' or '3-4x in 18 months'. "
        "Explain the math: TAM size, market share assumptions, valuation comparison."
    )
    
    bear_case_outcome: str = Field(
        description="What's the downside if this fails? "
        "Total loss? 50% haircut? Explain the floor (cash per share, liquidation value, etc.)"
    )
    
    probability_assessment: str = Field(
        description="Based ONLY on evidence in filings, what's your probability estimate? "
        "What concrete milestones have been achieved? What remains unproven? "
        "Be honest about execution risk."
    )
    
    expected_value: str = Field(
        description="Quick expected value calc: (Upside × Probability) vs. (Downside × (1-Probability)). "
        "Does the math work? Is this 3:1 risk/reward or better?"
    )


class NoveltyAssessment(BaseModel):
    """Evaluation of how novel/contrarian this opportunity is."""
    
    business_model_novelty: Literal["Conventional", "Incrementally Better", "Novel", "Revolutionary"] = Field(
        description="How novel is the approach? "
        "Revolutionary = doing something never done before. "
        "Novel = proven elsewhere, new to this industry. "
        "Incrementally Better = faster/cheaper version of existing. "
        "Conventional = standard playbook."
    )
    
    what_sounds_impossible: str = Field(
        description="Describe in one sentence what this company is attempting that sounds crazy or impossible. "
        "If nothing sounds impossible, state: 'This is a conventional business opportunity.'"
    )
    
    why_market_doubts: str = Field(
        description="WHY is the market skeptical or assigning low probability? "
        "Technical difficulty? Regulatory risk? Unproven management? Capital intensity? "
        "If the market ISN'T skeptical, this probably isn't contrarian."
    )
    
    progress_evidence: List[str] = Field(
        description="Concrete evidence from filings that they're making progress on the impossible thing. "
        "Examples: partnerships with credible players, milestones achieved, "
        "customer pre-orders, successful pilots, regulatory approvals, etc. "
        "ONLY include evidence actually in the filing."
    )


class MoonshotAnalysisResult(BaseModel):
    """Schema for moonshot/asymmetric opportunity analysis."""

    quick_verdict: Literal[
        "PASS - Conventional Business",
        "PASS - Interesting but Low Asymmetry", 
        "INVESTIGATE - Asymmetric Setup",
        "PRIORITY - Moonshot with Evidence"
    ] = Field(
        description="Immediate classification. "
        "PRIORITY = Novel idea + evidence of progress + major asymmetry. "
        "INVESTIGATE = Some asymmetry but needs more research. "
        "PASS = Either conventional or no real asymmetry."
    )

    one_sentence_thesis: str = Field(
        description="The bull case in ONE sentence. "
        "Format: '[Company] is [doing impossible thing] and if successful could [outcome] because [TAM/opportunity].' "
        "Example: 'ASTS is building satellite-direct-to-phone connectivity and if successful could "
        "capture a $50B+ market by eliminating cell towers.'"
    )

    novelty: NoveltyAssessment = Field(
        description="How novel and contrarian is this opportunity?"
    )

    asymmetry: AsymmetryAnalysis = Field(
        description="Risk/reward asymmetry analysis"
    )

    market_misunderstanding: str = Field(
        description="What is the market getting wrong or not pricing in? "
        "Examples: Underestimating technical progress, Overestimating competition, "
        "Missing a pivot, Not seeing the optionality, Focusing on old business while new one builds. "
        "If market seems rationally priced, say so."
    )

    catalysts_and_timeline: str = Field(
        description="What needs to happen and WHEN for the thesis to play out? "
        "Extract specific dates, milestones, product launches, regulatory decisions from filings. "
        "Format: 'Q3 2025: Product launch. H1 2026: Expected profitability.'"
    )

    credibility_signals: List[str] = Field(
        description="Evidence that this isn't vaporware. "
        "Look for: partnerships with major companies, venture backing from credible firms, "
        "industry veterans on management team, paying customers (not just pilots), "
        "regulatory approvals, peer-reviewed publications, etc."
    )

    execution_risks: List[str] = Field(
        description="Top 3-5 reasons this could fail. Be brutally honest. "
        "Technology risk? Regulatory? Funding? Competition? Market timing?"
    )

    capital_situation: str = Field(
        description="Financial runway analysis. "
        "Cash on hand, burn rate, months of runway. "
        "Will they need to raise more? At what valuation? Is dilution a risk? "
        "Quote specific numbers from cash flow statement."
    )

    comparable_examples: str = Field(
        description="Has anyone done something similar before? "
        "Examples: 'SpaceX proved reusable rockets work. This is reusable [X].' "
        "Or: 'Tesla showed EVs can be premium. This is premium [Y].' "
        "If truly unprecedented, say so."
    )

    insider_alignment: str = Field(
        description="Are insiders buying or selling? How much do they own? "
        "Look for: recent insider purchases, founder ownership %, "
        "management compensation structure (cash vs. equity). "
        "Are they eating their own cooking?"
    )

    anti_consensus_score: int = Field(
        ge=0, le=100,
        description="How contrarian is this opportunity? "
        "0 = Consensus quality pick. "
        "100 = Market thinks it's impossible/worthless but evidence suggests otherwise. "
        "Score based on: short interest, analyst coverage (lack of = good), "
        "recent price action vs. fundamentals, sentiment in filings vs. stock performance."
    )

    moonshot_conviction: int = Field(
        ge=0, le=100,
        description="Overall conviction score for this as a moonshot opportunity. "
        "Combines: Novelty + Asymmetry + Evidence of Progress + Capital Runway. "
        "70+ = High conviction asymmetric bet. "
        "50-69 = Worth deeper research. "
        "Below 50 = Pass."
    )

    what_would_kill_thesis: str = Field(
        description="What single piece of evidence would make you immediately walk away? "
        "Be specific: 'Failed Phase 3 trial', 'Loss of key partnership', "
        "'Competitor launches first', 'Regulatory rejection', etc."
    )


class MoonshotOpportunityFinder(CustomWorkflow):
    """
    Identifies asymmetric, contrarian opportunities with 10x+ potential.
    Designed to find the next ASTS, not the next quality compounder.
    """

    name = "Moonshot & Asymmetric Opportunity Finder"
    description = "Find contrarian bets with 10x potential that traditional screens miss"
    icon = "🚀"
    min_years = 1
    category = "asymmetric"

    @property
    def prompt_template(self) -> str:
        return """
You are a contrarian venture investor searching for asymmetric opportunities in public markets.

You are NOT looking for quality compounders or Buffett-style moats. Those are fine, but BORING.

You ARE looking for companies attempting something that:
- Sounds impossible or at least very difficult
- Would be worth 10x+ if it works
- The market is skeptical about or ignoring
- Shows tangible evidence of progress in the filings

Think: ASTS before it 10x'd (satellite-direct-to-phone seemed impossible, but they were actually launching satellites).

### YOUR MENTAL FRAMEWORK

**STEP 1: THE SMELL TEST**

Read the business description and ask:
- Does this sound conventional or wild?
- Is this incremental improvement or 0-to-1 creation?
- Would most investors dismiss this as too risky/impossible?

If it's conventional, you can stop here and mark "PASS - Conventional Business."

**STEP 2: THE ASYMMETRY CHECK**

If it IS novel, now assess risk/reward:
- **Bull Case**: If this works, what's the upside? (Be specific: market size, market share, valuation)
- **Bear Case**: If this fails, what's the downside? (Cash per share? Liquidation value? Zero?)
- **Probability**: Based on evidence in filings, what's the odds? (20%? 40%? 60%?)
- **Math**: Does (Upside × Probability) >> (Downside × (1-Probability))?

Example: 
- Bull: 10x if they capture 5% of $50B market
- Bear: -60% (company has $3/share cash, stock at $8)
- Probability: 30% based on partnerships + successful pilots
- Math: (10x × 0.3) = 3.0 expected vs (0.6 × 0.7) = 0.42 expected → ~7:1 payoff

**STEP 3: THE EVIDENCE CHECK**

Don't just find moonshots. Find moonshots with PROOF OF LIFE:
- Partnerships with credible major players (AT&T, not "Joe's Telecom")
- Actual product milestones hit (not just promises)
- Customer traction (paying customers, not just pilots)
- Management from places where they've done hard things before
- Venture backing from top-tier firms
- Regulatory approvals or progress

**NO EVIDENCE = VAPORWARE. PASS.**

**STEP 4: THE MARKET MISUNDERSTANDING**

Why is this mispriced?
- Market underestimates technical progress?
- Market doesn't see the pivot?
- Company is pre-revenue so momentum investors ignore it?
- Short sellers attacking but fundamentals improving?
- Stuck in "old narrative" while new business builds?

If you can't articulate WHY the market is wrong, this isn't contrarian.

### SPECIFIC THINGS TO LOOK FOR IN THE FILING

**Novelty Signals:**
- Language like "first-of-its-kind", "pioneering", "unprecedented"
- Comparisons to other industries ("Uber for X", "SpaceX approach to Y")
- Heavy R&D spend relative to revenue (building something)
- Patents filed in new areas
- Regulatory pathways being created (not just followed)

**Progress Signals:**
- Named partnerships announced (check "Agreements" section)
- Milestones achieved vs. disclosed timelines
- Customer pre-orders or LOIs (Letters of Intent)
- Successful pilot programs or trials
- Regulatory approvals or submissions
- Manufacturing capacity coming online
- Hiring of industry veterans

**Capital Signals:**
- Cash on balance sheet vs. burn rate
- Recent funding rounds and from whom
- Insider buying (check beneficial ownership tables)
- Management compensation (equity-heavy = aligned)

**Contrarian Signals:**
- Recent stock decline despite operational progress
- High short interest
- Lack of analyst coverage (being ignored)
- Management discussing "misunderstood" narrative
- Guidance conservative vs. actual progress

### OUTPUT REQUIREMENTS

Be HONEST. Most companies are conventional. That's fine - mark them PASS and move on.

For the rare ones that ARE interesting:

1. **Start with the one-sentence thesis** - make it punchy and specific
2. **Explain what sounds impossible** - be clear about the audacious claim
3. **Show the evidence** - prove they're making real progress
4. **Do the math** - show the asymmetry quantitatively
5. **Identify the catalyst** - when does this thesis resolve?
6. **Admit the risks** - what could kill this?

### ANTI-PATTERNS (What NOT to do)

❌ Don't say "interesting company with solid fundamentals" - that's not a moonshot
❌ Don't use vague language like "potential upside" - quantify it
❌ Don't ignore capital constraints - no runway = no moonshot
❌ Don't recommend companies with no evidence of progress - that's gambling
❌ Don't be bullish on everything - be selective (90%+ should be PASS)

### TONE

Write like you're pitching this to a sophisticated investor who:
- Has heard 1000 pitches
- Hates vague bullshit
- Loves asymmetric bets with evidence
- Will call you out if the math doesn't work
- Respects intellectual honesty

Be specific. Be quantitative. Be skeptical. But when you DO find something real, be convicted.

---

Now analyze {ticker} for fiscal year {year}.

Remember: You're looking for the 1-in-100 company attempting something impossible with evidence it might actually work. Most companies will be PASS. That's the point.
"""

    @property
    def schema(self):
        return MoonshotAnalysisResult