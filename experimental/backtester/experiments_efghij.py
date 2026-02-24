#!/usr/bin/env python3
"""
EON Backtesting Experiments E–J
================================

E: Exact (Buffett, Taleb, Contrarian) triple-combo fingerprints
   Which specific 3-way action combination is most predictive?
   Uses all 20 combos with n>=30 to find the highest-signal fingerprints.

F: Final-verdict vs perspective alignment / disagreement
   Does the final AI verdict *agree* with all three perspectives, or does it
   override one? Does internal disagreement (final=BUY but a perspective says
   AVOID/PASS) predict lower returns vs full alignment?

G: Fragility as a standalone factor — beyond BUY/SELL labels
   Is Fragile/Robust itself a market signal, regardless of what the AI
   recommends? Tests Fragile stocks vs Robust stocks in absolute and
   excess return terms. Also tests the interaction with market regime.

H: Sell-signal anatomy — which SELL flavour is most reliable?
   Deep-dive into SELL sub-segments to find the single best short signal:
   - SELL by conviction (High/Medium/Low)
   - SELL by moat (Wide/Narrow/None — is a Wide-Moat SELL an overvalued
     quality name that mean-reverts?)
   - SELL by antifragile (Fragile SELL = structural deterioration)
   - SELL where ALL perspectives agree vs only some
   - STRONG SELL only

I: Contrarian-only portfolios — long the most contrarian BUYs
   The contrarian sub-score (conviction_level + action_signal) as a
   standalone signal. Tests whether high-conviction contrarian calls
   (stocks the market has given up on) generate the most alpha.
   Also tests: contrarian BUY with Buffett disagreement (pure
   contrarian vs value-backed contrarian).

J: Multi-factor composite — combining the best signals found
   Builds the "best" portfolio from experiments A–I:
   1. Buffett+Contrarian PRIORITY (exp A winner)
   2. High-conviction BUY + Fragile (exp C hidden gem)
   3. Stable multi-year SELL (exp D)
   4. SELL + No-Moat (exp H candidate)
   Tests whether combining them improves significance vs any single factor.

Run:
    python -m experimental.backtester.experiments_efghij
"""

import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats as scipy_stats

from .exp_lib import (
    DEFAULT_DB_PATH, DEFAULT_HOLDING_PERIODS, ACTION_RANK,
    Signal, load_signals, fetch_prices, forward_returns,
    ttest, welch, sig_stars, describe, print_table, section, pl,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

HP = DEFAULT_HOLDING_PERIODS


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT E: Exact (B, T, C) triple-combo fingerprints
# ══════════════════════════════════════════════════════════════════════════════

def experiment_e(signals, prices, bench):
    section("EXPERIMENT E: Exact Triple-Combo Fingerprints (B, T, C)")
    print("  Every unique (Buffett, Taleb, Contrarian) action triple with n≥20.")
    print("  Goal: find which specific AI 'fingerprint' is most predictive.\n")

    # Collect excess returns per combo
    combo_data: dict = defaultdict(lambda: {p: [] for p in HP})
    combo_counts: Counter = Counter()

    for sig in signals:
        if sig.ticker not in prices:
            continue
        fwd = forward_returns(sig, prices[sig.ticker], bench, HP)
        if not fwd:
            continue
        key = (sig.buffett_action, sig.taleb_action, sig.contrarian_action)
        combo_counts[key] += 1
        for p, (sr, br, er) in fwd.items():
            if er is not None:
                combo_data[key][p].append(er)

    # Filter to n>=20 and sort by 1Y mean excess
    qualified = [(k, v) for k, v in combo_data.items() if combo_counts[k] >= 20]
    qualified.sort(key=lambda x: -np.mean(x[1].get(252, [0]) or [0]))

    print(f"  {'(B, T, C) Combo':45s}  {'n':>5s}  {'1M':>10s}  {'3M':>10s}  {'6M':>10s}  {'1Y':>10s}  {'2Y':>10s}")
    print("─" * 115)
    for key, d in qualified:
        n = combo_counts[key]
        line = f"  {str(key):45s}  {n:>5d}"
        for p in HP:
            vals = d.get(p, [])
            if len(vals) < 3:
                line += f"  {'N/A':>10s}"
            else:
                arr = np.array(vals)
                _, pv = ttest(vals)
                s = sig_stars(pv).strip()
                line += f"  {arr.mean():>+7.1%}{s:>3s}"
        print(line)

    # Highlight top performers
    print("\n  TOP FINGERPRINTS by 1Y excess (n≥20, p<0.10):")
    for key, d in qualified:
        vals_1y = d.get(252, [])
        if len(vals_1y) < 5:
            continue
        arr = np.array(vals_1y)
        _, pv = ttest(list(arr))
        if arr.mean() > 0.03 and pv < 0.10:
            print(f"    {str(key):45s}  n={combo_counts[key]:4d}  1Y={arr.mean():+.1%}  p={pv:.3f} {sig_stars(pv).strip()}")

    print("\n  WORST FINGERPRINTS (best shorts) by 1Y excess (n≥20, p<0.10):")
    for key, d in sorted(qualified, key=lambda x: np.mean(x[1].get(252, [0]) or [0])):
        vals_1y = d.get(252, [])
        if len(vals_1y) < 5:
            continue
        arr = np.array(vals_1y)
        _, pv = ttest(list(arr))
        if arr.mean() < -0.02 and pv < 0.10:
            print(f"    {str(key):45s}  n={combo_counts[key]:4d}  1Y={arr.mean():+.1%}  p={pv:.3f} {sig_stars(pv).strip()}")


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT F: Final-verdict vs perspective alignment
# ══════════════════════════════════════════════════════════════════════════════

def experiment_f(signals, prices, bench):
    section("EXPERIMENT F: Final Verdict ↔ Perspective Alignment")
    print("  Does the final verdict *agree* with all underlying perspectives?")
    print("  'Aligned BUY' = final=BUY AND every perspective is PRIORITY/INVESTIGATE (not PASS/AVOID).")
    print("  'Override BUY' = final=BUY but ≥1 perspective says PASS or opposes.\n")

    groups = {
        # BUY alignment
        "BUY — B+C aligned (both PRIORITY)":
            lambda s: s.action in ("BUY","STRONG BUY") and s.buffett_action == "PRIORITY" and s.contrarian_action == "PRIORITY",
        "BUY — C aligned only (B=PASS/INVESTIGATE)":
            lambda s: s.action in ("BUY","STRONG BUY") and s.contrarian_action == "PRIORITY" and s.buffett_action != "PRIORITY",
        "BUY — B aligned only (C=PASS/INVESTIGATE)":
            lambda s: s.action in ("BUY","STRONG BUY") and s.buffett_action == "PRIORITY" and s.contrarian_action != "PRIORITY",
        "BUY — no perspective aligns (all PASS)":
            lambda s: s.action in ("BUY","STRONG BUY") and s.buffett_action == "PASS" and s.contrarian_action in ("PASS","INVESTIGATE"),
        # SELL alignment
        "SELL — all perspectives cautious":
            lambda s: s.action in ("SELL","STRONG SELL") and s.buffett_action in ("PASS","INVESTIGATE") and s.contrarian_action in ("PASS","INVESTIGATE"),
        "SELL — Contrarian flags weakness":
            lambda s: s.action in ("SELL","STRONG SELL") and s.contrarian_action in ("PRIORITY","INVESTIGATE"),
        "SELL — Buffett flags weakness":
            lambda s: s.action in ("SELL","STRONG SELL") and s.buffett_action in ("INVESTIGATE","PRIORITY"),
        # Disagreement
        "HOLD but B=PRIORITY (AI holds back Buffett BUY)":
            lambda s: s.action == "HOLD" and s.buffett_action == "PRIORITY",
        "HOLD but C=PRIORITY (AI holds back Contrarian BUY)":
            lambda s: s.action == "HOLD" and s.contrarian_action == "PRIORITY",
    }

    data: dict = {g: {p: [] for p in HP} for g in groups}
    for sig in signals:
        if sig.ticker not in prices:
            continue
        fwd = forward_returns(sig, prices[sig.ticker], bench, HP)
        if not fwd:
            continue
        for gname, fn in groups.items():
            if fn(sig):
                for p, (sr, br, er) in fwd.items():
                    if er is not None:
                        data[gname][p].append(er)

    print_table("EXPERIMENT F — Final Verdict Alignment (excess vs SPY)", list(groups), data)

    # Key insight: does HOLD-suppressing a Buffett PRIORITY signal mean we leave alpha on the table?
    print("\n  INSIGHT — What happens if you ignore the final verdict and just trade Buffett PRIORITY?")
    bp_all: dict = {p: [] for p in HP}
    bp_hold: dict = {p: [] for p in HP}
    bp_buy: dict = {p: [] for p in HP}
    for sig in signals:
        if sig.ticker not in prices or sig.buffett_action != "PRIORITY":
            continue
        fwd = forward_returns(sig, prices[sig.ticker], bench, HP)
        if not fwd:
            continue
        for p, (sr, br, er) in fwd.items():
            if er is not None:
                bp_all[p].append(er)
                if sig.action == "HOLD":
                    bp_hold[p].append(er)
                elif sig.action in ("BUY","STRONG BUY"):
                    bp_buy[p].append(er)

    for p in [252, 504]:
        a, h, b_ = bp_all[p], bp_hold[p], bp_buy[p]
        if len(a) >= 3:
            _, pa = ttest(a); _, ph = ttest(h) if len(h)>=3 else (0,1); _, pb_ = ttest(b_) if len(b_)>=3 else (0,1)
            print(f"    {pl(p)}: All Buffett-PRIORITY → {np.mean(a):+.1%} (n={len(a)}, p={pa:.3f})")
            if len(b_)>=3: print(f"         Final=BUY  → {np.mean(b_):+.1%} (n={len(b_)}, p={pb_:.3f})")
            if len(h)>=3:  print(f"         Final=HOLD → {np.mean(h):+.1%} (n={len(h)}, p={ph:.3f})")


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT G: Fragility as a standalone factor
# ══════════════════════════════════════════════════════════════════════════════

def experiment_g(signals, prices, bench):
    section("EXPERIMENT G: Fragility as a Standalone Factor")
    print("  Is Fragile/Robust a market signal *independent* of the BUY/SELL verdict?")
    print("  Tests Fragile vs Robust stocks in absolute and relative terms, all actions.\n")

    groups = {
        "Fragile — all actions":                  lambda s: s.antifragile == "Fragile",
        "Robust — all actions":                   lambda s: s.antifragile == "Robust",
        "Antifragile — all actions":              lambda s: s.antifragile == "Antifragile",
        "Fragile + BUY":                          lambda s: s.antifragile == "Fragile" and s.action in ("BUY","STRONG BUY"),
        "Fragile + HOLD":                         lambda s: s.antifragile == "Fragile" and s.action == "HOLD",
        "Fragile + SELL":                         lambda s: s.antifragile == "Fragile" and s.action in ("SELL","STRONG SELL"),
        "Robust + BUY":                           lambda s: s.antifragile == "Robust" and s.action in ("BUY","STRONG BUY"),
        "Robust + HOLD":                          lambda s: s.antifragile == "Robust" and s.action == "HOLD",
        "Robust + SELL":                          lambda s: s.antifragile == "Robust" and s.action in ("SELL","STRONG SELL"),
        "Fragile + Wide Moat (oxymoron?)":        lambda s: s.antifragile == "Fragile" and s.moat == "Wide",
        "Fragile + No Moat (double trouble)":     lambda s: s.antifragile == "Fragile" and s.moat == "None",
        "Robust + Wide Moat (fortress)":          lambda s: s.antifragile == "Robust" and s.moat == "Wide",
    }

    data: dict = {g: {p: [] for p in HP} for g in groups}
    for sig in signals:
        if sig.ticker not in prices:
            continue
        fwd = forward_returns(sig, prices[sig.ticker], bench, HP)
        if not fwd:
            continue
        for gname, fn in groups.items():
            if fn(sig):
                for p, (sr, br, er) in fwd.items():
                    if er is not None:
                        data[gname][p].append(er)

    print_table("EXPERIMENT G — Antifragile Rating as Standalone Factor (excess vs SPY)", list(groups), data)

    # Fragile vs Robust spread
    print("\n  FRAGILE vs ROBUST SPREAD (Fragile excess − Robust excess):")
    for p in HP:
        f = data["Fragile — all actions"][p]
        r = data["Robust — all actions"][p]
        if len(f) >= 10 and len(r) >= 10:
            spread = np.mean(f) - np.mean(r)
            t, pv = welch(f, r)
            print(f"    {pl(p)}: Fragile={np.mean(f):+.1%} (n={len(f)})  Robust={np.mean(r):+.1%} (n={len(r)})  spread={spread:+.1%}  p={pv:.3f} {sig_stars(pv).strip()}")

    # Fragile + BUY vs Robust + BUY spread
    print("\n  FRAGILE+BUY vs ROBUST+BUY (the 'beaten-up BUY' premium):")
    for p in HP:
        fb = data["Fragile + BUY"][p]
        rb = data["Robust + BUY"][p]
        if len(fb) >= 10 and len(rb) >= 10:
            spread = np.mean(fb) - np.mean(rb)
            t, pv = welch(fb, rb)
            print(f"    {pl(p)}: F+BUY={np.mean(fb):+.1%} (n={len(fb)})  R+BUY={np.mean(rb):+.1%} (n={len(rb)})  spread={spread:+.1%}  p={pv:.3f} {sig_stars(pv).strip()}")


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT H: SELL-signal anatomy — which SELL sub-type is most reliable?
# ══════════════════════════════════════════════════════════════════════════════

def experiment_h(signals, prices, bench):
    section("EXPERIMENT H: SELL-Signal Anatomy — Finding the Best Short Signal")
    print("  Deep-dive into every SELL sub-segment to isolate the most reliable short.\n")

    sell_groups = {
        # By verdict intensity
        "SELL (all)":                             lambda s: s.action in ("SELL","STRONG SELL"),
        "STRONG SELL only":                       lambda s: s.action == "STRONG SELL",
        "SELL (not STRONG SELL)":                 lambda s: s.action == "SELL",
        # By conviction
        "SELL + High Conviction":                 lambda s: s.action in ("SELL","STRONG SELL") and s.conviction == "High",
        "SELL + Medium Conviction":               lambda s: s.action in ("SELL","STRONG SELL") and s.conviction == "Medium",
        "SELL + Low/Unknown Conviction":          lambda s: s.action in ("SELL","STRONG SELL") and s.conviction in ("Low","Unknown"),
        # By moat — wide moat SELL = overpriced quality
        "SELL + Wide Moat (overpriced quality)":  lambda s: s.action in ("SELL","STRONG SELL") and s.moat == "Wide",
        "SELL + Narrow Moat":                     lambda s: s.action in ("SELL","STRONG SELL") and s.moat == "Narrow",
        "SELL + No Moat (broken model)":          lambda s: s.action in ("SELL","STRONG SELL") and s.moat == "None",
        # By antifragile — fragile SELL = structurally deteriorating
        "SELL + Fragile":                         lambda s: s.action in ("SELL","STRONG SELL") and s.antifragile == "Fragile",
        "SELL + Robust":                          lambda s: s.action in ("SELL","STRONG SELL") and s.antifragile == "Robust",
        # Perspective agreement on SELL
        "SELL + B disagrees (B=PRIORITY)":        lambda s: s.action in ("SELL","STRONG SELL") and s.buffett_action == "PRIORITY",
        "SELL + C disagrees (C=PRIORITY)":        lambda s: s.action in ("SELL","STRONG SELL") and s.contrarian_action == "PRIORITY",
        "SELL + all perspectives cautious":       lambda s: s.action in ("SELL","STRONG SELL") and s.buffett_action in ("PASS","INVESTIGATE") and s.contrarian_action in ("PASS","INVESTIGATE"),
        # Combinations
        "SELL + High Conv + Fragile":             lambda s: s.action in ("SELL","STRONG SELL") and s.conviction == "High" and s.antifragile == "Fragile",
        "SELL + Wide Moat + High Conv":           lambda s: s.action in ("SELL","STRONG SELL") and s.moat == "Wide" and s.conviction == "High",
        "SELL + No Moat + Fragile (worst combo)": lambda s: s.action in ("SELL","STRONG SELL") and s.moat == "None" and s.antifragile == "Fragile",
    }

    data: dict = {g: {p: [] for p in HP} for g in sell_groups}
    for sig in signals:
        if sig.ticker not in prices:
            continue
        fwd = forward_returns(sig, prices[sig.ticker], bench, HP)
        if not fwd:
            continue
        for gname, fn in sell_groups.items():
            if fn(sig):
                for p, (sr, br, er) in fwd.items():
                    if er is not None:
                        data[gname][p].append(er)

    print_table("EXPERIMENT H — SELL Sub-Segment Excess Returns vs SPY (negative = short works)", list(sell_groups), data)

    print("\n  RANKING by 1Y short alpha (most negative = best short signal, n≥20):")
    scored = []
    for g in sell_groups:
        vals = data[g].get(252, [])
        if len(vals) >= 20:
            arr = np.array(vals)
            _, pv = ttest(list(arr))
            scored.append((g, float(arr.mean()), len(vals), pv))
    scored.sort(key=lambda x: x[1])
    for g, mean_e, n, pv in scored:
        print(f"    {g:45s}  n={n:4d}  1Y_excess={mean_e:+.1%}  p={pv:.3f} {sig_stars(pv).strip()}")


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT I: Contrarian-only portfolios
# ══════════════════════════════════════════════════════════════════════════════

def experiment_i(signals, prices, bench):
    section("EXPERIMENT I: Contrarian-Only Portfolios")
    print("  Tests whether pure contrarian signals generate alpha independently.")
    print("  Key question: do stocks the market has given up on (Contrarian PRIORITY)")
    print("  outperform even without Buffett quality backing?\n")

    groups = {
        # Contrarian signal strength
        "Contrarian PRIORITY — all":
            lambda s: s.contrarian_action == "PRIORITY",
        "Contrarian PRIORITY + High Conv":
            lambda s: s.contrarian_action == "PRIORITY" and s.conviction == "High",
        "Contrarian PRIORITY + Medium Conv":
            lambda s: s.contrarian_action == "PRIORITY" and s.conviction == "Medium",
        # Backed vs unbacked by Buffett
        "Contrarian PRIORITY + Buffett PRIORITY":
            lambda s: s.contrarian_action == "PRIORITY" and s.buffett_action == "PRIORITY",
        "Contrarian PRIORITY + Buffett INVESTIGATE":
            lambda s: s.contrarian_action == "PRIORITY" and s.buffett_action == "INVESTIGATE",
        "Contrarian PRIORITY + Buffett PASS (pure contrarian)":
            lambda s: s.contrarian_action == "PRIORITY" and s.buffett_action == "PASS",
        # Contrarian BUY vs contrarian SELL final verdict
        "Contrarian PRIORITY + Final BUY":
            lambda s: s.contrarian_action == "PRIORITY" and s.action in ("BUY","STRONG BUY"),
        "Contrarian PRIORITY + Final HOLD":
            lambda s: s.contrarian_action == "PRIORITY" and s.action == "HOLD",
        "Contrarian PRIORITY + Final SELL":
            lambda s: s.contrarian_action == "PRIORITY" and s.action in ("SELL","STRONG SELL"),
        # Contrarian PRIORITY + Fragile (hated AND broken = max contrarian)
        "Contrarian PRIORITY + Fragile (max hated)":
            lambda s: s.contrarian_action == "PRIORITY" and s.antifragile == "Fragile",
        "Contrarian PRIORITY + Robust":
            lambda s: s.contrarian_action == "PRIORITY" and s.antifragile == "Robust",
        # Contrarian AVOID (stocks the contrarian warns against despite consensus love)
        "Contrarian PASS (consensus pet — avoid)":
            lambda s: s.contrarian_action == "PASS" and s.action in ("BUY","STRONG BUY"),
        # Contrarian INVESTIGATE
        "Contrarian INVESTIGATE + Final BUY":
            lambda s: s.contrarian_action == "INVESTIGATE" and s.action in ("BUY","STRONG BUY"),
        "Contrarian INVESTIGATE + Final SELL":
            lambda s: s.contrarian_action == "INVESTIGATE" and s.action in ("SELL","STRONG SELL"),
    }

    data: dict = {g: {p: [] for p in HP} for g in groups}
    for sig in signals:
        if sig.ticker not in prices:
            continue
        fwd = forward_returns(sig, prices[sig.ticker], bench, HP)
        if not fwd:
            continue
        for gname, fn in groups.items():
            if fn(sig):
                for p, (sr, br, er) in fwd.items():
                    if er is not None:
                        data[gname][p].append(er)

    print_table("EXPERIMENT I — Contrarian Sub-Segments (excess vs SPY)", list(groups), data)

    # Head-to-head: pure contrarian vs buffett-backed contrarian
    print("\n  KEY COMPARISON — Pure Contrarian vs Buffett-Backed Contrarian:")
    for p in [252, 504]:
        pure = data["Contrarian PRIORITY + Buffett PASS (pure contrarian)"][p]
        backed = data["Contrarian PRIORITY + Buffett PRIORITY"][p]
        if len(pure) >= 5 and len(backed) >= 5:
            t, pv = welch(backed, pure)
            print(f"    {pl(p)}: Backed={np.mean(backed):+.1%} (n={len(backed)})  Pure={np.mean(pure):+.1%} (n={len(pure)})  spread={np.mean(backed)-np.mean(pure):+.1%}  p={pv:.3f} {sig_stars(pv).strip()}")


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT J: Multi-factor composite — combining the best signals
# ══════════════════════════════════════════════════════════════════════════════

def experiment_j(signals, prices, bench):
    section("EXPERIMENT J: Multi-Factor Composite — Best-of-Breed Portfolio")
    print("  Combines the strongest signals discovered across all experiments.")
    print("  Tests whether layering filters improves significance vs single factors.\n")

    # From prior experiments:
    # A winner: B+C agree PRIORITY → 2Y +10.2%
    # B winner: High conviction BUY → 2Y +16%
    # C winner: BUY + Fragile → 1Y +13.3%, 2Y +26.3%
    # D winner: Stable multi-year SELL → 2Y -26.8%
    # Build per-ticker signal history for stable SELL detection
    by_ticker: dict = defaultdict(list)
    for s in signals:
        by_ticker[s.ticker].append((s.fiscal_year, s))
    for t in by_ticker:
        by_ticker[t].sort(key=lambda x: x[0])

    stable_sell_tickers = set()
    for ticker, entries in by_ticker.items():
        consecutive = 0
        for i, (fy, sig) in enumerate(entries):
            if sig.action in ("SELL", "STRONG SELL"):
                consecutive += 1
            else:
                consecutive = 0
            if consecutive >= 2:
                stable_sell_tickers.add((ticker, fy))

    groups = {
        # === LONG SIDE — best BUY signals ===
        "[LONG-1] B+C PRIORITY → BUY (exp A winner)":
            lambda s: s.buffett_action == "PRIORITY" and s.contrarian_action == "PRIORITY" and s.action in ("BUY","STRONG BUY"),
        "[LONG-2] High-conv BUY (exp B winner)":
            lambda s: s.conviction == "High" and s.action in ("BUY","STRONG BUY"),
        "[LONG-3] BUY + Fragile (exp C hidden gem)":
            lambda s: s.action in ("BUY","STRONG BUY") and s.antifragile == "Fragile",
        "[LONG-4] B+C PRIORITY + High Conv BUY (A×B)":
            lambda s: s.buffett_action == "PRIORITY" and s.contrarian_action == "PRIORITY" and s.action in ("BUY","STRONG BUY") and s.conviction == "High",
        "[LONG-5] High-conv BUY + Fragile (B×C)":
            lambda s: s.conviction == "High" and s.action in ("BUY","STRONG BUY") and s.antifragile == "Fragile",
        "[LONG-6] B+C PRIORITY + BUY + Fragile (A×C)":
            lambda s: s.buffett_action == "PRIORITY" and s.contrarian_action == "PRIORITY" and s.action in ("BUY","STRONG BUY") and s.antifragile == "Fragile",
        "[LONG-7] ALL THREE: B+C PRIORITY + High Conv + Fragile":
            lambda s: s.buffett_action == "PRIORITY" and s.contrarian_action == "PRIORITY" and s.conviction == "High" and s.action in ("BUY","STRONG BUY") and s.antifragile == "Fragile",
        # === SHORT SIDE — best SELL signals ===
        "[SHORT-1] SELL (all) (baseline)":
            lambda s: s.action in ("SELL","STRONG SELL"),
        "[SHORT-2] SELL + High Conv (exp B)":
            lambda s: s.action in ("SELL","STRONG SELL") and s.conviction == "High",
        "[SHORT-3] SELL + Fragile (exp H candidate)":
            lambda s: s.action in ("SELL","STRONG SELL") and s.antifragile == "Fragile",
        "[SHORT-4] Stable multi-year SELL (exp D winner)":
            lambda s: (s.ticker, s.fiscal_year) in stable_sell_tickers,
        "[SHORT-5] SELL + No Moat (exp H candidate)":
            lambda s: s.action in ("SELL","STRONG SELL") and s.moat == "None",
        "[SHORT-6] SELL + High Conv + Fragile (B×C combined)":
            lambda s: s.action in ("SELL","STRONG SELL") and s.conviction == "High" and s.antifragile == "Fragile",
        "[SHORT-7] SELL + No Moat + Fragile (double trouble)":
            lambda s: s.action in ("SELL","STRONG SELL") and s.moat == "None" and s.antifragile == "Fragile",
    }

    data: dict = {g: {p: [] for p in HP} for g in groups}
    for sig in signals:
        if sig.ticker not in prices:
            continue
        fwd = forward_returns(sig, prices[sig.ticker], bench, HP)
        if not fwd:
            continue
        for gname, fn in groups.items():
            if fn(sig):
                for p, (sr, br, er) in fwd.items():
                    if er is not None:
                        data[gname][p].append(er)

    print_table("EXPERIMENT J — Multi-Factor Composite Signals (excess vs SPY)", list(groups), data)

    # Build best long-short spread portfolios from the above
    print("\n  BEST L/S PORTFOLIOS — combining long and short signals:")
    print(f"  {'Portfolio':55s}  {'nL':>5s}  {'nS':>5s}  {'1Y spread':>12s}  {'2Y spread':>12s}")
    print("─" * 110)

    long_candidates = [k for k in groups if k.startswith("[LONG")]
    short_candidates = [k for k in groups if k.startswith("[SHORT")]

    for lk in long_candidates:
        for sk in short_candidates:
            for p in [252, 504]:
                lv = data[lk][p]
                sv = data[sk][p]
                if len(lv) < 10 or len(sv) < 10:
                    continue
                spread = np.mean(lv) - np.mean(sv)
                combined = list(lv) + list(-np.array(sv))
                _, pv = ttest(combined)
                if spread > 0.10 and pv < 0.10:
                    label = f"LONG: {lk[8:25]}... vs SHORT: {sk[9:25]}..."
                    print(f"  {label:55s}  {len(lv):>5d}  {len(sv):>5d}  "
                          f"{'--- ' if p!=252 else f'{spread:+.1%} p={pv:.3f}{sig_stars(pv).strip()}':>12s}  "
                          f"{'--- ' if p!=504 else f'{spread:+.1%} p={pv:.3f}{sig_stars(pv).strip()}':>12s}")

    # Cleaner: just show best combos explicitly
    best_combos = [
        ("[LONG-2] High-conv BUY (exp B winner)", "[SHORT-4] Stable multi-year SELL (exp D winner)"),
        ("[LONG-3] BUY + Fragile (exp C hidden gem)", "[SHORT-3] SELL + Fragile (exp H candidate)"),
        ("[LONG-2] High-conv BUY (exp B winner)", "[SHORT-6] SELL + High Conv + Fragile (B×C combined)"),
        ("[LONG-5] High-conv BUY + Fragile (B×C)", "[SHORT-4] Stable multi-year SELL (exp D winner)"),
        ("[LONG-1] B+C PRIORITY → BUY (exp A winner)", "[SHORT-4] Stable multi-year SELL (exp D winner)"),
        ("[LONG-2] High-conv BUY (exp B winner)", "[SHORT-2] SELL + High Conv (exp B)"),
        ("[LONG-3] BUY + Fragile (exp C hidden gem)", "[SHORT-4] Stable multi-year SELL (exp D winner)"),
    ]
    print("\n  EXPLICIT BEST COMBOS:")
    print(f"  {'Long leg':45s}  {'Short leg':40s}  {'nL':>5s}  {'nS':>5s}  {'1Y':>12s}  {'2Y':>12s}")
    print("─" * 130)
    for lk, sk in best_combos:
        nl = max((len(data[lk][p]) for p in HP), default=0)
        ns = max((len(data[sk][p]) for p in HP), default=0)
        line = f"  {lk[:45]:45s}  {sk[:40]:40s}  {nl:>5d}  {ns:>5d}"
        for p in [252, 504]:
            lv = data[lk][p]
            sv = data[sk][p]
            if len(lv) < 5 or len(sv) < 5:
                line += f"  {'N/A':>12s}"
                continue
            spread = np.mean(lv) - np.mean(sv)
            combined = list(lv) + list(-np.array(sv))
            _, pv = ttest(combined)
            line += f"  {spread:+.1%} p={pv:.3f}{sig_stars(pv).strip():>4s}"
        print(line)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 120)
    print("  EON EXPERIMENTS E–J: Deep Alpha Discovery")
    print("  E: Triple combos  F: Alignment  G: Fragility factor")
    print("  H: SELL anatomy   I: Contrarian  J: Multi-factor composite")
    print("=" * 120)

    signals = load_signals(DEFAULT_DB_PATH, max_fy=2024, min_fy=2020)
    if not signals:
        print("No signals found.")
        sys.exit(1)

    tickers = sorted(set(s.ticker for s in signals))
    min_fy = min(s.fiscal_year for s in signals)
    logger.info(f"Fetching prices for {len(tickers)} tickers...")
    prices, bench = fetch_prices(tickers, min_fy, 2024)
    if bench is None:
        print("ERROR: No SPY data.")
        sys.exit(1)
    logger.info(f"Prices ready for {len(prices)}/{len(tickers)} tickers.")

    experiment_e(signals, prices, bench)
    experiment_f(signals, prices, bench)
    experiment_g(signals, prices, bench)
    experiment_h(signals, prices, bench)
    experiment_i(signals, prices, bench)
    experiment_j(signals, prices, bench)

    print("\n" + "=" * 120)
    print("  All experiments E–J complete.")
    print("=" * 120)


if __name__ == "__main__":
    main()
