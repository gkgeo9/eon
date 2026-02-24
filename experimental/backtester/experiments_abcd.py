#!/usr/bin/env python3
"""
Extra EON backtesting experiments.

Experiment A: Perspective Agreement vs. Disagreement
  Does it matter *which* two perspectives agree (Buffett+Taleb vs Buffett+Contrarian
  vs Taleb+Contrarian)? Does a cross-signal DISAGREEMENT (one PRIORITY, one AVOID)
  predict higher volatility / lower returns?

Experiment B: Conviction Calibration
  Is the AI's stated conviction level (High / Medium / Low) actually calibrated?
  Do High-conviction calls outperform Medium/Low-conviction calls?
  Tested separately for BUY and SELL signals.

Experiment C: Moat + Action Interaction
  Wide-Moat BUYs vs Narrow-Moat BUYs vs No-Moat BUYs — does moat quality
  predict which BUY calls actually generate alpha?
  Wide-Moat SELLs vs narrow/no-moat SELLs — does the AI correctly identify
  moat deterioration?

Experiment D: Year-over-Year Signal Drift
  For tickers analyzed in consecutive fiscal years, does a signal that
  *upgrades* (SELL->HOLD->BUY across years) or *downgrades* outperform
  a stable signal? (Momentum in the AI's own opinion.)
"""

import json
import logging
import re
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

# ── shared helpers ─────────────────────────────────────────────────────────────

DEFAULT_DB_PATH = Path("data/eon.db")
DEFAULT_HOLDING_PERIODS = [21, 63, 126, 252, 504]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ACTION_RANK = {"STRONG BUY": 2, "BUY": 1, "HOLD": 0, "SELL": -1, "STRONG SELL": -2, "UNKNOWN": 0}
PERIOD_LABELS = {21: "1M", 63: "3M", 126: "6M", 252: "1Y", 504: "2Y"}


def period_label(p: int) -> str:
    return PERIOD_LABELS.get(p, f"{p}d")


def _parse_action(fv: str) -> str:
    m = re.match(r"(STRONG BUY|STRONG SELL|BUY|SELL|HOLD)", fv.upper())
    return m.group(1) if m else "UNKNOWN"


def _parse_conviction(fv: str) -> str:
    m = re.search(r"Conviction[:\s]*(\w+)", fv, re.IGNORECASE)
    if m:
        c = m.group(1).capitalize()
        if c in ("High", "Medium", "Low"):
            return c
    return "Unknown"


def _parse_moat(raw: str) -> str:
    r = raw.strip()
    if r.startswith("Wide"):
        return "Wide"
    if r.startswith("None") or r.startswith("No "):
        return "None"
    return "Narrow"


def _parse_af(raw: str) -> str:
    m = re.match(r"(Antifragile|Robust|Fragile)", raw)
    return m.group(1) if m else "Robust"


@dataclass
class Signal:
    ticker: str
    fiscal_year: int
    action: str
    conviction: str
    buffett_action: str
    taleb_action: str
    contrarian_action: str
    moat: str
    antifragile: str
    composite_score: float = 0.0


def load_all_signals(db_path: Path, max_fy: int = 2024, min_fy: int = 2020) -> List[Signal]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ar.ticker, ar.fiscal_year, ar.result_json
        FROM analysis_results ar
        JOIN analysis_runs runs ON ar.run_id = runs.run_id
        WHERE ar.result_type = 'SimplifiedAnalysis'
          AND ar.fiscal_year <= ? AND ar.fiscal_year >= ?
          AND runs.status = 'completed'
        ORDER BY ar.ticker, ar.fiscal_year
        """,
        (max_fy, min_fy),
    )
    seen = set()
    signals = []
    for row in cur.fetchall():
        key = (row["ticker"], row["fiscal_year"])
        if key in seen:
            continue
        seen.add(key)
        try:
            d = json.loads(row["result_json"])
            fv = d.get("final_verdict", "")
            b = d.get("buffett", {})
            t = d.get("taleb", {})
            c = d.get("contrarian", {})
            signals.append(Signal(
                ticker=row["ticker"],
                fiscal_year=row["fiscal_year"],
                action=_parse_action(fv),
                conviction=_parse_conviction(fv),
                buffett_action=b.get("action_signal", ""),
                taleb_action=t.get("action_signal", ""),
                contrarian_action=c.get("action_signal", ""),
                moat=_parse_moat(b.get("moat_rating", "")),
                antifragile=_parse_af(t.get("antifragile_rating", "")),
            ))
        except Exception as e:
            pass
    conn.close()
    logger.info(f"Loaded {len(signals)} signals (FY{min_fy}-{max_fy})")
    return signals


# ── price fetching ─────────────────────────────────────────────────────────────

def fetch_prices(tickers: List[str], min_fy: int, max_fy: int) -> Tuple[Dict, Optional[pd.DataFrame]]:
    from experimental.backtester.price_fetcher import PriceFetcher
    pf = PriceFetcher()
    all_tickers = list(set(tickers + ["SPY"]))
    prices = pf.get_prices_batch(all_tickers, f"{min_fy}-01-01", f"{max_fy + 7}-01-01")
    bench = prices.pop("SPY", None)
    return prices, bench


def compute_forward_returns(
    signal: Signal,
    stock_prices: pd.DataFrame,
    bench_prices: pd.DataFrame,
    holding_periods: List[int],
) -> Optional[Dict[int, Tuple[float, float, float]]]:
    """Returns dict of period -> (stock_ret, bench_ret, excess_ret). None if no entry."""
    entry_ts = pd.Timestamp(f"{signal.fiscal_year + 1}-04-01")
    sc = stock_prices["Close"]
    bc = bench_prices["Close"]

    valid = sc.index[sc.index >= entry_ts]
    if len(valid) == 0:
        return None
    actual = valid[0]
    entry_p = float(sc.loc[actual])

    bv = bc.index[bc.index >= entry_ts]
    if len(bv) == 0:
        return None
    b_actual = bv[0]
    b_entry_p = float(bc.loc[b_actual])

    result = {}
    for period in holding_periods:
        idx = sc.index.get_loc(actual)
        exit_idx = idx + period
        if exit_idx >= len(sc):
            continue
        stock_ret = float(sc.iloc[exit_idx]) / entry_p - 1.0

        bidx = bc.index.get_loc(b_actual)
        bex = bidx + period
        if bex >= len(bc):
            result[period] = (stock_ret, None, None)
            continue
        bench_ret = float(bc.iloc[bex]) / b_entry_p - 1.0
        result[period] = (stock_ret, bench_ret, stock_ret - bench_ret)
    return result if result else None


# ── statistical helpers ────────────────────────────────────────────────────────

def ttest_and_describe(
    values: List[float],
    label: str,
    n_label: str = "",
) -> Dict:
    if len(values) < 3:
        return {"label": label, "n": len(values), "mean": None, "median": None, "t": None, "p": None}
    arr = np.array(values)
    t, p = scipy_stats.ttest_1samp(arr, 0)
    return {
        "label": label,
        "n": len(arr),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "std": float(arr.std()),
        "beat_rate": float((arr > 0).mean()),
        "t": float(t),
        "p": float(p),
        "sig": "***" if p < 0.01 else ("**" if p < 0.05 else ("*" if p < 0.10 else "")),
    }


def print_comparison_table(
    groups: List[Dict],
    holding_periods: List[int],
    title: str,
    data: Dict[str, Dict[int, List[float]]],  # group_name -> period -> excess_returns
):
    print(f"\n{'═'*110}")
    print(f"  {title}")
    print(f"{'═'*110}")

    hdr = f"  {'Group':38s}  {'n':>5s}"
    for p in holding_periods:
        pl = period_label(p)
        hdr += f"  {pl:>12s}"
    print(hdr)
    print("─" * 110)

    for g in groups:
        gname = g["name"]
        gdata = data.get(gname, {})
        # Find n from first available period
        n = next((len(v) for v in gdata.values() if v), 0)
        line = f"  {gname:38s}  {n:>5d}"
        for p in holding_periods:
            vals = gdata.get(p, [])
            if len(vals) < 3:
                line += f"  {'N/A':>12s}"
            else:
                arr = np.array(vals)
                mean_e = arr.mean()
                _, pv = scipy_stats.ttest_1samp(arr, 0)
                sig = "***" if pv < 0.01 else ("**" if pv < 0.05 else ("*" if pv < 0.10 else ""))
                line += f"  {mean_e:>+7.1%}{sig:>3s} ({len(vals):>3d})"
        print(line)

    print("\n  Legend: excess return vs SPY | significance: *p<.10, **p<.05, ***p<.01")


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT A: Which pair of agreeing perspectives matters most?
# ══════════════════════════════════════════════════════════════════════════════

def experiment_a(signals: List[Signal], prices: Dict, bench: pd.DataFrame, holding_periods: List[int]):
    print("\n" + "█" * 110)
    print("  EXPERIMENT A: Perspective Agreement Patterns")
    print("  Q: Which PAIR of agreeing perspectives (B+T, B+C, T+C) generates the most alpha?")
    print("     And does AI self-disagreement (mixed BUY+SELL signals) predict bad outcomes?")
    print("█" * 110)

    def is_buy(a): return a == "PRIORITY"
    def is_sell(a): return a == "AVOID"

    groups = {
        "B+T agree PRIORITY (not C)": lambda s: is_buy(s.buffett_action) and is_buy(s.taleb_action) and not is_buy(s.contrarian_action),
        "B+C agree PRIORITY (not T)": lambda s: is_buy(s.buffett_action) and is_buy(s.contrarian_action) and not is_buy(s.taleb_action),
        "T+C agree PRIORITY (not B)": lambda s: is_buy(s.taleb_action) and is_buy(s.contrarian_action) and not is_buy(s.buffett_action),
        "ALL 3 agree PRIORITY": lambda s: is_buy(s.buffett_action) and is_buy(s.taleb_action) and is_buy(s.contrarian_action),
        "Buffett PRIORITY only": lambda s: is_buy(s.buffett_action) and not is_buy(s.taleb_action) and not is_buy(s.contrarian_action),
        "Contrarian PRIORITY only": lambda s: not is_buy(s.buffett_action) and not is_buy(s.taleb_action) and is_buy(s.contrarian_action),
        "Taleb PRIORITY only": lambda s: not is_buy(s.buffett_action) and is_buy(s.taleb_action) and not is_buy(s.contrarian_action),
        "Mixed (B=PRIORITY, C=AVOID)": lambda s: is_buy(s.buffett_action) and is_sell(s.contrarian_action),
        "Mixed (C=PRIORITY, B=AVOID)": lambda s: is_sell(s.buffett_action) and is_buy(s.contrarian_action),
        "PASS everywhere (control)": lambda s: s.buffett_action == "PASS" and s.taleb_action == "PASS" and s.contrarian_action == "PASS",
    }

    # Collect excess returns per group per period
    data: Dict[str, Dict[int, List[float]]] = {g: {p: [] for p in holding_periods} for g in groups}
    counts = {g: 0 for g in groups}

    for sig in signals:
        if sig.ticker not in prices:
            continue
        fwd = compute_forward_returns(sig, prices[sig.ticker], bench, holding_periods)
        if not fwd:
            continue
        for gname, gfn in groups.items():
            if gfn(sig):
                counts[gname] += 1
                for p, (sr, br, er) in fwd.items():
                    if er is not None:
                        data[gname][p].append(er)

    group_list = [{"name": g} for g in groups]
    print_comparison_table(group_list, holding_periods, "EXPERIMENT A — Excess Returns by Perspective Agreement Pattern", data)

    # Highlight key insights
    print("\n  KEY FINDINGS:")
    for gname in groups:
        d = data[gname]
        # find best period
        best_p = None
        best_mean = -999
        best_p_val = 1.0
        for p in holding_periods:
            vals = d.get(p, [])
            if len(vals) >= 5:
                mean_e = np.mean(vals)
                _, pv = scipy_stats.ttest_1samp(np.array(vals), 0)
                if mean_e > best_mean:
                    best_mean = mean_e
                    best_p = p
                    best_p_val = pv
        n = counts[gname]
        if best_p:
            sig_tag = "*** SIGNIFICANT" if best_p_val < 0.05 else ("~ marginal" if best_p_val < 0.10 else "not sig")
            print(f"    {gname:45s} n={n:4d}  best: {period_label(best_p)} {best_mean:+.1%}  p={best_p_val:.3f}  {sig_tag}")


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT B: Conviction Calibration
# ══════════════════════════════════════════════════════════════════════════════

def experiment_b(signals: List[Signal], prices: Dict, bench: pd.DataFrame, holding_periods: List[int]):
    print("\n" + "█" * 110)
    print("  EXPERIMENT B: Conviction Calibration")
    print("  Q: Is the AI's stated conviction (High/Medium/Low) actually predictive of returns?")
    print("     Tested separately for BUY and SELL calls.")
    print("█" * 110)

    combos = {
        "BUY + High Conviction": lambda s: s.action in ("BUY", "STRONG BUY") and s.conviction == "High",
        "BUY + Medium Conviction": lambda s: s.action in ("BUY", "STRONG BUY") and s.conviction == "Medium",
        "BUY + Low/Unknown Conv.": lambda s: s.action in ("BUY", "STRONG BUY") and s.conviction in ("Low", "Unknown"),
        "HOLD + High Conviction": lambda s: s.action == "HOLD" and s.conviction == "High",
        "HOLD + Medium Conviction": lambda s: s.action == "HOLD" and s.conviction == "Medium",
        "SELL + High Conviction": lambda s: s.action in ("SELL", "STRONG SELL") and s.conviction == "High",
        "SELL + Medium Conviction": lambda s: s.action in ("SELL", "STRONG SELL") and s.conviction == "Medium",
        "SELL + Low/Unknown Conv.": lambda s: s.action in ("SELL", "STRONG SELL") and s.conviction in ("Low", "Unknown"),
    }

    data: Dict[str, Dict[int, List[float]]] = {g: {p: [] for p in holding_periods} for g in combos}

    for sig in signals:
        if sig.ticker not in prices:
            continue
        fwd = compute_forward_returns(sig, prices[sig.ticker], bench, holding_periods)
        if not fwd:
            continue
        for gname, gfn in combos.items():
            if gfn(sig):
                for p, (sr, br, er) in fwd.items():
                    if er is not None:
                        data[gname][p].append(er)

    group_list = [{"name": g} for g in combos]
    print_comparison_table(group_list, holding_periods, "EXPERIMENT B — Conviction Calibration (Excess vs SPY)", data)

    # Spread between high and low conviction within same direction
    print("\n  CONVICTION PREMIUM (High minus Low/Unknown conviction, same direction):")
    for period in [252, 504]:
        pl = period_label(period)
        buy_high = np.mean(data["BUY + High Conviction"][period]) if len(data["BUY + High Conviction"][period]) >= 3 else None
        buy_low = np.mean(data["BUY + Low/Unknown Conv."][period]) if len(data["BUY + Low/Unknown Conv."][period]) >= 3 else None
        sell_high = np.mean(data["SELL + High Conviction"][period]) if len(data["SELL + High Conviction"][period]) >= 3 else None
        sell_low = np.mean(data["SELL + Low/Unknown Conv."][period]) if len(data["SELL + Low/Unknown Conv."][period]) >= 3 else None
        if buy_high and buy_low:
            print(f"    {pl} BUY:  High={buy_high:+.1%}  Low/Unk={buy_low:+.1%}  premium={buy_high-buy_low:+.1%}")
        if sell_high and sell_low:
            # For SELLs, more negative is better for a short
            print(f"    {pl} SELL: High={sell_high:+.1%}  Low/Unk={sell_low:+.1%}  (more negative = short works better)")


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT C: Moat Quality × Action Interaction
# ══════════════════════════════════════════════════════════════════════════════

def experiment_c(signals: List[Signal], prices: Dict, bench: pd.DataFrame, holding_periods: List[int]):
    print("\n" + "█" * 110)
    print("  EXPERIMENT C: Moat Quality × Action Interaction")
    print("  Q: Does moat rating improve the quality of BUY/SELL calls?")
    print("     Wide-Moat BUYs vs Narrow/No-Moat BUYs — and same for SELLs.")
    print("█" * 110)

    combos = {
        # BUY side
        "BUY + Wide Moat": lambda s: s.action in ("BUY", "STRONG BUY") and s.moat == "Wide",
        "BUY + Narrow Moat": lambda s: s.action in ("BUY", "STRONG BUY") and s.moat == "Narrow",
        "BUY + No Moat": lambda s: s.action in ("BUY", "STRONG BUY") and s.moat == "None",
        # SELL side (short alpha: want negative excess)
        "SELL + Wide Moat": lambda s: s.action in ("SELL", "STRONG SELL") and s.moat == "Wide",
        "SELL + Narrow Moat": lambda s: s.action in ("SELL", "STRONG SELL") and s.moat == "Narrow",
        "SELL + No Moat": lambda s: s.action in ("SELL", "STRONG SELL") and s.moat == "None",
        # HOLD side — is Wide-Moat HOLD worth buying anyway?
        "HOLD + Wide Moat": lambda s: s.action == "HOLD" and s.moat == "Wide",
        "HOLD + No Moat": lambda s: s.action == "HOLD" and s.moat == "None",
        # Antifragile filter cross
        "BUY + Antifragile/Robust": lambda s: s.action in ("BUY", "STRONG BUY") and s.antifragile in ("Antifragile", "Robust"),
        "BUY + Fragile": lambda s: s.action in ("BUY", "STRONG BUY") and s.antifragile == "Fragile",
        "SELL + Fragile": lambda s: s.action in ("SELL", "STRONG SELL") and s.antifragile == "Fragile",
    }

    data: Dict[str, Dict[int, List[float]]] = {g: {p: [] for p in holding_periods} for g in combos}

    for sig in signals:
        if sig.ticker not in prices:
            continue
        fwd = compute_forward_returns(sig, prices[sig.ticker], bench, holding_periods)
        if not fwd:
            continue
        for gname, gfn in combos.items():
            if gfn(sig):
                for p, (sr, br, er) in fwd.items():
                    if er is not None:
                        data[gname][p].append(er)

    group_list = [{"name": g} for g in combos]
    print_comparison_table(group_list, holding_periods, "EXPERIMENT C — Moat + Antifragile × Action Interaction (Excess vs SPY)", data)

    print("\n  MOAT PREMIUM on BUY calls (Wide minus No-Moat, at 1Y and 2Y):")
    for period in [252, 504]:
        pl = period_label(period)
        wide = data["BUY + Wide Moat"][period]
        no_moat = data["BUY + No Moat"][period]
        narrow = data["BUY + Narrow Moat"][period]
        if len(wide) >= 3 and len(no_moat) >= 3:
            w, nm, nr = np.mean(wide), np.mean(no_moat), np.mean(narrow) if len(narrow) >= 3 else float('nan')
            print(f"    {pl}: Wide={w:+.1%} (n={len(wide)})  Narrow={nr:+.1%} (n={len(narrow)})  None={nm:+.1%} (n={len(no_moat)})  premium={w-nm:+.1%}")

    print("\n  SHORT QUALITY on SELL calls (want most negative excess — No-Moat should be worst stocks):")
    for period in [252, 504]:
        pl = period_label(period)
        for gname in ["SELL + Wide Moat", "SELL + Narrow Moat", "SELL + No Moat"]:
            vals = data[gname][period]
            if len(vals) >= 3:
                mean_e = np.mean(vals)
                _, pv = scipy_stats.ttest_1samp(np.array(vals), 0)
                print(f"    {pl} {gname:30s}: mean_excess={mean_e:+.1%}  n={len(vals)}  p={pv:.3f}")


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT D: Signal Drift / AI Momentum
# ══════════════════════════════════════════════════════════════════════════════

def experiment_d(signals: List[Signal], prices: Dict, bench: pd.DataFrame, holding_periods: List[int]):
    print("\n" + "█" * 110)
    print("  EXPERIMENT D: AI Signal Drift (Year-over-Year Opinion Changes)")
    print("  Q: When the AI upgrades a stock (e.g. SELL→BUY across FY), does that predict")
    print("     outperformance? Does a downgrade predict underperformance?")
    print("     'Stable BUY' vs 'Upgrading to BUY' vs 'Stable SELL' vs 'Downgrading to SELL'")
    print("█" * 110)

    # Build per-ticker timeseries of action ranks
    by_ticker: Dict[str, List[Tuple[int, Signal]]] = defaultdict(list)
    for s in signals:
        by_ticker[s.ticker].append((s.fiscal_year, s))
    for ticker in by_ticker:
        by_ticker[ticker].sort(key=lambda x: x[0])

    # Classify each signal by its drift from prior year
    @dataclass
    class DriftSignal:
        sig: Signal
        drift: str  # "upgrade", "downgrade", "stable_buy", "stable_sell", "stable_hold", "first_year"

    drift_signals: List[DriftSignal] = []
    for ticker, entries in by_ticker.items():
        for i, (fy, sig) in enumerate(entries):
            if i == 0:
                drift_signals.append(DriftSignal(sig=sig, drift="first_year"))
                continue
            prev_sig = entries[i - 1][1]
            prev_fy = entries[i - 1][0]
            if fy - prev_fy > 2:  # big gap — treat as first year
                drift_signals.append(DriftSignal(sig=sig, drift="first_year"))
                continue
            prev_rank = ACTION_RANK.get(prev_sig.action, 0)
            curr_rank = ACTION_RANK.get(sig.action, 0)
            if curr_rank > prev_rank:
                drift = "upgrade"
            elif curr_rank < prev_rank:
                drift = "downgrade"
            elif sig.action in ("BUY", "STRONG BUY"):
                drift = "stable_buy"
            elif sig.action in ("SELL", "STRONG SELL"):
                drift = "stable_sell"
            else:
                drift = "stable_hold"
            drift_signals.append(DriftSignal(sig=sig, drift=drift))

    drift_counts = defaultdict(int)
    for ds in drift_signals:
        drift_counts[ds.drift] += 1
    print(f"\n  Drift distribution: {dict(drift_counts)}")

    # Compute excess returns per drift category
    groups = ["upgrade", "downgrade", "stable_buy", "stable_sell", "stable_hold", "first_year"]
    data: Dict[str, Dict[int, List[float]]] = {g: {p: [] for p in holding_periods} for g in groups}

    for ds in drift_signals:
        sig = ds.sig
        if sig.ticker not in prices:
            continue
        fwd = compute_forward_returns(sig, prices[sig.ticker], bench, holding_periods)
        if not fwd:
            continue
        for p, (sr, br, er) in fwd.items():
            if er is not None:
                data[ds.drift][p].append(er)

    group_list = [{"name": g} for g in groups]
    print_comparison_table(
        group_list,
        holding_periods,
        "EXPERIMENT D — Signal Drift × Forward Excess Returns",
        data,
    )

    # Upgrade vs Downgrade spread
    print("\n  DRIFT SPREAD (upgrade excess - downgrade excess):")
    for period in holding_periods:
        pl = period_label(period)
        up = data["upgrade"][period]
        dn = data["downgrade"][period]
        if len(up) >= 3 and len(dn) >= 3:
            spread = np.mean(up) - np.mean(dn)
            # Welch t-test
            t, pv = scipy_stats.ttest_ind(np.array(up), np.array(dn))
            sig_tag = "***" if pv < 0.01 else ("**" if pv < 0.05 else ("*" if pv < 0.10 else ""))
            print(f"    {pl}: upgrade={np.mean(up):+.1%} (n={len(up)})  downgrade={np.mean(dn):+.1%} (n={len(dn)})  spread={spread:+.1%}  p={pv:.3f} {sig_tag}")

    # Also test: multi-year consecutive upgrades (strong momentum in AI opinion)
    print("\n  CONSECUTIVE UPGRADES (2+ years of improving signal vs 2+ years worsening):")
    consec_up: Dict[int, List[float]] = {p: [] for p in holding_periods}
    consec_dn: Dict[int, List[float]] = {p: [] for p in holding_periods}

    for ticker, entries in by_ticker.items():
        if ticker not in prices:
            continue
        for i in range(2, len(entries)):
            fy0, s0 = entries[i - 2]
            fy1, s1 = entries[i - 1]
            fy2, s2 = entries[i]
            if fy1 - fy0 > 2 or fy2 - fy1 > 2:
                continue
            r0 = ACTION_RANK.get(s0.action, 0)
            r1 = ACTION_RANK.get(s1.action, 0)
            r2 = ACTION_RANK.get(s2.action, 0)
            fwd = compute_forward_returns(s2, prices[ticker], bench, holding_periods)
            if not fwd:
                continue
            if r1 > r0 and r2 > r1:  # two consecutive upgrades
                for p, (sr, br, er) in fwd.items():
                    if er is not None:
                        consec_up[p].append(er)
            elif r1 < r0 and r2 < r1:  # two consecutive downgrades
                for p, (sr, br, er) in fwd.items():
                    if er is not None:
                        consec_dn[p].append(er)

    for period in holding_periods:
        pl = period_label(period)
        up2 = consec_up[period]
        dn2 = consec_dn[period]
        if len(up2) >= 3 and len(dn2) >= 3:
            t, pv = scipy_stats.ttest_ind(np.array(up2), np.array(dn2))
            print(f"    {pl}: 2x-upgrade={np.mean(up2):+.1%} (n={len(up2)})  2x-downgrade={np.mean(dn2):+.1%} (n={len(dn2)})  spread={np.mean(up2)-np.mean(dn2):+.1%}  p={pv:.3f}")
        else:
            print(f"    {pl}: 2x-upgrade n={len(up2)}  2x-downgrade n={len(dn2)} (insufficient data)")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 110)
    print("  EON EXTRA EXPERIMENTS — Deep Signal Structure Analysis")
    print("  A: Perspective Agreement Patterns  B: Conviction Calibration")
    print("  C: Moat × Action Interaction        D: Year-over-Year Signal Drift")
    print("=" * 110)

    signals = load_all_signals(DEFAULT_DB_PATH, max_fy=2024, min_fy=2020)
    if not signals:
        print("No signals found.")
        sys.exit(1)

    tickers = sorted(set(s.ticker for s in signals))
    min_fy = min(s.fiscal_year for s in signals)
    print(f"\nFetching prices for {len(tickers)} tickers...")
    prices, bench = fetch_prices(tickers, min_fy, 2024)
    if bench is None:
        print("ERROR: No SPY data.")
        sys.exit(1)
    print(f"Prices fetched for {len(prices)}/{len(tickers)} tickers.")

    holding_periods = DEFAULT_HOLDING_PERIODS

    experiment_a(signals, prices, bench, holding_periods)
    experiment_b(signals, prices, bench, holding_periods)
    experiment_c(signals, prices, bench, holding_periods)
    experiment_d(signals, prices, bench, holding_periods)

    print("\n" + "=" * 110)
    print("  All experiments complete.")
    print("=" * 110)


if __name__ == "__main__":
    main()
