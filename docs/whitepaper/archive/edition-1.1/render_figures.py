# ruff: noqa: RUF001
# Mathematical signs and typographic dashes below are intentional figure text.
"""Render the paper's eight figures from the frozen evidence snapshot.

No database, model, or network access: everything comes from figure-data/.
SVG for Markdown, PDF for LaTeX, PNG for review. Run from anywhere:

  python docs/whitepaper/render_figures.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "eon-paper-mpl"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "figure-config.yaml"
CFG = yaml.safe_load(CONFIG_PATH.read_text())
C = CFG["palette"]
E = json.loads((HERE / "figure-data/evidence.json").read_text())
B = E["backtest"]
OUT = HERE / "figures"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "text.color": C["ink"],
        "axes.labelcolor": C["ink"],
        "xtick.color": C["muted"],
        "ytick.color": C["muted"],
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "svg.hashsalt": "eon-whitepaper-v1",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
        "axes.axisbelow": True,
        "hatch.linewidth": 0.6,
    }
)


# ---------------------------------------------------------------- primitives


def canvas(height: float, title: str, subtitle: str) -> tuple[Figure, Axes]:
    fig = plt.figure(figsize=(CFG["figure_width_inches"], height), facecolor="white")
    ax = fig.add_axes((0, 0, 1, 1), xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    ax.text(0.015, 1 - 0.18 / height, title, size=14, weight="bold", va="top")
    ax.text(0.015, 1 - 0.49 / height, subtitle, size=9, color=C["muted"], va="top")
    return fig, ax


def text(ax: Axes, x: float, y: float, value: str, **kwargs: Any) -> None:
    kwargs.setdefault("size", 9)
    ax.text(x, y, value, va=kwargs.pop("va", "center"), **kwargs)


def arrow(
    ax: Axes, start: tuple[float, float], end: tuple[float, float], color: str | None = None
) -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        zorder=0,
        arrowprops={"arrowstyle": "-|>", "color": color or C["muted"], "lw": 1, "mutation_scale": 10},
    )


def box(
    ax: Axes, x: float, y: float, w: float, h: float, face: str | None = None, **kwargs: Any
) -> None:
    ax.add_patch(
        Rectangle(
            (x, y),
            w,
            h,
            facecolor=face or C["light"],
            edgecolor=kwargs.pop("edgecolor", "none"),
            **kwargs,
        )
    )


def footer(ax: Axes, value: str) -> None:
    text(ax, 0.015, 0.035, value, color=C["muted"], va="bottom")


def save(fig: Figure, name: str) -> None:
    for ext in ["svg", "pdf", "png"]:
        metadata: dict[str, Any] = {}
        if ext == "pdf":
            metadata = {"CreationDate": None, "ModDate": None, "Creator": "EON paper renderer"}
        elif ext == "svg":
            metadata = {"Date": None, "Creator": "EON paper renderer"}
        fig.savefig(OUT / f"{name}.{ext}", dpi=CFG["preview_dpi"], metadata=metadata)
    plt.close(fig)


def pct(value: float, digits: int = 1, sign: bool = True) -> str:
    return f"{value * 100:+.{digits}f}" if sign else f"{value * 100:.{digits}f}"


# ------------------------------------------------------------------- figures


def one_reading() -> None:
    s = E["specimen"]
    fig, ax = canvas(
        5.35,
        "One filing becomes one countable verdict",
        "Specimen: Apple 10-K for fiscal 2025, filed 31 Oct 2025  /  illustrative, not evidence",
    )
    # Input and call.
    for x, w, face, head, body, ink in [
        (0.015, 0.27, C["light"], "INPUT", "The whole 10-K text,\nname and fiscal year", C["ink"]),
        (0.365, 0.27, C["accent"], "ONE MODEL CALL", "Gemini 2.5 Flash with\na JSON response schema", "white"),
        (0.715, 0.27, C["accent_light"], f"{s['total_fields']} FIELDS", "Three lenses of eleven,\nsynthesis, final verdict", C["ink"]),
    ]:
        box(ax, x, 0.715, w, 0.13, face)
        text(ax, x + 0.015, 0.81, head, weight="bold", color="white" if ink == "white" else C["accent"] if face == C["accent_light"] else C["ink"])
        text(ax, x + 0.015, 0.757, body, color=ink, linespacing=1.4)
    arrow(ax, (0.29, 0.78), (0.36, 0.78))
    arrow(ax, (0.64, 0.78), (0.71, 0.78))
    # Three lenses.
    lenses = [
        ("BUFFETT", "buffett", ["Moat and moat rating", "Management, pricing power", "ROIC, free cash flow", "Intrinsic value"]),
        ("TALEB", "taleb", ["Fragility, tail risks", "Optionality, skin in the game", "Hidden risks, dependencies", "Lindy effect, via negativa"]),
        ("CONTRARIAN", "contrarian", ["Consensus, why it is wrong", "Hidden strengths and flaws", "Market pricing, positioning", "Catalyst timeline"]),
    ]
    for i, (name, key, rows) in enumerate(lenses):
        x = 0.015 + i * 0.33
        box(ax, x, 0.32, 0.31, 0.325, "#F3F4F2")
        text(ax, x + 0.015, 0.61, f"{name}  ·  11 fields", weight="bold")
        for j, row in enumerate(rows):
            text(ax, x + 0.015, 0.56 - j * 0.042, row, color=C["muted"])
        lens = s["lenses"][key]
        verdict = lens["verdict"].rstrip(".")
        text(ax, x + 0.015, 0.39, f"Lens verdict: {verdict}", weight="bold", color=C["accent"])
        text(ax, x + 0.015, 0.35, f"Action signal: {lens['action_signal']}", color=C["accent"])
        arrow(ax, (x + 0.155, 0.315), (x + 0.155 + (1 - i) * 0.15 * 1.1, 0.262))
    # Final verdict.
    box(ax, 0.2, 0.17, 0.6, 0.085, C["accent"])
    text(ax, 0.5, 0.2125, f"FINAL VERDICT   {s['final_verdict_opening'].replace('. ', '  ·  ')}", ha="center", color="white", weight="bold", size=10)
    text(ax, 0.5, 0.12, "The backtest reads only the first word: STRONG BUY, BUY, HOLD, SELL or STRONG SELL.", ha="center")
    footer(ax, "Source: data/eon.db, stored reading 1. Filed after the model's cutoff; no outcome is claimed.")
    save(fig, "01-one-reading")


def three_designs() -> None:
    m = {k: date.fromisoformat(v["date"]) for k, v in E["milestones"].items()}
    a, mb, ob, o = E["archive"], E["market_batch"], E["options_batch"], E["origin"]
    fig, ax = canvas(
        4.6,
        "Fix the question, then read everything",
        "Four designs, May 2025 to June 2026  /  dates from files, git history and batch records",
    )
    chart = fig.add_axes((0.3, 0.19, 0.68, 0.6))
    start, end = date(2025, 4, 15), date(2026, 7, 1)
    chart.set_xlim(start, end)
    chart.set_ylim(-0.6, 3.6)
    chart.set_yticks([])
    ticks = [date(2025, 6, 1), date(2025, 10, 1), date(2026, 2, 1), date(2026, 6, 1)]
    chart.set_xticks(ticks, [t.strftime("%b %Y") for t in ticks])
    chart.tick_params(axis="x", length=0, pad=6)
    chart.grid(axis="x", color=C["light"], lw=0.8)

    def span(y: float, a0: date, a1: date, face: str) -> None:
        chart.barh(y, max((a1 - a0).days, 3), left=a0, height=0.42, color=face, lw=0)

    rows = [
        (3, "Origin", "A study of excellence"),
        (2, "Design 1", "Workflow builder"),
        (1, "Design 2", "One question, all filings"),
        (0, "Design 3", "Hypothesis workflows"),
    ]
    for y, name, detail in rows:
        yy = 0.19 + 0.6 * (y + 0.6) / 4.2
        text(ax, 0.015, yy + 0.026, name, weight="bold")
        text(ax, 0.015, yy - 0.02, detail, color=C["muted"])
    days = sorted(o["readings_by_day"])
    span(3, date.fromisoformat(days[0]), date(2025, 6, 4), C["warning"])
    chart.text(date(2025, 6, 14), 3, f"{o['filing_readings']:,} filing readings in May,\nthen scans on 26 May and 4 June", va="center", size=9, linespacing=1.3)
    span(2, m["workflow_builder_added"], m["workflow_builder_removed"], C["muted"])
    chart.text(m["workflow_builder_added"] - timedelta(days=6), 2, f"{a['saved_workflows']} saved chains", va="center", ha="right", size=9)
    market0 = date.fromisoformat(mb["first_reading"][:10])
    market1 = date.fromisoformat(mb["last_reading"][:10])
    span(1, market0, market1, C["accent"])
    options0 = date.fromisoformat(ob["first_reading"][:10])
    span(1, options0, options0 + timedelta(days=2), C["accent_mid"])
    chart.text(market0 - timedelta(days=6), 1, f"{mb['readings']:,} readings in 13 days", va="center", ha="right", size=9, color=C["accent"], weight="bold")
    span(0, m["cspp_split_into_four_calls"], m["anchored_scores_in_code"], C["ink"])
    chart.text(m["cspp_split_into_four_calls"] - timedelta(days=6), 0, "Scores judged by the model,\ntotals computed in code", va="center", ha="right", size=9, linespacing=1.3)
    cutoff = date.fromisoformat(B["knowledge_cutoff"])
    footer(ax, "Sources: origin files; git log; fintel.db; eon.db. Rust: a ledger written before its outcomes.")
    save(fig, "03-three-designs")


def quota_clock() -> None:
    mb = E["market_batch"]
    hourly = {datetime.fromisoformat(k): v for k, v in mb["hourly_utc"].items()}
    days = mb["per_quota_day"]
    fig, ax = canvas(
        4.0,
        "The quota is the clock",
        "Market-wide batch, 8 to 21 February 2026  /  readings per hour, UTC",
    )
    chart = fig.add_axes((0.07, 0.24, 0.9, 0.46))
    t0 = min(hourly).replace(hour=0)
    t1 = max(hourly).replace(hour=23)
    hours = [t0 + timedelta(hours=i) for i in range(int((t1 - t0).total_seconds() // 3600) + 1)]
    chart.bar(hours, [hourly.get(h, 0) for h in hours], width=1 / 24, color=C["accent"], lw=0, align="edge")
    reset = CFG["quota_reset_hour_utc"]
    for day in sorted(days):
        start = datetime.fromisoformat(day) + timedelta(hours=reset)
        chart.axvline(start, color=C["warning"], lw=0.7, ls=":")
        chart.text(start + timedelta(hours=12), 238, f"{days[day]}", ha="center", size=9, color=C["ink"])
    chart.set_xlim(t0, t1)
    chart.set_ylim(0, 260)
    chart.set_yticks([0, 100, 200])
    chart.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    chart.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    chart.tick_params(length=0, pad=5)
    chart.grid(axis="y", color=C["light"], lw=0.7)
    text(ax, 0.07, 0.745, "Readings per quota day (above the bars)", color=C["muted"])
    ceiling = CFG["keys"] * CFG["requests_per_key_per_day"]
    text(ax, 0.015, 0.125, f"{CFG['keys']} keys × {CFG['requests_per_key_per_day']} requests = {ceiling} readings a day.", weight="bold", color=C["accent"])
    text(ax, 0.55, 0.125, "Dotted lines: quota reset, midnight Pacific.", color=C["warning"])
    footer(ax, f"Source: data/eon.db, batch {mb['name']}. The last quota day is partial.")
    save(fig, "02-quota-clock")


def verdict_mix() -> None:
    order = ["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"]
    faces = [C["accent"], C["accent_mid"], C["light"], C["warning_mid"], C["warning"]]
    hatches = ["", "", "", "", ""]
    data = {
        y: d for y, d in B["verdicts_by_vintage"].items() if sum(d.values()) >= CFG["min_vintage_readings"]
    }
    fig, ax = canvas(
        3.9,
        "Half of every vintage is HOLD",
        "Final verdicts by fiscal-year vintage  /  vintages with at least 400 dated readings",
    )
    chart = fig.add_axes((0.14, 0.2, 0.74, 0.5))
    years = sorted(data)
    for i, year in enumerate(years):
        counts = data[year]
        n = sum(counts.values())
        left = 0.0
        for verdict, face, hatch in zip(order, faces, hatches, strict=True):
            share = counts.get(verdict, 0) / n
            chart.barh(i, share, left=left, color=face, height=0.62, lw=0.4, edgecolor="white", hatch=hatch)
            if share >= 0.06:
                chart.text(left + share / 2, i, f"{share:.0%}", ha="center", va="center", size=9, color="white" if verdict in ("STRONG BUY", "STRONG SELL") else C["ink"])
            left += share
        chart.text(1.01, i, f"n = {n:,}", va="center", size=9, color=C["muted"])
    chart.set_yticks(range(len(years)), [f"FY{y}" for y in years])
    chart.invert_yaxis()
    chart.set_xlim(0, 1)
    chart.set_xticks([])
    chart.tick_params(length=0)
    for verdict, face, x in zip(order, faces, [0.14, 0.325, 0.44, 0.555, 0.67], strict=True):
        box(ax, x, 0.765, 0.018, 0.035, face, edgecolor=C["muted"] if verdict == "HOLD" else "none", lw=0.5)
        text(ax, x + 0.025, 0.782, verdict.title())
    footer(ax, "Source: evaluation/results.json. Vintage = fiscal-year label. Shares under 6% are unlabelled.")
    save(fig, "04-verdict-mix")


def cutoff_timeline() -> None:
    cutoff = date.fromisoformat(B["knowledge_cutoff"])
    price_end = date.fromisoformat(B["price_end"])
    fig, ax = canvas(
        4.4,
        "Most outcomes predate the model's cutoff",
        "One-year windows by vintage, from median entry  /  whiskers: 10th to 90th percentile entry",
    )
    chart = fig.add_axes((0.12, 0.25, 0.78, 0.5))
    lo, hi = date(2021, 1, 1), date(2027, 3, 1)
    chart.axvspan(lo, cutoff, color=C["light"], lw=0)
    chart.axvline(cutoff, color=C["warning"], lw=1.4)
    chart.axvline(price_end, color=C["muted"], lw=1, ls="--")
    windows = [w for w in B["entry_windows"] if 2020 <= w["fiscal_year"] <= 2025]
    for i, w in enumerate(windows):
        entry = date.fromisoformat(w["entry_median"])
        exit_ = entry + timedelta(days=365)
        before = exit_ < cutoff
        after = entry > cutoff
        face = C["muted"] if before else C["accent"] if after else C["warning_mid"]
        seen = min(exit_, price_end)
        chart.barh(i, (seen - entry).days, left=entry, height=0.5, color=face, lw=0, hatch="" if before or after else "///")
        if exit_ > price_end:
            chart.barh(i, (exit_ - price_end).days, left=price_end, height=0.5, color="white", edgecolor=face, lw=0.8, ls="--")
        chart.plot([date.fromisoformat(w["entry_p10"]), date.fromisoformat(w["entry_p90"])], [i, i], color=C["ink"], lw=1)
    chart.set_yticks(range(len(windows)), [f"FY{w['fiscal_year']}" for w in windows])
    chart.invert_yaxis()
    chart.set_xlim(lo, hi)
    chart.xaxis.set_major_locator(mdates.YearLocator())
    chart.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    chart.tick_params(length=0, pad=5)
    chart.text(cutoff - timedelta(days=20), -0.9, "Knowledge cutoff, Jan 2025", ha="right", size=9, color=C["warning"], weight="bold")
    chart.text(price_end + timedelta(days=15), -0.9, "Prices end", size=9, color=C["muted"])
    chart.set_ylim(len(windows) - 0.4, -1.3)
    legend = [
        (C["muted"], "", "Outcome may be in training data"),
        (C["warning_mid"], "///", "Straddles the cutoff"),
        (C["accent"], "", "Filed after the cutoff"),
    ]
    for (face, hatch, label), x in zip(legend, [0.12, 0.49, 0.72], strict=True):
        ax.add_patch(Rectangle((x, 0.13), 0.022, 0.035, facecolor=face, hatch=hatch, edgecolor="white", lw=0))
        text(ax, x + 0.03, 0.148, label)
    footer(ax, "Source: evaluation/trades.csv. Dashed outline: part of the window not yet observed.")
    save(fig, "05-cutoff-timeline")


def horizons() -> None:
    fig, ax = canvas(
        4.6,
        "After the cutoff: same sign, wider intervals",
        "BUY minus SELL, excess over SPY  /  95% intervals  /  cutoff 31 January 2025",
    )
    labels = ["6M", "1Y", "2Y"]
    panels = [
        ("A  Mean spread, percentage points", "spread", "spread_se", (-15, 45)),
        ("B  Rank spread, percentile points", "rank_spread", "rank_spread_se", (-5, 25)),
    ]
    for p, (title, key, se_key, limits) in enumerate(panels):
        left = 0.06 + p * 0.49
        text(ax, left - 0.045, 0.79, title, weight="bold")
        chart = fig.add_axes((left + 0.02, 0.24, 0.41, 0.47))
        chart.axhline(0, color=C["ink"], lw=0.8)
        for i, horizon in enumerate(labels):
            h = B["horizons"][horizon]
            for offset, sample, face, marker in [
                (-0.12, "window_before_cutoff", C["muted"], "s"),
                (0.12, "filed_after_cutoff", C["accent"], "o"),
            ]:
                s = h.get(sample, {})
                if key not in s:
                    chart.text(i + offset, limits[0] + 3, "no data\nyet", ha="center", size=9, color=C["accent"])
                    continue
                value, half = s[key] * 100, 1.96 * s[se_key] * 100
                clipped = min(value + half, limits[1])
                chart.plot([i + offset] * 2, [value - half, clipped], color=face, lw=1.4)
                if value + half > limits[1]:
                    chart.annotate("", xy=(i + offset, limits[1]), xytext=(i + offset, limits[1] - 3), arrowprops={"arrowstyle": "-|>", "color": face, "lw": 1.2})
                chart.scatter([i + offset], [value], marker=marker, s=34, color=face, zorder=3, edgecolor="white", lw=0.6)
                chart.text(i + offset + (0.08 if offset > 0 else -0.08), value, f"{value:.1f}", va="center", ha="left" if offset > 0 else "right", size=9, color=face)
        chart.set_xlim(-0.5, 2.5)
        chart.set_ylim(*limits)
        chart.set_xticks(range(3), labels)
        chart.tick_params(length=0, pad=5)
        chart.grid(axis="y", color=C["light"], lw=0.7)
    ax.scatter([0.075], [0.135], marker="s", s=30, color=C["muted"])
    text(ax, 0.095, 0.135, "Window closed before the cutoff")
    ax.scatter([0.49], [0.135], marker="o", s=30, color=C["accent"])
    text(ax, 0.51, 0.135, "Filed after the cutoff")
    footer(ax, "Source: evaluation/results.json. Intervals: 1.96 Welch standard errors.")
    save(fig, "06-horizons")


def decomposition() -> None:
    fig, ax = canvas(
        3.9,
        "The cutoff removed the industry tilt, not the rest",
        "One-year rank spread, split by a within-industry permutation test  /  percentile points",
    )
    chart = fig.add_axes((0.3, 0.28, 0.62, 0.42))
    rows = [("historical", "Closed before the cutoff"), ("post_cutoff_1y", "Filed after the cutoff")]
    for i, (key, label) in enumerate(rows):
        t = B["primary"][key]["rank_within_vintage_industry"]
        tilt, total = t["null_mean"] * 100, t["observed_spread"] * 100
        within = total - tilt
        chart.barh(i, tilt, color=C["light"], edgecolor=C["muted"], hatch="///", height=0.5, lw=0.6)
        chart.barh(i, within, left=tilt, color=C["accent"], height=0.5, lw=0)
        chart.text(total + 0.3, i, f"{total:.1f}  (p = {t['p_two_sided']:.4f})", va="center", size=9)
        chart.text(tilt + within / 2, i, f"{within:.1f}", ha="center", va="center", size=9, color="white", weight="bold")
        if tilt >= 1:
            chart.text(tilt / 2, i, f"{tilt:.1f}", ha="center", va="center", size=9, color=C["ink"], weight="bold")
    labels = []
    for key, label in rows:
        n = B["primary"][key]["summary"]
        labels.append(f"{label}\n{n['n_long']:,} BUY, {n['n_short']:,} SELL")
    chart.set_ylim(1.6, -0.6)
    chart.set_xlim(0, 16)
    chart.set_yticks([0, 1], labels)
    for tick in chart.get_yticklabels():
        tick.set_color(C["ink"])
        tick.set_linespacing(1.4)
    chart.set_xticks([0, 5, 10, 15])
    chart.tick_params(length=0, pad=5)
    chart.grid(axis="x", color=C["light"], lw=0.7)
    box(ax, 0.3, 0.13, 0.022, 0.035, C["light"], edgecolor=C["muted"], hatch="///", lw=0.6)
    text(ax, 0.33, 0.148, "Industry tilt (null mean)")
    box(ax, 0.64, 0.13, 0.022, 0.035, C["accent"])
    text(ax, 0.67, 0.148, "Within industry")
    footer(ax, "Source: evaluation/results.json. Rank statistic added after seeing the tails.")
    save(fig, "07-decomposition")


def tails() -> None:
    values = B["post_cutoff_1y"]
    top = B["post_cutoff_1y_top"][0]
    fig, ax = canvas(
        4.0,
        "One stock can decide a mean",
        "Filed after the cutoff  /  one-year excess return over SPY per reading, symmetric log scale",
    )
    chart = fig.add_axes((0.12, 0.25, 0.85, 0.47))
    rng = np.random.default_rng(20260929)
    for i, (leg, face, label) in enumerate([("long", C["accent"], "BUY"), ("short", C["warning"], "SELL")]):
        v = np.array(values[leg]) * 100
        chart.scatter(v, i + rng.uniform(-0.18, 0.18, len(v)), s=7, color=face, alpha=0.55, lw=0)
        mean, median = v.mean(), np.median(v)
        chart.plot([mean, mean], [i - 0.3, i + 0.3], color=C["ink"], lw=1.6)
        chart.plot([median, median], [i - 0.3, i + 0.3], color=C["ink"], lw=1.2, ls=":")
        chart.text(-100, i - 0.36, f"{label}  n = {len(v)}   mean {mean:+.1f}%   median {median:+.1f}%".replace("-", "−"), size=9, va="center", color=face, weight="bold")
    chart.set_xscale("symlog", linthresh=100)
    chart.set_xlim(-100, 5000)
    chart.set_xticks([-100, -50, 0, 50, 100, 1000, 3000], ["−100%", "−50%", "0", "+50%", "+100%", "+1,000%", "+3,000%"])
    chart.set_ylim(1.55, -0.95)
    chart.set_yticks([])
    chart.tick_params(length=0, pad=5)
    chart.grid(axis="x", color=C["light"], lw=0.7)
    chart.annotate(
        f"{top['ticker']}  +{top['excess_1Y'] * 100:,.0f}%\nalone adds about {top['excess_1Y'] * 100 / len(values['long']):.0f} points\nto the BUY mean",
        xy=(top["excess_1Y"] * 100, 0),
        xytext=(150, -0.62),
        size=9,
        color=C["warning"],
        arrowprops={"arrowstyle": "-|>", "color": C["warning"], "lw": 1},
    )
    text(ax, 0.12, 0.13, "Solid line: mean.  Dotted line: median.  Linear between −100% and +100%.", color=C["muted"])
    footer(ax, "Source: evaluation/trades.csv. Filed after 31 Jan 2025; outcome by 28 Sep 2026.")
    save(fig, "08-tails")


def forward_tests() -> None:
    o = E["origin"]["ledger"]["scores"]
    post = B["primary"]["post_cutoff_1y"]["rank_within_vintage_industry"]
    rows = [
        ("EON verdict", "BUY − SELL; filed after cutoff", post["observed_spread"], post["null_mean"], post["null_sd"], post["p_two_sided"], C["accent"]),
        ("2025 compounder score", "Top − bottom fifth; 10–13 May 2025", o["compounder"]["quintile_rank_spread"]["observed"], o["compounder"]["quintile_rank_spread"]["null_mean"], o["compounder"]["quintile_rank_spread"]["null_sd"], o["compounder"]["quintile_rank_spread"]["p_two_sided"], C["warning"]),
        ("2025 contrarian alpha", "Top − bottom fifth; 26 May 2025", o["alpha"]["quintile_rank_spread"]["observed"], o["alpha"]["quintile_rank_spread"]["null_mean"], o["alpha"]["quintile_rank_spread"]["null_sd"], o["alpha"]["quintile_rank_spread"]["p_two_sided"], C["muted"]),
        ("2025 options direction", "Calls − puts; 4 June 2025, 6 months", o["direction"]["spread"]["observed"], o["direction"]["spread"]["null_mean"], o["direction"]["spread"]["null_sd"], o["direction"]["spread"]["p_two_sided"], C["muted"]),
    ]
    fig, ax = canvas(
        4.3,
        "The clean tests do not agree",
        "Tests the model could not pass from memory  /  percentile points of excess return",
    )
    chart = fig.add_axes((0.44, 0.2, 0.53, 0.56))
    chart.axvline(0, color=C["ink"], lw=0.8)
    for i, (label, when, obs, mean, sd, p, face) in enumerate(rows):
        lo, hi = (mean - 1.96 * sd) * 100, (mean + 1.96 * sd) * 100
        chart.barh(i, hi - lo, left=lo, height=0.42, color=C["light"], lw=0)
        chart.scatter([obs * 100], [i], s=46, color=face, zorder=3, edgecolor="white", lw=0.6)
        value = f"{obs * 100:+.1f}  (p = {p:.2g})".replace("-", "−")
        if obs * 100 < lo:
            chart.text(obs * 100 - 0.9, i, value, ha="right", va="center", size=9, color=face)
        else:
            chart.text(max(obs * 100, hi) + 0.9, i, value, ha="left", va="center", size=9, color=face)
        yy = 0.2 + 0.56 * (3.6 - i - 0.1) / 4.2
        text(ax, 0.015, yy + 0.022, label, weight="bold", size=9)
        text(ax, 0.015, yy - 0.022, when, color=C["muted"])
    chart.set_ylim(3.6, -0.6)
    chart.set_yticks([])
    chart.set_xlim(-27, 25)
    chart.set_xticks([-10, 0, 10])
    chart.tick_params(length=0, pad=5)
    chart.grid(axis="x", color=C["light"], lw=0.7)
    box(ax, 0.44, 0.105, 0.022, 0.035, C["light"])
    text(ax, 0.47, 0.122, "95% of within-industry shuffles")
    footer(ax, "Sources: evaluation/results.json; evaluation/origin-ledger/results.json. One year unless stated.")
    save(fig, "09-forward-tests")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    sources = [CONFIG_PATH, HERE / "figure-data/evidence.json", Path(__file__)]
    run: dict[str, Any] = {
        "stage": "whitepaper-figures",
        "timestamp": datetime.now(UTC).isoformat(),
        "config": CFG,
        "versions": {
            "python": sys.version.split()[0],
            "matplotlib": matplotlib.__version__,
            "numpy": np.__version__,
        },
        "inputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    }
    (OUT / "run.json").write_text(json.dumps(run, indent=2) + "\n")
    renders = [one_reading, quota_clock, three_designs, verdict_mix, cutoff_timeline, horizons, decomposition, tails, forward_tests]
    assert len(renders) == CFG["figure_count"]
    for render in renders:
        render()
    run["outputs"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(OUT.iterdir())
        if p.suffix in {".svg", ".png", ".pdf"}
    }
    (OUT / "run.json").write_text(json.dumps(run, indent=2) + "\n")
    print(f"Rendered {len(renders)} figures as SVG, PDF and PNG.")


if __name__ == "__main__":
    main()
