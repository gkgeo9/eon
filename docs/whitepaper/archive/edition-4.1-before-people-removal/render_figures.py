# ruff: noqa: RUF001
# Mathematical signs and typographic dashes below are intentional figure text.
"""Render the paper's seventeen figures from the frozen evidence snapshot.

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
import matplotlib.font_manager as fm
for font in Path("/System/Library/Fonts/Supplemental").glob("Arial*.ttf"):
    fm.fontManager.addfont(str(font))
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
ST = E["stories"]
LONG_SET, SHORT_SET = {"BUY", "STRONG BUY"}, {"SELL", "STRONG SELL"}
VERDICT_FACE = {
    "STRONG BUY": C["accent"], "BUY": C["accent_mid"], "HOLD": C["light"],
    "SELL": C["warning_mid"], "STRONG SELL": C["warning"],
}
OUT = HERE / "figures"
plt.rcParams.update(
    {
        "font.family": ["Arial", "DejaVu Sans"],
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
    # Source paths are collected in Appendix C; statistical annotations stay
    # within their plots and captions rather than a second caption here.
    return


def save(fig: Figure, name: str) -> None:
    from matplotlib.text import Text
    for item in fig.findobj(Text):
        if item.get_fontsize() < 8.2:
            item.set_fontsize(8.2)
        item.set_text(item.get_text().replace("p = 0.0001", "p ≤ 0.0001"))
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
        4.8,
        "One filing becomes one countable verdict",
        "Specimen: Apple 10-K for fiscal 2025, filed 31 Oct 2025  /  first stored reading",
    )
    # Input and call.
    for x, w, face, head, body, ink in [
        (0.015, 0.27, C["light"], "INPUT", "Extracted 10-K text,\nname and fiscal year", C["ink"]),
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
    apple = [r for r in ST["named"]["AAPL"] if r["fiscal_year"] == 2025][0]
    text(ax, 0.5, 0.12, f"Six months later, Apple had trailed SPY by {abs(apple['excess_6M']) * 100:.1f} points: a draw.", ha="center", weight="bold")
    footer(ax, "Source: data/eon.db, reading 1; evaluation/trades.csv. The reading's claims are not audited.")
    save(fig, "01-one-reading")


def three_designs() -> None:
    m = {k: date.fromisoformat(v["date"]) for k, v in E["milestones"].items()}
    a, mb, ob, o = E["archive"], E["market_batch"], E["options_batch"], E["origin"]
    fig, ax = canvas(
        4.6,
        "Fix the question, then read everything",
        "Four stages, May 2025 to June 2026  /  dates from files, git history and batch records",
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
    footer(ax, "Sources: origin files; git log; fintel.db; eon.db. The rust bar's scores predate their outcomes.")
    save(fig, "10-four-stages")


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
    text(ax, 0.015, 0.125, f"Nominal allowance: {ceiling} requests/day.", weight="bold", color=C["accent"])
    text(ax, 0.55, 0.125, "Dotted lines: quota reset, midnight Pacific.", color=C["warning"])
    footer(ax, f"Source: data/eon.db, batch {mb['name']}. The last quota day is partial.")
    save(fig, "06-quota-clock")


def verdict_mix() -> None:
    order = ["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"]
    faces = [C["accent"], C["accent_mid"], C["light"], C["warning_mid"], C["warning"]]
    hatches = ["///", "", "", "", "///"]
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
    fig, ax = canvas(
        4.8,
        "Three dates decide what a test can prove",
        "When the filing appeared, where the model's knowledge ends, and when the verdict was written",
    )
    rows = [
        (0.73, "WITH HINDSIGHT", ["Filing", "Outcome", "Model cutoff", "Reading"],
         "The model may already know how the story ended.", C["muted"]),
        (0.49, "AFTER THE CUTOFF", ["Model cutoff", "Filing", "Outcome begins", "Reading"],
         "The filing follows the stated cutoff; the verdict still came late.", C["accent"]),
        (0.25, "WRITTEN IN ADVANCE", ["Filing", "Reading", "Record frozen", "Outcome"],
         "The verdict exists before anything it predicts. Only this is a forecast.", C["warning"]),
    ]
    xs = [0.12, 0.365, 0.61, 0.855]
    for y, label, events, note, face in rows:
        text(ax, 0.015, y + 0.1, label, weight="bold", color=face)
        ax.plot([xs[0], xs[-1]], [y, y], color=face, lw=1.2)
        for x, event in zip(xs, events, strict=True):
            ax.scatter([x], [y], s=28, color=face, zorder=3)
            text(ax, x, y + 0.035, event, ha="center", va="bottom")
        text(ax, 0.015, y - 0.07, note, color=C["muted"])
    footer(ax, "Event order is schematic; spacing is not elapsed time. Source: the evaluation protocols.")
    save(fig, "09-three-clocks")


def horizons() -> None:
    fig, ax = canvas(
        4.6,
        "After the cutoff: same sign, wider intervals",
        "BUY minus SELL  /  descriptive ±1.96 SE bars  /  January 2025 cutoff",
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
    footer(ax, "Source: evaluation/results.json. Bars assume independent readings; not clustered intervals.")
    save(fig, "06-horizons")


def decomposition() -> None:
    fig, ax = canvas(
        3.9,
        "After the cutoff, the industry bet disappeared",
        "One-year BUY-minus-SELL rank spread, split in two  /  percentile points",
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
        n = B["primary"][key]["rank_within_vintage_industry"]
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
    text(ax, 0.33, 0.148, "Which industries it favoured")
    box(ax, 0.64, 0.13, 0.022, 0.035, C["accent"])
    text(ax, 0.67, 0.148, "Which companies within them")
    footer(ax, "Source: evaluation/results.json. Exploratory; decomposition does not identify a cause.")
    save(fig, "06-decomposition")


def tails() -> None:
    values = B["post_cutoff_1y"]
    top = B["post_cutoff_1y_top"][0]
    fig, ax = canvas(
        4.0,
        "One stock can decide a mean",
        "Post-cutoff filings  /  one-year excess over SPY, percentage points  /  symmetric log axis",
    )
    chart = fig.add_axes((0.12, 0.25, 0.85, 0.47))
    rng = np.random.default_rng(20260929)
    for i, (leg, face, label) in enumerate([("long", C["accent"], "BUY"), ("short", C["warning"], "SELL")]):
        v = np.array(values[leg]) * 100
        chart.scatter(v, i + rng.uniform(-0.18, 0.18, len(v)), s=7, color=face, alpha=0.55, lw=0)
        mean, median = v.mean(), np.median(v)
        chart.plot([mean, mean], [i - 0.3, i + 0.3], color=C["ink"], lw=1.6)
        chart.plot([median, median], [i - 0.3, i + 0.3], color=C["ink"], lw=1.2, ls=":")
        chart.text(-100, i + 0.40, f"{label}  n = {len(v)}   mean {mean:+.1f}   median {median:+.1f}".replace("-", "−"), size=9, va="center", color=face, weight="bold")
    chart.set_xscale("symlog", linthresh=100)
    chart.set_xlim(min(-150, min(values["long"] + values["short"]) * 100 - 5), 5000)
    chart.set_xticks([-100, 0, 100, 1000, 3000], ["−100", "0", "+100", "+1,000", "+3,000"])
    chart.set_ylim(1.55, -0.95)
    chart.set_yticks([])
    chart.tick_params(length=0, pad=5)
    chart.grid(axis="x", color=C["light"], lw=0.7)
    chart.annotate(
        f"Babcock & Wilcox, \\$0.46 to \\$15.72\n+{top['excess_1Y'] * 100:,.0f} points, checked twice\nadds {top['excess_1Y'] * 100 / len(values['long']):.0f} points to the BUY mean",
        xy=(top["excess_1Y"] * 100, 0),
        xytext=(100, -0.72),
        size=9,
        color=C["warning"],
        arrowprops={"arrowstyle": "-|>", "color": C["warning"], "lw": 1},
    )
    text(ax, 0.12, 0.13, "Solid line: mean.  Dotted line: median.  Linear between −100 and +100 points.", color=C["muted"])
    footer(ax, "Source: evaluation/trades.csv; BW checked against Nasdaq closes. Filed after 31 Jan 2025.")
    save(fig, "12-tails")


def forward_tests() -> None:
    scores = E["origin"]["ledger"]["scores"]
    rows = [
        ("Compounder resemblance", "May 2025 · 1 year · n = 1,766", scores["compounder"]["quintile_rank_spread"], C["warning"]),
        ("Contrarian score", "May 2025 · 1 year · n = 1,780", scores["alpha"]["quintile_rank_spread"], C["muted"]),
        ("Options direction", "June 2025 · 6 months · n = 849", scores["direction"]["spread"], C["muted"]),
    ]
    fig, ax = canvas(
        4.2,
        "Looking like a great company was a bad sign",
        "Scores written down in 2025, before their outcomes  /  top minus bottom, return percentile",
    )
    chart = fig.add_axes((0.44, 0.24, 0.53, 0.50))
    chart.axvline(0, color=C["ink"], lw=0.8)
    for i, (label, detail, t, face) in enumerate(rows):
        obs, lo, hi = [t[k] * 100 for k in ("observed", "null_p2_5", "null_p97_5")]
        chart.plot([lo, hi], [i, i], color=C["light"], lw=12, solid_capstyle="butt")
        chart.scatter([obs], [i], marker="o", s=43, color=face, zorder=3, edgecolor="white", lw=0.7)
        value = f"{obs:+.1f}  p = {t['p_two_sided']:.2g}".replace("-", "−")
        if obs < lo:
            chart.text(obs - 0.8, i, value, ha="right", va="center", size=9, color=face)
        else:
            chart.text(max(obs, hi) + 0.8, i, value, ha="left", va="center", size=9, color=face)
        yy = 0.24 + 0.50 * (2.6 - i) / 3.2
        text(ax, 0.015, yy + 0.02, label, weight="bold")
        text(ax, 0.015, yy - 0.025, detail, color=C["muted"])
    chart.set_ylim(2.6, -0.6)
    chart.set_yticks([])
    chart.set_xlim(-27, 16)
    chart.set_xticks([-10, 0, 10])
    chart.tick_params(length=0, pad=5)
    chart.grid(axis="x", color=C["light"], lw=0.7)
    text(ax, 0.015, 0.13, "Band: middle 95% of industry shuffles, not a confidence interval.", color=C["muted"])
    footer(ax, "Source: evaluation/origin-ledger/results.json. Top/bottom score groups include threshold ties.")
    save(fig, "14-dated-ledger")


def staircase() -> None:
    hist = B["primary"]["historical"]["rank_within_vintage_industry"]
    post = B["primary"]["post_cutoff_1y"]["rank_within_vintage_industry"]
    comp = E["origin"]["ledger"]["scores"]["compounder"]["quintile_rank_spread"]
    fig, ax = canvas(
        4.9,
        "The stricter the test, the weaker the signal",
        "How far the model's favourites out-ranked its rejects  /  one year, percentile points",
    )
    chart = fig.add_axes((0.06, 0.3, 0.9, 0.44))
    steps = [
        (hist["observed_spread"], "Graded with hindsight", "Outcomes the model may\nalready have read about", C["muted"], hist["p_two_sided"], "BUY vs SELL"),
        (post["observed_spread"], "Graded on filings it\ncould not have read", "Filed after its cutoff;\nstatistic chosen late", C["accent"], post["p_two_sided"], "BUY vs SELL"),
        (comp["observed"], "Graded against scores\nwritten in advance", "May 2025 resemblance to\n39 great companies", C["warning"], comp["p_two_sided"], "top vs bottom fifth"),
    ]
    for i, (value, head, sub, face, pv, contrast) in enumerate(steps):
        v = value * 100
        chart.bar(i, v, width=0.56, color=face, lw=0)
        chart.text(i, v + (0.8 if v >= 0 else -0.8), f"{v:+.1f}".replace("-", "−"), ha="center", va="bottom" if v >= 0 else "top", size=17, weight="bold", color=face)
        x = 0.06 + 0.9 * (i + 0.5) / 3
        text(ax, x, 0.215, head, ha="center", weight="bold", linespacing=1.3)
        text(ax, x, 0.125, sub, ha="center", color=C["muted"], linespacing=1.3)
    chart.axhline(0, color=C["ink"], lw=0.9)
    chart.set_xlim(-0.5, 2.5)
    chart.set_ylim(-16, 16)
    chart.set_xticks([])
    chart.set_yticks([-10, 0, 10], ["−10", "0", "+10"])
    chart.tick_params(length=0, pad=4)
    chart.grid(axis="y", color=C["light"], lw=0.7)
    footer(ax, "Sources: evaluation/results.json; origin-ledger/results.json. The third bar tests a different score.")
    save(fig, "01-staircase")


def verdict_ladder() -> None:
    order = ["STRONG SELL", "SELL", "HOLD", "BUY", "STRONG BUY"]
    short = ["Str. sell", "Sell", "Hold", "Buy", "Str. buy"]
    fig, ax = canvas(
        4.5,
        "After the cutoff, the SELL calls stop working",
        "Average one-year return percentile by verdict  /  0.5 is the middle of the pack",
    )
    panels = [("historical", "BEFORE THE CUTOFF", C["muted"]), ("post_cutoff", "AFTER THE CUTOFF", C["accent"])]
    for p, (key, label, face) in enumerate(panels):
        lad = ST["ladder"][key]
        left = 0.08 + p * 0.47
        chart = fig.add_axes((left, 0.27, 0.4, 0.46))
        text(ax, left, 0.79, label, weight="bold", color=face)
        chart.axhline(0.5, color=C["ink"], lw=0.8, ls=":")
        xs, ys = [], []
        for i, verdict in enumerate(order):
            r = lad["verdicts"][verdict]
            y, se = r["mean_rank"], r["rank_se"] or 0
            chart.plot([i, i], [y - 1.96 * se, y + 1.96 * se], color=VERDICT_FACE[verdict] if verdict != "HOLD" else C["muted"], lw=1.3)
            small = r["n"] < 60
            chart.scatter([i], [y], s=44, zorder=3, color="white" if small else (VERDICT_FACE[verdict] if verdict != "HOLD" else C["muted"]), edgecolor=VERDICT_FACE[verdict] if verdict != "HOLD" else C["muted"], lw=1.4)
            xs.append(i)
            ys.append(y)
        chart.plot(xs, ys, color=face, lw=1, alpha=0.6, zorder=2)
        chart.set_xlim(-0.5, 4.5)
        chart.set_ylim(0.35, 0.68)
        chart.set_xticks(range(5), [f"{lab}\n{lad['verdicts'][v]['n']:,}" for lab, v in zip(short, order, strict=True)])
        chart.set_yticks([0.4, 0.5, 0.6] if p == 0 else [])
        chart.tick_params(length=0, pad=4)
        chart.grid(axis="y", color=C["light"], lw=0.7)
        text(ax, left, 0.11, f"Spearman {lad['spearman_level_vs_rank']:.3f},  p = {lad['p_two_sided']:.2g}".replace("-", "−"), color=face)
    footer(ax, "Source: evaluation/stories.json. Numbers: readings. Bars: ±1.96 SE. Hollow: fewer than 60.")
    save(fig, "11-verdict-ladder")


def fading_edge() -> None:
    vint = B["vintages"]
    years = [y for y in sorted(vint) if "1Y" in vint[y] and 2020 <= int(y) <= 2025]
    fig, ax = canvas(
        4.2,
        "The edge shrank as the cutoff approached",
        "One-year BUY-minus-SELL rank spread by fiscal year  /  percentile points  /  ±1.96 SE",
    )
    chart = fig.add_axes((0.1, 0.24, 0.86, 0.5))
    chart.axhline(0, color=C["ink"], lw=0.8)
    chart.axvspan(3.5, 5.5, color=C["accent_light"], lw=0)
    chart.axvline(3.5, color=C["warning"], lw=1.3)
    chart.text(3.55, 30, "Model's knowledge cutoff", color=C["warning"], size=9, weight="bold", va="top")
    for i, y in enumerate(years):
        r = vint[y]["1Y"]
        v, se = r["rank_spread"] * 100, 1.96 * r["rank_spread_se"] * 100
        small = r["n_long"] + r["n_short"] < 200
        face = C["accent"] if int(y) >= 2024 else C["muted"]
        chart.plot([i, i], [v - se, v + se], color=face, lw=1.4)
        chart.scatter([i], [v], s=50, zorder=3, color="white" if small else face, edgecolor=face, lw=1.5)
        chart.text(i + 0.12, v, f"{v:.1f}", va="center", size=9, color=face)
        chart.text(i, -13.5, f"{r['n_long']}/{r['n_short']}", ha="center", size=9, color=C["muted"])
    chart.set_xlim(-0.5, len(years) - 0.5)
    chart.set_ylim(-15, 31)
    chart.set_xticks(range(len(years)), [f"FY{y}\nfiled {int(y) + 1}" for y in years])
    chart.set_yticks([0, 10, 20])
    chart.tick_params(length=0, pad=5)
    chart.grid(axis="y", color=C["light"], lw=0.7)
    text(ax, 0.1, 0.12, "Numbers below the axis: BUY / SELL readings. Hollow: fewer than 200 readings.", color=C["muted"])
    footer(ax, "Source: evaluation/results.json. FY2023's window straddles the cutoff; FY2024 is mostly after it.")
    save(fig, "05-fading-edge")


def company_grid() -> None:
    g = ST["grid"]
    rows = g["drawn"]
    years = [str(y) for y in ST["config"]["grid"]["fiscal_years"]]
    height = 8.6
    fig, ax = canvas(
        height,
        "Company by company, the edge is thin",
        f"{len(rows)} companies drawn at random, seed {ST['config']['grid']['seed']}  /  one-year excess return over SPY, points",
    )
    top, bottom = 0.855, 0.125
    row_h = (top - bottom) / len(rows)
    x0, col_w = 0.36, 0.122
    for j, y in enumerate(years):
        text(ax, x0 + j * col_w + col_w / 2, top + 0.025, f"FY{y}", ha="center", weight="bold")
    cut_x = x0 + 4 * col_w - 0.004
    ax.plot([cut_x, cut_x], [bottom, top + 0.045], color=C["warning"], lw=1.2, ls="--")
    text(ax, cut_x + 0.005, top + 0.058, "cutoff", color=C["warning"], size=9, weight="bold")
    for i, row in enumerate(rows):
        y = top - (i + 1) * row_h
        ax.add_patch(FancyBboxPatch((0.015, y + row_h * 0.16), 0.075, row_h * 0.68, boxstyle="round,pad=0,rounding_size=0.006", facecolor=C["ink"], edgecolor="none"))
        text(ax, 0.0525, y + row_h / 2, row["ticker"], ha="center", color="white", weight="bold", size=8.5)
        name = row["name"]
        for suffix in (", Inc.", " Inc.", " Incorporated", " Corporation", " Enterprises", " L.P.", ", Inc"):
            name = name.replace(suffix, "")
        name = name.replace("International", "Intl.")
        import textwrap
        name = "\n".join(textwrap.wrap(name, width=24))
        text(ax, 0.1, y + row_h / 2, name, color=C["muted"], size=8.2, linespacing=1.0)
        for j, yr in enumerate(years):
            cell = row["cells"][yr]
            verdict, excess = cell["verdict"], cell["excess"] * 100
            face = VERDICT_FACE[verdict]
            ax.add_patch(FancyBboxPatch((x0 + j * col_w + 0.004, y + row_h * 0.1), col_w - 0.008, row_h * 0.8, boxstyle="round,pad=0,rounding_size=0.006", facecolor=face, edgecolor="none"))
            dark = verdict in ("STRONG BUY", "STRONG SELL")
            mark = ""
            if verdict in LONG_SET | SHORT_SET:
                right = (verdict in LONG_SET and excess > 0) or (verdict in SHORT_SET and excess < 0)
                mark = " ✓" if right else " ✗"
            label = f"{excess:+,.0f}{mark}".replace("-", "−")
            text(ax, x0 + j * col_w + col_w / 2, y + row_h / 2, label, ha="center", size=8.5, color="white" if dark else C["ink"], weight="bold" if mark else "normal")
    legend = [("STRONG BUY", "Strong buy"), ("BUY", "Buy"), ("HOLD", "Hold"), ("SELL", "Sell"), ("STRONG SELL", "Strong sell")]
    for k, (verdict, label) in enumerate(legend):
        lx = 0.015 + k * 0.155
        ax.add_patch(FancyBboxPatch((lx, 0.083), 0.022, 0.016, boxstyle="round,pad=0,rounding_size=0.003", facecolor=VERDICT_FACE[verdict], edgecolor=C["muted"] if verdict == "HOLD" else "none", lw=0.5))
        text(ax, lx + 0.03, 0.091, label)
    text(ax, 0.79, 0.091, f"✓ {g['directional_agree']} of {g['directional_cells']} calls", weight="bold", color=C["accent"])
    footer(ax, f"Source: evaluation/stories.json. Pool: {g['eligible']} companies read every year, with a BUY and a SELL.")
    save(fig, "13-company-grid")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    sources = [CONFIG_PATH, HERE / "figure-data/evidence.json", Path(__file__), HERE / "render_diagrams.py"]
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
    for stale in OUT.glob("*.*"):
        if stale.suffix in {".svg", ".pdf", ".png"}:
            stale.unlink()
    import render_diagrams as d

    renders = [
        one_reading, d.lineage, d.architecture, d.life_of_filing, d.execution, quota_clock,
        d.database, d.catalogue, cutoff_timeline, d.before_after, verdict_ladder, tails,
        company_grid, forward_tests, d.options_ledger, d.shortcomings, d.sealed_bet,
    ]
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
