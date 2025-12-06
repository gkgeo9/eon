#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for success factors prompt restoration.

Validates that the restored prompt contains all critical elements
from the original 10K_automator implementation.
"""

import pytest
from fintel.analysis.fundamental.prompts.success_factors import SUCCESS_FACTORS_PROMPT


class TestSuccessFactorsPrompt:
    """Test that success factors prompt was properly restored from 10K_automator."""

    def test_prompt_exists_and_not_empty(self):
        """Test that prompt is defined and non-empty."""
        assert SUCCESS_FACTORS_PROMPT is not None
        assert len(SUCCESS_FACTORS_PROMPT) > 0
        assert isinstance(SUCCESS_FACTORS_PROMPT, str)

    def test_prompt_is_comprehensive(self):
        """Test that prompt is comprehensive (not the degraded 18-line version)."""
        # Original was 110+ lines, degraded version was ~18 lines
        # Minimum 50 lines for comprehensive analysis guidance
        line_count = len(SUCCESS_FACTORS_PROMPT.strip().split('\n'))
        assert line_count >= 50, f"Prompt only has {line_count} lines, expected 50+"

    def test_prompt_contains_placeholders(self):
        """Test that prompt contains required format placeholders."""
        assert "{company_name}" in SUCCESS_FACTORS_PROMPT
        assert "{years_str}" in SUCCESS_FACTORS_PROMPT

    def test_prompt_contains_critical_analysis_guidelines(self):
        """Test that critical analysis guidelines from original are present."""
        critical_guidelines = [
            "Base your analysis exclusively on the information provided",
            "Present a balanced assessment",
            "both favorable and unfavorable",
            "specific data points",
            "Do not assume the company is either successful or unsuccessful",
            "Avoid subjective judgments",
            "evidence",
        ]

        for guideline in critical_guidelines:
            assert guideline in SUCCESS_FACTORS_PROMPT, \
                f"Missing critical guideline: '{guideline}'"

    def test_prompt_contains_json_structure_guidance(self):
        """Test that JSON structure specification is present."""
        # Should have JSON schema embedded in prompt
        json_keywords = [
            "JSON",
            "company_name",
            "period_analyzed",
            "business_model",
            "core_operations",
            "strategic_shifts",
        ]

        for keyword in json_keywords:
            assert keyword in SUCCESS_FACTORS_PROMPT, \
                f"Missing JSON structure keyword: '{keyword}'"

    def test_prompt_contains_all_major_sections(self):
        """Test that all major analysis sections are specified."""
        major_sections = [
            "business_model",
            "performance_factors",
            "financial_metrics",
            "market_position",
            "management_assessment",
            "research_development",
            "risk_assessment",
            "stakeholder_impacts",
            "forward_outlook",
        ]

        for section in major_sections:
            assert section in SUCCESS_FACTORS_PROMPT, \
                f"Missing major analysis section: '{section}'"

    def test_prompt_contains_financial_metrics_detail(self):
        """Test that financial metrics section has detailed guidance."""
        financial_keywords = [
            "revenue",
            "profit",
            "cash",
            "capital",
        ]

        for keyword in financial_keywords:
            assert keyword.lower() in SUCCESS_FACTORS_PROMPT.lower(), \
                f"Missing financial keyword: '{keyword}'"

    def test_prompt_contains_strategic_shift_guidance(self):
        """Test that strategic shift analysis guidance is present."""
        assert "strategic_shifts" in SUCCESS_FACTORS_PROMPT
        assert "period" in SUCCESS_FACTORS_PROMPT
        assert "change" in SUCCESS_FACTORS_PROMPT
        assert "measured_outcome" in SUCCESS_FACTORS_PROMPT or "outcome" in SUCCESS_FACTORS_PROMPT

    def test_prompt_word_count_substantial(self):
        """Test that prompt has substantial word count (not degraded version)."""
        word_count = len(SUCCESS_FACTORS_PROMPT.split())
        # Original ~2400 words, degraded ~200 words
        # Require at least 1000 words for comprehensive guidance
        assert word_count >= 1000, \
            f"Prompt only has {word_count} words, expected 1000+ (original had ~2400)"

    def test_prompt_formatting_works(self):
        """Test that prompt can be formatted with company data."""
        formatted = SUCCESS_FACTORS_PROMPT.format(
            company_name="Test Corp",
            years_str="2022, 2023, 2024"
        )

        assert "Test Corp" in formatted
        assert "2022, 2023, 2024" in formatted
        assert "{company_name}" not in formatted
        assert "{years_str}" not in formatted


class TestSuccessFactorsPromptQuality:
    """Test the quality and completeness of the restored prompt."""

    def test_prompt_has_specific_field_descriptions(self):
        """Test that specific field descriptions are present (not generic)."""
        # These are specific field descriptions from the original prompt
        specific_descriptions = [
            "core_operations",
            "operational_consistency",
            "revenue_analysis",
            "profitability",
            "leadership",
            "governance",
            "methodology",
            "innovation",
        ]

        for desc in specific_descriptions:
            assert desc.lower() in SUCCESS_FACTORS_PROMPT.lower(), \
                f"Missing specific field description: '{desc}'"

    def test_prompt_emphasizes_objectivity(self):
        """Test that prompt emphasizes objective, evidence-based analysis."""
        objectivity_keywords = [
            "objective",
            "evidence",
            "specific",
            "balanced",
            "data",
            "metrics",
        ]

        found_count = sum(1 for kw in objectivity_keywords
                         if kw.lower() in SUCCESS_FACTORS_PROMPT.lower())

        # Should find at least 4 of these objectivity-related terms
        assert found_count >= 4, \
            f"Only found {found_count}/6 objectivity keywords - prompt may not emphasize evidence-based analysis"

    def test_prompt_structure_is_detailed(self):
        """Test that prompt provides detailed structural guidance."""
        # Count number of field specifications (looking for nested structures)
        nested_indicators = [
            "List[",
            "description=",
            "including",
            "specific",
            "detailed",
            "comprehensive",
        ]

        found_count = sum(1 for indicator in nested_indicators
                         if indicator in SUCCESS_FACTORS_PROMPT)

        assert found_count >= 3, \
            f"Only found {found_count} structural indicators - prompt may lack detail"

    def test_prompt_not_generic(self):
        """Test that prompt is not generic/shallow."""
        # Generic prompts use vague language like "analyze the company"
        # Specific prompts use detailed instructions

        # Should NOT be dominated by generic language
        generic_only_phrases = [
            "analyze the",
            "assess the",
            "evaluate the",
        ]

        # Count generic phrases
        generic_count = sum(SUCCESS_FACTORS_PROMPT.lower().count(phrase)
                           for phrase in generic_only_phrases)

        # Prompt should have detailed guidance, not just generic instructions
        # If it's mostly generic, it's degraded
        total_sentences = SUCCESS_FACTORS_PROMPT.count('.')
        generic_ratio = generic_count / max(total_sentences, 1)

        assert generic_ratio < 0.5, \
            f"Prompt is {generic_ratio:.1%} generic phrases - may be degraded version"


class TestSuccessFactorsPromptComparison:
    """Compare restored prompt against known characteristics of original."""

    def test_prompt_length_comparable_to_original(self):
        """Test that prompt length is comparable to original (not degraded)."""
        char_count = len(SUCCESS_FACTORS_PROMPT)

        # Original was ~12,000+ characters
        # Degraded was ~1,000 characters
        # Require at least 8,000 for restored version
        assert char_count >= 8000, \
            f"Prompt only has {char_count} characters, expected 8000+ (original had ~12000)"

    def test_prompt_has_multi_level_structure(self):
        """Test that prompt specifies multi-level nested structure."""
        # Original had detailed nested JSON with multiple levels
        # e.g., business_model.strategic_shifts[].period

        # Look for evidence of nested structure specification
        structure_patterns = [
            "strategic_shifts",
            "performance_factors",
            "identified_risks",
            "key_decisions",
            "notable_initiatives",
        ]

        found = [p for p in structure_patterns if p in SUCCESS_FACTORS_PROMPT]

        assert len(found) >= 4, \
            f"Only found {len(found)}/5 nested structure patterns - prompt may lack depth"

    def test_prompt_specifies_evidence_requirements(self):
        """Test that prompt requires evidence and specificity."""
        evidence_requirements = [
            "specific",
            "metrics",
            "data points",
            "quantifiable",
            "measured",
        ]

        found = [req for req in evidence_requirements
                if req.lower() in SUCCESS_FACTORS_PROMPT.lower()]

        assert len(found) >= 3, \
            f"Only found {len(found)}/5 evidence requirements - prompt may not enforce rigor"
