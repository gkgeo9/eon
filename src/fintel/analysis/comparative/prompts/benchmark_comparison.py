#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Benchmark comparison prompt for comparing companies against top 50.

RESTORED FROM: 10K_automator/compare_excellent_to_top_50.py
and compare_random_to_top_50.py

This comprehensive prompt analyzes whether a company exhibits the patterns
of proven multi-decade compounders.
"""

# Full benchmark comparison prompt from 10K_automator
BENCHMARK_COMPARISON_PROMPT = """
# FUTURE COMPOUNDER IDENTIFICATION ANALYSIS

Analyze this company's 10-K data against the proven success principles identified in the top 50 meta-analysis to determine if it shows the foundational characteristics of companies that deliver exceptional long-term performance (30+ year compounders).

## COMPOUNDER DNA SCORING SYSTEM

Use this balanced scoring system that recognizes both the presence and maturity of key success patterns:

* 90-100: Future Compounder - The company demonstrates a clear, comprehensive pattern that strongly resembles top performers, with exceptional implementation of critical success factors. Its approach appears deeply embedded in its strategy and operations, showing consistency, adaptability, and a long-term orientation. The company is positioned for sustainable competitive advantage rather than temporary success.

* 75-89: Strong Potential - The company shows significant alignment with top performer patterns in most key areas. Their approach reflects intentional design rather than happenstance, though implementation may still be evolving in some areas. The foundation for long-term compounding is present but not yet fully realized or proven.

* 60-74: Developing Contender - The company shows meaningful elements of top performer patterns, with solid fundamentals but significant room for improvement in key areas. The company may excel in some dimensions while having notable gaps in others. Long-term compounding potential exists but requires substantial further development.

* 40-59: Partial Alignment - The company exhibits some positive elements found in top performers, but lacks the cohesive pattern associated with long-term compounders. The business may be successful in the short-to-medium term but lacks the fundamental characteristics needed for multi-decade excellence.

* 20-39: Limited Alignment - The company shows minimal resemblance to the patterns of top performers. While pockets of strength may exist, the overall approach lacks the foundational elements associated with long-term value creation.

* 0-19: Misaligned - The company's approach runs counter to the patterns observed in top performers, with fundamental weaknesses in critical areas that would typically prevent long-term compounding.

## PATTERN RECOGNITION FRAMEWORK

For each success factor from the top 50 meta-analysis:

1. PATTERN IDENTIFICATION: Identify how the company approaches this area, looking for both stated strategies and operational evidence.

2. MATURITY ASSESSMENT: Evaluate the depth and consistency of implementation, distinguishing between nascent efforts and deeply embedded practices.

3. ADAPTABILITY EVALUATION: Assess whether the approach shows signs of appropriate evolution in response to changing conditions while maintaining core principles.

4. COMPETITIVE ADVANTAGE ANALYSIS: Determine whether the company's approach in this area contributes to sustainable differentiation rather than temporary advantage.

5. FUTURE ORIENTATION: Consider evidence of long-term thinking versus short-term optimization in the company's approach.

## CRITICAL SUCCESS FACTOR WEIGHTING

While all factors matter, give particular attention to these historically predictive characteristics:

1. Disciplined capital allocation with clear evidence of high-return reinvestment
2. Strong operational execution capabilities that create margin advantage
3. Distinctive business model with inherent economic advantages
4. Leadership approach that balances consistency with appropriate adaptation
5. Ability to build and maintain deep domain expertise in core markets
6. Evidence of strong, resilient culture supporting the business model

## OUTPUT FORMAT

Return ONLY a valid JSON object structured as follows:

{
    "company_name": "Name of the company being analyzed",
    "analysis_date": "Current date",
    "compounder_potential": {
        "score": 0-100 overall potential score,
        "category": "Future Compounder/Strong Potential/Developing Contender/Partial Alignment/Limited Alignment/Misaligned",
        "summary": "3-4 sentence summary of the company's potential as a long-term compounder",
        "distinctive_strengths": ["3-5 most compelling characteristics that could drive long-term outperformance"],
        "critical_gaps": ["3-5 most concerning weaknesses that could limit long-term compounding"],
        "stage_context": "Assessment of the company's current business stage and how it affects the evaluation"
    },
    "success_factor_alignment": [
        {
            "factor": "Name of universal success factor",
            "alignment": "Strong/Moderate/Weak/Absent",
            "score": 0-100 score for this specific factor,
            "pattern_assessment": "Description of how the company's approach compares to top performers in this area",
            "maturity_level": "Assessment of how developed and embedded this pattern is within the company",
            "competitive_advantage": "Analysis of whether this factor contributes to sustainable differentiation"
        }
    ],
    "leadership_assessment": {
        "alignment": "Strong/Moderate/Weak",
        "score": 0-100 leadership alignment score,
        "patterns_present": ["Leadership patterns from top performers that appear present"],
        "patterns_missing": ["Leadership patterns from top performers that appear absent"],
        "long_term_orientation": "Assessment of leadership's focus on long-term value creation versus short-term results"
    },
    "strategic_positioning_assessment": {
        "alignment": "Strong/Moderate/Weak",
        "score": 0-100 strategic alignment score,
        "approaches_present": ["Strategic positioning approaches from top 50 that appear present"],
        "approaches_missing": ["Strategic positioning approaches from top 50 that appear absent"],
        "defensibility": "Assessment of how defensible the company's strategic position appears over a multi-decade horizon"
    },
    "financial_patterns_assessment": {
        "alignment": "Strong/Moderate/Weak",
        "score": 0-100 financial patterns alignment score,
        "patterns_present": ["Financial patterns from top performers that appear present"],
        "patterns_missing": ["Financial patterns from top performers that appear missing"],
        "capital_allocation_quality": "Specific assessment of the company's capital allocation approach and its potential to drive compounding"
    },
    "innovation_systems_assessment": {
        "alignment": "Strong/Moderate/Weak",
        "score": 0-100 innovation systems alignment score,
        "systems_present": ["Innovation systems from top performers that appear present"],
        "systems_missing": ["Innovation systems from top performers that appear missing"],
        "adaptability_assessment": "Evaluation of the company's ability to innovate within its core model rather than requiring fundamental pivots"
    },
    "operational_excellence_assessment": {
        "alignment": "Strong/Moderate/Weak",
        "score": 0-100 operational excellence alignment score,
        "factors_present": ["Operational excellence factors from top performers that appear present"],
        "factors_missing": ["Operational excellence factors from top performers that appear missing"],
        "execution_quality": "Assessment of the company's operational execution capabilities and its impact on competitive advantage"
    },
    "customer_relationship_assessment": {
        "alignment": "Strong/Moderate/Weak",
        "score": 0-100 customer relationship alignment score,
        "models_present": ["Customer relationship models from top performers that appear present"],
        "models_missing": ["Customer relationship models from top performers that appear missing"],
        "durability_assessment": "Evaluation of how sticky and durable customer relationships appear to be"
    },
    "cross_pattern_relationship_assessment": {
        "alignment": "Strong/Moderate/Weak",
        "score": 0-100 cross-pattern relationship alignment score,
        "relationships_present": ["Cross-pattern relationships from top performers that appear present"],
        "relationships_missing": ["Cross-pattern relationships from top performers that appear missing"],
        "system_coherence": "Assessment of how well the company's various success elements work together as a coherent system"
    },
    "predictive_indicators_assessment": {
        "alignment": "Strong/Moderate/Weak",
        "score": 0-100 predictive indicators alignment score,
        "indicators_present": ["Predictive indicators from top performers that appear present"],
        "indicators_missing": ["Predictive indicators from top performers that appear missing"],
        "forward_indicators": "Identification of leading indicators that suggest future compounding potential"
    },
    "final_assessment": {
        "verdict": "Assessment of likelihood to be a multi-decade compounder",
        "probability_of_outperformance": "High/Medium/Low",
        "reasoning": "Explanation of why this probability was assigned",
        "key_areas_to_monitor": ["3-5 specific areas to watch that could confirm or challenge the compounding thesis"],
        "meta_conclusions_alignment": "Assessment of how the company aligns with the meta_conclusions from the top 50 analysis"
    },
    "investor_considerations": {
        "research_priorities": ["Suggested areas for deeper investigation based on this initial screening"],
        "potential_catalysts": ["Possible events or developments that could accelerate or reveal compounding potential"],
        "key_risks": ["Specific risks to the compounding thesis that deserve particular attention"]
    }
}
"""


__all__ = [
    'BENCHMARK_COMPARISON_PROMPT',
]
