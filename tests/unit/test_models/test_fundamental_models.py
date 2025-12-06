#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for fundamental analysis Pydantic models.
"""

import pytest
from pydantic import ValidationError

from fintel.analysis.fundamental.models.basic import (
    FinancialHighlights,
    TenKAnalysis,
    RevenueSegment,
    GeographicBreakdown,
)
from fintel.analysis.fundamental.models.success_factors import (
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


class TestFinancialHighlights:
    """Test FinancialHighlights model validation."""

    def test_valid_financial_highlights(self):
        """Test creating valid FinancialHighlights."""
        highlights = FinancialHighlights(
            total_revenue="$100M",
            net_income="$20M",
            operating_margin="20%",
            debt_to_equity="0.5",
            free_cash_flow="$15M"
        )
        assert highlights.total_revenue == "$100M"
        assert highlights.net_income == "$20M"

    def test_financial_highlights_serialization(self):
        """Test JSON serialization."""
        highlights = FinancialHighlights(
            total_revenue="$100M",
            net_income="$20M",
            operating_margin="20%",
            debt_to_equity="0.5",
            free_cash_flow="$15M"
        )
        data = highlights.model_dump()
        assert data["total_revenue"] == "$100M"

        # Test deserialization
        reconstructed = FinancialHighlights(**data)
        assert reconstructed == highlights


class TestRevenueSegment:
    """Test RevenueSegment model validation."""

    def test_valid_revenue_segment(self):
        """Test creating valid RevenueSegment."""
        segment = RevenueSegment(
            name="Cloud Services",
            revenue="$50M",
            percentage="50%",
            growth="20% YoY"
        )
        assert segment.name == "Cloud Services"
        assert segment.revenue == "$50M"

    def test_revenue_segment_serialization(self):
        """Test JSON serialization."""
        segment = RevenueSegment(
            name="Cloud Services",
            revenue="$50M",
            percentage="50%",
            growth="20% YoY"
        )
        data = segment.model_dump()
        reconstructed = RevenueSegment(**data)
        assert reconstructed == segment


class TestGeographicBreakdown:
    """Test GeographicBreakdown model validation."""

    def test_valid_geographic_breakdown(self):
        """Test creating valid GeographicBreakdown."""
        geo = GeographicBreakdown(
            region="North America",
            revenue="$60M",
            percentage="60%"
        )
        assert geo.region == "North America"
        assert geo.revenue == "$60M"

    def test_geographic_breakdown_serialization(self):
        """Test JSON serialization."""
        geo = GeographicBreakdown(
            region="North America",
            revenue="$60M",
            percentage="60%"
        )
        data = geo.model_dump()
        reconstructed = GeographicBreakdown(**data)
        assert reconstructed == geo


class TestTenKAnalysis:
    """Test TenKAnalysis model validation."""

    def test_minimal_tenk_analysis(self):
        """Test creating TenKAnalysis with minimal required fields."""
        highlights = FinancialHighlights(
            total_revenue="$100M",
            net_income="$20M",
            operating_margin="20%",
            debt_to_equity="0.5",
            free_cash_flow="$15M"
        )

        analysis = TenKAnalysis(
            company_name="Test Corp",
            fiscal_year=2024,
            business_description="A test company",
            key_products_services=["Product A", "Service B"],
            financial_highlights=highlights,
            business_model="B2B SaaS",
            revenue_streams=["Subscriptions", "Professional services"],
            key_risks=["Market competition", "Regulatory changes"],
            opportunities=["Market expansion", "New products"],
            competitive_advantages=["Strong brand", "Technology moat"],
            management_discussion="Strong leadership team",
            notable_changes=["Acquired Company X"],
            forward_looking="Expected 20% growth"
        )

        assert analysis.company_name == "Test Corp"
        assert analysis.fiscal_year == 2024
        assert len(analysis.key_products_services) == 2

    def test_tenk_analysis_with_segments(self):
        """Test TenKAnalysis with revenue segments."""
        highlights = FinancialHighlights(
            total_revenue="$100M",
            net_income="$20M",
            operating_margin="20%",
            debt_to_equity="0.5",
            free_cash_flow="$15M"
        )

        segments = [
            RevenueSegment(
                name="Cloud",
                revenue="$50M",
                percentage="50%",
                growth="20% YoY"
            ),
            RevenueSegment(
                name="On-Premise",
                revenue="$50M",
                percentage="50%",
                growth="5% YoY"
            )
        ]

        analysis = TenKAnalysis(
            company_name="Test Corp",
            fiscal_year=2024,
            business_description="A test company",
            key_products_services=["Product A"],
            financial_highlights=highlights,
            business_model="B2B SaaS",
            revenue_streams=["Subscriptions"],
            key_risks=["Competition"],
            opportunities=["Expansion"],
            competitive_advantages=["Brand"],
            management_discussion="Strong leadership",
            notable_changes=["Acquisition"],
            forward_looking="Growth expected",
            revenue_segments=segments
        )

        assert len(analysis.revenue_segments) == 2
        assert analysis.revenue_segments[0].name == "Cloud"

    def test_tenk_analysis_serialization(self):
        """Test complete serialization/deserialization."""
        highlights = FinancialHighlights(
            total_revenue="$100M",
            net_income="$20M",
            operating_margin="20%",
            debt_to_equity="0.5",
            free_cash_flow="$15M"
        )

        analysis = TenKAnalysis(
            company_name="Test Corp",
            fiscal_year=2024,
            business_description="A test company",
            key_products_services=["Product A"],
            financial_highlights=highlights,
            business_model="B2B SaaS",
            revenue_streams=["Subscriptions"],
            key_risks=["Competition"],
            opportunities=["Expansion"],
            competitive_advantages=["Brand"],
            management_discussion="Strong leadership",
            notable_changes=["Acquisition"],
            forward_looking="Growth expected"
        )

        # Serialize to dict
        data = analysis.model_dump()
        assert data["company_name"] == "Test Corp"
        assert data["fiscal_year"] == 2024

        # Deserialize back
        reconstructed = TenKAnalysis(**data)
        assert reconstructed == analysis


class TestStrategicShift:
    """Test StrategicShift model validation."""

    def test_valid_strategic_shift(self):
        """Test creating valid StrategicShift."""
        shift = StrategicShift(
            period="2020-2022",
            change="Pivoted from hardware to software services",
            measured_outcome="Revenue from software grew from 20% to 60% of total"
        )
        assert shift.period == "2020-2022"
        assert "hardware to software" in shift.change

    def test_strategic_shift_serialization(self):
        """Test JSON serialization."""
        shift = StrategicShift(
            period="2020-2022",
            change="Pivoted from hardware to software services",
            measured_outcome="Revenue from software grew from 20% to 60% of total"
        )
        data = shift.model_dump()
        reconstructed = StrategicShift(**data)
        assert reconstructed == shift


class TestBusinessModel:
    """Test BusinessModel model validation."""

    def test_valid_business_model(self):
        """Test creating valid BusinessModel."""
        shifts = [
            StrategicShift(
                period="2020-2022",
                change="Pivoted to SaaS",
                measured_outcome="Recurring revenue increased 200%"
            )
        ]

        model = BusinessModel(
            core_operations="B2B SaaS platform providing analytics",
            strategic_shifts=shifts,
            operational_consistency="Maintained focus on enterprise customers"
        )

        assert "B2B SaaS" in model.core_operations
        assert len(model.strategic_shifts) == 1

    def test_business_model_with_no_shifts(self):
        """Test BusinessModel with empty strategic shifts."""
        model = BusinessModel(
            core_operations="Traditional manufacturing",
            strategic_shifts=[],
            operational_consistency="No major changes in 10 years"
        )

        assert len(model.strategic_shifts) == 0


class TestPerformanceFactor:
    """Test PerformanceFactor model validation."""

    def test_valid_performance_factor(self):
        """Test creating valid PerformanceFactor."""
        factor = PerformanceFactor(
            factor="Network effects",
            evidence="DAU grew 150% while CAC decreased 30%",
            impact="High - created defensible moat"
        )

        assert factor.factor == "Network effects"
        assert "150%" in factor.evidence


class TestFinancialMetrics:
    """Test FinancialMetrics model validation."""

    def test_valid_financial_metrics(self):
        """Test creating valid FinancialMetrics."""
        metrics = FinancialMetrics(
            revenue_analysis="10-year CAGR of 25%, with consistent growth",
            profitability_trends="Margins expanded from 15% to 35%",
            cash_flow_patterns="FCF positive since 2018, growing 40% annually",
            capital_allocation="70% reinvested in R&D, 30% to shareholders"
        )

        assert "CAGR of 25%" in metrics.revenue_analysis
        assert "35%" in metrics.profitability_trends


class TestMarketPosition:
    """Test MarketPosition model validation."""

    def test_valid_market_position(self):
        """Test creating valid MarketPosition."""
        position = MarketPosition(
            market_share="25% of addressable market, #2 position",
            competitive_advantages=["Technology moat", "Brand recognition"],
            barriers_to_entry="High - requires 5+ years to build comparable platform"
        )

        assert "25%" in position.market_share
        assert len(position.competitive_advantages) == 2


class TestManagementAssessment:
    """Test ManagementAssessment model validation."""

    def test_valid_management_assessment(self):
        """Test creating valid ManagementAssessment."""
        assessment = ManagementAssessment(
            key_decisions=[
                "Acquired competitor in 2020 for $500M",
                "Exited low-margin business in 2021"
            ],
            capital_allocation_quality="Excellent - high ROIC of 25%+",
            leadership_stability="CEO tenure 12 years, low executive turnover",
            strategic_clarity="Clear focus on enterprise cloud migration"
        )

        assert len(assessment.key_decisions) == 2
        assert "25%" in assessment.capital_allocation_quality


class TestResearchDevelopment:
    """Test ResearchDevelopment model validation."""

    def test_valid_research_development(self):
        """Test creating valid ResearchDevelopment."""
        rd = ResearchDevelopment(
            innovation_approach="Internal R&D + strategic acquisitions",
            rd_investment_trends="R&D spend grew from 15% to 22% of revenue",
            patent_portfolio="450 patents, 200 pending, key in AI/ML",
            technology_evolution="Migrated to microservices architecture"
        )

        assert "22%" in rd.rd_investment_trends
        assert "450 patents" in rd.patent_portfolio


class TestRiskMethodology:
    """Test RiskMethodology model validation."""

    def test_valid_risk_methodology(self):
        """Test creating valid RiskMethodology."""
        methodology = RiskMethodology(
            category="Market Risk",
            specific_risks=["Increased competition from Big Tech"],
            mitigation_strategies=["Differentiation through vertical integration"],
            effectiveness="Moderate - maintained market share despite new entrants"
        )

        assert methodology.category == "Market Risk"
        assert len(methodology.specific_risks) == 1


class TestEvolvingRiskFactor:
    """Test EvolvingRiskFactor model validation."""

    def test_valid_evolving_risk_factor(self):
        """Test creating valid EvolvingRiskFactor."""
        risk = EvolvingRiskFactor(
            risk="Regulatory compliance costs",
            evolution="Increased from $5M to $20M over 5 years",
            current_status="Stabilized - compliance framework established"
        )

        assert "Regulatory" in risk.risk
        assert "$20M" in risk.evolution


class TestStakeholderImpacts:
    """Test StakeholderImpacts model validation."""

    def test_valid_stakeholder_impacts(self):
        """Test creating valid StakeholderImpacts."""
        impacts = StakeholderImpacts(
            shareholders="TSR of 300% over 10 years, consistent dividends",
            employees="Headcount grew 5x, Glassdoor rating 4.2/5",
            customers="NPS score 70+, retention rate 95%",
            suppliers="Long-term partnerships, fair pricing practices",
            communities="$50M in community investments, carbon neutral by 2023"
        )

        assert "300%" in impacts.shareholders
        assert "95%" in impacts.customers


class TestForwardOutlook:
    """Test ForwardOutlook model validation."""

    def test_valid_forward_outlook(self):
        """Test creating valid ForwardOutlook."""
        outlook = ForwardOutlook(
            growth_trajectory="Expected 20-25% revenue growth next 3 years",
            strategic_priorities=[
                "International expansion",
                "New product categories"
            ],
            potential_challenges=[
                "Economic downturn risk",
                "Talent acquisition in tight market"
            ],
            financial_outlook="Target 40% operating margins by 2026"
        )

        assert "20-25%" in outlook.growth_trajectory
        assert len(outlook.strategic_priorities) == 2
        assert len(outlook.potential_challenges) == 2


class TestCompanySuccessFactors:
    """Test complete CompanySuccessFactors model validation."""

    def test_minimal_success_factors(self):
        """Test creating CompanySuccessFactors with minimal data."""
        business_model = BusinessModel(
            core_operations="B2B SaaS",
            strategic_shifts=[],
            operational_consistency="Consistent strategy"
        )

        financial_metrics = FinancialMetrics(
            revenue_analysis="Steady growth",
            profitability_trends="Improving margins",
            cash_flow_patterns="Positive FCF",
            capital_allocation="Reinvestment focused"
        )

        market_position = MarketPosition(
            market_share="15% market share",
            competitive_advantages=["Technology"],
            barriers_to_entry="Moderate"
        )

        management = ManagementAssessment(
            key_decisions=["Product launch"],
            capital_allocation_quality="Good",
            leadership_stability="Stable",
            strategic_clarity="Clear"
        )

        rd = ResearchDevelopment(
            innovation_approach="Internal R&D",
            rd_investment_trends="Increasing",
            patent_portfolio="50 patents",
            technology_evolution="Cloud migration"
        )

        risk_methodology = RiskMethodology(
            category="Market",
            specific_risks=["Competition"],
            mitigation_strategies=["Differentiation"],
            effectiveness="Moderate"
        )

        stakeholders = StakeholderImpacts(
            shareholders="Positive returns",
            employees="Growing team",
            customers="High satisfaction",
            suppliers="Fair partnerships",
            communities="Community support"
        )

        outlook = ForwardOutlook(
            growth_trajectory="Expected growth",
            strategic_priorities=["Expansion"],
            potential_challenges=["Competition"],
            financial_outlook="Positive"
        )

        factors = CompanySuccessFactors(
            company_name="Test Corp",
            period_analyzed=["2023", "2024"],
            business_model=business_model,
            performance_factors=[],
            financial_metrics=financial_metrics,
            market_position=market_position,
            management_assessment=management,
            research_development=rd,
            risk_assessment=[risk_methodology],
            evolving_risks=[],
            stakeholder_impacts=stakeholders,
            distinguishing_characteristics=[],
            forward_outlook=outlook
        )

        assert factors.company_name == "Test Corp"
        assert len(factors.period_analyzed) == 2

    def test_success_factors_serialization(self):
        """Test complete serialization/deserialization."""
        business_model = BusinessModel(
            core_operations="B2B SaaS",
            strategic_shifts=[],
            operational_consistency="Consistent"
        )

        financial_metrics = FinancialMetrics(
            revenue_analysis="Growth",
            profitability_trends="Improving",
            cash_flow_patterns="Positive",
            capital_allocation="Reinvestment"
        )

        market_position = MarketPosition(
            market_share="15%",
            competitive_advantages=["Tech"],
            barriers_to_entry="Moderate"
        )

        management = ManagementAssessment(
            key_decisions=["Launch"],
            capital_allocation_quality="Good",
            leadership_stability="Stable",
            strategic_clarity="Clear"
        )

        rd = ResearchDevelopment(
            innovation_approach="R&D",
            rd_investment_trends="Increasing",
            patent_portfolio="50",
            technology_evolution="Cloud"
        )

        risk_methodology = RiskMethodology(
            category="Market",
            specific_risks=["Competition"],
            mitigation_strategies=["Differentiation"],
            effectiveness="Moderate"
        )

        stakeholders = StakeholderImpacts(
            shareholders="Positive",
            employees="Growing",
            customers="Satisfied",
            suppliers="Fair",
            communities="Supportive"
        )

        outlook = ForwardOutlook(
            growth_trajectory="Growth",
            strategic_priorities=["Expansion"],
            potential_challenges=["Competition"],
            financial_outlook="Positive"
        )

        factors = CompanySuccessFactors(
            company_name="Test Corp",
            period_analyzed=["2023"],
            business_model=business_model,
            performance_factors=[],
            financial_metrics=financial_metrics,
            market_position=market_position,
            management_assessment=management,
            research_development=rd,
            risk_assessment=[risk_methodology],
            evolving_risks=[],
            stakeholder_impacts=stakeholders,
            distinguishing_characteristics=[],
            forward_outlook=outlook
        )

        # Serialize
        data = factors.model_dump()
        assert data["company_name"] == "Test Corp"

        # Deserialize
        reconstructed = CompanySuccessFactors(**data)
        assert reconstructed == factors
