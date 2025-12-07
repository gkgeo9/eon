#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contrarian variant perception lens - Pydantic models.

EXACT Field descriptions from standardized_sec_ai/ppee.py
Following the pattern: Field descriptions ARE the prompt guidance.
"""

from typing import List
from pydantic import BaseModel, Field


class ContrarianViewAnalysis(BaseModel):
    """
    The Contrarian View - What's Everyone Missing?

    Focus on: Variant perception, second-order effects, misunderstood metrics,
    and finding edge through contrarian thinking.
    """
    consensus_view: str = Field(
        description="What is the mainstream Wall Street narrative on this company? Bull consensus (everyone loves it) or bear consensus (everyone hates it)? What's the prevailing story? What metrics is everyone watching? Be specific about current sentiment and positioning."
    )
    consensus_wrong_because: List[str] = Field(
        description="3-5 SPECIFIC reasons why consensus is wrong. Use data and logic. Examples: 'Market focuses on revenue growth but ignores deteriorating unit economics' or 'Everyone assumes competition but moat is actually widening - here's proof'. Be bold but rigorous."
    )
    hidden_strengths: List[str] = Field(
        description="3-5 underappreciated positives not in the mainstream narrative. What are people missing? Hidden assets, undervalued segments, management changes, strategic pivots, etc. Provide evidence from the filing."
    )
    hidden_weaknesses: List[str] = Field(
        description="3-5 overrated aspects everyone loves that are actually problematic. Challenge the sacred cows. Examples: 'Growth is from low-quality acquisitions' or 'Margins expanding due to one-time cost cuts, not sustainable'. Show your work."
    )
    misunderstood_metrics: str = Field(
        description="What is the market obsessing over that doesn't actually matter? What SHOULD they watch instead? Example: 'Market focuses on revenue growth but should watch customer acquisition costs vs lifetime value' or 'Everyone watches P/E but should watch FCF conversion'."
    )
    second_order_effects: List[str] = Field(
        description="Play the tape forward: What happens NEXT that people aren't thinking about? Consequences of consequences. If X happens, then Y happens, then Z happens. Think 2-3 moves ahead. Example: 'Price increases → competitor response → market share loss → margin compression'."
    )
    variant_perception: str = Field(
        description="Your UNIQUE take that differs from consensus. This is your investment thesis. Explain: (1) What you believe that's different, (2) Why consensus is wrong, (3) What edge/information asymmetry you have, (4) What would prove you right. Be specific and bold."
    )
    contrarian_rating: str = Field(
        description="Strong Contrarian BUY (high conviction against pessimistic consensus) / Weak Contrarian Buy / Neutral (no edge) / Contrarian SELL (high conviction against bullish consensus). Explain the edge."
    )


__all__ = ['ContrarianViewAnalysis']
