# ruff: noqa: RUF001
"""Edition 3 diagrams and new evidence figures, drawn with the house primitives.

Imported by render_figures.py; reads only figure-data/evidence.json.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import median
from typing import Any

import matplotlib.dates as mdates
import numpy as np
from matplotlib.axes import Axes
from matplotlib.patches import FancyBboxPatch

from render_figures import B, C, CFG, E, ST, arrow, canvas, footer, save, text


def rbox(ax: Axes, x: float, y: float, w: float, h: float, face: str, edge: str = "none", lw: float = 0.8, r: float = 0.012) -> None:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", facecolor=face, edgecolor=edge, lw=lw))


# ------------------------------------------------------------------ lineage


def lineage() -> None:
    fig, ax = canvas(
        5.6,
        "Five versions, one idea carried forward",
        "May 2025 to June 2026  /  each version kept what the last one taught",
    )
    stages = [
        ("10K_automator", "May–Jun 2025", C["amber"], "Scripts that read thirty years of great companies",
         "PDF pipeline · parallel workers · progress files · 11,741 readings"),
        ("standardized_sec_ai", "Oct–Nov 2025", C["indigo_mid"], "One reusable 10-K processor",
         "Pydantic schemas · the three-lens prompt · PDF discovery"),
        ("Fintel", "Dec 2025–Jan 2026", C["indigo"], "An application with a workflow builder",
         "SQLite + migrations · Streamlit interface · cross-process locks"),
        ("EON", "Feb 2026", C["accent"], "One question, asked of every filing",
         "batch queue, leases · CLI, Discord · Windows and Mac · 6,568 in 13 days"),
        ("Workflows", "May–Jun 2026", C["accent_mid"], "Hypotheses written as modules",
         "model judges, code sums · one call or four · moonshot, CSPP, options"),
    ]
    top, row_h, gap = 0.8, 0.118, 0.022
    for i, (name, when, face, what, kept) in enumerate(stages):
        y = top - (i + 1) * row_h - i * gap
        rbox(ax, 0.015, y, 0.24, row_h, face)
        text(ax, 0.03, y + row_h * 0.64, name, weight="bold", color="white", size=9.5 if len(name) < 16 else 8.5)
        text(ax, 0.03, y + row_h * 0.3, when, color="white", size=8.5)
        rbox(ax, 0.27, y, 0.715, row_h, C["paper"])
        text(ax, 0.285, y + row_h * 0.66, what, weight="bold", size=9)
        text(ax, 0.285, y + row_h * 0.3, kept, size=8.5, color=C["muted"])
        if i < len(stages) - 1:
            arrow(ax, (0.135, y - 0.001), (0.135, y - gap + 0.001), C["muted"])
    footer(ax, "Sources: origin files and dates; git history of EON; data/archive/fintel.db; data/eon.db.")
    save(fig, "02-lineage")


# ------------------------------------------------------------- architecture


def architecture() -> None:
    fig, ax = canvas(
        6.9,
        "Five layers between a filing and a verdict",
        "EON's architecture  /  module names from the repository",
    )
    layers = [
        ("SOURCES", C["muted"], [("SEC EDGAR", "10-K HTML and filing metadata"), ("Market data", "Yahoo prices, FactSet snapshot")]),
        ("ACQUIRE", C["indigo"], [("Downloader", "EDGAR filings,\ncached per year"), ("SEC queue", "≤ 10 req/s,\nfile-locked"), ("Converter", "headless Chrome\nprints a PDF"), ("Extractor", "PyPDF2 text,\nnothing cut")]),
        ("REASON", C["accent"], [("Prompt + schema", "three lenses,\n35 fields"), ("Key manager", "25 keys,\nleast-used first"), ("Request queue", "per-key locks,\n25 slots"), ("Gemini call", "validated;\nretried by cause")]),
        ("REMEMBER", C["amber"], [("SQLite (WAL)", "runs, results,\nbatch items"), ("File cache", "27.5 GB PDFs,\nfetched once"), ("Backups", "backup API,\nlast five kept"), ("Migrations", "v001–v014,\nat start-up")]),
        ("OPERATE", C["ink"], [("CLI", "multi-day\nbatches"), ("Web UI", "explore and\nresume"), ("Discord", "alerts while\nyou sleep"), ("Monitors", "disk, memory,\nstray Chrome")]),
    ]
    top, row_h, gap = 0.855, 0.118, 0.032
    for r, (label, face, boxes) in enumerate(layers):
        y = top - (r + 1) * row_h - r * gap
        text(ax, 0.015, y + row_h / 2, label, weight="bold", color=face, size=9)
        n = len(boxes)
        x0, span = 0.155, 0.83
        bw = (span - (n - 1) * 0.014) / n
        for i, (title, body) in enumerate(boxes):
            x = x0 + i * (bw + 0.014)
            light = {C["muted"]: C["light"], C["indigo"]: C["indigo_light"], C["accent"]: C["accent_light"], C["amber"]: C["amber_light"], C["ink"]: C["light"]}[face]
            rbox(ax, x, y, bw, row_h, light)
            text(ax, x + 0.012, y + row_h - 0.028, title, weight="bold", color=face if face != C["muted"] else C["ink"], size=9)
            text(ax, x + 0.012, y + row_h * 0.36, body, size=8, color=C["ink"], linespacing=1.3)
            if label == "ACQUIRE" and i < n - 1:
                arrow(ax, (x + bw, y + row_h / 2), (x + bw + 0.014, y + row_h / 2), C["indigo"])
            if label == "REASON" and i < n - 1:
                arrow(ax, (x + bw, y + row_h / 2), (x + bw + 0.014, y + row_h / 2), C["accent"])
        if r < len(layers) - 1:
            arrow(ax, (0.57, y - 0.002), (0.57, y - gap + 0.002), C["muted"])
    footer(ax, "Source: eon/ package structure; limits from eon/ai/api_config.py. Arrows: the path of one filing.")
    save(fig, "03-architecture")


# --------------------------------------------------------- life of a filing


def life_of_filing() -> None:
    p = E["pipeline"]
    html = p["html_10k_samples"]
    html_chars = median(r["html_chars"] for r in html)
    visible = median(r["visible_chars"] for r in html)
    ratios = [r["markup_ratio"] for r in html]
    tags = [r["inline_xbrl_tags"] for r in html]
    reading = E["inventory"]["reading_chars_median"]
    fig, ax = canvas(
        4.9,
        f"A {int(p['pages_median'])}-page filing becomes one word",
        "The median 10-K on its way through EON  /  characters, logarithmic scale",
    )
    chart = fig.add_axes((0.36, 0.2, 0.6, 0.58))
    rows = [
        ("EDGAR HTML", f"{min(ratios):.1f}–{max(ratios):.1f}× more than its text", html_chars, C["muted"]),
        ("Visible text", "what a person would read", visible, C["indigo_mid"]),
        ("Text sent to the model", f"{int(p['pages_median'])} pages ≈ {p['tokens_median_est'] // 1000}k tokens", p["chars_median"], C["indigo"]),
        ("The reading", "35 fields, about 5,000 words", reading, C["accent_mid"]),
        ("The verdict", "one word", 4, C["accent"]),
    ]
    for i, (label, sub, value, face) in enumerate(rows):
        chart.barh(i, value, left=1, color=face, height=0.58, lw=0)
        chart.text(value * 1.25, i, f"{value:,.0f}", va="center", size=9, color=face, weight="bold")
        yy = 0.2 + 0.58 * (len(rows) - 0.5 - i) / len(rows)
        text(ax, 0.015, yy + 0.022, label, weight="bold")
        text(ax, 0.015, yy - 0.022, sub, color=C["muted"], size=8.5)
    chart.set_xscale("log")
    chart.set_xlim(1, 3e8)
    chart.set_ylim(len(rows) - 0.5, -0.5)
    chart.set_yticks([])
    chart.set_xticks([1, 1e2, 1e4, 1e6], ["1", "100", "10k", "1M"])
    chart.tick_params(length=0, pad=5)
    chart.grid(axis="x", color=C["light"], lw=0.7)
    footer(ax, f"Sources: evaluation/pipeline-measurements.json ({len(html)} raw 10-Ks; {p['sample']} PDFs); data/eon.db.")
    save(fig, "04-life-of-a-filing")


# ---------------------------------------------------------------- execution


def execution() -> None:
    fig, ax = canvas(
        5.6,
        "One company runs in a line; a batch runs in lanes",
        "How the CLI executes  /  schematic, not to scale",
    )
    stage_face = {"download": C["indigo_mid"], "pdf": C["indigo"], "text": C["indigo_light"], "model": C["accent"], "save": C["amber"], "pause": C["light"], "reset": C["amber_light"]}

    def lane(chart: Any, y: float, segments: list[tuple[str, float]], start: float = 0.0) -> float:
        x = start
        for kind, width in segments:
            chart.barh(y, width, left=x, height=0.55, color=stage_face[kind], lw=0.4, edgecolor="white", hatch="///" if kind in ("pause", "reset") else None)
            x += width
        return x

    one_year = [("download", 0.5), ("pdf", 1.1), ("text", 0.4), ("model", 1.6), ("save", 0.25), ("pause", 1.0)]
    top = fig.add_axes((0.14, 0.64, 0.84, 0.13))
    text(ax, 0.015, 0.815, "A  eon analyze AAPL --years 3", weight="bold")
    x = 0.0
    for yr in range(3):
        x = lane(top, 0, one_year, x)
    for k in range(3):
        top.text(k * 4.85 + 0.1, 0.62, f"year {k + 1}", size=8, color=C["muted"])
    top.set_xlim(0, 15.5)
    top.set_ylim(-0.6, 0.9)
    top.axis("off")
    text(ax, 0.015, 0.7, "one\nprocess", color=C["muted"], size=8.5, linespacing=1.2)

    low = fig.add_axes((0.14, 0.16, 0.84, 0.42))
    text(ax, 0.015, 0.59, "B  eon batch companies.csv  (25 keys; five lanes shown)", weight="bold")
    rng = np.random.default_rng(5)
    for w in range(5):
        x = w * 0.6
        while x < 10.5:
            seg = [(k, v * rng.uniform(0.8, 1.25)) for k, v in one_year]
            x = lane(low, w, seg, x)
        lane(low, w, [("reset", 3.2)], 10.7)
        x2 = 13.9
        lane(low, w, one_year[:4], x2)
        low.text(-0.3, w, f"worker {w + 1}", ha="right", va="center", size=8.5, color=C["muted"])
        for hb in np.arange(1.5, 10.5, 2.2):
            low.plot([hb + w * 0.2], [w - 0.38], marker="|", color=C["ink"], ms=5, lw=0)
    low.axvline(10.7, color=C["amber"], lw=1.3)
    low.text(10.8, 5.0, "keys spent: every worker\nwaits for midnight Pacific", size=8.5, color=C["amber"], va="top", weight="bold")
    low.text(0, 5.0, "staggered starts; each worker leases\none company and reserves one key", size=8.5, color=C["muted"], va="top")
    low.set_xlim(-0.2, 19.5)
    low.set_ylim(6.0, -0.6)
    low.axis("off")
    legend = [("download", "SEC download"), ("pdf", "Chrome → PDF"), ("text", "text"), ("model", "model call"), ("save", "save year"), ("pause", "per-key pause"), ("reset", "quota wait")]
    for k, (kind, label) in enumerate(legend):
        lx = 0.015 + (k % 4) * 0.245
        ly = 0.13 - (k // 4) * 0.035
        ax.add_patch(FancyBboxPatch((lx, ly - 0.012), 0.022, 0.024, boxstyle="round,pad=0,rounding_size=0.003", facecolor=stage_face[kind], edgecolor="none", hatch="///" if kind in ("pause", "reset") else None))
        text(ax, lx + 0.03, ly, label, size=8.5)
    text(ax, 0.75, 0.095, "|  lease heartbeat", size=8.5, color=C["ink"])
    footer(ax, "Source: eon/cli, eon/ui/services/batch_queue.py, eon/ai/request_queue.py.")
    save(fig, "05-execution")


# ----------------------------------------------------------------- database


def database() -> None:
    fig, ax = canvas(
        6.2,
        "The database is the batch's memory",
        "Core tables and the mechanisms that keep many writers from colliding",
    )
    tables = [
        (0.015, 0.54, "batch_jobs", ["batch_id", "status, priority", "totals: done / failed", "last_activity_at"], C["indigo"]),
        (0.015, 0.2, "batch_items", ["batch_id → batch_jobs", "ticker, status", "lease_owner", "lease_expires_at", "last_heartbeat_at", "completed_years_list"], C["indigo"]),
        (0.265, 0.54, "analysis_runs", ["run_id", "ticker, analysis_type", "config_json", "completed_years"], C["accent"]),
        (0.265, 0.2, "analysis_results", ["run_id → analysis_runs", "ticker, fiscal_year", "result_type", "result_json (35 fields)", "UNIQUE(run, ticker, year,", "   filing, type)"], C["accent"]),
    ]
    for x, y, name, cols, face in tables:
        h = 0.07 + 0.042 * len(cols)
        rbox(ax, x, y, 0.23, h, "white", edge=face, lw=1.1)
        rbox(ax, x, y + h - 0.05, 0.23, 0.05, face)
        text(ax, x + 0.01, y + h - 0.025, name, weight="bold", color="white", size=9)
        for j, col in enumerate(cols):
            text(ax, x + 0.012, y + h - 0.08 - j * 0.042, col, size=8.2, color=C["ink"])
    arrow(ax, (0.13, 0.54), (0.13, 0.48), C["indigo"])
    arrow(ax, (0.38, 0.54), (0.38, 0.505), C["accent"])
    arrow(ax, (0.245, 0.32), (0.265, 0.32), C["muted"])
    notes = [
        ("WAL journal", "readers never block the one writer"),
        ("busy_timeout 30 s", "then up to 10 retries, jittered backoff"),
        ("Claim a company", "UPDATE … WHERE pending: one winner"),
        ("Heartbeat", "renews the lease; silence lets it expire"),
        ("Crash recovery", "dead worker's items return to pending"),
        ("Save each year", "resume from the last completed fiscal year"),
        ("v014 unique index", "ended a double-save that duplicated rows"),
        ("Backups", "SQLite backup API; the last five kept"),
    ]
    text(ax, 0.53, 0.805, "HOW CONCURRENT WRITES STAY SAFE", weight="bold", color=C["amber"], size=9)
    for j, (head, body) in enumerate(notes):
        y = 0.75 - j * 0.07
        rbox(ax, 0.53, y - 0.027, 0.455, 0.055, C["amber_light"])
        text(ax, 0.543, y + 0.008, head, weight="bold", size=8.5)
        text(ax, 0.543, y - 0.014, body, size=8.2, color=C["ink"])
    text(ax, 0.015, 0.14, "Also: file_cache, year checkpoints, custom prompts; 14 migrations.", size=8.5, color=C["muted"])
    footer(ax, "Source: eon/ui/database/repository.py and migrations; eon/ui/services/batch_queue.py.")
    save(fig, "07-database")


# ---------------------------------------------------------------- catalogue


def catalogue() -> None:
    inv = E["inventory"]["counts"]
    fig, ax = canvas(
        4.8,
        f"{inv['total']:,} answers in seventeen months",
        "Every stored model answer, by kind of question  /  bubble area is the number of answers",
    )
    chart = fig.add_axes((0.25, 0.2, 0.72, 0.55))
    rows = ["Excellence study", "Contrarian scan", "Options", "Three-lens verdict", "Frameworks"]
    items = [
        (0, date(2025, 5, 8), inv["origin_filing_readings"] + inv["origin_factor_syntheses"] + inv["origin_comparisons"], C["amber"], "2025 scripts"),
        (1, date(2025, 5, 26), inv["origin_contrarian"], C["amber"], ""),
        (2, date(2025, 6, 4), inv["origin_options"], C["amber"], ""),
        (3, date(2025, 12, 20), inv["fintel_archive"], C["indigo"], "Fintel"),
        (3, date(2026, 1, 28), inv["eon_mac"], C["indigo_mid"], "Mac"),
        (3, date(2026, 2, 14), inv["eon_SimplifiedAnalysis"], C["accent"], "EON"),
        (2, date(2026, 2, 25), inv["eon_AsymmetricOptionsV4"], C["accent"], ""),
        (4, date(2026, 5, 21), inv["eon_CSPPv26AnalysisResult"], C["accent_mid"], "CSPP"),
        (4, date(2026, 6, 4), inv["eon_MoonshotExcellenceResult"], C["accent_mid"], "Moonshot"),
    ]
    offsets = {"Fintel": (-40, "right", -0.28), "Mac": (0, "center", -0.42), "EON": (30, "left", -0.02), "CSPP": (-8, "right", -0.3), "Moonshot": (10, "left", -0.3)}
    for r, d, n, face, label in items:
        chart.scatter([d], [r], s=max(18, n / 12), color=face, alpha=0.85, lw=0, zorder=3)
        dx, ha, dy = offsets.get(label, (26 if n >= 3000 else 12, "left", -0.26))
        tag = f"{label}  {n:,}" if label in offsets else f"{n:,}"
        chart.text(d + timedelta(days=dx), r + dy, tag, size=8.5, color=C["ink"], weight="bold", ha=ha)
        if label and label not in offsets:
            chart.text(d + timedelta(days=dx), r + 0.14, label, size=8, color=C["muted"])
    chart.set_yticks(range(len(rows)), rows)
    chart.set_ylim(len(rows) - 0.4, -0.6)
    chart.set_xlim(date(2025, 4, 1), date(2026, 9, 30))
    ticks = [date(2025, 5, 1), date(2025, 9, 1), date(2026, 1, 1), date(2026, 5, 1)]
    chart.set_xticks(ticks, [t.strftime("%b %Y") for t in ticks])
    chart.tick_params(length=0, pad=5)
    chart.grid(axis="x", color=C["light"], lw=0.7)
    for label in chart.get_yticklabels():
        label.set_color(C["ink"])
    footer(ax, "Sources: origin project files; data/archive/fintel.db; data/eon_mac.db; data/eon.db.")
    save(fig, "08-catalogue")


# ------------------------------------------------------------- before/after


def before_after() -> None:
    h = B["horizons"]
    fig, ax = canvas(
        4.2,
        "After the cutoff, ranks halve; averages turn to noise",
        "One-year BUY minus SELL, the same test on both sides of the cutoff  /  95% intervals",
    )
    rows = [("Mean spread", "percentage points", "spread", "spread_se", (-15, 45)), ("Rank spread", "percentile points", "rank_spread", "rank_spread_se", (-5, 25))]
    for r, (label, unit, key, se_key, lim) in enumerate(rows):
        chart = fig.add_axes((0.24, 0.52 - r * 0.3, 0.52, 0.2))
        text(ax, 0.015, 0.62 - r * 0.3 + 0.02, label, weight="bold")
        text(ax, 0.015, 0.62 - r * 0.3 - 0.025, unit, color=C["muted"], size=8.5)
        chart.axvline(0, color=C["ink"], lw=0.8)
        for k, (sample, face, name) in enumerate([("window_before_cutoff", C["muted"], "before"), ("filed_after_cutoff", C["accent"], "after")]):
            s = h["1Y"][sample]
            v, half = s[key] * 100, 1.96 * s[se_key] * 100
            y = k
            chart.plot([max(v - half, lim[0]), min(v + half, lim[1])], [y, y], color=face, lw=2.2, solid_capstyle="round")
            chart.scatter([v], [y], s=50, color=face, zorder=3, edgecolor="white", lw=0.8)
            chart.text(lim[1] + 0.5, y, f"{name}: {v:.1f} ± {half:.1f}", va="center", size=8.5, color=face, weight="bold")
        chart.set_xlim(*lim)
        chart.set_ylim(1.6, -0.6)
        chart.set_yticks([])
        chart.tick_params(length=0, pad=4, labelsize=8.5)
        chart.grid(axis="x", color=C["light"], lw=0.7)
        for spine in ("right",):
            chart.spines[spine].set_visible(False)
    text(ax, 0.015, 0.12, f"Before: {h['1Y']['window_before_cutoff']['n_long']:,} BUY, {h['1Y']['window_before_cutoff']['n_short']:,} SELL.   After: {h['1Y']['filed_after_cutoff']['n_long']} BUY, {h['1Y']['filed_after_cutoff']['n_short']} SELL.", color=C["muted"])
    footer(ax, "Source: evaluation/results.json. Intervals: 1.96 standard errors assuming independent readings.")
    save(fig, "10-before-after")


# ----------------------------------------------------------- options ledger


def options_ledger() -> None:
    o = ST["options_ledger"]
    order = [("Put Bias (Downside Tail)", "Put bias"), ("No Edge (Skip)", "No edge"), ("Straddle Bias (Binary)", "Straddle"), ("Call Bias (Upside Tail)", "Call bias")]
    fig, ax = canvas(
        4.6,
        "It saw how far a stock would move, not which way",
        "Options scan of 25–26 February 2026, graded six months on  /  written before the outcome",
    )
    panels = [("mean_rank", "WHICH WAY", "Average return percentile"), ("mean_abs_rank", "HOW FAR", "Average size-of-move percentile")]
    for p, (key, head, ylab) in enumerate(panels):
        left = 0.08 + p * 0.48
        chart = fig.add_axes((left, 0.27, 0.4, 0.43))
        text(ax, left, 0.77, head, weight="bold", color=C["accent"] if p else C["muted"])
        text(ax, left, 0.735, ylab, color=C["muted"], size=8.5)
        for i, (k, lab) in enumerate(order):
            r = o["by_bias"][k]
            v = r[key]
            face = {"Put bias": C["warning_mid"], "No edge": C["light"], "Straddle": C["indigo_mid"], "Call bias": C["accent_mid"]}[lab]
            chart.bar(i, v - 0.5, bottom=0.5, color=face, width=0.62, lw=0)
            chart.text(i, v + (0.004 if v >= 0.5 else -0.004), f"{v:.3f}", ha="center", va="bottom" if v >= 0.5 else "top", size=8.5)
            chart.text(i, 0.425, f"{lab}\n{r['n']:,}", ha="center", va="top", size=8.5, color=C["ink"])
        chart.axhline(0.5, color=C["ink"], lw=0.8)
        chart.set_ylim(0.43, 0.56)
        chart.set_xlim(-0.6, 3.6)
        chart.set_xticks([])
        chart.set_yticks([0.45, 0.5, 0.55] if p == 0 else [])
        chart.tick_params(length=0, pad=4)
        chart.grid(axis="y", color=C["light"], lw=0.7)
    d, m, s = o["call_minus_put_rank"], o["straddle_minus_no_edge_abs_rank"], o["score_vs_abs_move_spearman"]
    text(ax, 0.08, 0.115, f"Calls − puts: {d['observed'] * 100:+.1f} points, p = {d['p_two_sided']:.2f}".replace("-", "−"), color=C["muted"])
    text(ax, 0.56, 0.115, f"Straddle − no edge: {m['observed'] * 100:+.1f}, p = {m['p_two_sided']:.3f}", color=C["accent"])
    text(ax, 0.56, 0.08, f"Score vs move size: ρ = {s['observed']:.2f}, p = {s['p_two_sided']:.4f}", color=C["accent"])
    footer(ax, f"Source: evaluation/stories.json; {o['n']:,} companies, {o['by_bias']['Call Bias (Upside Tail)']['n']} with a call bias.")
    save(fig, "15-options-ledger")


# ------------------------------------------------------------- shortcomings


def shortcomings() -> None:
    sc = E["score_clustering"]["compounder"]
    fig, ax = canvas(
        6.2,
        "Eight ways a fluent model went wrong",
        "Measured in the project's own outputs, 2025–2026",
    )
    o = ST["options_ledger"]["by_bias"]
    total = sum(v["n"] for v in o.values())
    cards = [
        ("99.8%", "of May 2025 analyses dated\nthemselves 2024 (1,916 of 1,919)", C["amber"]),
        ("91", "options ideas with expiry\ndates already in the past", C["amber"]),
        (f"{sc['top_values']['68'] / sc['n']:.0%}", "of all 'compounder' scores\nwere exactly 68", C["indigo"]),
        (f"{o['Put Bias (Downside Tail)']['n'] / total:.0%}", "of companies given a put bias;\n"
         f"only {o['Call Bias (Upside Tail)']['n'] / total:.0%} a call bias", C["warning"]),
        ("51%", "of three-lens verdicts\nwere HOLD", C["muted"]),
        ("~130", "spellings of six 'success\nfactors' before schemas", C["indigo"]),
        ("462", "verdicts that opened with a\nlabel instead of the answer", C["muted"]),
        ("100%", "of great companies credited\nwith 'continuous innovation'", C["warning"]),
    ]
    for k, (big, small, face) in enumerate(cards):
        col, row = k % 2, k // 2
        x, y = 0.015 + col * 0.49, 0.66 - row * 0.19
        rbox(ax, x, y, 0.475, 0.165, C["paper"])
        ax.add_patch(FancyBboxPatch((x, y), 0.012, 0.165, boxstyle="square,pad=0", facecolor=face, edgecolor="none"))
        text(ax, x + 0.03, y + 0.0825, big, size=16, weight="bold", color=face)
        text(ax, x + 0.17, y + 0.0825, small, size=8.5, linespacing=1.35)
    footer(ax, "Sources: origin files; evaluation outputs; data/eon.db; the flattening script's notes (~130).")
    save(fig, "16-shortcomings")


# --------------------------------------------------------------- sealed bet


def sealed_bet() -> None:
    s = E["sealed"]
    calls = s["published_calls"]
    buys = sorted(c["ticker"] for c in calls if c["verdict"] == "STRONG BUY")
    sells = sorted(c["ticker"] for c in calls if c["verdict"] == "STRONG SELL")
    fig, ax = canvas(
        4.9,
        f"The bet: {len(calls)} calls to check in October 2027",
        "EON's strongest current verdicts, frozen 28 September 2026  /  every one, not a selection",
    )
    for g, (label, tickers, face) in enumerate([("STRONG BUY", buys, C["accent"]), ("STRONG SELL", sells, C["warning"])]):
        y0 = 0.78 - g * 0.33
        text(ax, 0.015, y0, f"{label}  ·  {len(tickers)}", weight="bold", color=face)
        for i, t in enumerate(tickers):
            col, row = i % 10, i // 10
            x, y = 0.015 + col * 0.098, y0 - 0.075 - row * 0.068
            rbox(ax, x, y - 0.024, 0.09, 0.05, face)
            text(ax, x + 0.045, y, t, ha="center", color="white", weight="bold", size=8.5)
    text(ax, 0.015, 0.105, f"All {s['companies']:,} verdicts are frozen in evaluation/sealed-ledger/ledger.csv, SHA-256 {s['ledger_sha256'][:16]}…", size=8.5, color=C["ink"])
    footer(ax, "Primary test fixed in advance: BUY-type minus SELL-type return rank over the following year.")
    save(fig, "17-sealed-bet")
