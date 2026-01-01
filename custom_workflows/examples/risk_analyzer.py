#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Risk Factor Analyzer Workflow.

Extracts and analyzes risk factors from SEC filings to identify
material risks, their severity, and potential mitigations.
"""

from typing import List, Literal
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow


class RiskFactor(BaseModel):
    """A single risk factor extracted from the filing."""
    category: Literal[
        "Operational", "Financial", "Regulatory", "Competitive",
        "Macroeconomic", "Legal", "Cybersecurity", "ESG", "Other"
    ] = Field(description="Risk category")
    title: str = Field(description="Brief title for the risk (5-10 words)")
    description: str = Field(description="Detailed description of the risk")
    severity: Literal["Low", "Medium", "High", "Critical"] = Field(
        description="Severity rating based on potential impact"
    )
    likelihood: Literal["Unlikely", "Possible", "Likely", "Very Likely"] = Field(
        description="Likelihood of the risk materializing"
    )
    mitigation: str = Field(description="Company's stated mitigation strategy, if any")
    is_new: bool = Field(
        description="True if this appears to be a new risk not mentioned in prior years"
    )


class RiskAnalysisResult(BaseModel):
    """Schema for comprehensive risk analysis."""

    executive_summary: str = Field(
        description="2-3 sentence overview of the company's risk profile"
    )

    top_risks: List[RiskFactor] = Field(
        description="Top 5 most significant risk factors from the filing"
    )

    risk_concentration: str = Field(
        description="Analysis of where risks are concentrated. "
        "Are risks diversified or clustered in one area?"
    )

    new_or_escalated_risks: List[str] = Field(
        description="Risks that appear new or have been escalated in severity"
    )

    hidden_risks: List[str] = Field(
        description="Potential risks NOT mentioned but implied by the business model"
    )

    overall_risk_score: int = Field(
        ge=0, le=100,
        description="Overall risk score 0-100: "
        "0-25=Low risk, 26-50=Moderate, 51-75=Elevated, 76-100=High risk"
    )

    risk_trend: Literal["Improving", "Stable", "Deteriorating"] = Field(
        description="Direction of overall risk profile"
    )

    red_flags: List[str] = Field(
        description="Specific language or disclosures that are concerning"
    )


class RiskFactorAnalyzer(CustomWorkflow):
    """Analyzes and categorizes risk factors from SEC filings."""

    name = "Risk Factor Analyzer"
    description = "Extract, categorize, and rate risk factors from 10-K filings"
    icon = "⚠️"
    min_years = 1
    category = "risk"

    @property
    def prompt_template(self) -> str:
        return """
You are a risk management analyst reviewing {ticker} for fiscal year {year}.

Analyze the SEC filing with a focus on the Risk Factors section and any risk-related disclosures throughout the document.

### ANALYSIS FRAMEWORK

1. **RISK EXTRACTION**
   - Extract the most material risk factors
   - Categorize each risk (Operational, Financial, Regulatory, etc.)
   - Rate severity and likelihood
   - Note any mitigation strategies mentioned

2. **RISK ASSESSMENT**
   - Evaluate risk concentration (are risks diversified or clustered?)
   - Identify risks that appear new or escalated
   - Look for "hidden" risks implied but not explicitly stated

3. **RED FLAG DETECTION**
   - Language changes suggesting deterioration
   - Vague or evasive risk disclosures
   - Missing discussion of obvious risks
   - Over-reliance on insurance or indemnification

4. **OVERALL RISK PROFILE**
   - Score the overall risk level (0-100)
   - Assess whether the risk profile is improving or deteriorating
   - Identify the single biggest risk to monitor

### SEVERITY RATINGS

- **Critical**: Existential threat to the business
- **High**: Could materially impair operations or finances
- **Medium**: Meaningful but manageable impact
- **Low**: Minor or well-mitigated risks

### LIKELIHOOD RATINGS

- **Very Likely**: Expected to occur
- **Likely**: More probable than not
- **Possible**: Could happen under certain conditions
- **Unlikely**: Remote but possible

### IMPORTANT

- Quote specific language from the filing when identifying red flags
- Consider risks that affect the ENTIRE business, not just one segment
- Look for risks that could trigger a cascade of problems
- Note if management seems to be downplaying obvious risks
"""

    @property
    def schema(self):
        return RiskAnalysisResult
