#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Perspectives Analyzer

Tests the multi-perspective analysis models without making API calls.
"""

from fintel.analysis.perspectives.models import (
    BuffettAnalysis,
    TalebAnalysis,
    ContrarianViewAnalysis,
    MultiPerspectiveAnalysis
)


def test_buffett_model():
    """Test Buffett analysis model."""
    print("\nTesting BuffettAnalysis model...")

    buffett = BuffettAnalysis(
        business_understanding="Simple subscription software business with predictable revenue",
        economic_moat="Network effects: value increases with each new user. Switching costs: integrated into customer workflows.",
        moat_rating="Wide",
        management_quality="A - Strong capital allocation, 15% insider ownership, consistent share buybacks at reasonable prices",
        pricing_power="Yes - raised prices 12% in 2023, volume decreased only 3%",
        return_on_invested_capital="ROIC: 35% (2019), 38% (2020), 42% (2021), 45% (2022), 47% (2023). Improving trend, well above 10% benchmark.",
        free_cash_flow_quality="FCF: $10B (2019) to $18B (2023), 12% CAGR. FCF/NI ratio: 95%. Growing faster than revenue (8%).",
        business_tailwinds=[
            "Cloud migration driving 25%+ enterprise SaaS spending growth",
            "Remote work increasing demand for collaboration tools",
            "Digital transformation accelerating across industries"
        ],
        intrinsic_value_estimate="Owner earnings: $20B. 10x multiple = $200B value. Market cap: $150B. Margin of safety: 33%.",
        buffett_verdict="BUY - Wide moat, excellent management, 33% margin of safety. High conviction long-term hold."
    )

    print("  Business understanding:", buffett.business_understanding[:50] + "...")
    print("  Moat rating:", buffett.moat_rating)
    print("  Verdict:", buffett.buffett_verdict[:50] + "...")
    print("  BuffettAnalysis model: OK")


def test_taleb_model():
    """Test Taleb analysis model."""
    print("\nTesting TalebAnalysis model...")

    taleb = TalebAnalysis(
        fragility_assessment="Debt/EBITDA: 0.5x (low risk). Can survive 50% revenue drop for 18 months with current cash. Fixed costs: 30% of revenue. Top customer: 8% of revenue (acceptable).",
        tail_risk_exposure=[
            "Regulatory: 10% probability, severe impact - Major market ban could cut revenue 20-30%",
            "Cyber attack: 5% probability, catastrophic - Data breach could destroy trust and trigger lawsuits",
            "Key person risk: 8% probability, moderate - CEO departure could cause 10-15% stock drop",
            "Tech disruption: 15% probability, severe - New competing technology could emerge",
            "Economic recession: 30% probability, moderate - Could reduce new customer acquisition 20-30%"
        ],
        optionality_and_asymmetry="Multiple expansion opportunities: international markets (untapped), adjacent products, M&A. Limited downside due to recurring revenue base. 10x upside possible, 50% downside maximum.",
        skin_in_the_game="CEO owns $500M stock (8% of company), CFO owns $100M (1.5%). Both buying on open market last 6 months. High alignment.",
        hidden_risks=[
            "Customer concentration in tech sector (60%) creates sector-specific risk",
            "Key technical employee attrition could slow product development",
            "Accounting: aggressive revenue recognition practices",
            "Supplier dependency on cloud infrastructure providers",
            "Patent portfolio weaker than competitors"
        ],
        lindy_effect="Business model: 8 years old (relatively new). SaaS model proven over 20+ years (Salesforce). Moderate Lindy effect.",
        dependency_chains="Critical: AWS infrastructure (99.99% SLA but single point). Key engineer team (5 people). Enterprise sales team (relationship-based).",
        via_negativa=[
            "Stop expanding into low-margin consulting services (distracts from core product)",
            "Stop acquisition of unprofitable startups (value destruction)",
            "Stop expensive marketing campaigns with poor ROI"
        ],
        antifragile_rating="Robust",
        taleb_verdict="NEUTRAL - Robust business model with good risk management, but lacks antifragile characteristics. No asymmetric upside from volatility."
    )

    print("  Fragility assessment:", taleb.fragility_assessment[:50] + "...")
    print("  Tail risks:", len(taleb.tail_risk_exposure))
    print("  Antifragile rating:", taleb.antifragile_rating)
    print("  Verdict:", taleb.taleb_verdict[:50] + "...")
    print("  TalebAnalysis model: OK")


def test_contrarian_model():
    """Test Contrarian analysis model."""
    print("\nTesting ContrarianViewAnalysis model...")

    contrarian = ContrarianViewAnalysis(
        consensus_view="Bear consensus: Company is overvalued at 40x earnings, growth slowing from 50% to 20%, competition intensifying.",
        consensus_wrong_because=[
            "Market focuses on headline growth rate but ignores improving unit economics - CAC payback dropped from 18 to 12 months",
            "Competition narrative ignores this company's network effects - each new customer makes platform more valuable",
            "Valuation comparison uses wrong peer group - should compare to infrastructure, not application software"
        ],
        hidden_strengths=[
            "Enterprise customer retention at 98%, indicating strong product-market fit",
            "Gross margin expanding (65% to 72%) despite price competition claims",
            "Technical moat: proprietary data advantage compounds over time",
            "Management owns 15% and buying aggressively at current prices"
        ],
        hidden_weaknesses=[
            "Customer concentration risk not disclosed - top 10 customers are 40% of revenue",
            "Stock-based comp is 25% of revenue (unsustainable)",
            "R&D spending declining as % of revenue (7% to 5%) - cutting muscle, not fat"
        ],
        misunderstood_metrics="Market obsesses over user growth (slowing). Should watch: revenue per customer (up 30%), gross retention (98%), customer payback period (improving). Market watches trailing indicators, not leading ones.",
        second_order_effects=[
            "If enterprise adoption increases → platform effects strengthen → harder for competitors to dislodge → pricing power increases",
            "If stock comp moderates → profitability inflects → FCF margins expand → valuation multiple compresses but total value increases",
            "If competitors fail → market consolidates → this company gains pricing power and market share"
        ],
        variant_perception="Market sees slowing growth company facing competition. Reality: company transitioning from land-grab to harvest phase with improving economics and strengthening moat. Next 18-24 months will show margin expansion and FCF inflection that market isn't modeling.",
        contrarian_rating="Strong Contrarian BUY"
    )

    print("  Consensus view:", contrarian.consensus_view[:50] + "...")
    print("  Reasons consensus wrong:", len(contrarian.consensus_wrong_because))
    print("  Hidden strengths:", len(contrarian.hidden_strengths))
    print("  Rating:", contrarian.contrarian_rating)
    print("  ContrarianViewAnalysis model: OK")


def test_multi_perspective_model():
    """Test combined multi-perspective model."""
    print("\nTesting MultiPerspectiveAnalysis model...")

    # Create component models (reusing from above)
    buffett = BuffettAnalysis(
        business_understanding="Test",
        economic_moat="Test",
        moat_rating="Wide",
        management_quality="A",
        pricing_power="Yes",
        return_on_invested_capital="35%",
        free_cash_flow_quality="High",
        business_tailwinds=["Tailwind 1"],
        intrinsic_value_estimate="$200B",
        buffett_verdict="BUY"
    )

    taleb = TalebAnalysis(
        fragility_assessment="Test",
        tail_risk_exposure=["Risk 1"],
        optionality_and_asymmetry="Test",
        skin_in_the_game="High",
        hidden_risks=["Risk 1"],
        lindy_effect="Test",
        dependency_chains="Test",
        via_negativa=["Stop 1"],
        antifragile_rating="Robust",
        taleb_verdict="NEUTRAL"
    )

    contrarian = ContrarianViewAnalysis(
        consensus_view="Test",
        consensus_wrong_because=["Reason 1"],
        hidden_strengths=["Strength 1"],
        hidden_weaknesses=["Weakness 1"],
        misunderstood_metrics="Test",
        second_order_effects=["Effect 1"],
        variant_perception="Test",
        contrarian_rating="Strong Contrarian BUY"
    )

    multi = MultiPerspectiveAnalysis(
        ticker="TEST",
        company_name="Test Company Inc",
        fiscal_year=2023,
        buffett_lens=buffett,
        taleb_lens=taleb,
        contrarian_lens=contrarian,
        key_insights=[
            "Wide moat business with excellent management and improving economics",
            "Robust (not antifragile) but well-positioned for volatility",
            "Market missing margin expansion story - variant perception opportunity",
            "33% margin of safety provides downside protection",
            "Near-term catalyst: FCF inflection in next 2-3 quarters"
        ],
        final_verdict="BUY with High conviction. This is a quality business (Buffett), with manageable risks (Taleb), trading at a discount due to market misunderstanding (Contrarian). Recommended position size: 5-8% of portfolio. Time horizon: 3-5 years. Would change mind if: (1) gross margins compress below 65%, (2) customer retention drops below 95%, (3) management insider selling accelerates."
    )

    print("  Ticker:", multi.ticker)
    print("  Company:", multi.company_name)
    print("  Year:", multi.fiscal_year)
    print("  Key insights:", len(multi.key_insights))
    print("  Final verdict:", multi.final_verdict[:50] + "...")
    print("  MultiPerspectiveAnalysis model: OK")

    # Test serialization
    data = multi.model_dump()
    print("  Serialization: OK")

    return True


def main():
    """Run all perspective model tests."""
    print("="*80)
    print("PERSPECTIVES ANALYZER MODEL TESTS")
    print("="*80)

    try:
        test_buffett_model()
        test_taleb_model()
        test_contrarian_model()
        test_multi_perspective_model()

        print("\n" + "="*80)
        print("ALL PERSPECTIVE MODEL TESTS PASSED")
        print("="*80)
        return 0

    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
