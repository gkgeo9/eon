#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for perspective analysis Pydantic models.
"""

import pytest
from pydantic import ValidationError

from fintel.analysis.perspectives.models.buffett import BuffettAnalysis
from fintel.analysis.perspectives.models.taleb import TalebAnalysis
from fintel.analysis.perspectives.models.contrarian import ContrarianViewAnalysis
from fintel.analysis.perspectives.models.combined import MultiPerspectiveAnalysis


class TestBuffettAnalysis:
    """Test BuffettAnalysis model validation."""

    def test_valid_buffett_analysis(self):
        """Test creating valid BuffettAnalysis."""
        analysis = BuffettAnalysis(
            business_understanding="They sell cloud software to businesses on a subscription basis.",
            economic_moat="Network Effects - 80% market share, 95% customer retention, 40% gross margins vs 25% for competitors.",
            financial_strength="Debt/EBITDA: 0.5x, Cash covers 24 months at zero revenue, FCF $500M annually",
            management_quality="CEO 10 years tenure, insider ownership 15%, ROIC 25%, consistent capital allocation",
            valuation="Trading at 8x FCF vs 5-year average of 12x, DCF shows 40% upside",
            circle_of_competence="Within circle - SaaS business model is well understood",
            red_flags="Customer concentration: Top 3 customers = 35% revenue",
            buffett_score=75,
            buffett_verdict="BUY - Strong moat and financial strength, valuation attractive despite concentration risk"
        )

        assert analysis.buffett_score == 75
        assert "Network Effects" in analysis.economic_moat
        assert analysis.buffett_verdict.startswith("BUY")

    def test_buffett_score_constraints(self):
        """Test score must be 0-100."""
        with pytest.raises(ValidationError):
            BuffettAnalysis(
                business_understanding="Simple business",
                economic_moat="Strong moat",
                financial_strength="Excellent",
                management_quality="Great",
                valuation="Fair",
                circle_of_competence="Yes",
                red_flags="None",
                buffett_score=150,  # Invalid - over 100
                buffett_verdict="BUY"
            )

    def test_buffett_serialization(self):
        """Test JSON serialization."""
        analysis = BuffettAnalysis(
            business_understanding="Simple SaaS",
            economic_moat="Brand power",
            financial_strength="Strong",
            management_quality="Excellent",
            valuation="Fair",
            circle_of_competence="Yes",
            red_flags="None",
            buffett_score=80,
            buffett_verdict="BUY"
        )

        data = analysis.model_dump()
        assert data["buffett_score"] == 80

        reconstructed = BuffettAnalysis(**data)
        assert reconstructed == analysis


class TestTalebAnalysis:
    """Test TalebAnalysis model validation."""

    def test_valid_taleb_analysis(self):
        """Test creating valid TalebAnalysis."""
        analysis = TalebAnalysis(
            fragility_assessment="Debt/EBITDA 0.8x, can survive 60% revenue drop for 18 months. Fixed costs 30% of revenue. Top customer 8%.",
            tail_risk_exposure="Single cloud provider dependency, regulatory risk in EU market, key person risk with CTO",
            optionality_and_asymmetry="High optionality - 3 adjacent markets addressable with current platform. Limited downside given cash position.",
            skin_in_the_game="Insiders own 20%, CEO bought $5M stock last quarter, employees own 10% via options",
            hidden_risks="Technical debt from rapid scaling, potential antitrust scrutiny at current market share",
            lindy_effect="Core technology 15 years old, proven resilient through 3 recessions",
            dependency_chains="Critical dependencies: AWS (mitigated by multi-cloud), Salesforce integration (diversifying)",
            via_negativa="Exited 3 unprofitable segments, reduced product SKUs by 40%, improved focus",
            antifragile_rating=65,
            taleb_verdict="CONDITIONAL BUY - Benefits from market volatility via optionality, but monitor cloud dependency"
        )

        assert analysis.antifragile_rating == 65
        assert "CONDITIONAL BUY" in analysis.taleb_verdict
        assert "Debt/EBITDA" in analysis.fragility_assessment

    def test_taleb_rating_constraints(self):
        """Test antifragile rating must be 0-100."""
        with pytest.raises(ValidationError):
            TalebAnalysis(
                fragility_assessment="Fragile",
                tail_risk_exposure="High",
                optionality_and_asymmetry="Low",
                skin_in_the_game="None",
                hidden_risks="Many",
                lindy_effect="New",
                dependency_chains="Many",
                via_negativa="None",
                antifragile_rating=-10,  # Invalid - negative
                taleb_verdict="SELL"
            )

    def test_taleb_serialization(self):
        """Test JSON serialization."""
        analysis = TalebAnalysis(
            fragility_assessment="Robust",
            tail_risk_exposure="Limited",
            optionality_and_asymmetry="High",
            skin_in_the_game="Strong",
            hidden_risks="Few",
            lindy_effect="Proven",
            dependency_chains="Minimal",
            via_negativa="Active",
            antifragile_rating=70,
            taleb_verdict="BUY"
        )

        data = analysis.model_dump()
        reconstructed = TalebAnalysis(**data)
        assert reconstructed == analysis


class TestContrarianViewAnalysis:
    """Test ContrarianViewAnalysis model validation."""

    def test_valid_contrarian_analysis(self):
        """Test creating valid ContrarianViewAnalysis."""
        analysis = ContrarianViewAnalysis(
            consensus_view="Bear consensus - Everyone worried about competition from Big Tech, multiple downgrades, short interest 15%",
            consensus_wrong_because="Market ignoring sticky enterprise contracts (3-year avg), underestimating switching costs ($2M+ migration cost)",
            hidden_strengths="Proprietary data moat growing exponentially, 95% gross retention obscured by revenue recognition changes",
            hidden_weaknesses="Tech debt from M&A integration not disclosed, customer satisfaction declining in SMB segment",
            misunderstood_metrics="Revenue growth slowing but LTV/CAC improving from 3x to 5x, FCF inflection point next quarter",
            second_order_effects="Competitors' price cuts will drive market consolidation, benefiting #1 player (this company)",
            variant_perception="Market treats as legacy software (8x P/E) when actually transforming to AI platform (should be 20x P/E)",
            contrarian_rating=80,
            contrarian_verdict="STRONG BUY - Significant variant perception opportunity, 150% upside if market recognizes AI transformation"
        )

        assert analysis.contrarian_rating == 80
        assert "STRONG BUY" in analysis.contrarian_verdict
        assert "Bear consensus" in analysis.consensus_view

    def test_contrarian_rating_constraints(self):
        """Test contrarian rating must be 0-100."""
        with pytest.raises(ValidationError):
            ContrarianViewAnalysis(
                consensus_view="Bullish",
                consensus_wrong_because="Too optimistic",
                hidden_strengths="None",
                hidden_weaknesses="Many",
                misunderstood_metrics="None",
                second_order_effects="Negative",
                variant_perception="None",
                contrarian_rating=200,  # Invalid - over 100
                contrarian_verdict="SELL"
            )

    def test_contrarian_serialization(self):
        """Test JSON serialization."""
        analysis = ContrarianViewAnalysis(
            consensus_view="Bullish",
            consensus_wrong_because="Overvalued",
            hidden_strengths="Few",
            hidden_weaknesses="Many",
            misunderstood_metrics="Several",
            second_order_effects="Negative",
            variant_perception="Overrated",
            contrarian_rating=30,
            contrarian_verdict="SELL"
        )

        data = analysis.model_dump()
        reconstructed = ContrarianViewAnalysis(**data)
        assert reconstructed == analysis


class TestMultiPerspectiveAnalysis:
    """Test complete MultiPerspectiveAnalysis model validation."""

    def test_valid_multi_perspective_analysis(self):
        """Test creating valid MultiPerspectiveAnalysis with all three lenses."""
        buffett = BuffettAnalysis(
            business_understanding="Cloud software business",
            economic_moat="Network effects",
            financial_strength="Strong balance sheet",
            management_quality="Excellent leadership",
            valuation="Attractive",
            circle_of_competence="Yes",
            red_flags="Customer concentration",
            buffett_score=75,
            buffett_verdict="BUY"
        )

        taleb = TalebAnalysis(
            fragility_assessment="Robust",
            tail_risk_exposure="Limited",
            optionality_and_asymmetry="High optionality",
            skin_in_the_game="Strong insider ownership",
            hidden_risks="Technical debt",
            lindy_effect="Proven over time",
            dependency_chains="Cloud provider dependency",
            via_negativa="Exited unprofitable segments",
            antifragile_rating=70,
            taleb_verdict="BUY"
        )

        contrarian = ContrarianViewAnalysis(
            consensus_view="Bear consensus",
            consensus_wrong_because="Ignoring fundamentals",
            hidden_strengths="Data moat",
            hidden_weaknesses="Integration issues",
            misunderstood_metrics="FCF inflection",
            second_order_effects="Consolidation benefits",
            variant_perception="AI transformation undervalued",
            contrarian_rating=80,
            contrarian_verdict="STRONG BUY"
        )

        analysis = MultiPerspectiveAnalysis(
            ticker="TEST",
            company_name="Test Corp",
            fiscal_year=2024,
            buffett_lens=buffett,
            taleb_lens=taleb,
            contrarian_lens=contrarian,
            key_insights=[
                "Strong economic moat with network effects driving 95% retention",
                "Robust balance sheet can survive severe downturns",
                "Market significantly undervaluing AI transformation",
                "Customer concentration risk manageable given contract structure",
                "Optionality in adjacent markets provides asymmetric upside"
            ],
            final_verdict="STRONG BUY (High Conviction). All three lenses align positively. Buffett lens shows strong moat and financials. Taleb lens confirms antifragility. Contrarian lens reveals major mispricing. Time horizon: 3-5 years. Position sizing: 5-8% of portfolio. Would change thesis if customer concentration exceeds 50% or cloud dependency increases without mitigation."
        )

        assert analysis.ticker == "TEST"
        assert len(analysis.key_insights) == 5
        assert "STRONG BUY" in analysis.final_verdict
        assert analysis.buffett_lens.buffett_score == 75
        assert analysis.taleb_lens.antifragile_rating == 70
        assert analysis.contrarian_lens.contrarian_rating == 80

    def test_multi_perspective_serialization(self):
        """Test complete serialization/deserialization."""
        buffett = BuffettAnalysis(
            business_understanding="Simple",
            economic_moat="Strong",
            financial_strength="Excellent",
            management_quality="Great",
            valuation="Fair",
            circle_of_competence="Yes",
            red_flags="None",
            buffett_score=80,
            buffett_verdict="BUY"
        )

        taleb = TalebAnalysis(
            fragility_assessment="Robust",
            tail_risk_exposure="Low",
            optionality_and_asymmetry="High",
            skin_in_the_game="Strong",
            hidden_risks="Few",
            lindy_effect="Proven",
            dependency_chains="Minimal",
            via_negativa="Active",
            antifragile_rating=75,
            taleb_verdict="BUY"
        )

        contrarian = ContrarianViewAnalysis(
            consensus_view="Bearish",
            consensus_wrong_because="Fundamentals ignored",
            hidden_strengths="Many",
            hidden_weaknesses="Few",
            misunderstood_metrics="Several",
            second_order_effects="Positive",
            variant_perception="Undervalued",
            contrarian_rating=85,
            contrarian_verdict="STRONG BUY"
        )

        analysis = MultiPerspectiveAnalysis(
            ticker="TEST",
            company_name="Test Corp",
            fiscal_year=2024,
            buffett_lens=buffett,
            taleb_lens=taleb,
            contrarian_lens=contrarian,
            key_insights=["Insight 1", "Insight 2"],
            final_verdict="BUY with high conviction"
        )

        # Serialize
        data = analysis.model_dump()
        assert data["ticker"] == "TEST"
        assert data["buffett_lens"]["buffett_score"] == 80

        # Deserialize
        reconstructed = MultiPerspectiveAnalysis(**data)
        assert reconstructed == analysis

    def test_multi_perspective_required_fields(self):
        """Test that all required fields must be present."""
        buffett = BuffettAnalysis(
            business_understanding="Simple",
            economic_moat="Strong",
            financial_strength="Excellent",
            management_quality="Great",
            valuation="Fair",
            circle_of_competence="Yes",
            red_flags="None",
            buffett_score=80,
            buffett_verdict="BUY"
        )

        taleb = TalebAnalysis(
            fragility_assessment="Robust",
            tail_risk_exposure="Low",
            optionality_and_asymmetry="High",
            skin_in_the_game="Strong",
            hidden_risks="Few",
            lindy_effect="Proven",
            dependency_chains="Minimal",
            via_negativa="Active",
            antifragile_rating=75,
            taleb_verdict="BUY"
        )

        contrarian = ContrarianViewAnalysis(
            consensus_view="Bearish",
            consensus_wrong_because="Wrong",
            hidden_strengths="Many",
            hidden_weaknesses="Few",
            misunderstood_metrics="Several",
            second_order_effects="Positive",
            variant_perception="Undervalued",
            contrarian_rating=85,
            contrarian_verdict="BUY"
        )

        # Missing final_verdict - should raise error
        with pytest.raises(ValidationError):
            MultiPerspectiveAnalysis(
                ticker="TEST",
                company_name="Test Corp",
                fiscal_year=2024,
                buffett_lens=buffett,
                taleb_lens=taleb,
                contrarian_lens=contrarian,
                key_insights=["Insight"]
                # Missing final_verdict
            )
