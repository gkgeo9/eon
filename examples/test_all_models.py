#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive Model Test

Tests instantiation of all Pydantic models in fintel to ensure they work correctly.
"""

def test_basic_models():
    """Test basic fundamental analysis models."""
    print("\nTesting basic fundamental analysis models...")

    from fintel.analysis.fundamental.models.basic import (
        TenKAnalysis,
        FinancialHighlights
    )

    fh = FinancialHighlights(
        revenue="$100M",
        profit="$20M",
        cash_position="$50M cash"
    )

    analysis = TenKAnalysis(
        business_model="Test model",
        unique_value="Test value",
        key_strategies=["Strategy 1"],
        financial_highlights=fh,
        risks=["Risk 1"],
        management_quality="Good",
        innovation="Strong",
        competitive_position="Leader",
        esg_factors="Positive",
        key_takeaways=["Takeaway 1"]
    )

    assert analysis.business_model == "Test model"
    print("  TenKAnalysis: OK")


def test_success_factors_models():
    """Test success factors models (objective path)."""
    print("\nTesting success factors models (objective)...")

    from fintel.analysis.fundamental.models.success_factors import (
        CompanySuccessFactors,
        BusinessModel,
        StrategicShift,
        PerformanceFactor,
        FinancialMetrics,
        MarketPosition,
        ManagementAssessment,
        ResearchDevelopment,
        RiskMethodology,
        EvolvingRiskFactor,
        StakeholderImpacts,
        ForwardOutlook
    )

    # Create minimal nested models
    shift = StrategicShift(
        period="2020",
        change="Pivoted to subscriptions",
        measured_outcome="Revenue increased 50%"
    )

    biz_model = BusinessModel(
        core_operations="SaaS platform",
        strategic_shifts=[shift],
        operational_consistency="Maintained enterprise focus"
    )

    perf_factor = PerformanceFactor(
        factor="Network effects",
        business_impact="Increased retention",
        development="Strengthened over time"
    )

    fin_metrics = FinancialMetrics(
        revenue_analysis="Grew 30% CAGR",
        profit_analysis="Margins expanded",
        capital_decisions="Focused on R&D",
        financial_position=["Strong balance sheet"]
    )

    mkt_pos = MarketPosition(
        factor="Market share",
        durability="High",
        business_effect="Pricing power"
    )

    mgmt = ManagementAssessment(
        key_decisions=["Acquisition in 2020"],
        leadership_approach=["Data-driven"],
        governance_structure="Independent board"
    )

    rd = ResearchDevelopment(
        methodology="15% of revenue",
        notable_initiatives=["AI platform"],
        outcomes="3 new products launched"
    )

    risk_method = RiskMethodology(
        methodology="Quarterly risk assessment",
        identified_risks=["Competition"],
        vulnerabilities=["Key person dependency"]
    )

    evolving_risk = EvolvingRiskFactor(
        category="Regulatory",
        description="Data privacy",
        trajectory="Increasing scrutiny",
        potential_consequences="Fines possible",
        mitigation_efforts="Compliance team hired"
    )

    stakeholder = StakeholderImpacts(
        customer_impact="High satisfaction",
        investor_outcomes="Strong returns",
        broader_impacts="Carbon neutral"
    )

    outlook = ForwardOutlook(
        positive_factors=["Market tailwinds"],
        challenges=["Competition"],
        trajectory_assessment="Positive"
    )

    # Create full model
    factors = CompanySuccessFactors(
        company_name="Test Corp",
        period_analyzed=["2020", "2021", "2022"],
        business_model=biz_model,
        performance_factors=[perf_factor],
        financial_metrics=fin_metrics,
        market_position=[mkt_pos],
        management_assessment=mgmt,
        research_development=rd,
        risk_assessment=risk_method,
        evolving_risk_factors=[evolving_risk],
        stakeholder_impacts=stakeholder,
        distinguishing_characteristics=["First mover"],
        forward_outlook=outlook
    )

    assert factors.company_name == "Test Corp"
    print("  CompanySuccessFactors: OK")


def test_excellent_company_models():
    """Test excellent company factors models."""
    print("\nTesting excellent company factors models...")

    from fintel.analysis.fundamental.models.excellent_company_factors import (
        ExcellentCompanyFactors,
        KeyChange,
        BusinessEvolution,
        SuccessFactor,
        FinancialPerformance,
        CompetitiveAdvantage,
        ManagementExcellence,
        InnovationStrategy,
        RiskManagement,
        ValueCreation,
        FutureOutlook
    )

    # Create minimal nested models
    change = KeyChange(
        year="2020",
        change="Launched new product line",
        impact="Revenue increased 40%"
    )

    evolution = BusinessEvolution(
        core_model="SaaS subscription platform",
        key_changes=[change],
        strategic_consistency="Maintained enterprise focus throughout"
    )

    factor = SuccessFactor(
        factor="Customer focus",
        importance="Critical",
        evolution="Consistently strong"
    )

    fin_perf = FinancialPerformance(
        revenue_trends="30% CAGR over the period",
        profitability="Margins expanding from 15% to 28%",
        capital_allocation="Disciplined - focused on R&D and selective M&A",
        financial_strengths=["High ROIC", "Fortress balance sheet", "Strong FCF generation"]
    )

    advantage = CompetitiveAdvantage(
        advantage="Brand",
        sustainability="High - built over 10+ years",
        impact="Pricing power and customer loyalty (NPS of 75)"
    )

    mgmt = ManagementExcellence(
        key_decisions=["Acquisition in 2020", "Platform shift in 2018"],
        leadership_qualities=["Exceptional vision", "Strong execution", "Customer focus"],
        governance="Independent board with 80% independent directors"
    )

    innovation = InnovationStrategy(
        approach="Dual track - core product innovation (70%) plus emerging tech bets (30%)",
        key_innovations=["AI platform", "Mobile-first redesign", "Developer ecosystem"],
        results="3 new products launched, market leading NPS"
    )

    risk = RiskManagement(
        approach="Proactive risk assessment with quarterly reviews",
        key_risks_addressed=["Regulatory compliance", "Cybersecurity threats", "Key person dependency"],
        vulnerabilities=["International expansion risks", "Technology disruption"]
    )

    value = ValueCreation(
        customer_value="Saved customers 30% on average through platform efficiency",
        shareholder_value="500% total return, $50B market cap created",
        societal_value="Carbon neutral operations, strong employee satisfaction (4.5/5.0 Glassdoor)"
    )

    outlook = FutureOutlook(
        strengths_to_leverage=["Network effects", "Brand strength", "Technology platform"],
        challenges_to_address=["International expansion", "Competition from new entrants"],
        growth_potential="Strong - TAM expanding, positioned to capture share"
    )

    # Create full model
    excellent = ExcellentCompanyFactors(
        company_name="Excellent Corp",
        years_analyzed=["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"],
        business_evolution=evolution,
        success_factors=[factor],
        financial_performance=fin_perf,
        competitive_advantages=[advantage],
        management_excellence=mgmt,
        innovation_strategy=innovation,
        risk_management=risk,
        value_creation=value,
        future_outlook=outlook,
        unique_attributes=["Maintained growth while profitable"]
    )

    assert excellent.company_name == "Excellent Corp"
    print("  ExcellentCompanyFactors: OK")


def test_benchmark_models():
    """Test benchmark comparison models."""
    print("\nTesting benchmark comparison models...")

    from fintel.analysis.comparative.models.benchmark_comparison import (
        BenchmarkComparison,
        CompounderPotential,
        SuccessFactorAlignment,
        LeadershipAssessment,
        StrategicPositioningAssessment,
        FinancialPatternsAssessment,
        InnovationSystemsAssessment,
        OperationalExcellenceAssessment,
        CustomerRelationshipAssessment,
        CrossPatternRelationshipAssessment,
        PredictiveIndicatorsAssessment,
        FinalAssessment,
        InvestorConsiderations
    )

    # Create nested models
    potential = CompounderPotential(
        score=85,
        category="Strong Potential",
        summary="High alignment with compounders showing network effects and pricing power",
        distinctive_strengths=["Network effects", "Pricing power", "Brand moat"],
        critical_gaps=["International presence", "Innovation pace"],
        stage_context="Mature business transitioning to growth phase"
    )

    alignment = SuccessFactorAlignment(
        factor="Customer obsession",
        alignment="Strong",
        score=90,
        pattern_assessment="Deeply embedded in culture similar to top performers",
        maturity_level="Highly developed - NPS of 75, retention 97%",
        competitive_advantage="Strong differentiation through customer focus"
    )

    leadership = LeadershipAssessment(
        alignment="Strong",
        score=85,
        patterns_present=["Long-term orientation", "Capital allocation discipline", "Insider ownership"],
        patterns_missing=["Succession planning", "International experience"],
        long_term_orientation="High - demonstrated through consistent investment in R&D"
    )

    strategic = StrategicPositioningAssessment(
        alignment="Strong",
        score=88,
        approaches_present=["Wide moat from network effects", "Dominant niche position"],
        approaches_missing=["Geographic diversification", "Multiple product lines"],
        defensibility="High - network effects create strong barriers to entry"
    )

    financial = FinancialPatternsAssessment(
        alignment="Strong",
        score=90,
        patterns_present=["High ROIC", "Expanding margins", "Strong FCF generation"],
        patterns_missing=["Dividend policy", "Share buyback consistency"],
        capital_allocation_quality="Excellent - disciplined reinvestment in high-return opportunities"
    )

    innovation = InnovationSystemsAssessment(
        alignment="Moderate",
        score=75,
        systems_present=["Consistent R&D investment", "Technology platform"],
        systems_missing=["Innovation labs", "Venture arm"],
        adaptability_assessment="Good ability to innovate within core model"
    )

    operational = OperationalExcellenceAssessment(
        alignment="Strong",
        score=87,
        factors_present=["Execution consistency", "Scalability", "Quality metrics"],
        factors_missing=["Supply chain resilience", "Manufacturing innovation"],
        execution_quality="High reliability with best-in-class operational metrics"
    )

    customer = CustomerRelationshipAssessment(
        alignment="Strong",
        score=92,
        models_present=["High switching costs", "Customer success teams", "Net dollar retention"],
        models_missing=["Community building", "Customer advisory boards"],
        durability_assessment="Very durable - 97% retention indicates sticky relationships"
    )

    cross_pattern = CrossPatternRelationshipAssessment(
        alignment="Strong",
        score=84,
        relationships_present=["Customer focus drives innovation", "Financial discipline enables investment"],
        relationships_missing=["Leadership succession planning"],
        system_coherence="High - elements reinforce each other effectively"
    )

    predictive = PredictiveIndicatorsAssessment(
        alignment="Strong",
        score=86,
        indicators_present=["Increasing pricing power", "Expanding margins", "Customer expansion"],
        indicators_missing=["International momentum", "New product pipeline"],
        forward_indicators="Net dollar retention and margin expansion suggest future compounding"
    )

    final = FinalAssessment(
        verdict="Strong compounder candidate with high probability of sustained outperformance",
        probability_of_outperformance="High",
        reasoning="Multiple reinforcing factors align with top performer patterns",
        key_areas_to_monitor=["Customer retention", "Gross margin", "International expansion", "Innovation output"],
        meta_conclusions_alignment="Strong alignment with top 50 meta-conclusions"
    )

    investor = InvestorConsiderations(
        research_priorities=["Validate moat sustainability", "Assess management succession"],
        potential_catalysts=["International expansion success", "New product launches"],
        key_risks=["Competition intensification", "Key person dependency", "Execution missteps"]
    )

    comparison = BenchmarkComparison(
        company_name="Test Corp",
        analysis_date="2024-01-15",
        compounder_potential=potential,
        success_factor_alignment=[alignment],
        leadership_assessment=leadership,
        strategic_positioning_assessment=strategic,
        financial_patterns_assessment=financial,
        innovation_systems_assessment=innovation,
        operational_excellence_assessment=operational,
        customer_relationship_assessment=customer,
        cross_pattern_relationship_assessment=cross_pattern,
        predictive_indicators_assessment=predictive,
        final_assessment=final,
        investor_considerations=investor
    )

    assert comparison.company_name == "Test Corp"
    assert comparison.compounder_potential.score == 85
    print("  BenchmarkComparison: OK")


def test_contrarian_models():
    """Test contrarian scanner models."""
    print("\nTesting contrarian scanner models...")

    from fintel.analysis.comparative.models.contrarian_scores import (
        ContrarianAnalysis,
        ContrarianScores
    )

    scores = ContrarianScores(
        strategic_anomaly=85,
        asymmetric_resources=75,
        contrarian_positioning=90,
        cross_industry_dna=80,
        early_infrastructure=70,
        intellectual_capital=88
    )

    analysis = ContrarianAnalysis(
        ticker="TEST",
        company_name="Test Corp",
        overall_alpha_score=82,
        scores=scores,
        key_insights=[
            "Company making bold strategic pivot away from industry norms",
            "Leadership team has cross-industry experience from tech and manufacturing",
            "Building infrastructure for markets that don't exist yet"
        ],
        investment_thesis="Market misunderstands the business model transformation and undervalues intellectual property portfolio",
        risk_factors=["Execution risk on strategic pivot", "Market timing uncertainty", "Capital requirements"],
        catalyst_timeline="12-18 months for thesis validation through product launches and customer wins",
        confidence_level="HIGH"
    )

    assert analysis.ticker == "TEST"
    assert analysis.overall_alpha_score == 82
    assert analysis.scores.strategic_anomaly == 85
    print("  ContrarianAnalysis: OK")


def main():
    """Run all model tests."""
    print("="*80)
    print("COMPREHENSIVE MODEL TESTS")
    print("="*80)

    try:
        test_basic_models()
        test_success_factors_models()
        test_excellent_company_models()
        test_benchmark_models()
        test_contrarian_models()

        print("\n" + "="*80)
        print("ALL MODEL TESTS PASSED")
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
