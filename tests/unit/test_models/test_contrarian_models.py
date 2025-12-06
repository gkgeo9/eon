#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for contrarian analysis Pydantic models.
"""

import pytest
from pydantic import ValidationError

from fintel.analysis.comparative.models.contrarian_scores import (
    ContrarianScores,
    ContrarianAnalysis
)


class TestContrarianScores:
    """Test ContrarianScores model validation."""

    def test_valid_contrarian_scores(self):
        """Test creating valid ContrarianScores with all dimensions."""
        scores = ContrarianScores(
            strategic_anomaly=75,
            asymmetric_resources=65,
            contrarian_positioning=80,
            cross_industry_dna=70,
            early_infrastructure=60,
            intellectual_capital=85
        )

        assert scores.strategic_anomaly == 75
        assert scores.asymmetric_resources == 65
        assert scores.contrarian_positioning == 80
        assert scores.cross_industry_dna == 70
        assert scores.early_infrastructure == 60
        assert scores.intellectual_capital == 85

    def test_score_constraints_min(self):
        """Test that scores cannot be below 0."""
        with pytest.raises(ValidationError):
            ContrarianScores(
                strategic_anomaly=-10,  # Invalid
                asymmetric_resources=50,
                contrarian_positioning=50,
                cross_industry_dna=50,
                early_infrastructure=50,
                intellectual_capital=50
            )

    def test_score_constraints_max(self):
        """Test that scores cannot exceed 100."""
        with pytest.raises(ValidationError):
            ContrarianScores(
                strategic_anomaly=50,
                asymmetric_resources=150,  # Invalid
                contrarian_positioning=50,
                cross_industry_dna=50,
                early_infrastructure=50,
                intellectual_capital=50
            )

    def test_all_scores_at_boundaries(self):
        """Test scores at boundary values (0 and 100)."""
        # All zeros
        scores_zero = ContrarianScores(
            strategic_anomaly=0,
            asymmetric_resources=0,
            contrarian_positioning=0,
            cross_industry_dna=0,
            early_infrastructure=0,
            intellectual_capital=0
        )
        assert scores_zero.strategic_anomaly == 0

        # All 100s
        scores_hundred = ContrarianScores(
            strategic_anomaly=100,
            asymmetric_resources=100,
            contrarian_positioning=100,
            cross_industry_dna=100,
            early_infrastructure=100,
            intellectual_capital=100
        )
        assert scores_hundred.intellectual_capital == 100

    def test_contrarian_scores_serialization(self):
        """Test JSON serialization."""
        scores = ContrarianScores(
            strategic_anomaly=75,
            asymmetric_resources=65,
            contrarian_positioning=80,
            cross_industry_dna=70,
            early_infrastructure=60,
            intellectual_capital=85
        )

        data = scores.model_dump()
        assert data["strategic_anomaly"] == 75
        assert len(data) == 6

        reconstructed = ContrarianScores(**data)
        assert reconstructed == scores


class TestContrarianAnalysis:
    """Test ContrarianAnalysis model validation."""

    def test_valid_contrarian_analysis(self):
        """Test creating valid ContrarianAnalysis."""
        scores = ContrarianScores(
            strategic_anomaly=75,
            asymmetric_resources=65,
            contrarian_positioning=80,
            cross_industry_dna=70,
            early_infrastructure=60,
            intellectual_capital=85
        )

        analysis = ContrarianAnalysis(
            ticker="AAPL",
            company_name="Apple Inc.",
            overall_alpha_score=72,
            scores=scores,
            key_insights=[
                "Strategic shift to services generating 40% margin vs 20% hardware",
                "Asymmetric bet on vertical integration (chip design) paying off with 30% performance advantage",
                "Contrarian positioning: Privacy focus while industry monetizes data"
            ],
            investment_thesis="Apple is misunderstood as mature hardware company when actually transforming to high-margin services platform with unmatched ecosystem lock-in. Market undervalues services transition (25% of revenue, 40% margins, growing 20% YoY).",
            risk_factors=[
                "iPhone concentration risk (50% of revenue)",
                "Regulatory pressure on App Store fees",
                "China dependency (20% of revenue, geopolitical risk)"
            ],
            catalyst_timeline="12-18 months for services inflection to be recognized by market",
            confidence_level="HIGH"
        )

        assert analysis.ticker == "AAPL"
        assert analysis.overall_alpha_score == 72
        assert len(analysis.key_insights) == 3
        assert len(analysis.risk_factors) == 3
        assert analysis.confidence_level == "HIGH"

    def test_overall_alpha_score_constraints(self):
        """Test overall_alpha_score must be 0-100."""
        scores = ContrarianScores(
            strategic_anomaly=50,
            asymmetric_resources=50,
            contrarian_positioning=50,
            cross_industry_dna=50,
            early_infrastructure=50,
            intellectual_capital=50
        )

        with pytest.raises(ValidationError):
            ContrarianAnalysis(
                ticker="TEST",
                company_name="Test",
                overall_alpha_score=150,  # Invalid
                scores=scores,
                key_insights=["Insight"],
                investment_thesis="Thesis",
                risk_factors=["Risk"],
                catalyst_timeline="12 months",
                confidence_level="MEDIUM"
            )

    def test_empty_lists_allowed(self):
        """Test that empty lists are allowed for insights and risks."""
        scores = ContrarianScores(
            strategic_anomaly=50,
            asymmetric_resources=50,
            contrarian_positioning=50,
            cross_industry_dna=50,
            early_infrastructure=50,
            intellectual_capital=50
        )

        analysis = ContrarianAnalysis(
            ticker="TEST",
            company_name="Test Corp",
            overall_alpha_score=50,
            scores=scores,
            key_insights=[],  # Empty is allowed
            investment_thesis="Thesis",
            risk_factors=[],  # Empty is allowed
            catalyst_timeline="Unknown",
            confidence_level="LOW"
        )

        assert len(analysis.key_insights) == 0
        assert len(analysis.risk_factors) == 0

    def test_contrarian_analysis_serialization(self):
        """Test complete serialization/deserialization."""
        scores = ContrarianScores(
            strategic_anomaly=75,
            asymmetric_resources=65,
            contrarian_positioning=80,
            cross_industry_dna=70,
            early_infrastructure=60,
            intellectual_capital=85
        )

        analysis = ContrarianAnalysis(
            ticker="NVDA",
            company_name="NVIDIA",
            overall_alpha_score=88,
            scores=scores,
            key_insights=[
                "Positioned at intersection of three mega-trends: AI, gaming, autonomous vehicles",
                "Asymmetric infrastructure bet: Built CUDA ecosystem 15 years ago, now unassailable moat",
                "Cross-industry DNA: Gaming company becoming data center infrastructure provider"
            ],
            investment_thesis="NVIDIA is the picks-and-shovels of the AI revolution with 80%+ market share in AI training chips. CUDA software moat creates 10-year switching costs. Market still pricing as cyclical semiconductor vs. AI infrastructure platform.",
            risk_factors=[
                "Potential competition from custom AI chips (Google TPU, Amazon Trainium)",
                "Customer concentration: Top 4 cloud providers = 50% revenue",
                "Geopolitical risk: China export restrictions"
            ],
            catalyst_timeline="6-12 months as AI adoption accelerates",
            confidence_level="HIGH"
        )

        # Serialize
        data = analysis.model_dump()
        assert data["ticker"] == "NVDA"
        assert data["overall_alpha_score"] == 88
        assert data["scores"]["strategic_anomaly"] == 75

        # Deserialize
        reconstructed = ContrarianAnalysis(**data)
        assert reconstructed == analysis

    def test_confidence_level_values(self):
        """Test that confidence_level can be any string (no enum constraint)."""
        scores = ContrarianScores(
            strategic_anomaly=50,
            asymmetric_resources=50,
            contrarian_positioning=50,
            cross_industry_dna=50,
            early_infrastructure=50,
            intellectual_capital=50
        )

        for confidence in ["HIGH", "MEDIUM", "LOW", "VERY HIGH", "UNCERTAIN"]:
            analysis = ContrarianAnalysis(
                ticker="TEST",
                company_name="Test",
                overall_alpha_score=50,
                scores=scores,
                key_insights=["Insight"],
                investment_thesis="Thesis",
                risk_factors=["Risk"],
                catalyst_timeline="12 months",
                confidence_level=confidence
            )
            assert analysis.confidence_level == confidence

    def test_realistic_low_score_company(self):
        """Test analysis for typical company with low contrarian scores."""
        scores = ContrarianScores(
            strategic_anomaly=25,  # Standard industry playbook
            asymmetric_resources=30,  # Resources spread evenly
            contrarian_positioning=20,  # Following consensus
            cross_industry_dna=15,  # Same-industry management
            early_infrastructure=25,  # Building for current needs
            intellectual_capital=20  # Standard IP portfolio
        )

        analysis = ContrarianAnalysis(
            ticker="GENERIC",
            company_name="Generic Corp",
            overall_alpha_score=23,  # Average of dimensions
            scores=scores,
            key_insights=[
                "Standard industry strategy with no differentiation",
                "Management from same industry backgrounds, maintaining status quo",
                "IP portfolio typical for sector, no hidden advantages"
            ],
            investment_thesis="Generic Corp follows industry playbook without contrarian positioning. While fundamentals are solid, no hidden alpha or variant perception opportunity exists. Fair value, not undervalued.",
            risk_factors=[
                "Commoditization risk in competitive market",
                "No distinctive competitive advantages",
                "Vulnerable to industry disruption"
            ],
            catalyst_timeline="No clear catalysts identified",
            confidence_level="MEDIUM"
        )

        assert analysis.overall_alpha_score == 23
        assert all(score <= 30 for score in [
            scores.strategic_anomaly,
            scores.asymmetric_resources,
            scores.contrarian_positioning,
            scores.cross_industry_dna,
            scores.early_infrastructure,
            scores.intellectual_capital
        ])

    def test_realistic_high_score_company(self):
        """Test analysis for exceptional company with high contrarian scores."""
        scores = ContrarianScores(
            strategic_anomaly=85,  # Bold counterintuitive moves
            asymmetric_resources=78,  # All-in bet on opportunity
            contrarian_positioning=82,  # Inverse to industry

            cross_industry_dna=75,  # Importing foreign practices
            early_infrastructure=88,  # Building for future markets
            intellectual_capital=90  # Game-changing unrecognized IP
        )

        analysis = ContrarianAnalysis(
            ticker="TSLA",
            company_name="Tesla",
            overall_alpha_score=83,
            scores=scores,
            key_insights=[
                "Strategic anomaly: Vertical integration in age of outsourcing (batteries, chips, insurance, energy)",
                "Asymmetric infrastructure: Built charging network and battery production at massive scale pre-demand",
                "Contrarian positioning: Direct-to-consumer model vs dealer franchise",
                "Cross-industry DNA: Software/tech company approach applied to automotive manufacturing",
                "Early infrastructure: FSD investment building for autonomy future 5+ years out",
                "Intellectual capital: Battery tech, manufacturing innovation, FSD data moat undervalued by market"
            ],
            investment_thesis="Tesla executing multi-decade contrarian strategy: redefining automotive as software/energy platform. Market undervalues optionality in energy, autonomy, AI. Asymmetric bet on vertical integration creating compounding advantages. Infrastructure built for 10M+ unit production.",
            risk_factors=[
                "Execution risk on multiple fronts (FSD, Cybertruck, energy)",
                "Key person risk with CEO",
                "Competition from legacy OEMs with deeper pockets",
                "Regulatory uncertainty around autonomy"
            ],
            catalyst_timeline="3-5 years for full thesis validation, but intermediate catalysts quarterly",
            confidence_level="MEDIUM"
        )

        assert analysis.overall_alpha_score == 83
        assert all(score >= 75 for score in [
            scores.strategic_anomaly,
            scores.asymmetric_resources,
            scores.contrarian_positioning,
            scores.cross_industry_dna,
            scores.early_infrastructure,
            scores.intellectual_capital
        ])
        assert len(analysis.key_insights) == 6
