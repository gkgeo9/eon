"""
Signal extraction from SimplifiedAnalysis results.

Defines what constitutes a "STRONG" outcome and extracts tradeable signals
from multi-perspective analysis data.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


class SignalStrength(Enum):
    """Signal strength tiers based on perspective agreement."""

    ALL_PRIORITY = "all_priority"  # All 3 perspectives signal PRIORITY
    MAJORITY_PRIORITY = "majority_priority"  # 2+ perspectives signal PRIORITY
    ANY_PRIORITY = "any_priority"  # At least 1 perspective signals PRIORITY
    NO_SIGNAL = "no_signal"  # No PRIORITY signals


class Perspective(Enum):
    BUFFETT = "buffett"
    TALEB = "taleb"
    CONTRARIAN = "contrarian"


@dataclass
class PerspectiveSignal:
    """Signal from a single analysis perspective."""

    perspective: Perspective
    action_signal: str  # PRIORITY / INVESTIGATE / PASS
    verdict: str  # BUY/HOLD/PASS, EMBRACE/NEUTRAL/AVOID, STRONG BUY/BUY/NEUTRAL/AVOID
    is_strong: bool  # Whether this perspective's signal is "strong"

    # Perspective-specific fields
    moat_rating: Optional[str] = None  # Buffett: Wide/Narrow/None
    antifragile_rating: Optional[str] = None  # Taleb: Fragile/Robust/Antifragile
    conviction_level: Optional[str] = None  # Contrarian: Low/Medium/High


@dataclass
class CompositeSignal:
    """Composite signal from all three perspectives for a single ticker-year."""

    ticker: str
    fiscal_year: int
    signal_date: str  # Estimated date when signal would be actionable (YYYY-MM-DD)

    buffett: PerspectiveSignal
    taleb: PerspectiveSignal
    contrarian: PerspectiveSignal

    strength: SignalStrength
    priority_count: int  # Number of perspectives signaling PRIORITY
    final_verdict: str  # Raw final_verdict text from analysis

    @property
    def is_strong(self) -> bool:
        """Whether this is considered a STRONG outcome for backtesting."""
        return self.strength in (
            SignalStrength.ALL_PRIORITY,
            SignalStrength.MAJORITY_PRIORITY,
        )

    @property
    def perspectives_signaling_priority(self) -> List[str]:
        """Which perspectives signaled PRIORITY."""
        result = []
        if self.buffett.action_signal == "PRIORITY":
            result.append("buffett")
        if self.taleb.action_signal == "PRIORITY":
            result.append("taleb")
        if self.contrarian.action_signal == "PRIORITY":
            result.append("contrarian")
        return result


def _extract_perspective_signal(
    perspective: Perspective,
    data: Dict[str, Any],
) -> PerspectiveSignal:
    """Extract signal from a single perspective's analysis data."""
    action_signal = data.get("action_signal", "PASS").upper().strip()

    if perspective == Perspective.BUFFETT:
        verdict = data.get("buffett_verdict", "PASS").upper().strip()
        moat = data.get("moat_rating", "")
        is_strong = action_signal == "PRIORITY" and verdict == "BUY"
        return PerspectiveSignal(
            perspective=perspective,
            action_signal=action_signal,
            verdict=verdict,
            is_strong=is_strong,
            moat_rating=moat,
        )

    elif perspective == Perspective.TALEB:
        verdict = data.get("taleb_verdict", "AVOID").upper().strip()
        antifragile = data.get("antifragile_rating", "")
        is_strong = action_signal == "PRIORITY" and verdict == "EMBRACE"
        return PerspectiveSignal(
            perspective=perspective,
            action_signal=action_signal,
            verdict=verdict,
            is_strong=is_strong,
            antifragile_rating=antifragile,
        )

    else:  # CONTRARIAN
        verdict = data.get("contrarian_verdict", "NEUTRAL").upper().strip()
        conviction = data.get("conviction_level", "Low")
        is_strong = action_signal == "PRIORITY" and verdict in ("STRONG BUY", "BUY")
        return PerspectiveSignal(
            perspective=perspective,
            action_signal=action_signal,
            verdict=verdict,
            is_strong=is_strong,
            conviction_level=conviction,
        )


def estimate_signal_date(fiscal_year: int) -> str:
    """
    Estimate when a 10-K analysis signal would be actionable.

    SEC requires 10-K filing within 60 days of fiscal year end for large
    accelerated filers, 75 days for accelerated, 90 days for non-accelerated.
    Most fiscal years end Dec 31. We use a conservative 90-day delay, plus
    a few days for analysis processing.

    Returns YYYY-MM-DD string.
    """
    # Fiscal year ending Dec 31 + 90 days filing delay + ~5 days for analysis
    # = approximately April 1 of the following year
    return f"{fiscal_year + 1}-04-01"


def extract_signal(
    ticker: str,
    fiscal_year: int,
    result_data: Dict[str, Any],
) -> CompositeSignal:
    """
    Extract a composite trading signal from a SimplifiedAnalysis result.

    Args:
        ticker: Stock ticker symbol.
        fiscal_year: Fiscal year of the 10-K filing.
        result_data: Parsed SimplifiedAnalysis JSON data.

    Returns:
        CompositeSignal with strength classification.
    """
    buffett_data = result_data.get("buffett", {})
    taleb_data = result_data.get("taleb", {})
    contrarian_data = result_data.get("contrarian", {})

    buffett_signal = _extract_perspective_signal(Perspective.BUFFETT, buffett_data)
    taleb_signal = _extract_perspective_signal(Perspective.TALEB, taleb_data)
    contrarian_signal = _extract_perspective_signal(Perspective.CONTRARIAN, contrarian_data)

    # Count PRIORITY signals
    priority_count = sum(
        1
        for sig in (buffett_signal, taleb_signal, contrarian_signal)
        if sig.action_signal == "PRIORITY"
    )

    # Classify signal strength
    if priority_count == 3:
        strength = SignalStrength.ALL_PRIORITY
    elif priority_count >= 2:
        strength = SignalStrength.MAJORITY_PRIORITY
    elif priority_count >= 1:
        strength = SignalStrength.ANY_PRIORITY
    else:
        strength = SignalStrength.NO_SIGNAL

    return CompositeSignal(
        ticker=ticker,
        fiscal_year=fiscal_year,
        signal_date=estimate_signal_date(fiscal_year),
        buffett=buffett_signal,
        taleb=taleb_signal,
        contrarian=contrarian_signal,
        strength=strength,
        priority_count=priority_count,
        final_verdict=result_data.get("final_verdict", ""),
    )


def filter_strong_signals(
    signals: List[CompositeSignal],
    min_strength: SignalStrength = SignalStrength.ANY_PRIORITY,
) -> List[CompositeSignal]:
    """
    Filter signals to only include those meeting minimum strength threshold.

    Strength ordering (strongest to weakest):
        ALL_PRIORITY > MAJORITY_PRIORITY > ANY_PRIORITY > NO_SIGNAL
    """
    strength_order = {
        SignalStrength.ALL_PRIORITY: 3,
        SignalStrength.MAJORITY_PRIORITY: 2,
        SignalStrength.ANY_PRIORITY: 1,
        SignalStrength.NO_SIGNAL: 0,
    }

    min_level = strength_order[min_strength]
    return [s for s in signals if strength_order[s.strength] >= min_level]
