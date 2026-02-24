#!/usr/bin/env python3
"""
Independent Cohort-Based Backtesting
=====================================

Runs every experiment (A–J) as 5 independent single-year cohorts
(FY2020, FY2021, FY2022, FY2023, FY2024), then aggregates via
Fama-MacBeth (mean-of-year-means, t-tested on 5 observations).

Each cohort has at most one observation per ticker → true independence.
No return-window overlap between cohorts at the 1Y horizon.

Run:
    python -m experimental.backtester.run_independent
"""

import logging
import sys
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as scipy_stats

from .exp_lib import (
    DEFAULT_DB_PATH,
    ACTION_RANK,
    Signal,
    load_signals,
    fetch_prices,
    forward_returns,
    pl as _pl_base,
    sig_stars,
    ttest,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

FISCAL_YEARS = [2020, 2021, 2022, 2023, 2024]

# Max available trading days per cohort (entry = April 1 of FY+1, data through ~Feb 2026):
#   FY2020: ~1218d (4.8Y)  FY2021: ~965d (3.8Y)  FY2022: ~714d (2.8Y)
#   FY2023: ~465d (1.8Y)   FY2024: ~214d (0.8Y)
# We use "almost a year" boundaries so every cohort contributes where it can.
# Each period is set just under the max available for the newest qualifying cohort.
COMPUTE_PERIODS = [210, 460, 710, 960, 1210]
DISPLAY_PERIODS = [210, 460, 710, 960, 1210]

# Map periods to human-readable labels: days → decimal years
_PERIOD_LABELS = {
    210: "0.8Y",
    460: "1.8Y",
    710: "2.8Y",
    960: "3.8Y",
    1210: "4.8Y",
}


def pl(p: int) -> str:
    return _PERIOD_LABELS.get(p, f"{p / 252:.1f}Y")

FilterFn = Callable[[Signal], bool]
GroupDef = Dict[str, FilterFn]


# ══════════════════════════════════════════════════════════════════════════════
# GROUP DEFINITIONS — mirrors experiments_abcd.py and experiments_efghij.py
# ══════════════════════════════════════════════════════════════════════════════

def _is_buy(a: str) -> bool:
    return a == "PRIORITY"


def _is_sell(a: str) -> bool:
    return a == "AVOID"


def get_experiment_groups(
    all_signals: List[Signal],
) -> Dict[str, GroupDef]:
    """Return {experiment_name: {group_name: filter_fn}} for all experiments.

    `all_signals` is needed for Experiment D (drift) and J (stable SELL)
    which require cross-year ticker history to compute labels.
    """

    # ── Pre-compute drift labels and stable-sell labels from full history ──
    by_ticker: Dict[str, List[Tuple[int, Signal]]] = defaultdict(list)
    for s in all_signals:
        by_ticker[s.ticker].append((s.fiscal_year, s))
    for t in by_ticker:
        by_ticker[t].sort(key=lambda x: x[0])

    # Drift labels: (ticker, fiscal_year) -> drift category
    drift_labels: Dict[Tuple[str, int], str] = {}
    for ticker, entries in by_ticker.items():
        for i, (fy, sig) in enumerate(entries):
            if i == 0:
                drift_labels[(ticker, fy)] = "first_year"
                continue
            prev_fy = entries[i - 1][0]
            if fy - prev_fy > 2:
                drift_labels[(ticker, fy)] = "first_year"
                continue
            prev_rank = ACTION_RANK.get(entries[i - 1][1].action, 0)
            curr_rank = ACTION_RANK.get(sig.action, 0)
            if curr_rank > prev_rank:
                drift_labels[(ticker, fy)] = "upgrade"
            elif curr_rank < prev_rank:
                drift_labels[(ticker, fy)] = "downgrade"
            elif sig.action in ("BUY", "STRONG BUY"):
                drift_labels[(ticker, fy)] = "stable_buy"
            elif sig.action in ("SELL", "STRONG SELL"):
                drift_labels[(ticker, fy)] = "stable_sell"
            else:
                drift_labels[(ticker, fy)] = "stable_hold"

    # Stable SELL: (ticker, fiscal_year) set for 2+ consecutive SELL years
    stable_sell_set: set = set()
    for ticker, entries in by_ticker.items():
        consecutive = 0
        for i, (fy, sig) in enumerate(entries):
            if sig.action in ("SELL", "STRONG SELL"):
                consecutive += 1
            else:
                consecutive = 0
            if consecutive >= 2:
                stable_sell_set.add((ticker, fy))

    # ── Experiment A: Perspective Agreement ──
    exp_a: GroupDef = {
        "B+C agree PRIORITY (not T)": lambda s: _is_buy(s.buffett_action) and _is_buy(s.contrarian_action) and not _is_buy(s.taleb_action),
        "T+C agree PRIORITY (not B)": lambda s: _is_buy(s.taleb_action) and _is_buy(s.contrarian_action) and not _is_buy(s.buffett_action),
        "ALL 3 agree PRIORITY": lambda s: _is_buy(s.buffett_action) and _is_buy(s.taleb_action) and _is_buy(s.contrarian_action),
        "Buffett PRIORITY only": lambda s: _is_buy(s.buffett_action) and not _is_buy(s.taleb_action) and not _is_buy(s.contrarian_action),
        "Contrarian PRIORITY only": lambda s: not _is_buy(s.buffett_action) and not _is_buy(s.taleb_action) and _is_buy(s.contrarian_action),
        "PASS everywhere (control)": lambda s: s.buffett_action == "PASS" and s.taleb_action == "PASS" and s.contrarian_action == "PASS",
    }

    # ── Experiment B: Conviction Calibration ──
    exp_b: GroupDef = {
        "BUY + High Conviction": lambda s: s.action in ("BUY", "STRONG BUY") and s.conviction == "High",
        "BUY + Medium Conviction": lambda s: s.action in ("BUY", "STRONG BUY") and s.conviction == "Medium",
        "BUY + Low/Unknown Conv.": lambda s: s.action in ("BUY", "STRONG BUY") and s.conviction in ("Low", "Unknown"),
        "SELL + High Conviction": lambda s: s.action in ("SELL", "STRONG SELL") and s.conviction == "High",
        "SELL + Medium Conviction": lambda s: s.action in ("SELL", "STRONG SELL") and s.conviction == "Medium",
        "SELL + Low/Unknown Conv.": lambda s: s.action in ("SELL", "STRONG SELL") and s.conviction in ("Low", "Unknown"),
    }

    # ── Experiment C: Moat × Action ──
    exp_c: GroupDef = {
        "BUY + Wide Moat": lambda s: s.action in ("BUY", "STRONG BUY") and s.moat == "Wide",
        "BUY + Narrow Moat": lambda s: s.action in ("BUY", "STRONG BUY") and s.moat == "Narrow",
        "BUY + No Moat": lambda s: s.action in ("BUY", "STRONG BUY") and s.moat == "None",
        "SELL + Wide Moat": lambda s: s.action in ("SELL", "STRONG SELL") and s.moat == "Wide",
        "SELL + Narrow Moat": lambda s: s.action in ("SELL", "STRONG SELL") and s.moat == "Narrow",
        "SELL + No Moat": lambda s: s.action in ("SELL", "STRONG SELL") and s.moat == "None",
        "BUY + Antifragile/Robust": lambda s: s.action in ("BUY", "STRONG BUY") and s.antifragile in ("Antifragile", "Robust"),
        "BUY + Fragile": lambda s: s.action in ("BUY", "STRONG BUY") and s.antifragile == "Fragile",
        "SELL + Fragile": lambda s: s.action in ("SELL", "STRONG SELL") and s.antifragile == "Fragile",
    }

    # ── Experiment D: Signal Drift ──
    exp_d: GroupDef = {
        "upgrade": lambda s: drift_labels.get((s.ticker, s.fiscal_year)) == "upgrade",
        "downgrade": lambda s: drift_labels.get((s.ticker, s.fiscal_year)) == "downgrade",
        "stable_buy": lambda s: drift_labels.get((s.ticker, s.fiscal_year)) == "stable_buy",
        "stable_sell": lambda s: drift_labels.get((s.ticker, s.fiscal_year)) == "stable_sell",
        "stable_hold": lambda s: drift_labels.get((s.ticker, s.fiscal_year)) == "stable_hold",
    }

    # ── Experiment E: Triple-Combo Fingerprints (top combos only) ──
    exp_e: GroupDef = {
        "(PASS,PASS,PRIORITY)": lambda s: s.buffett_action == "PASS" and s.taleb_action == "PASS" and s.contrarian_action == "PRIORITY",
        "(PRI,INV,PRIORITY)": lambda s: s.buffett_action == "PRIORITY" and s.taleb_action == "INVESTIGATE" and s.contrarian_action == "PRIORITY",
        "(PASS,PASS,PASS)": lambda s: s.buffett_action == "PASS" and s.taleb_action == "PASS" and s.contrarian_action == "PASS",
        "(PASS,INV,PASS)": lambda s: s.buffett_action == "PASS" and s.taleb_action == "INVESTIGATE" and s.contrarian_action == "PASS",
        "(PASS,INV,PRIORITY)": lambda s: s.buffett_action == "PASS" and s.taleb_action == "INVESTIGATE" and s.contrarian_action == "PRIORITY",
        "(PASS,INV,INV)": lambda s: s.buffett_action == "PASS" and s.taleb_action == "INVESTIGATE" and s.contrarian_action == "INVESTIGATE",
        "(INV,INV,INV)": lambda s: s.buffett_action == "INVESTIGATE" and s.taleb_action == "INVESTIGATE" and s.contrarian_action == "INVESTIGATE",
    }

    # ── Experiment F: Final Verdict Alignment ──
    exp_f: GroupDef = {
        "BUY — B+C aligned": lambda s: s.action in ("BUY", "STRONG BUY") and s.buffett_action == "PRIORITY" and s.contrarian_action == "PRIORITY",
        "BUY — C aligned only": lambda s: s.action in ("BUY", "STRONG BUY") and s.contrarian_action == "PRIORITY" and s.buffett_action != "PRIORITY",
        "BUY — B aligned only": lambda s: s.action in ("BUY", "STRONG BUY") and s.buffett_action == "PRIORITY" and s.contrarian_action != "PRIORITY",
        "SELL — all cautious": lambda s: s.action in ("SELL", "STRONG SELL") and s.buffett_action in ("PASS", "INVESTIGATE") and s.contrarian_action in ("PASS", "INVESTIGATE"),
        "SELL — C flags weakness": lambda s: s.action in ("SELL", "STRONG SELL") and s.contrarian_action in ("PRIORITY", "INVESTIGATE"),
    }

    # ── Experiment G: Fragility Factor ──
    exp_g: GroupDef = {
        "Fragile — all actions": lambda s: s.antifragile == "Fragile",
        "Robust — all actions": lambda s: s.antifragile == "Robust",
        "Fragile + BUY": lambda s: s.antifragile == "Fragile" and s.action in ("BUY", "STRONG BUY"),
        "Fragile + SELL": lambda s: s.antifragile == "Fragile" and s.action in ("SELL", "STRONG SELL"),
        "Robust + BUY": lambda s: s.antifragile == "Robust" and s.action in ("BUY", "STRONG BUY"),
        "Robust + SELL": lambda s: s.antifragile == "Robust" and s.action in ("SELL", "STRONG SELL"),
    }

    # ── Experiment H: SELL Anatomy ──
    exp_h: GroupDef = {
        "SELL (all)": lambda s: s.action in ("SELL", "STRONG SELL"),
        "STRONG SELL only": lambda s: s.action == "STRONG SELL",
        "SELL + High Conviction": lambda s: s.action in ("SELL", "STRONG SELL") and s.conviction == "High",
        "SELL + Low/Unknown Conv": lambda s: s.action in ("SELL", "STRONG SELL") and s.conviction in ("Low", "Unknown"),
        "SELL + Wide Moat": lambda s: s.action in ("SELL", "STRONG SELL") and s.moat == "Wide",
        "SELL + No Moat": lambda s: s.action in ("SELL", "STRONG SELL") and s.moat == "None",
        "SELL + Fragile": lambda s: s.action in ("SELL", "STRONG SELL") and s.antifragile == "Fragile",
        "SELL + Robust": lambda s: s.action in ("SELL", "STRONG SELL") and s.antifragile == "Robust",
        "SELL + No Moat + Fragile": lambda s: s.action in ("SELL", "STRONG SELL") and s.moat == "None" and s.antifragile == "Fragile",
    }

    # ── Experiment I: Contrarian Portfolios ──
    exp_i: GroupDef = {
        "Contrarian PRIORITY — all": lambda s: s.contrarian_action == "PRIORITY",
        "C-PRI + Buffett PRIORITY": lambda s: s.contrarian_action == "PRIORITY" and s.buffett_action == "PRIORITY",
        "C-PRI + Buffett PASS (pure)": lambda s: s.contrarian_action == "PRIORITY" and s.buffett_action == "PASS",
        "C-PRI + Final BUY": lambda s: s.contrarian_action == "PRIORITY" and s.action in ("BUY", "STRONG BUY"),
        "C-PRI + Fragile (max hated)": lambda s: s.contrarian_action == "PRIORITY" and s.antifragile == "Fragile",
        "C-PRI + Robust": lambda s: s.contrarian_action == "PRIORITY" and s.antifragile == "Robust",
    }

    # ── Experiment J: Multi-Factor Composite ──
    exp_j: GroupDef = {
        "[L] B+C PRI → BUY": lambda s: s.buffett_action == "PRIORITY" and s.contrarian_action == "PRIORITY" and s.action in ("BUY", "STRONG BUY"),
        "[L] High-conv BUY": lambda s: s.conviction == "High" and s.action in ("BUY", "STRONG BUY"),
        "[L] BUY + Fragile": lambda s: s.action in ("BUY", "STRONG BUY") and s.antifragile == "Fragile",
        "[L] High-conv BUY + Fragile": lambda s: s.conviction == "High" and s.action in ("BUY", "STRONG BUY") and s.antifragile == "Fragile",
        "[S] SELL (all)": lambda s: s.action in ("SELL", "STRONG SELL"),
        "[S] Stable multi-yr SELL": lambda s: (s.ticker, s.fiscal_year) in stable_sell_set,
        "[S] SELL + Fragile": lambda s: s.action in ("SELL", "STRONG SELL") and s.antifragile == "Fragile",
        "[S] SELL + High Conv + Fragile": lambda s: s.action in ("SELL", "STRONG SELL") and s.conviction == "High" and s.antifragile == "Fragile",
        "[S] SELL + No Moat + Fragile": lambda s: s.action in ("SELL", "STRONG SELL") and s.moat == "None" and s.antifragile == "Fragile",
    }

    return {
        "A: Perspective Agreement": exp_a,
        "B: Conviction Calibration": exp_b,
        "C: Moat x Action": exp_c,
        "D: Signal Drift": exp_d,
        "E: Triple-Combo Fingerprints": exp_e,
        "F: Verdict Alignment": exp_f,
        "G: Fragility Factor": exp_g,
        "H: SELL Anatomy": exp_h,
        "I: Contrarian Portfolios": exp_i,
        "J: Multi-Factor Composite": exp_j,
    }


# ══════════════════════════════════════════════════════════════════════════════
# COHORT RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_cohort(
    signals: List[Signal],
    prices: Dict,
    bench,
    groups: GroupDef,
    holding_periods: List[int],
) -> Dict[str, Dict[int, List[float]]]:
    """Run group filters on a single cohort. Returns {group: {period: [excess_returns]}}."""
    data: Dict[str, Dict[int, List[float]]] = {g: {p: [] for p in holding_periods} for g in groups}
    for sig in signals:
        if sig.ticker not in prices:
            continue
        fwd = forward_returns(sig, prices[sig.ticker], bench, holding_periods)
        if not fwd:
            continue
        for gname, fn in groups.items():
            if fn(sig):
                for p, (sr, br, er) in fwd.items():
                    if er is not None:
                        data[gname][p].append(er)
    return data


# ══════════════════════════════════════════════════════════════════════════════
# FAMA-MACBETH AGGREGATION
# ══════════════════════════════════════════════════════════════════════════════

def fama_macbeth(
    year_results: Dict[int, Dict[str, Dict[int, List[float]]]],
    groups: GroupDef,
    holding_periods: List[int],
) -> Dict[str, Dict[int, dict]]:
    """Compute FM stats: mean-of-year-means, t-tested on K year observations.

    Returns {group: {period: {fm_mean, fm_t, fm_p, year_means, year_ns}}}.
    """
    result: Dict[str, Dict[int, dict]] = {}
    for gname in groups:
        result[gname] = {}
        for p in holding_periods:
            year_means = []
            year_ns = []
            for fy in sorted(year_results.keys()):
                vals = year_results[fy].get(gname, {}).get(p, [])
                year_ns.append(len(vals))
                if len(vals) >= 3:
                    year_means.append(float(np.mean(vals)))
                # If < 3 observations in a year, skip that year (don't use noisy mean)

            if len(year_means) >= 3:
                arr = np.array(year_means)
                t, pv = scipy_stats.ttest_1samp(arr, 0)
                result[gname][p] = {
                    "fm_mean": float(arr.mean()),
                    "fm_t": float(t),
                    "fm_p": float(pv),
                    "n_years": len(year_means),
                    "year_means": year_means,
                    "year_ns": year_ns,
                }
            else:
                result[gname][p] = {
                    "fm_mean": None,
                    "fm_t": None,
                    "fm_p": None,
                    "n_years": len(year_means),
                    "year_means": year_means,
                    "year_ns": year_ns,
                }
    return result


# ══════════════════════════════════════════════════════════════════════════════
# DISPLAY
# ══════════════════════════════════════════════════════════════════════════════

def print_cohort_table(
    exp_name: str,
    groups: GroupDef,
    year_results: Dict[int, Dict[str, Dict[int, List[float]]]],
    fm: Dict[str, Dict[int, dict]],
    period: int,
):
    """Print one table for a given experiment and holding period."""
    plabel = pl(period)
    w = 155
    print(f"\n{'═' * w}")
    print(f"  {exp_name} — Independent Cohort Results ({plabel} excess vs SPY)")
    print(f"{'═' * w}")

    # Header
    hdr = f"  {'Group':40s}"
    for fy in FISCAL_YEARS:
        hdr += f"  {'FY' + str(fy):>16s}"
    hdr += f"  {'FM mean':>10s}  {'FM p':>10s}  {'yrs':>4s}"
    print(hdr)
    print("─" * w)

    for gname in groups:
        line = f"  {gname:40s}"
        for fy in FISCAL_YEARS:
            vals = year_results.get(fy, {}).get(gname, {}).get(period, [])
            n = len(vals)
            if n < 3:
                cell = f"n={n}" if n > 0 else "—"
                line += f"  {cell:>16s}"
            else:
                mean_e = np.mean(vals)
                line += f"  {mean_e:>+7.1%} (n={n:>4d})"
        # FM aggregate
        fm_data = fm.get(gname, {}).get(period, {})
        fm_mean = fm_data.get("fm_mean")
        fm_p = fm_data.get("fm_p")
        n_years = fm_data.get("n_years", 0)
        if fm_mean is not None:
            stars = sig_stars(fm_p).strip()
            line += f"  {fm_mean:>+8.1%}{stars:>2s}"
            line += f"  {fm_p:>10.3f}"
        else:
            line += f"  {'N/A':>10s}  {'N/A':>10s}"
        line += f"  {n_years:>4d}"
        print(line)

    print(f"\n  FM = Fama-MacBeth: mean of {len(FISCAL_YEARS)} year-means, t-tested on independent year observations")
    print(f"  {sig_stars(0.001).strip()}p<.01  {sig_stars(0.03).strip()}p<.05  {sig_stars(0.08).strip()}p<.10")


def print_ls_spreads(
    year_results: Dict[int, Dict[str, Dict[int, List[float]]]],
    fm: Dict[str, Dict[int, dict]],
    period: int,
):
    """Print long-short spread table for Experiment J."""
    plabel = pl(period)
    long_groups = ["[L] B+C PRI → BUY", "[L] High-conv BUY", "[L] BUY + Fragile", "[L] High-conv BUY + Fragile"]
    short_groups = ["[S] SELL (all)", "[S] Stable multi-yr SELL", "[S] SELL + Fragile", "[S] SELL + High Conv + Fragile"]

    print(f"\n  LONG/SHORT SPREADS ({plabel}) — per-year and FM aggregate:")
    print(f"  {'L/S combo':50s}", end="")
    for fy in FISCAL_YEARS:
        print(f"  {'FY' + str(fy):>10s}", end="")
    print(f"  {'FM spread':>12s}  {'FM p':>8s}")
    print("─" * 145)

    for lk in long_groups:
        for sk in short_groups:
            year_spreads = []
            cells = []
            for fy in FISCAL_YEARS:
                lv = year_results.get(fy, {}).get(lk, {}).get(period, [])
                sv = year_results.get(fy, {}).get(sk, {}).get(period, [])
                if len(lv) >= 3 and len(sv) >= 3:
                    spread = float(np.mean(lv)) - float(np.mean(sv))
                    year_spreads.append(spread)
                    cells.append(f"{spread:>+8.1%}")
                else:
                    cells.append(f"{'N/A':>10s}")

            if len(year_spreads) < 3:
                continue  # not enough years to FM-test

            fm_arr = np.array(year_spreads)
            fm_spread = float(fm_arr.mean())
            _, fm_p = scipy_stats.ttest_1samp(fm_arr, 0)
            stars = sig_stars(fm_p).strip()

            label = f"L:{lk[4:22]:18s} / S:{sk[4:25]}"
            line = f"  {label:50s}"
            for c in cells:
                line += f"  {c:>10s}"
            line += f"  {fm_spread:>+9.1%}{stars:>3s}  {fm_p:>8.3f}"
            print(line)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 155)
    print("  EON INDEPENDENT COHORT EXPERIMENTS — MAX-HORIZON VIEW")
    print("  Each fiscal year run independently — one observation per ticker per cohort")
    print("  Periods: 0.8Y(210d) 1.8Y(460d) 2.8Y(710d) 3.8Y(960d) 4.8Y(1210d)")
    print("  Fama-MacBeth aggregation: mean of year-means, t-tested on independent year observations")
    print("=" * 155)

    # Load all signals (needed for drift/stable-sell labelling)
    all_signals = load_signals(DEFAULT_DB_PATH, max_fy=2024, min_fy=2020)
    if not all_signals:
        print("No signals found.")
        sys.exit(1)

    # Split into cohorts
    cohorts: Dict[int, List[Signal]] = defaultdict(list)
    for s in all_signals:
        cohorts[s.fiscal_year].append(s)

    print("\n  Cohort sizes:")
    for fy in FISCAL_YEARS:
        sigs = cohorts.get(fy, [])
        unique_t = len(set(s.ticker for s in sigs))
        print(f"    FY{fy}: {len(sigs):5d} signals, {unique_t:5d} unique tickers")

    print("\n  Horizon coverage (which cohorts have data at each period):")
    # FY entry dates: April 1 of FY+1. Data ends ~Feb 2026.
    _max_days = {2020: 1218, 2021: 965, 2022: 714, 2023: 465, 2024: 214}
    for p in DISPLAY_PERIODS:
        contributing = [f"FY{fy}" for fy in FISCAL_YEARS if _max_days.get(fy, 0) >= p]
        print(f"    {pl(p):>5s} ({p:4d}d): {len(contributing)} cohorts — {', '.join(contributing)}")
    print(f"    FM requires >= 3 cohorts with data → max FM-testable horizon: 2.8Y (710d)")

    # Verify independence: no ticker should appear twice within any cohort
    for fy in FISCAL_YEARS:
        tickers = [s.ticker for s in cohorts.get(fy, [])]
        dupes = len(tickers) - len(set(tickers))
        if dupes > 0:
            print(f"  WARNING: FY{fy} has {dupes} duplicate tickers!")

    # Fetch prices once
    all_tickers = sorted(set(s.ticker for s in all_signals))
    min_fy = min(s.fiscal_year for s in all_signals)
    logger.info(f"Fetching prices for {len(all_tickers)} tickers...")
    prices, bench = fetch_prices(all_tickers, min_fy, 2024)
    if bench is None:
        print("ERROR: No SPY data.")
        sys.exit(1)
    logger.info(f"Prices ready for {len(prices)}/{len(all_tickers)} tickers.")

    # Get all experiment group definitions
    experiments = get_experiment_groups(all_signals)

    # Run each cohort for each experiment
    for exp_name, groups in experiments.items():
        year_results: Dict[int, Dict[str, Dict[int, List[float]]]] = {}
        for fy in FISCAL_YEARS:
            year_results[fy] = run_cohort(cohorts.get(fy, []), prices, bench, groups, COMPUTE_PERIODS)

        fm = fama_macbeth(year_results, groups, COMPUTE_PERIODS)

        # Print tables for each display period
        for period in DISPLAY_PERIODS:
            print_cohort_table(exp_name, groups, year_results, fm, period)

        # L/S spreads for Experiment J
        if exp_name.startswith("J"):
            for period in DISPLAY_PERIODS:
                print_ls_spreads(year_results, fm, period)

    # ── SUMMARY: findings that survive FM correction ──
    print(f"\n{'█' * 155}")
    print("  SUMMARY: Findings that survive Fama-MacBeth independence correction (p < 0.10)")
    print(f"{'█' * 155}")

    for exp_name, groups in experiments.items():
        year_results: Dict[int, Dict[str, Dict[int, List[float]]]] = {}
        for fy in FISCAL_YEARS:
            year_results[fy] = run_cohort(cohorts.get(fy, []), prices, bench, groups, COMPUTE_PERIODS)
        fm = fama_macbeth(year_results, groups, COMPUTE_PERIODS)

        hits = []
        for gname in groups:
            for p in DISPLAY_PERIODS:
                fd = fm.get(gname, {}).get(p, {})
                if fd.get("fm_p") is not None and fd["fm_p"] < 0.10:
                    hits.append((gname, p, fd["fm_mean"], fd["fm_p"], fd["n_years"]))

        if hits:
            print(f"\n  {exp_name}:")
            for gname, p, mean_e, pv, ny in hits:
                stars = sig_stars(pv).strip()
                print(f"    {gname:42s}  {pl(p):>4s}  {mean_e:>+8.1%}  p={pv:.3f} {stars:>3s}  ({ny} years)")

    print(f"\n{'=' * 155}")
    print("  All independent cohort experiments complete.")
    print(f"{'=' * 155}")


if __name__ == "__main__":
    main()
