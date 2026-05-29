#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Moonshot Options Finder Workflow.

Reads the most recent 10-K of a company and decides whether it is a candidate
for an *asymmetric options play* -- and if so, exactly what kind of play to put
on. Designed to be run across a SET of companies (batch) so the resulting
``moonshot_options_score`` can be used to rank which names offer the best
convex, heavily-asymmetric bets.

WHAT IS A MOONSHOT (for an OPTIONS play, specifically)
------------------------------------------------------
A "moonshot" here is NOT a good company. It is a non-linear payoff setup. Owning
calls/LEAPS only pays if FIVE things line up. This workflow exists to test all
five against the filing, because a setup missing any one of them is a lottery
ticket, not a moonshot:

  1. NON-LINEAR PAYOFF IF THE THESIS WORKS. The company is attempting a 0-to-1
     thing (new TAM, platform shift, regulatory unlock, distressed turnaround)
     that re-rates the equity 2-10x+, not 20%. Linear stories belong in the
     stock book, not in options.

  2. A "RIGHT TO WIN" -- why THIS company. Moonshots fail constantly, so the
     asymmetry is only real if the company is *structurally* positioned to
     pull it off: scarce assets (spectrum, mines, FDA designations, data,
     installed base), defensible IP, credible-counterparty partnerships, and
     operators who have done hard things before. No right to win => gamble.

  3. ROOM TO MOVE -- not already priced in. For long options to pay, the market
     must NOT already discount success. Tells: depressed valuation vs the prize,
     a new business hidden inside an "old narrative", small cap vs addressable
     TAM, heavy short interest, thin/absent analyst coverage. If success is
     already in the price, the premium is rich and the asymmetry is gone.

  4. A DATED CATALYST. Options decay. You need identifiable events (launch,
     PDUFA/FDA, contract award, debt resolution, earnings inflection) inside a
     tradeable window so expiry can be matched to the catalyst. No catalyst =>
     buy stock, not options.

  5. SURVIVABLE RUNWAY TO THE CATALYST. THE options-specific killer: a company
     that must raise equity before the catalyst can crater the stock (and your
     calls) even if the thesis is intact. Runway-vs-catalyst timing and
     dilution risk are weighted heavily here.

When all five hold, the payoff distribution is fat-tailed and bimodal -- works
big or fails -- which is exactly the regime where defined-risk long options beat
owning the stock (capped premium, convex upside).

HISTORICAL ANCHORS (used to calibrate the model's judgment)
-----------------------------------------------------------
  * ASTS  -- satellite-direct-to-phone "impossible"; scarce spectrum + AT&T /
             Verizon / Vodafone partnerships (right to win); pre-revenue so
             ignored; LEAPS printed on launch milestones.
  * NVDA  -- pre-2023 AI-compute platform; CUDA moat; market underpricing the
             datacenter inflection; long calls into the ramp.
  * CVNA  -- 2022->2023 distressed turnaround; bankruptcy priced in; debt
             restructuring catalyst; huge short interest; LEAPS ~10x on
             survival + unit-economics inflection.
  * LLY/NVO (GLP-1) -- obesity TAM massively underestimated; clinical readouts
             as catalysts; LEAPS on the TAM re-rating.
  * Counter-example (to enforce discipline): pre-revenue meme name with no
             right-to-win and no dated catalyst => PASS. That is gambling.

ARCHITECTURE
------------
Two sequential Gemini calls (the max the user authorized), because the two jobs
are genuinely different and each is sharper when focused:

  Call 1  DIAGNOSE  -- read the 10-K and test the 5 moonshot conditions, the
                       right-to-win, whether it is priced in, runway, and
                       catalysts. Produces a structured diagnosis.
  Call 2  STRUCTURE -- given ONLY the distilled diagnosis (plus the filing for
                       reference), design the concrete options play: instrument,
                       direction, expiry matched to catalyst+runway, strike
                       aggressiveness, the asymmetry math, and the final
                       ranking score.

A single call with one giant schema tends to shortchange the trade design in
favor of the narrative (or vice-versa); splitting keeps both rigorous. The
final ``schema`` returned for DB/UI compatibility is ``MoonshotOptionsResult``,
which embeds the Call-1 diagnosis as a sub-object so the reasoning is visible
alongside the recommendation.
"""

import csv
import os
import threading
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from custom_workflows.base import CustomWorkflow
from eon.core import get_logger
from eon.core.exceptions import AIProviderError

logger = get_logger(__name__)


# ===========================================================================
# OPTIONAL FACTSET MARKET-DATA ENRICHMENT
# ---------------------------------------------------------------------------
# The 10-K answers the *fundamental* moonshot questions (right-to-win, runway,
# catalysts) but is blind to the *market* side: implied vol, skew, short
# interest, live valuation, and option liquidity. Those are exactly the inputs
# needed to judge "is it priced in?" and "which option structure?". This module
# optionally injects a per-ticker snapshot from a FactSet CSV into both prompts.
#
# It is STRICTLY OPTIONAL and gracefully degrading: if no CSV is configured or
# the ticker is absent, the workflow behaves exactly as the 10-K-only version.
#
# CSV format (one row per ticker; column order does not matter):
#   * A 'ticker' or 'symbol' column is required to key the row.
#   * Any of the recognized columns below are rendered with friendly labels.
#   * Any other columns are passed through generically.
# Data is treated as "as-of" reference context (it may lag by a day or two),
# NOT as executable live quotes -- recommendations stay structural.
#
# Config: set EON_FACTSET_CSV to the CSV path, or drop a file at
#   <data_dir>/factset/options_context.csv
# ===========================================================================

# Recognized columns -> (human label, unit/interpretation hint for the model).
# These are the fields that actually move this workflow's outputs.
_FACTSET_FIELDS: Dict[str, tuple] = {
    "as_of_date": ("As-of date", "snapshot date; data may lag a day or two"),
    "price": ("Last price", "current share price (USD)"),
    "market_cap": ("Market cap", "live market cap; use for the payoff-multiple math"),
    "iv_30d": ("Implied vol (30d)", "annualized IV, %"),
    "iv_rank": (
        "IV rank",
        "0-100; HIGH (>70) = options rich, favor spreads/calendars; LOW (<30) = cheap, favor outright long calls/LEAPS",
    ),
    "iv_percentile": ("IV percentile", "0-100; same interpretation as IV rank"),
    "realized_vol_30d": (
        "Realized vol (30d)",
        "annualized RV, %; IV >> RV means options expensive",
    ),
    "iv_rv_ratio": ("IV/RV ratio", ">1.2 rich, <1.0 cheap"),
    "term_structure": (
        "IV term structure",
        "front-vs-back month; backwardation = event/fear priced near-term",
    ),
    "skew_25d": (
        "25-delta skew",
        "put-call skew; heavy put skew = downside fear priced; call skew = lottery/FOMO priced",
    ),
    "option_volume": ("Avg daily option volume", "contracts/day; liquidity gate"),
    "open_interest": (
        "Total open interest",
        "contracts; liquidity gate -- thin OI = wide spreads, hard to size",
    ),
    "short_interest_pct_float": (
        "Short interest",
        "% of float short; high = contrarian/squeeze signal",
    ),
    "days_to_cover": ("Days to cover", "short-interest / avg volume; >5 = crowded short"),
    "borrow_fee": ("Borrow fee", "% hard-to-borrow cost; high = squeeze risk / expensive to short"),
    "analyst_count": (
        "Analyst coverage",
        "number of covering analysts; low/zero = ignored by the street",
    ),
    "avg_rating": ("Avg analyst rating", "consensus rating"),
    "pct_off_52w_high": ("% off 52-week high", "depressed despite progress = contrarian tell"),
    "ev_sales": ("EV/Sales", "valuation multiple"),
    "ev_ebitda": ("EV/EBITDA", "valuation multiple"),
    "ps_ratio": ("P/S", "valuation multiple"),
    "next_earnings_date": ("Next earnings date", "near-term catalyst / vol event"),
}

_TICKER_KEYS = ("ticker", "symbol", "Ticker", "Symbol", "TICKER", "SYMBOL")

# Class/module-level cache: the analysis service builds a FRESH workflow
# instance per run across many parallel workers, so the CSV is parsed once
# here (keyed by mtime) and shared, guarded by a lock.
_factset_lock = threading.Lock()
_factset_cache: Dict[str, Dict[str, str]] = {}
_factset_cache_path: Optional[str] = None
_factset_cache_mtime: Optional[float] = None


def _resolve_factset_path() -> Optional[Path]:
    """Return the configured FactSet CSV path, or None if not available."""
    env_path = os.environ.get("EON_FACTSET_CSV")
    if env_path:
        p = Path(env_path).expanduser()
        return p if p.is_file() else None
    # Fall back to a default location under the data dir, if config is usable.
    try:
        from eon.core import get_config

        p = get_config().get_data_path("factset", "options_context.csv")
        return p if p.is_file() else None
    except Exception:
        return None


def _load_factset() -> Dict[str, Dict[str, str]]:
    """Load and cache the FactSet CSV, keyed by uppercased ticker.

    Reloads only when the file path or mtime changes. Returns an empty dict
    when no CSV is configured or parsing fails (enrichment is optional).
    """
    global _factset_cache, _factset_cache_path, _factset_cache_mtime

    path = _resolve_factset_path()
    if path is None:
        return {}

    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}

    with _factset_lock:
        if str(path) == _factset_cache_path and mtime == _factset_cache_mtime:
            return _factset_cache

        rows: Dict[str, Dict[str, str]] = {}
        try:
            with path.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                tkey = next((k for k in (reader.fieldnames or []) if k in _TICKER_KEYS), None)
                if tkey is None:
                    logger.warning("FactSet CSV %s has no ticker/symbol column; ignoring.", path)
                    rows = {}
                else:
                    for row in reader:
                        tk = (row.get(tkey) or "").strip().upper()
                        if tk:
                            rows[tk] = {k: (v or "").strip() for k, v in row.items()}
            logger.info("Loaded FactSet market data for %d tickers from %s", len(rows), path)
        except Exception as e:  # malformed CSV must never break analysis
            logger.warning("Failed to load FactSet CSV %s: %s", path, e)
            rows = {}

        _factset_cache = rows
        _factset_cache_path = str(path)
        _factset_cache_mtime = mtime
        return rows


def get_market_context(ticker: str) -> tuple:
    """Return (formatted_block, asof_date) for a ticker.

    formatted_block is "" when no data is available. asof_date is None unless
    the row carries an 'as_of_date'.
    """
    data = _load_factset()
    if not data:
        return "", None
    row = data.get((ticker or "").strip().upper())
    if not row:
        return "", None

    tkey_present = {k for k in _TICKER_KEYS}
    asof = row.get("as_of_date") or None

    lines: List[str] = []
    rendered = set()
    # Recognized fields first, in a sensible order, with labels + hints.
    for col, (label, hint) in _FACTSET_FIELDS.items():
        val = row.get(col)
        if val:
            lines.append(f"  - {label}: {val}  ({hint})")
            rendered.add(col)
    # Pass through any extra columns generically.
    for col, val in row.items():
        if col in rendered or col in tkey_present or not val:
            continue
        lines.append(f"  - {col}: {val}")

    if not lines:
        return "", asof

    header = (
        "EXTERNAL MARKET DATA (FactSet snapshot -- reference context, may lag "
        "a day or two; treat as approximate, NOT as executable live quotes):"
    )
    return header + "\n" + "\n".join(lines), asof


# ===========================================================================
# CALL 1 SCHEMA -- DIAGNOSIS
# ===========================================================================


class MoonshotDiagnosis(BaseModel):
    """Tests the five moonshot conditions against the filing."""

    is_moonshot_candidate: Literal[
        "YES - Clear asymmetric setup",
        "MAYBE - Some asymmetry, gaps remain",
        "NO - Conventional or linear business",
    ] = Field(
        description="Early gate. YES only if there is a genuine non-linear "
        "payoff AND a plausible right-to-win. Most companies are NO -- that is "
        "expected and correct."
    )

    audacious_thesis: str = Field(
        description="ONE sentence: the impossible/non-linear thing this company "
        "is attempting that, if it works, re-rates the equity 2-10x+. "
        "If nothing qualifies, write: 'No non-linear thesis -- conventional business.'"
    )

    payoff_if_it_works: str = Field(
        description="The bull-case magnitude WITH the math. State the addressable "
        "TAM, the share/penetration assumption, and the implied multiple vs "
        "today's market cap. Be specific (e.g. '$50B TAM, 5% share at 4x sales "
        "=> ~6x from here'). Use figures from the filing where possible."
    )

    right_to_win: List[str] = Field(
        description="Why THIS company can plausibly pull it off. List concrete "
        "structural advantages found in the filing: scarce/licensed assets, "
        "defensible IP/patents, named credible-counterparty partnerships, "
        "regulatory designations, installed base, or operators with relevant "
        "track records. Empty list = no right to win = gamble, not moonshot."
    )

    evidence_of_progress: List[str] = Field(
        description="Concrete proof-of-life from the filing (NOT promises): "
        "milestones hit, paying customers/LOIs, pilots succeeded, capacity "
        "coming online, approvals/submissions, patents granted. Distinguish "
        "evidence from aspiration."
    )

    capital_runway: str = Field(
        description="THE options-critical check. Cash on hand, quarterly burn, "
        "months of runway, and debt maturities -- quote real numbers from the "
        "cash-flow/balance sheet. Will they need to raise equity BEFORE the "
        "catalyst? Dilution before the payoff can wipe out option holders even "
        "if the thesis is right. State the dilution/financing risk explicitly."
    )

    dated_catalysts: List[str] = Field(
        description="Specific events with timing that could resolve the thesis. "
        "Format 'Timeframe: Event' (e.g. 'H2 2026: first commercial launch', "
        "'Q3: debt maturity refinance'). Catalysts define the option expiry. "
        "Empty = no tradeable catalyst => prefer stock over options."
    )

    is_it_priced_in: str = Field(
        description="Is the market already discounting success? Assess valuation "
        "vs the prize, whether a new business is hidden inside an 'old narrative', "
        "market cap vs TAM, short interest, and analyst coverage. If success is "
        "already priced, options are expensive and the asymmetry is gone."
    )

    room_to_move: Literal[
        "WIDE - market largely ignores the optionality",
        "SOME - partially recognized",
        "NARROW - success mostly priced in",
    ] = Field(
        description="Judgment on remaining upside room for the OPTION to capture, "
        "derived from is_it_priced_in."
    )

    volatility_character: str = Field(
        description="Fundamental read on the payoff distribution: is it bimodal/"
        "fat-tailed (works big or fails)? Are there binary events that imply "
        "rich near-term implied vol (favor spreads to cut vega) or is vol likely "
        "moderate (favor outright long calls/LEAPS)? Reason from the fundamentals; "
        "live IV is not in the filing."
    )

    key_risks: List[str] = Field(
        description="Top 3-5 ways this fails: technology, regulatory, financing/"
        "dilution, competition, execution, timing. Be brutally honest."
    )

    thesis_killer: str = Field(
        description="The single piece of news that would make you abandon the "
        "trade immediately (e.g. 'failed pivotal trial', 'loss of anchor "
        "partner', 'forced dilutive raise', 'competitor ships first')."
    )

    market_signals_used: List[str] = Field(
        default_factory=list,
        description="If an EXTERNAL MARKET DATA block was provided, list the "
        "specific signals that informed the 'priced-in' / room-to-move call "
        "(e.g. 'IV rank 82 = options rich', 'short interest 31% of float', "
        "'no analyst coverage', 'trading 70% off highs'). Empty if no market "
        "data was supplied (then the judgment is fundamentals-only).",
    )


# ===========================================================================
# CALL 2 SCHEMA -- TRADE STRUCTURE (intermediate; merged into final)
# ===========================================================================


class OptionsStructure(BaseModel):
    """The concrete options play and the ranking scores."""

    moonshot_archetype: Literal[
        "0-to-1 Platform / New TAM",
        "Hypergrowth Inflection",
        "Regulatory / Approval Unlock",
        "Distressed Turnaround / Survival",
        "Hidden Optionality (old narrative masks new)",
        "Commodity / Resource Leverage",
        "Not a Moonshot",
    ] = Field(
        description="Classify the setup. 'Not a Moonshot' if the diagnosis "
        "found no non-linear payoff or no right-to-win."
    )

    one_line_pitch: str = Field(
        description="The trade in one punchy line: '[Company] -- [structure] to "
        "capture [thesis] by [catalyst]; risk capped at premium for [X]x upside.'"
    )

    direction: Literal["Bullish", "Bearish", "No Trade"] = Field(
        description="Trade direction. Most moonshots are Bullish (long convexity). "
        "Bearish only when the filing shows a fragile, over-priced story heading "
        "into a negative catalyst. 'No Trade' for PASS names."
    )

    recommended_play: Literal[
        "Long LEAPS Calls (>12mo)",
        "Long Calls / Call Debit Spread (1-6mo)",
        "Call Calendar / Diagonal",
        "Stock + Protective Put / Risk Reversal",
        "Long Puts / Put Debit Spread (bearish)",
        "No Options Trade (buy stock or pass)",
    ] = Field(
        description="The optimal structure given catalyst timing, runway, and "
        "the volatility character from the diagnosis."
    )

    play_rationale: str = Field(
        description="WHY this structure. Tie it together: match expiry to the "
        "catalyst AND to the cash runway (never hold past a likely dilutive "
        "raise); use spreads/calendars when binary events make near-term IV "
        "rich; use LEAPS when the thesis is a multi-quarter ramp with survivable "
        "runway. Explain the duration choice explicitly."
    )

    suggested_expiry_window: str = Field(
        description="Concrete expiry guidance, e.g. 'Jan-2027 LEAPS -- past the "
        "2026 launch ramp but before the next likely raise' or '3-month, "
        "expiring just after the Q3 contract decision'."
    )

    strike_aggressiveness: Literal[
        "ATM (highest delta, lower convexity)",
        "Moderately OTM (balanced)",
        "Deep OTM (lottery convexity)",
        "N/A",
    ] = Field(
        description="Strike selection and why, given conviction and how much "
        "room-to-move the diagnosis found."
    )

    iv_environment: Literal[
        "Rich - prefer spreads/calendars to cut vega",
        "Moderate - outright longs acceptable",
        "Cheap - favor outright long calls/LEAPS",
        "Unknown - no market data provided",
    ] = Field(
        description="Implied-vol read. Base on the EXTERNAL MARKET DATA block "
        "(IV rank/percentile, IV vs realized) if provided; otherwise 'Unknown - "
        "no market data provided' and reason about structure from fundamentals."
    )

    options_liquidity: Literal[
        "Liquid - tradeable",
        "Thin - use limit orders / smaller size",
        "Illiquid - options impractical, consider stock",
        "Unknown - no market data provided",
    ] = Field(
        description="Tradeability gate from option volume / open interest in the "
        "EXTERNAL MARKET DATA block. A great thesis with illiquid options is not "
        "an options play. 'Unknown' if no market data was supplied."
    )

    asymmetry_summary: str = Field(
        description="The convexity case: realistic option-level upside multiple "
        "if the thesis works vs the defined downside (premium at risk). State "
        "the equity move you are underwriting and the rough option payoff."
    )

    expected_value_logic: str = Field(
        description="Probability-weighted sanity check: estimated probability "
        "the thesis resolves favorably (from the evidence, be honest), times "
        "the payoff, vs the premium. Does the math clear a ~3:1 bar?"
    )

    priced_in_room_score: int = Field(
        ge=0,
        le=100,
        description="How much upside room remains for the OPTION to capture. "
        "100 = market ignores the optionality entirely; 0 = success fully "
        "priced in (no edge).",
    )

    moonshot_options_score: int = Field(
        ge=0,
        le=100,
        description="PRIMARY RANKING SCORE across a set of companies. Combine: "
        "non-linear payoff size + strength of right-to-win + evidence of "
        "progress + room to move + survivable runway + a clean dated catalyst. "
        "70+ = high-conviction asymmetric options bet; 50-69 = worth deeper "
        "work; <50 = pass. Be selective -- most names should score low.",
    )

    final_verdict: Literal[
        "PRIORITY - asymmetric options bet with evidence",
        "INVESTIGATE - promising, needs confirmation",
        "PASS - no asymmetric options edge",
    ] = Field(
        description="Final call. PRIORITY requires all five moonshot conditions " "broadly met."
    )

    position_sizing_note: str = Field(
        description="Sizing guidance treating this as a small, defined-risk "
        "asymmetric bet (premium you can lose entirely), not a core position. "
        "Note if runway/dilution risk argues for staggering entries around the "
        "catalyst."
    )

    what_would_change_my_mind: str = Field(
        description="The specific evidence that would upgrade a PASS or downgrade "
        "a PRIORITY -- the thing to watch between now and the catalyst."
    )


# ===========================================================================
# FINAL SCHEMA -- returned to DB/UI (embeds the diagnosis)
# ===========================================================================


class MoonshotOptionsResult(BaseModel):
    """Final merged result: trade recommendation + the diagnosis behind it."""

    # --- headline / ranking fields (kept at top level for easy sorting) ---
    moonshot_options_score: int = Field(
        ge=0, le=100, description="Primary ranking score (0-100) for comparing companies."
    )
    final_verdict: str = Field(description="PRIORITY / INVESTIGATE / PASS.")
    moonshot_archetype: str = Field(description="The kind of moonshot setup (or 'Not a Moonshot').")
    one_line_pitch: str = Field(description="The trade in one line.")
    recommended_play: str = Field(description="The recommended options structure.")
    priced_in_room_score: int = Field(
        ge=0, le=100, description="Remaining upside room for the option to capture (100 = lots)."
    )

    # --- full trade structure ---
    structure: OptionsStructure = Field(description="The detailed options play and scores.")

    # --- the reasoning behind it ---
    diagnosis: MoonshotDiagnosis = Field(
        description="The moonshot diagnosis from reading the 10-K."
    )

    # --- market-data enrichment metadata (set in code, not by the model) ---
    used_market_data: bool = Field(
        default=False,
        description="True if a FactSet market-data snapshot was injected into "
        "the prompts for this ticker.",
    )
    market_data_asof: Optional[str] = Field(
        default=None,
        description="As-of date of the injected FactSet snapshot, if available.",
    )

    # --- run metadata ---
    partial: bool = Field(
        default=False,
        description="True if one of the two Gemini calls failed and this result " "is degraded.",
    )
    notes: Optional[str] = Field(
        default=None, description="Any degradation / failure notes from the run."
    )


# ===========================================================================
# PROMPTS
# ===========================================================================

_PROMPT_DIAGNOSE = """
You are a contrarian, evidence-driven analyst hunting for ASYMMETRIC OPTIONS
setups in public equities. You are reading the most recent 10-K of {ticker}
(fiscal year {year}).

You are NOT grading this as a quality compounder. You are testing whether it is
a MOONSHOT: a non-linear payoff that an options buyer could capture with capped
downside. A moonshot for an options play requires ALL FIVE of these. Test each
against the filing, honestly:

  1. NON-LINEAR PAYOFF -- a 0-to-1 thesis (new TAM, platform shift, regulatory
     unlock, distressed turnaround) that could re-rate the equity 2-10x+, not 20%.
  2. RIGHT TO WIN -- why THIS company specifically can pull it off: scarce/
     licensed assets, defensible IP, credible-counterparty partnerships,
     regulatory designations, installed base, proven operators. No right to win
     = lottery ticket, not moonshot.
  3. ROOM TO MOVE -- the market does NOT already price success. Look for a new
     business hidden in an old narrative, small cap vs TAM, depressed valuation,
     heavy short interest, thin analyst coverage.
  4. DATED CATALYST -- specific events with timing that resolve the thesis
     inside a tradeable window. No catalyst => prefer stock over options.
  5. SURVIVABLE RUNWAY -- THE options killer. If they must raise equity before
     the catalyst, dilution can crater the stock and the calls even if the
     thesis is right. Check cash, burn, runway months, and debt maturities.

Calibrate against history: ASTS (scarce spectrum + carrier partnerships, pre-
revenue and ignored), NVDA pre-2023 (CUDA moat, datacenter inflection underpriced),
CVNA 2022-23 (bankruptcy priced in, debt-restructuring catalyst, huge short
interest), LLY/NVO GLP-1 (TAM underestimated, clinical readouts as catalysts).
A pre-revenue name with no right-to-win and no dated catalyst is a GAMBLE -- say so.

Be quantitative. Quote cash balances, burn, debt, TAM, and market cap when the
filing gives them. Distinguish EVIDENCE (milestones, contracts, approvals) from
ASPIRATION (plans, intentions). Most companies are NOT moonshots -- mark them so.

USING EXTERNAL MARKET DATA: If an "EXTERNAL MARKET DATA" block is provided below
(FactSet snapshot), use it to sharpen the "ROOM TO MOVE / priced-in" judgment --
short interest, analyst coverage, live valuation vs the prize, and % off highs
are far better priced-in evidence than anything in the 10-K. The filing's market
cap can be a year stale; prefer the snapshot's live market cap for the payoff
math. Record which signals you used in 'market_signals_used'. If no such block
is provided, reason from fundamentals only and leave that list empty.

Produce the structured diagnosis. Do not design the trade yet -- that is the
next step.

Now analyze {ticker} for fiscal year {year}.
"""

_PROMPT_STRUCTURE = """
You are a Senior Derivatives Strategist. A research analyst has handed you the
moonshot diagnosis below for {ticker} (FY{year}). Your job is to design the
concrete OPTIONS PLAY and score it for ranking against other companies.

=== MOONSHOT DIAGNOSIS ===
{diagnosis_context}
=== END DIAGNOSIS ===

Translate the diagnosis into a trade. Rules of the desk:

  * MATCH EXPIRY TO BOTH the catalyst AND the cash runway. Never recommend
    holding an option past the point where a dilutive raise is likely -- that
    is how option holders get wiped out on a correct thesis.
  * If the payoff is bimodal with rich near-term implied vol (binary events),
    prefer DEBIT SPREADS or CALENDARS/DIAGONALS to cut vega; if vol is moderate
    and the thesis is a multi-quarter ramp with survivable runway, prefer LEAPS.
  * Strike aggressiveness scales with conviction and room-to-move: more room +
    higher conviction justifies further OTM convexity; thin room argues ATM or
    no trade.
  * If the diagnosis shows no non-linear payoff, no right-to-win, no catalyst,
    OR no survivable runway, the right answer is usually 'No Options Trade' and
    a PASS verdict. Be selective.
  * Most names should score below 50. Reserve 70+ for setups where all five
    moonshot conditions are broadly met with filing evidence.

USING EXTERNAL MARKET DATA: If an "EXTERNAL MARKET DATA" block is provided below
(FactSet snapshot), it is your edge for structure selection -- the diagnosis
above is fundamentals-only and cannot see the vol surface:
  * IV rank/percentile and IV-vs-realized set 'iv_environment': rich vol => cut
    vega with debit spreads / calendars; cheap vol => outright long calls/LEAPS.
  * Option volume and open interest set 'options_liquidity': thin OI means wide
    spreads and hard sizing -- a great thesis with illiquid options is NOT an
    options play (consider stock or pass).
  * Skew / term structure reveal what the market already prices (priced-in tail).
  * Use the live price / market cap (not the stale 10-K figure) for the payoff
    multiple. Treat all figures as as-of reference context, NOT executable
    quotes -- recommend structure, expiry windows, and strike DISTANCE, not
    hard prices.
If no market-data block is provided, set 'iv_environment' and
'options_liquidity' to their 'Unknown - no market data provided' values and
reason about structure from the fundamentals.

Do the asymmetry math at the option level (upside multiple vs premium at risk)
and a probability-weighted EV sanity check against a ~3:1 bar. Keep scores
consistent with the diagnosis (a NO/NARROW diagnosis cannot yield a 70+ score).

Now produce the options structure for {ticker}.
"""


# ===========================================================================
# WORKFLOW
# ===========================================================================


class MoonshotOptionsFinder(CustomWorkflow):
    """Find the best asymmetric options plays across a set of companies.

    Two-call orchestration: DIAGNOSE the moonshot conditions, then STRUCTURE the
    options trade. Returns a MoonshotOptionsResult whose ``moonshot_options_score``
    is the cross-company ranking field.
    """

    name = "Moonshot Options Finder"
    description = (
        "Reads the most recent 10-K and finds asymmetric options plays -- which "
        "companies are positioned for a non-linear move and exactly what options "
        "structure to use. Ranks a set of companies by moonshot_options_score."
    )
    icon = "🚀"
    min_years = 1
    max_years = 1
    category = "asymmetric"

    @property
    def prompt_template(self) -> str:
        # Required by the base class and used by validate_workflow(). The
        # orchestrated analyze() below uses the two dedicated prompts instead.
        return _PROMPT_DIAGNOSE

    @property
    def schema(self):
        return MoonshotOptionsResult

    # ---- orchestrated two-call analysis ----------------------------------

    def analyze(self, ticker: str, year: int, text: str, provider) -> MoonshotOptionsResult:
        """Run DIAGNOSE then STRUCTURE and merge into a MoonshotOptionsResult.

        Each call is guarded: if DIAGNOSE fails we still attempt STRUCTURE with
        a note; if STRUCTURE fails we return a degraded PASS result built from
        whatever diagnosis we have, so the run is never silently lost.
        """
        filing_block = f"\n\nHere's the filing content:\n\n{text}"

        # Optional FactSet market-data enrichment (no-op if not configured).
        market_block, market_asof = get_market_context(ticker)
        used_market_data = bool(market_block)
        market_section = f"\n\n{market_block}\n" if market_block else ""
        if used_market_data:
            logger.info(f"Moonshot: injected FactSet market data for {ticker}")

        # --- Call 1: DIAGNOSE -------------------------------------------------
        diag_obj: Optional[MoonshotDiagnosis] = None
        diag_err: Optional[str] = None
        try:
            prompt = (
                _PROMPT_DIAGNOSE.format(ticker=ticker, year=year) + market_section + filing_block
            )
            diag_obj = provider.generate_with_retry(
                prompt=prompt,
                schema=MoonshotDiagnosis,
                max_retries=3,
                retry_delay=10,
            )
            logger.info(f"Moonshot DIAGNOSE call succeeded for {ticker} {year}")
        except (AIProviderError, Exception) as e:
            diag_err = str(e)
            logger.error(f"Moonshot DIAGNOSE call failed for {ticker} {year}: {e}")

        # --- Call 2: STRUCTURE -----------------------------------------------
        struct_obj: Optional[OptionsStructure] = None
        struct_err: Optional[str] = None
        try:
            diag_ctx = (
                diag_obj.model_dump_json(indent=2)
                if diag_obj
                else "(DIAGNOSE call failed -- design conservatively and lean PASS "
                "unless the filing clearly shows an asymmetric setup)"
            )
            prompt = (
                _PROMPT_STRUCTURE.format(
                    ticker=ticker,
                    year=year,
                    diagnosis_context=diag_ctx,
                )
                + market_section
                + filing_block
            )
            struct_obj = provider.generate_with_retry(
                prompt=prompt,
                schema=OptionsStructure,
                max_retries=3,
                retry_delay=10,
            )
            logger.info(f"Moonshot STRUCTURE call succeeded for {ticker} {year}")
        except (AIProviderError, Exception) as e:
            struct_err = str(e)
            logger.error(f"Moonshot STRUCTURE call failed for {ticker} {year}: {e}")

        return self._merge(
            ticker,
            diag_obj,
            struct_obj,
            diag_err,
            struct_err,
            used_market_data=used_market_data,
            market_asof=market_asof,
        )

    # ---- merge -----------------------------------------------------------

    def _merge(
        self,
        ticker: str,
        diag_obj: Optional[MoonshotDiagnosis],
        struct_obj: Optional[OptionsStructure],
        diag_err: Optional[str],
        struct_err: Optional[str],
        used_market_data: bool = False,
        market_asof: Optional[str] = None,
    ) -> MoonshotOptionsResult:
        """Assemble the final result, degrading gracefully on partial failure."""
        diagnosis = diag_obj or self._placeholder_diagnosis(diag_err)
        structure = struct_obj or self._placeholder_structure(struct_err)

        failed = []
        if diag_obj is None:
            failed.append("DIAGNOSE")
        if struct_obj is None:
            failed.append("STRUCTURE")

        if struct_obj is None and diag_obj is None:
            # Both calls failed -- raise so the analysis service logs a clean
            # failure rather than persisting a near-empty result.
            raise AIProviderError(
                f"Moonshot Options Finder: both calls failed for {ticker}. "
                f"DIAGNOSE={diag_err}; STRUCTURE={struct_err}"
            )

        notes = None
        if failed:
            notes = (
                f"Partial result -- failed call(s): {', '.join(failed)}. "
                f"DIAGNOSE error={diag_err}; STRUCTURE error={struct_err}"
            )

        return MoonshotOptionsResult(
            moonshot_options_score=structure.moonshot_options_score,
            final_verdict=structure.final_verdict,
            moonshot_archetype=structure.moonshot_archetype,
            one_line_pitch=structure.one_line_pitch,
            recommended_play=structure.recommended_play,
            priced_in_room_score=structure.priced_in_room_score,
            structure=structure,
            diagnosis=diagnosis,
            used_market_data=used_market_data,
            market_data_asof=market_asof,
            partial=bool(failed),
            notes=notes,
        )

    @staticmethod
    def _placeholder_diagnosis(err: Optional[str]) -> MoonshotDiagnosis:
        msg = "DIAGNOSE call failed; placeholder generated by merge step."
        return MoonshotDiagnosis(
            is_moonshot_candidate="NO - Conventional or linear business",
            audacious_thesis=msg,
            payoff_if_it_works=msg,
            right_to_win=[],
            evidence_of_progress=[],
            capital_runway=msg + (f" Error: {err}" if err else ""),
            dated_catalysts=[],
            is_it_priced_in=msg,
            room_to_move="NARROW - success mostly priced in",
            volatility_character=msg,
            key_risks=["Diagnosis unavailable -- call failed."],
            thesis_killer=msg,
        )

    @staticmethod
    def _placeholder_structure(err: Optional[str]) -> OptionsStructure:
        msg = "STRUCTURE call failed; placeholder generated by merge step."
        return OptionsStructure(
            moonshot_archetype="Not a Moonshot",
            one_line_pitch=msg,
            direction="No Trade",
            recommended_play="No Options Trade (buy stock or pass)",
            play_rationale=msg + (f" Error: {err}" if err else ""),
            suggested_expiry_window="N/A",
            strike_aggressiveness="N/A",
            iv_environment="Unknown - no market data provided",
            options_liquidity="Unknown - no market data provided",
            asymmetry_summary=msg,
            expected_value_logic=msg,
            priced_in_room_score=0,
            moonshot_options_score=0,
            final_verdict="PASS - no asymmetric options edge",
            position_sizing_note="No trade -- structuring call failed.",
            what_would_change_my_mind="Re-run the analysis (transient failure).",
        )
