#!/usr/bin/env python
"""
Moonshot x Excellence Finder Workflow (single Gemini call).

Reads the most recent 10-K (US) or 20-F (foreign annual report) of ONE company
and, in a SINGLE Gemini call, answers two linked questions at once:

  1. IS THIS AN ASYMMETRIC BET? -- the moonshot/options test: does the filing
     describe a non-linear payoff an options buyer could capture with capped
     downside (right-to-win, room-to-move, dated catalyst, survivable runway)?

  2. IS THIS COMPANY ON AN "EXCELLENT" TRAJECTORY? -- even if it is small or
     still growing, does it share the structural traits of companies we have
     already studied as excellent (durable compounders)? Is it investing for the
     future / building something that lasts, or just a lottery ticket?

The headline output is a single blended ``combined_score`` (asymmetry x
excellence) so a whole SET of companies can be ranked in one fast pass.

WHY ONE CALL
------------
The sibling workflow ``moonshot_options_finder`` splits the work into two Gemini
calls (DIAGNOSE then STRUCTURE) for maximum rigor. This workflow deliberately
collapses everything into ONE call so it can be run faster and more regularly
across many names. The prompt is heavily sectioned and the schema kept focused
to keep both the trade design and the excellence comparison honest in a single
pass.

THE EXCELLENT-COMPANY REFERENCE CORPUS
--------------------------------------
A corpus of previously-generated "excellent company" factor analyses (each a
JSON conforming to ``ExcellentCompanyFactors``) is injected into the prompt as
holistic REFERENCE CONTEXT. The model is told to use the corpus to judge whether
the target company echoes those excellent patterns -- it must NOT summarize the
corpus back. The corpus is loaded ONCE (cached) because the analysis service
builds a fresh workflow instance per company in a batch; the corpus is identical
every run.

Loading order (all optional; the workflow degrades to 10-K-only if absent):
  1. EON_EXCELLENCE_FACTORS_FILE  -- explicit path to a single unified file.
  2. <factors_dir>/unified_factors.json  -- a pre-combined file the user builds.
  3. fallback: concatenate every *.json in <factors_dir> (minified).
where factors_dir = EON_EXCELLENCE_FACTORS_DIR or
<repo>/experimental/excellent_company_factors.

The whole corpus is capped to EON_EXCELLENCE_MAX_TOKENS (default 250k) so the
single call never blows past Gemini's context when paired with a large filing.

OPTIONAL MARKET-DATA ENRICHMENT (reused from moonshot_options_finder)
--------------------------------------------------------------------
The 10-K is blind to the market side ("is it priced in?", "which structure?").
The same two optional, independently-degrading sources used by the sibling
workflow are injected here verbatim:
  * FactSet CSV snapshot (EON_FACTSET_CSV) -- IV rank, skew, short interest, live
    valuation, option volume / open interest, etc.
  * Live yfinance aggregate options chain (EON_YFINANCE_OPTIONS=1) -- the real
    tradeable expiry ladder (per-expiry counts, OI, volume, median IV; no strikes).

WALL-CLOCK WATCHDOG
-------------------
Reused from the sibling workflow. Some huge bank/insurer/large-filing 10-Ks make
a single Gemini call grind for hours with no error, and there is no reliable way
to know which filings are too big until a run times out. The TOTAL analysis time
is capped (EON_MOONSHOT_TIMEOUT_SECONDS, default 1800s); on overrun we raise
TimeoutError so the batch abandons this name and moves on.
"""

import json
import os
import threading
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from custom_workflows.base import CustomWorkflow

# Reuse the sibling workflow's battle-tested helpers rather than re-implementing
# them: FactSet/yfinance enrichment, SEC form fingerprinting, and the wall-clock
# watchdog. They are public module-level functions with graceful degradation.
from custom_workflows.moonshot_options_finder import (
    _ANNUAL_FORMS,
    _analysis_timeout_seconds,
    _call_with_deadline,
    _detect_form_type,
    get_market_context,
    get_options_chain_summary,
)
from eon.core import get_logger
from eon.core.exceptions import AIProviderError

logger = get_logger(__name__)


# ===========================================================================
# EXCELLENT-COMPANY REFERENCE CORPUS LOADER
# ---------------------------------------------------------------------------
# Loads the corpus of "excellent company" factor JSONs and renders them into a
# single reference block for the prompt. STRICTLY OPTIONAL and gracefully
# degrading: any failure (missing dir/file, bad JSON) returns ("", meta) and the
# workflow runs 10-K-only.
#
# The corpus is identical for every company in a batch, so it is built ONCE and
# cached in a module global behind a lock (the analysis service spins up a fresh
# workflow instance per run across many parallel workers).
#
# Config:
#   EON_EXCELLENCE_FACTORS_FILE   explicit path to a single unified JSON file
#   EON_EXCELLENCE_FACTORS_DIR    folder of factor JSONs (default: repo path)
#   EON_EXCELLENCE_MAX_TOKENS     corpus token budget (default 250000)
# ===========================================================================

_UNIFIED_FILENAME = "unified_factors.json"

_CORPUS_LOCK = threading.Lock()
# Cached (corpus_block, meta) once built. ``None`` means "not built yet".
_corpus_cache: tuple[str, dict] | None = None


def _repo_root() -> Path:
    """Repo root: this file lives at <repo>/custom_workflows/<thisfile>.py."""
    return Path(__file__).resolve().parents[1]


def _factors_dir() -> Path:
    """Folder holding the excellent-company factor JSONs (env-overridable)."""
    env_dir = os.environ.get("EON_EXCELLENCE_FACTORS_DIR")
    if env_dir and env_dir.strip():
        return Path(env_dir.strip().strip('"').strip("'")).expanduser()
    return _repo_root() / "experimental" / "excellent_company_factors"


def _excellence_max_tokens() -> int:
    """Token budget for the corpus so the single call never overruns context."""
    try:
        return max(1000, int(os.environ.get("EON_EXCELLENCE_MAX_TOKENS", "250000")))
    except (TypeError, ValueError):
        return 250000


def _minify_json_file(path: Path) -> str | None:
    """Return a minified one-line JSON string for ``path``, or None on failure."""
    try:
        with path.open(encoding="utf-8-sig") as fh:
            obj = json.load(fh)
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    except Exception as e:  # bad/locked/oversized JSON must never break analysis
        logger.warning("Excellence corpus: failed to read %s: %s", path, e)
        return None


def _resolve_unified_file() -> Path | None:
    """Return the unified corpus file path if one exists, else None."""
    env_file = os.environ.get("EON_EXCELLENCE_FACTORS_FILE")
    if env_file and env_file.strip():
        p = Path(env_file.strip().strip('"').strip("'")).expanduser()
        if p.is_file():
            return p
        logger.warning("EON_EXCELLENCE_FACTORS_FILE=%s is not a file; ignoring.", env_file)
    unified = _factors_dir() / _UNIFIED_FILENAME
    return unified if unified.is_file() else None


def _build_excellence_corpus() -> tuple[str, dict]:
    """Build the corpus block + metadata. Pure function (no caching here).

    Returns ("", meta) when no corpus is available so the workflow degrades to a
    10-K-only analysis. ``meta`` always carries 'source' and 'reason'.
    """
    max_tokens = _excellence_max_tokens()
    max_chars = max_tokens * 4  # rough chars-per-token heuristic

    # --- 1 & 2: a single unified file (explicit env, or unified_factors.json) ---
    unified = _resolve_unified_file()
    if unified is not None:
        body = _minify_json_file(unified)
        if body:
            truncated = len(body) > max_chars
            if truncated:
                body = body[:max_chars]
            meta = {
                "source": "unified",
                "file_count": 1,
                "approx_tokens": len(body) // 4,
                "truncated": truncated,
                "reason": None,
            }
            return body, meta

    # --- 3: fallback -- concatenate every other *.json in the factors dir ------
    fdir = _factors_dir()
    if not fdir.is_dir():
        return "", {
            "source": None,
            "file_count": 0,
            "approx_tokens": 0,
            "truncated": False,
            "reason": f"factors dir not found: {fdir}",
        }

    parts: list[str] = []
    used = 0
    total_chars = 0
    truncated = False
    files = sorted(p for p in fdir.glob("*.json") if p.name != _UNIFIED_FILENAME)
    for path in files:
        body = _minify_json_file(path)
        if not body:
            continue
        chunk = f"### {path.stem}\n{body}"
        if total_chars + len(chunk) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 200:  # only bother if a meaningful slice fits
                parts.append(chunk[:remaining])
                used += 1
            truncated = True
            break
        parts.append(chunk)
        total_chars += len(chunk) + 2  # +2 for the join separator
        used += 1

    if not parts:
        return "", {
            "source": None,
            "file_count": 0,
            "approx_tokens": 0,
            "truncated": False,
            "reason": f"no readable *.json files in {fdir}",
        }

    block = "\n\n".join(parts)
    return block, {
        "source": "concatenated",
        "file_count": used,
        "approx_tokens": len(block) // 4,
        "truncated": truncated,
        "reason": None,
    }


def get_excellence_corpus() -> tuple[str, dict]:
    """Return the cached (corpus_block, meta), building it once on first use."""
    global _corpus_cache
    with _CORPUS_LOCK:
        if _corpus_cache is None:
            try:
                _corpus_cache = _build_excellence_corpus()
            except Exception as e:  # never let corpus loading break the analysis
                logger.warning("Excellence corpus build failed: %s", e)
                _corpus_cache = (
                    "",
                    {
                        "source": None,
                        "file_count": 0,
                        "approx_tokens": 0,
                        "truncated": False,
                        "reason": f"build error: {e}",
                    },
                )
        return _corpus_cache


# ===========================================================================
# OUTPUT SCHEMA (single call -> single result)
# ===========================================================================


class SharedTrait(BaseModel):
    """One excellent-company trait the target company plausibly shares."""

    trait: str = Field(
        description="The excellent-company trait the target plausibly shares "
        "(e.g. 'scalable platform economics', 'reinvestment-driven compounding', "
        "'durable moat from switching costs')."
    )
    evidence_in_filing: str = Field(
        description="Concrete evidence FROM THIS COMPANY'S filing/market data that "
        "it exhibits (or is building toward) this trait. Quote figures where possible."
    )
    excellent_pattern_echoed: str = Field(
        description="Which pattern in the excellent-company reference corpus this "
        "echoes (name the kind of excellent company / factor it resembles). Do NOT "
        "summarize the whole corpus -- just name the specific pattern matched."
    )


class MoonshotExcellenceResult(BaseModel):
    """Single-call result: asymmetric-bet diagnosis blended with an excellence read."""

    # --- headline / ranking (top-level for easy cross-company sorting) -------
    combined_score: int = Field(
        ge=0,
        le=100,
        description="PRIMARY RANKING SCORE across a set of companies. A blend of "
        "asymmetry_score (the convex options/moonshot setup) and "
        "excellence_alignment_score (how strongly it shares excellent-company "
        "traits / is investing for the future). Weight asymmetry and excellence "
        "roughly equally, but a name with NO non-linear payoff cannot score high "
        "no matter how 'excellent' it looks, and vice-versa. 70+ = strong "
        "asymmetric bet that is also building toward durable excellence; 50-69 = "
        "worth deeper work; <50 = pass. Be selective -- most names should be low.",
    )
    final_verdict: Literal[
        "PRIORITY - asymmetric bet also building toward excellence",
        "INVESTIGATE - promising, needs confirmation",
        "PASS - no asymmetric edge or no excellence trajectory",
    ] = Field(
        description="Final call. PRIORITY requires BOTH a real asymmetric setup AND a credible excellence trajectory."
    )
    moonshot_archetype: Literal[
        "0-to-1 Platform / New TAM",
        "Hypergrowth Inflection",
        "Regulatory / Approval Unlock",
        "Distressed Turnaround / Survival",
        "Hidden Optionality (old narrative masks new)",
        "Commodity / Resource Leverage",
        "Not a Moonshot",
    ] = Field(
        description="Classify the setup. 'Not a Moonshot' if there is no non-linear payoff or no right-to-win."
    )
    one_line_pitch: str = Field(
        description="The thesis in one punchy line: '[Company] -- [structure] to "
        "capture [thesis] by [catalyst]; building [excellent trait]; risk capped "
        "at premium for [X]x upside.'"
    )
    recommended_play: Literal[
        "Long LEAPS Calls (>12mo)",
        "Long Calls / Call Debit Spread (1-6mo)",
        "Call Calendar / Diagonal",
        "Stock + Protective Put / Risk Reversal",
        "Long Puts / Put Debit Spread (bearish)",
        "No Options Trade (buy stock or pass)",
    ] = Field(
        description="The optimal options structure given catalyst timing, runway, and the volatility character."
    )

    # --- sub-scores ----------------------------------------------------------
    asymmetry_score: int = Field(
        ge=0,
        le=100,
        description="The convex-options/moonshot setup strength ALONE. Combine: "
        "non-linear payoff size + strength of right-to-win + evidence of progress "
        "+ room to move + survivable runway + a clean dated catalyst. 70+ only "
        "when all five moonshot conditions are broadly met with filing evidence.",
    )
    excellence_alignment_score: int = Field(
        ge=0,
        le=100,
        description="How strongly this company shares the structural traits of the "
        "excellent companies in the reference corpus -- even if it is small or "
        "still growing. Reward durable moats, reinvestment-driven compounding, "
        "scalable economics, and credible long-horizon investment for the future. "
        "Penalize hype with no underlying build. Judge trajectory, not just size.",
    )
    priced_in_room_score: int = Field(
        ge=0,
        le=100,
        description="How much upside room remains for the bet to capture. 100 = "
        "market ignores the optionality entirely; 0 = success fully priced in.",
    )

    # --- moonshot diagnosis (condensed single-call version) ------------------
    audacious_thesis: str = Field(
        description="ONE sentence: the non-linear thing this company is attempting "
        "that, if it works, re-rates the equity 2-10x+. If nothing qualifies, "
        "write: 'No non-linear thesis -- conventional business.'"
    )
    payoff_if_it_works: str = Field(
        description="Bull-case magnitude WITH the math: addressable TAM, the share/"
        "penetration assumption, and the implied multiple vs today's market cap "
        "(prefer the live market cap from market data if provided)."
    )
    right_to_win: list[str] = Field(
        description="Why THIS company can plausibly pull it off: scarce/licensed "
        "assets, defensible IP, named credible-counterparty partnerships, "
        "regulatory designations, installed base, proven operators. Empty = gamble."
    )
    evidence_of_progress: list[str] = Field(
        description="Concrete proof-of-life from the filing (NOT promises): "
        "milestones hit, paying customers/LOIs, pilots, capacity, approvals, "
        "patents granted. Distinguish evidence from aspiration."
    )
    capital_runway: str = Field(
        description="THE options-critical check. Cash on hand, quarterly burn, "
        "runway months, debt maturities -- quote real numbers. Will they need to "
        "raise equity BEFORE the catalyst? State dilution/financing risk explicitly."
    )
    dated_catalysts: list[str] = Field(
        description="Specific events with timing that resolve the thesis, formatted "
        "'Timeframe: Event' (e.g. 'H2 2026: first commercial launch'). Empty = no "
        "tradeable catalyst => prefer stock over options."
    )
    is_it_priced_in: str = Field(
        description="Is the market already discounting success? Assess valuation vs "
        "the prize, a new business hidden in an old narrative, market cap vs TAM, "
        "short interest, and analyst coverage."
    )
    room_to_move: Literal[
        "WIDE - market largely ignores the optionality",
        "SOME - partially recognized",
        "NARROW - success mostly priced in",
    ] = Field(
        description="Remaining upside room for the bet to capture, derived from is_it_priced_in."
    )
    key_risks: list[str] = Field(
        description="Top 3-5 ways this fails: technology, regulatory, financing/"
        "dilution, competition, execution, timing. Be brutally honest."
    )
    thesis_killer: str = Field(
        description="The single piece of news that would make you abandon the bet "
        "immediately (e.g. 'failed pivotal trial', 'loss of anchor partner')."
    )

    # --- excellence alignment (the new scored dimension) ---------------------
    shared_excellent_traits: list[SharedTrait] = Field(
        description="The specific excellent-company traits this company plausibly "
        "shares or is building toward, each with filing evidence and the corpus "
        "pattern it echoes. Empty if it shares none."
    )
    missing_or_weak_traits: list[str] = Field(
        description="Important excellent-company traits this company clearly LACKS "
        "or is weak on -- the gaps between it and a durable compounder."
    )
    excellence_trajectory: Literal[
        "Already exhibits excellent-company traits",
        "Early but credibly on-track",
        "Investing for the future, unproven",
        "Not on an excellence path",
    ] = Field(
        description="Overall read on whether this company is on a durable-excellence trajectory, allowing for small/early companies."
    )
    on_track_assessment: str = Field(
        description="Is this company genuinely investing for the future and building "
        "something durable, or just chasing a one-off payoff? Tie the judgment to "
        "the excellent-company corpus and concrete filing evidence (R&D, capex, "
        "reinvestment, capability-building, capital allocation)."
    )

    # --- options structure ---------------------------------------------------
    direction: Literal["Bullish", "Bearish", "No Trade"] = Field(
        description="Trade direction. Most moonshots are Bullish (long convexity); "
        "Bearish only for a fragile, over-priced story into a negative catalyst."
    )
    suggested_expiry_window: str = Field(
        description="Concrete expiry guidance matched to BOTH the catalyst and the "
        "cash runway (never hold past a likely dilutive raise), e.g. 'Jan-2027 "
        "LEAPS -- past the 2026 launch ramp but before the next likely raise'."
    )
    strike_aggressiveness: Literal[
        "ATM (highest delta, lower convexity)",
        "Moderately OTM (balanced)",
        "Deep OTM (lottery convexity)",
        "N/A",
    ] = Field(
        description="Strike selection and why, given conviction and how much room-to-move there is."
    )
    iv_environment: Literal[
        "Rich - prefer spreads/calendars to cut vega",
        "Moderate - outright longs acceptable",
        "Cheap - favor outright long calls/LEAPS",
        "Unknown - no market data provided",
    ] = Field(
        description="Implied-vol read from the EXTERNAL MARKET DATA block if provided; otherwise 'Unknown'."
    )
    options_liquidity: Literal[
        "Liquid - tradeable",
        "Thin - use limit orders / smaller size",
        "Illiquid - options impractical, consider stock",
        "Unknown - no market data provided",
    ] = Field(
        description="Tradeability gate from option volume / open interest if provided; otherwise 'Unknown'."
    )
    asymmetry_summary: str = Field(
        description="The convexity case: realistic option-level upside multiple if "
        "the thesis works vs the defined downside (premium at risk)."
    )
    expected_value_logic: str = Field(
        description="Probability-weighted sanity check: honest probability the "
        "thesis resolves favorably, times the payoff, vs the premium. Clear ~3:1?"
    )

    # --- run metadata (set in code, not by the model) ------------------------
    used_market_data: bool = Field(
        default=False, description="True if a FactSet market-data snapshot was injected."
    )
    market_data_asof: str | None = Field(
        default=None, description="As-of date of the injected FactSet snapshot, if available."
    )
    used_live_options_chain: bool = Field(
        default=False,
        description="True if a live yfinance aggregate options-chain summary was injected.",
    )
    used_excellence_corpus: bool = Field(
        default=False, description="True if the excellent-company reference corpus was injected."
    )
    excellence_source: str | None = Field(
        default=None, description="How the corpus was loaded: 'unified', 'concatenated', or None."
    )
    excellence_factor_count: int | None = Field(
        default=None,
        description="Number of factor files included in the corpus (1 for a unified file).",
    )
    excellence_truncated: bool = Field(
        default=False, description="True if the corpus was truncated to fit the token budget."
    )
    notes: str | None = Field(
        default=None, description="Any degradation / form-type / corpus notes from the run."
    )


# ===========================================================================
# PROMPT (single combined template)
# ===========================================================================

_PROMPT = """
You are a contrarian, evidence-driven analyst hunting for ASYMMETRIC BETS in
public equities. You are reading the most recent annual report (a {form}) of
{ticker} (fiscal year {year}).

You must do TWO linked jobs in this one pass, and keep BOTH rigorous:

==================================================================
JOB 1 -- IS THIS AN ASYMMETRIC BET (MOONSHOT FOR AN OPTIONS PLAY)?
==================================================================
You are NOT grading this as a quality compounder for Job 1. A moonshot for an
options play requires ALL FIVE of these -- test each against the filing, honestly:

  1. NON-LINEAR PAYOFF -- a 0-to-1 thesis (new TAM, platform shift, regulatory
     unlock, distressed turnaround) that could re-rate the equity 2-10x+, not 20%.
  2. RIGHT TO WIN -- why THIS company specifically can pull it off: scarce/
     licensed assets, defensible IP, credible-counterparty partnerships,
     regulatory designations, installed base, proven operators. No right to win
     = lottery ticket, not moonshot.
  3. ROOM TO MOVE -- the market does NOT already price success. Look for a new
     business hidden in an old narrative, small cap vs TAM, depressed valuation,
     heavy short interest, thin analyst coverage.
  4. DATED CATALYST -- specific events with timing that resolve the thesis inside
     a tradeable window. No catalyst => prefer stock over options.
  5. SURVIVABLE RUNWAY -- THE options killer. If they must raise equity before
     the catalyst, dilution can crater the stock and the calls even if the thesis
     is right. Check cash, burn, runway months, and debt maturities.

Calibrate against history: ASTS (scarce spectrum + carrier partnerships, pre-
revenue and ignored), NVDA pre-2023 (CUDA moat, datacenter inflection underpriced),
CVNA 2022-23 (bankruptcy priced in, debt-restructuring catalyst, huge short
interest), LLY/NVO GLP-1 (TAM underestimated, clinical readouts as catalysts).
A pre-revenue name with no right-to-win and no dated catalyst is a GAMBLE -- say so.

Then design the concrete OPTIONS PLAY: match the expiry to BOTH the catalyst AND
the cash runway (never hold past a likely dilutive raise); prefer debit spreads/
calendars when binary events make near-term IV rich, LEAPS when it is a multi-
quarter ramp with survivable runway; scale strike aggressiveness with conviction
and room-to-move. Do the asymmetry math (option upside multiple vs premium at
risk) and a probability-weighted EV check against a ~3:1 bar.

==================================================================
JOB 2 -- IS THIS COMPANY ON AN "EXCELLENT" TRAJECTORY?
==================================================================
Below is an EXCELLENT-COMPANY REFERENCE CORPUS: a library of recurring success
patterns and/or per-company factor analyses distilled from companies we have
already studied as excellent, durable compounders (their mechanisms of advantage,
capital allocation, and failure modes). Use it HOLISTICALLY as a yardstick. Even
if {ticker} is small or still growing, judge whether it SHARES the structural
traits and operating MECHANISMS of those excellent companies -- durable moats,
reinvestment-driven compounding, scalable economics, operational density / network
effects, disciplined capital allocation, and credible long-horizon investment for
the future (R&D, capex, capability-building). Name the actual mechanism of
advantage, not just the category, and test whether it is strengthening, stable, or
weakening. Distinguish a company genuinely BUILDING something durable from one
merely chasing a one-off payoff.

IMPORTANT: Do NOT summarize the corpus back to me. Use it only as the standard
against which you judge {ticker}, and when you cite a match, name the specific
excellent pattern or mechanism it echoes. If the corpus is empty/absent, judge
excellence from first principles and note that no corpus was provided.

=== EXCELLENT-COMPANY REFERENCE CORPUS START ===
{excellence_corpus}
=== EXCELLENT-COMPANY REFERENCE CORPUS END ===

==================================================================
USING EXTERNAL MARKET DATA
==================================================================
If an "EXTERNAL MARKET DATA" (FactSet snapshot) and/or a "LIVE OPTIONS CHAIN"
(yfinance aggregate) block is provided below, use it to sharpen the priced-in /
room-to-move call and the trade structure: short interest, analyst coverage,
live valuation vs the prize, and % off highs are far better priced-in evidence
than the 10-K; IV rank / IV-vs-realized set 'iv_environment'; option volume / open
interest set 'options_liquidity'; anchor 'suggested_expiry_window' to an expiry
that actually exists with real OI/volume. The filing's market cap can be a year
stale -- prefer the snapshot's live market cap for the payoff math. Treat all
figures as as-of reference context, NOT executable quotes -- recommend structure,
expiry windows, and strike DISTANCE, not hard prices. If no such block is
provided, set 'iv_environment' and 'options_liquidity' to their 'Unknown' values
and reason from fundamentals.

The market-data block may also carry MULTI-YEAR fundamentals -- a 'Net Sales'
series (latest plus 'Net Sales - N y ago'), 5y/10y compound total returns, free
cash flow, EBITDA margin, total debt/equity, and insider purchases. Use these
directly for JOB 2: a long, steady revenue/return compounding record and positive
self-funding cash flow are direct evidence of an excellent trajectory, while heavy
leverage with negative cash flow sharpens the dilution/runway risk in JOB 1.

==================================================================
SCORING
==================================================================
  * 'asymmetry_score' (0-100): Job 1 strength alone (the five conditions).
  * 'excellence_alignment_score' (0-100): Job 2 -- how strongly it shares the
    corpus's excellent traits / is investing for the future (judge trajectory,
    not size).
  * 'combined_score' (0-100): the PRIMARY ranking field -- blend the two roughly
    equally, BUT a name with no non-linear payoff cannot score high however
    excellent it looks, and a hype name with no excellence build cannot score
    high however convex it looks. Be selective: most names should score below 50;
    reserve 70+ for setups that are BOTH a real asymmetric bet AND credibly
    building toward durable excellence.

Be quantitative -- quote cash, burn, debt, TAM, and market cap where the filing
gives them. Distinguish EVIDENCE from ASPIRATION. Most companies are neither
moonshots nor excellent -- mark them so.

Now analyze {ticker} for fiscal year {year} and produce the structured result.
"""


# ===========================================================================
# WORKFLOW
# ===========================================================================


class MoonshotExcellenceFinder(CustomWorkflow):
    """Single-call asymmetric-bet finder that also scores excellence alignment.

    Reads the most recent 10-K/20-F, injects the optional FactSet + live-chain
    market data and the excellent-company reference corpus, and makes ONE Gemini
    call that returns a ``MoonshotExcellenceResult`` whose ``combined_score`` is
    the cross-company ranking field.
    """

    name = "Moonshot x Excellence Finder"
    description = (
        "Single Gemini call: reads the most recent 10-K/20-F, hunts for an "
        "asymmetric options/moonshot setup, AND scores how strongly the company "
        "shares the traits of known excellent compounders. Ranks a set of "
        "companies by a blended combined_score."
    )
    icon = "🌙"
    min_years = 1
    max_years = 1
    category = "asymmetric"

    @property
    def prompt_template(self) -> str:
        return _PROMPT

    @property
    def schema(self):
        return MoonshotExcellenceResult

    # ---- single-call analysis -------------------------------------------------

    def analyze(self, ticker: str, year: int, text: str, provider) -> MoonshotExcellenceResult:
        """Run the one combined Gemini call and stamp run metadata on the result."""
        # --- Wall-clock watchdog (same as moonshot_options_finder) -----------
        # Some huge bank/insurer/large filings make a single Gemini call grind
        # for hours with no error; there is no reliable way to know which until a
        # run times out. Cap TOTAL time so the batch moves on instead of stalling.
        import time

        deadline_s = _analysis_timeout_seconds()
        _start = time.monotonic()

        def _remaining() -> float:
            return deadline_s - (time.monotonic() - _start)

        # --- Filing-type sanity ----------------------------------------------
        detected_form = _detect_form_type(text)
        form_note: str | None = None
        if detected_form is None:
            form_note = (
                "Could not detect the SEC form type from the document; analyzed "
                "as a 10-K by default."
            )
            logger.warning("MoonshotExcellence: %s FY%s -- %s", ticker, year, form_note)
        elif detected_form not in _ANNUAL_FORMS:
            msg = (
                f"Document for {ticker} FY{year} looks like a {detected_form}, not "
                f"an annual report (10-K/20-F). This workflow requires a full "
                f"annual filing; failing fast."
            )
            logger.error("MoonshotExcellence: %s", msg)
            raise AIProviderError(msg)
        elif detected_form != "10-K":
            form_note = (
                f"Filing is a {detected_form} (foreign/variant annual report), not "
                f"a standard 10-K. Analysis proceeded with that in mind."
            )
            logger.info("MoonshotExcellence: %s FY%s -- %s", ticker, year, form_note)

        form_label = detected_form or "10-K"
        filing_block = f"\n\nHere's the filing content:\n\n{text}"

        # --- Excellent-company reference corpus (cached, optional) -----------
        corpus_block, corpus_meta = get_excellence_corpus()
        used_excellence_corpus = bool(corpus_block)
        corpus_for_prompt = (
            corpus_block if corpus_block else "(no excellent-company corpus provided)"
        )
        if used_excellence_corpus:
            logger.info(
                "MoonshotExcellence: injected excellence corpus for %s "
                "(source=%s, files=%s, ~%s tokens, truncated=%s)",
                ticker,
                corpus_meta.get("source"),
                corpus_meta.get("file_count"),
                corpus_meta.get("approx_tokens"),
                corpus_meta.get("truncated"),
            )
        else:
            logger.warning(
                "MoonshotExcellence: no excellence corpus for %s (%s); running "
                "10-K-only excellence judgment.",
                ticker,
                corpus_meta.get("reason"),
            )

        # --- Optional external market data (no-ops unless configured) --------
        factset_block, market_asof = get_market_context(ticker)
        chain_block = get_options_chain_summary(ticker)
        used_market_data = bool(factset_block)
        used_live_options_chain = bool(chain_block)
        market_block = "\n\n".join(b for b in (factset_block, chain_block) if b)
        market_section = f"\n\n{market_block}\n" if market_block else ""
        if market_block:
            logger.info(
                "MoonshotExcellence: injected external market data for %s "
                "(factset=%s, live_chain=%s)",
                ticker,
                used_market_data,
                used_live_options_chain,
            )

        # --- The single Gemini call ------------------------------------------
        prompt = (
            _PROMPT.format(
                ticker=ticker,
                year=year,
                form=form_label,
                excellence_corpus=corpus_for_prompt,
            )
            + market_section
            + filing_block
        )
        result: MoonshotExcellenceResult = _call_with_deadline(
            lambda: provider.generate_with_retry(
                prompt=prompt,
                schema=MoonshotExcellenceResult,
                max_retries=3,
                retry_delay=10,
            ),
            _remaining(),
        )
        logger.info(f"MoonshotExcellence call succeeded for {ticker} {year}")

        # --- Stamp code-owned metadata ---------------------------------------
        result.used_market_data = used_market_data
        result.market_data_asof = market_asof
        result.used_live_options_chain = used_live_options_chain
        result.used_excellence_corpus = used_excellence_corpus
        result.excellence_source = corpus_meta.get("source")
        result.excellence_factor_count = corpus_meta.get("file_count") or None
        result.excellence_truncated = bool(corpus_meta.get("truncated"))

        notes_parts: list[str] = []
        if form_note:
            notes_parts.append(form_note)
        if not used_excellence_corpus and corpus_meta.get("reason"):
            notes_parts.append(f"Excellence corpus unavailable: {corpus_meta['reason']}")
        if notes_parts:
            result.notes = (
                f"{result.notes} | " + " | ".join(notes_parts)
                if result.notes
                else " | ".join(notes_parts)
            )

        return result
