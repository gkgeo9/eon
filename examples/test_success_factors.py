#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Success Factors Models

Tests both excellent company and objective company analysis models.
"""

from fintel.analysis.fundamental.models.success_factors import (
    CompanySuccessFactors,
    PerformanceFactor,
    FinancialMetric,
    MarketPositionElement
)
from fintel.analysis.fundamental.models.excellent_company_factors import (
    ExcellentCompanyFactors,
    SuccessFactor,
    CompetitiveAdvantage,
    ManagementExcellence
)


def test_objective_company_factors():
    """Test objective company success factors model."""
    print("\nTesting CompanySuccessFactors model (Objective Path)...")

    factors = CompanySuccessFactors(
        company_name="Test Corporation",
        period_analyzed="2015-2023 (9 years)",
        business_model=(
            "Operates platform connecting buyers and sellers. "
            "Revenue from transaction fees (60%), subscriptions (25%), and advertising (15%). "
            "Asset-light model with high operating leverage."
        ),
        performance_factors=[
            PerformanceFactor(
                factor="Network effects",
                business_impact="More sellers attract more buyers, which attracts more sellers. Created flywheel effect.",
                development="Started weak (2015), reached critical mass (2018), now self-reinforcing (2023)"
            ),
            PerformanceFactor(
                factor="Technology infrastructure",
                business_impact="Scalable platform handles 10x transaction volume with minimal marginal cost increase",
                development="Initially unstable, rebuilt core system (2017-2019), now industry-leading reliability"
            )
        ],
        financial_metrics=[
            FinancialMetric(
                metric="Revenue",
                values="$50M (2015) → $500M (2023)",
                trend="35% CAGR, accelerating in recent years"
            ),
            FinancialMetric(
                metric="Gross Margin",
                values="45% (2015) → 72% (2023)",
                trend="Steady expansion due to operating leverage"
            ),
            FinancialMetric(
                metric="Operating Margin",
                values="-20% (2015) → 15% (2023)",
                trend="Inflection to profitability in 2020"
            )
        ],
        market_position=[
            MarketPositionElement(
                aspect="Market share",
                current_state="35% of addressable market (up from 5% in 2015)",
                competitive_context="Top 2 player, main competitor at 40%"
            ),
            MarketPositionElement(
                aspect="Customer base",
                current_state="2M active users, 85% retention rate",
                competitive_context="Industry average retention: 65%"
            )
        ],
        distinguishing_characteristics=[
            "First-mover advantage in vertical marketplace",
            "Superior user experience backed by NPS of 72 vs industry 45",
            "Highly engaged community creating user-generated content",
            "Data advantage: 8 years of transaction data informing recommendations"
        ],
        management_assessment=(
            "CEO (founder, 8 years tenure) demonstrated ability to pivot business model in 2018. "
            "Strong technical background. CFO (hired 2020) brought financial discipline. "
            "Insider ownership: 25%. Recent stock sales minimal. "
            "Capital allocation improving: shifted from growth-at-all-costs to profitable growth."
        ),
        research_development=(
            "R&D spend: 15% of revenue (stable). Focus areas: machine learning for recommendations, "
            "fraud detection, mobile experience. Patent portfolio: 45 patents. "
            "Technical team: 200 engineers (40% of workforce). "
            "Innovation pace moderate but focused on core platform improvements."
        ),
        forward_outlook=(
            "Opportunity: International expansion (currently 90% US). "
            "Risks: Regulatory scrutiny of platform business models, potential entrant with deeper pockets. "
            "Financial trajectory: Expect margin expansion to continue as platform scales. "
            "Strategic positioning: Well-positioned if market continues consolidating."
        )
    )

    print("  Company:", factors.company_name)
    print("  Period:", factors.period_analyzed)
    print("  Performance factors:", len(factors.performance_factors))
    print("  Financial metrics:", len(factors.financial_metrics))
    print("  Market position elements:", len(factors.market_position))
    print("  Distinguishing characteristics:", len(factors.distinguishing_characteristics))

    # Test serialization
    data = factors.model_dump()
    assert data['company_name'] == "Test Corporation"
    print("  Serialization: OK")
    print("  CompanySuccessFactors model: OK")


def test_excellent_company_factors():
    """Test excellent company success factors model."""
    print("\nTesting ExcellentCompanyFactors model (Excellence Path)...")

    factors = ExcellentCompanyFactors(
        company_name="Excellent Tech Inc",
        years_analyzed=["2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"],
        business_evolution=(
            "2014-2016: Single product company focused on enterprise software. "
            "2017-2019: Expanded into platform play, launched developer ecosystem. "
            "2020-2023: Became multi-product company with cloud infrastructure, applications, and services. "
            "Revenue mix shifted from 100% licenses to 70% subscriptions. "
            "Maintained focus on enterprise customers throughout evolution."
        ),
        success_factors=[
            SuccessFactor(
                factor="Customer obsession",
                importance="Foundational - drove product decisions and created competitive moat",
                evolution="Always present but formalized into company processes (2018). Created customer advisory boards, weekly executive customer calls, NPS tracking."
            ),
            SuccessFactor(
                factor="Technical excellence",
                importance="Critical differentiator - attracted top talent and created product superiority",
                evolution="Invested 20-25% of revenue in R&D consistently. Built reputation as engineering-first culture. 15 patents filed annually."
            ),
            SuccessFactor(
                factor="Ecosystem strategy",
                importance="Created network effects and locked in customers",
                evolution="Launched in 2017 with 50 partners. Grew to 5,000+ partners by 2023. Partners driving 40% of new customer acquisition."
            )
        ],
        financial_performance=(
            "Revenue CAGR: 42% (2014-2023). "
            "Gross margin: 75-82% (best-in-class). "
            "Operating margin: Expanded from 5% to 28%. "
            "FCF margin: 25% (exceptional). "
            "ROIC: 35%+ consistently. "
            "Balance sheet: Net cash position, $10B+ cash. "
            "Key insight: Maintained pricing power throughout - never competed on price."
        ),
        competitive_advantages=[
            CompetitiveAdvantage(
                advantage="Switching costs",
                sustainability="High - deeply integrated into customer workflows. Average customer uses 8+ products.",
                evidence="Customer retention: 97% in enterprise segment. Expansion revenue: 130% net dollar retention."
            ),
            CompetitiveAdvantage(
                advantage="Brand and trust",
                sustainability="Very high - built over 10+ years, reinforced by customer success",
                evidence="Net Promoter Score: 75 (industry average: 30). Win rate vs competitors: 65%. Premium pricing: 20-30% above alternatives."
            ),
            CompetitiveAdvantage(
                advantage="Data and AI",
                sustainability="Increasing - compounds over time as data accumulates",
                evidence="10+ years of customer data. AI models improve recommendation accuracy by 3-5% annually. Proprietary dataset impossible to replicate."
            )
        ],
        management_excellence=ManagementExcellence(
            leadership_quality="Exceptional - founder-led with long-term orientation",
            capital_allocation="Disciplined - focused on organic R&D and selective M&A. Avoided large debt-financed acquisitions.",
            organizational_culture="Engineering-first, customer-obsessed, high-performance. Glassdoor: 4.5/5.0.",
            succession_planning="Strong bench - several executives could step into CEO role. Low turnover in senior leadership."
        ),
        innovation_strategy=(
            "Dual approach: Core product innovation (70% of R&D) + emerging tech bets (30% of R&D). "
            "Acquisitions: 2-3 small tuck-ins per year ($50-200M) for talent and technology. "
            "Internal innovation: Quarterly hackathons, 20% time for engineers, research lab for 3-5 year bets. "
            "Fast follower on some technologies, pioneer on others. Pragmatic, not dogmatic."
        ),
        risk_management=(
            "Identified risks: Regulatory (data privacy), technological disruption, key person dependency. "
            "Mitigation: Proactive compliance investments ($100M annually), continuous technology refresh cycles, "
            "distributed decision-making to reduce key person risk. Conservative accounting and disclosure. "
            "Stress tested: Maintained profitability through 2020 downturn (20% growth vs 35% trend)."
        ),
        value_creation=(
            "Stock return: 28% CAGR (2014-2023) vs S&P 500 12%. "
            "Market cap: $2B to $50B. "
            "Value creation driven by: Revenue growth (40%), margin expansion (30%), multiple expansion (30%). "
            "Shareholder value: $50B+ created. Minimal dilution (1% annually). "
            "Dividend: Initiated small dividend (0.5% yield) in 2022 while maintaining growth investments."
        ),
        future_outlook=(
            "TAM expansion: Core market $50B → $200B by 2030 (cloud migration). "
            "Positioning: Well-positioned as incumbent with superior product. "
            "Risks: Potential antitrust scrutiny, new entrants from adjacent markets. "
            "Expected trajectory: Deceleration to 20-25% growth but margin expansion should offset. "
            "Strategic options: International expansion, move down-market to SMB, vertical-specific solutions."
        ),
        unique_attributes=[
            "Maintained high growth (40%+) while achieving profitability",
            "Built ecosystem that creates defensible moat",
            "Avoided major strategic missteps over 10-year period",
            "Attracted and retained top-tier talent in competitive market",
            "Generated substantial shareholder value with minimal dilution",
            "Balanced growth investments with financial discipline"
        ]
    )

    print("  Company:", factors.company_name)
    print("  Years analyzed:", len(factors.years_analyzed))
    print("  Success factors:", len(factors.success_factors))
    print("  Competitive advantages:", len(factors.competitive_advantages))
    print("  Unique attributes:", len(factors.unique_attributes))

    # Test serialization
    data = factors.model_dump()
    assert data['company_name'] == "Excellent Tech Inc"
    print("  Serialization: OK")
    print("  ExcellentCompanyFactors model: OK")


def main():
    """Run all success factors model tests."""
    print("="*80)
    print("SUCCESS FACTORS MODEL TESTS")
    print("="*80)

    try:
        test_objective_company_factors()
        test_excellent_company_factors()

        print("\n" + "="*80)
        print("ALL SUCCESS FACTORS MODEL TESTS PASSED")
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
