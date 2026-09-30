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
        5.0,
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
        text(ax, 0.03, y + row_h * 0.64, name, weight="bold", color=C["ink"] if face in (C["amber"], C["indigo_mid"], C["accent_mid"]) else "white", size=9.5 if len(name) < 16 else 8.5)
        text(ax, 0.03, y + row_h * 0.3, when, color=C["ink"] if face in (C["amber"], C["indigo_mid"], C["accent_mid"]) else "white", size=8.5)
        rbox(ax, 0.27, y, 0.715, row_h, C["paper"])
        text(ax, 0.285, y + row_h * 0.66, what, weight="bold", size=9)
        text(ax, 0.285, y + row_h * 0.3, kept, size=8.5, color=C["muted"])
        if i < len(stages) - 1:
            arrow(ax, (0.135, y - 0.001), (0.135, y - gap + 0.001), C["muted"])
    footer(ax, "Sources: origin files and dates; git history of EON; data/archive/fintel.db; data/eon.db.")
    save(fig, "02-lineage")


# ------------------------------------------------------------- architecture


def architecture() -> None:
    fig, ax = canvas(5.4, "One reading, supported by a whole system",
                     "Solid arrows: filing → verdict  /  the surrounding machinery keeps it running")
    def card(x, y, w, h, title, body, face, tint):
        rbox(ax, x, y, w, h, tint)
        text(ax, x + .018, y + h - .028, title, weight="bold", color=face, size=9)
        text(ax, x + .018, y + h * .34, body, size=8.5, linespacing=1.35)
    card(.015,.775,.28,.105,"CLI", "start long-running work",C["indigo"],C["indigo_light"])
    card(.315,.775,.28,.105,"WEB INTERFACE", "launch, inspect, resume",C["indigo"],C["indigo_light"])
    card(.645,.775,.34,.105,"SHARED SERVICES", "one execution path",C["ink"],C["light"])
    for x in [.155,.455]:
        ax.plot([x,x,.81],[.775,.752,.752],color=C["indigo"],lw=.8)
    arrow(ax,(.81,.752),(.81,.775),C["indigo"])
    rows=[
      (.57,"01  ACQUIRE", C["indigo"],C["indigo_light"],[("EDGAR HTML","download and cache"),("Chrome → PDF","print the rendered page"),("Extract text","PyPDF2; no summary")]),
      (.365,"02  READ", C["accent"],C["accent_light"],[("Prompt + schema","three lenses · 35 fields"),("Model request","Gemini 2.5 Flash"),("Validate","accept or retry by cause")]),
      (.16,"03  REMEMBER", C["ink"],C["paper"],[("Save each year","result + run identity"),("SQLite database","results and queue state"),("Read / export","UI, CLI and evaluation")]),
    ]
    for y,label,face,tint,cards in rows:
        text(ax,.015,y+.152,label,weight="bold",color=face,size=9)
        for i,(title,body) in enumerate(cards):
            x=.015+i*.332
            card(x,y,.305,.12,title,body,face,tint)
            if i<2: arrow(ax,(x+.305,y+.06),(x+.332,y+.06),face)
    # Route each stage into the first box of the next without implying that
    # monitoring and storage services are additional steps in a model request.
    for y in [.57,.365]:
        ax.plot([.833,.833,.167],[y,y-.075,y-.075],color=C["muted"],lw=.8)
        arrow(ax,(.167,y-.075),(.167,y-.085),C["muted"])
    text(ax,.015,.072,"AROUND THE PATH",weight="bold",color=C["accent"],size=8.5)
    text(ax,.27,.072,"SEC queue · per-key locks · leases · backups · Discord alerts",size=8.3)
    footer(ax,"Source: eon/ package. Quotas and recovery govern the path; they are not extra analysis stages.")
    save(fig,"03-architecture")


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
        4.3,
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
        5.0,
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
            remaining = 10.7 - x
            clipped = []
            for kind, width in seg:
                if remaining <= 0: break
                take = min(width, remaining)
                clipped.append((kind, take))
                remaining -= take
            x = lane(low, w, clipped, x)
            if x >= 10.7: break
        lane(low, w, [("reset", 3.2)], 10.7)
        x2 = 13.9
        lane(low, w, one_year[:4], x2)
        low.text(-0.3, w, f"worker {w + 1}", ha="right", va="center", size=8.5, color=C["muted"])
        for hb in np.arange(1.5, 10.5, 2.2):
            low.plot([hb + w * 0.2], [w - 0.38], marker="|", color=C["ink"], ms=5, lw=0)
    low.axvline(10.7, color=C["amber"], lw=1.3)
    low.text(10.8, 5.0, "quota spent: workers wait\nfor midnight Pacific", size=8.5, color=C["ink"], va="top", weight="bold")
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
    fig, ax = canvas(5.4,"Many workers. One writer. A durable memory.",
                     "SQLite on one machine  /  claiming work and saving results are separate operations")
    text(ax,.015,.835,"A  CLAIM THE WORK",weight="bold",color=C["indigo"])
    states=[(.015,"PENDING",C["light"]),(.36,"RUNNING",C["indigo_light"]),(.705,"COMPLETE",C["accent_light"])]
    for x,label,face in states:
        rbox(ax,x,.72,.28,.075,face)
        text(ax,x+.14,.757,label,ha="center",weight="bold",size=9)
    arrow(ax,(.295,.757),(.36,.757),C["indigo"])
    arrow(ax,(.64,.757),(.705,.757),C["accent"])
    text(ax,.015,.683,"Conditional UPDATE: only a pending item can be claimed.",size=8.7)
    text(ax,.015,.65,"Heartbeat renews a 3 h lease every 5 min; stale work returns to pending.",size=8.7)
    text(ax,.015,.591,"B  SERIALIZE THE WRITES",weight="bold",color=C["accent"])
    for i in range(3):
        y=.48-i*.045
        rbox(ax,.015,y,.18,.035,C["indigo_light"])
        text(ax,.105,y+.0175,f"worker {i+1}",ha="center",size=8.5)
        arrow(ax,(.195,y+.0175),(.285,.442),C["indigo"])
    rbox(ax,.285,.4,.23,.095,C["accent_light"])
    text(ax,.4,.46,"ONE WRITER",ha="center",weight="bold",color=C["accent"])
    text(ax,.4,.426,"short transactions",ha="center",size=8.2)
    arrow(ax,(.515,.447),(.6,.447),C["accent"])
    rbox(ax,.6,.4,.195,.095,C["paper"],C["accent"])
    text(ax,.697,.46,"SQLite + WAL",ha="center",weight="bold",size=9)
    text(ax,.697,.426,"committed results",ha="center",size=8.2)
    rbox(ax,.83,.4,.155,.095,C["light"])
    text(ax,.907,.46,"UI / CLI",ha="center",weight="bold",size=8.5)
    text(ax,.907,.426,"readers",ha="center",size=8.2)
    arrow(ax,(.795,.447),(.83,.447),C["muted"])
    text(ax,.015,.363,"Busy writer? Wait up to 30 s; retry with backoff and jitter (10 attempts total).",size=8.5)
    text(ax,.015,.303,"C  KEEP TWO KINDS OF MEMORY",weight="bold",color=C["ink"])
    for x,title,body,face in [
       (.015,"batch_jobs → batch_items","queue state · owner · lease · progress",C["indigo_light"]),
       (.515,"analysis_runs → analysis_results","run config · year · validated answer",C["accent_light"])]:
        rbox(ax,x,.19,.47,.09,face)
        text(ax,x+.015,.248,title,weight="bold",size=8.7)
        text(ax,x+.015,.216,body,size=8.2)
    text(ax,.015,.133,"Per-year checkpoints reduce repeated work. A unique index rejects duplicate rows.",size=8.5)
    text(ax,.015,.098,"SQLite backup API keeps five copies. Leases are not an exactly-once guarantee.",size=8.5)
    footer(ax,"Source: repository.py, migrations v001–v014, batch_queue.py. WAL lets reads overlap writes.")
    save(fig,"07-database")


# ---------------------------------------------------------------- catalogue


def catalogue() -> None:
    inv = E["inventory"]["counts"]
    fig, ax = canvas(4.8, f"{inv['total']:,} stored answers", "Archive counts by analysis family  /  labels give exact totals")
    rows = [
      ("Excellence study", "May 2025", inv["origin_filing_readings"] + inv["origin_factor_syntheses"] + inv["origin_comparisons"], C["indigo"]),
      ("Contrarian scan", "May 2025", inv["origin_contrarian"], C["indigo"]),
      ("Options ideas", "June 2025", inv["origin_options"], C["indigo"]),
      ("Fintel analyses", "Dec 2025–Jan 2026", inv["fintel_archive"], C["indigo"]),
      ("Three-lens verdicts", "Jan–Jul 2026", inv["eon_mac"] + inv["eon_SimplifiedAnalysis"], C["accent"]),
      ("Options V4", "Feb 2026", inv["eon_AsymmetricOptionsV4"], C["accent"]),
      ("CSPP + Moonshot", "May–Jun 2026", inv["eon_CSPPv26AnalysisResult"] + inv["eon_MoonshotExcellenceResult"], C["accent"]),
    ]
    chart=fig.add_axes((.48,.16,.44,.65))
    for i,(label,when,n,face) in enumerate(rows):
        chart.barh(i,n,height=.48,color=face)
        chart.scatter([n],[i],s=16,color=face,zorder=3)
        chart.text(n+300,i,f"{n:,}",va="center",size=9)
        yy=.16+.65*(6.5-i)/7
        text(ax,.015,yy+.012,label,weight="bold")
        text(ax,.015,yy-.025,when,size=8.5,color=C["muted"])
    chart.set_ylim(6.5,-.5); chart.set_xlim(0,18500)
    chart.set_yticks([]); chart.set_xticks([0,5000,10000,15000],["0","5,000","10,000","15,000"])
    chart.tick_params(length=0); chart.grid(axis="x",color=C["light"])
    save(fig,"08-catalogue")


# ------------------------------------------------------------- before/after


def before_after() -> None:
    h = B["horizons"]
    fig, ax = canvas(
        4.2,
        "After the cutoff, ranks halve; averages turn to noise",
        "One-year BUY minus SELL, the same test on both sides of the cutoff  /  95% intervals",
    )
    rows = [("Mean spread", "percentage points", "spread", "spread_se", (-15, 45)), ("Rank spread", "percentile points", "rank_spread", "rank_spread_se", (-15, 45))]
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
        3.4,
        "Magnitude association; no directional evidence",
        "Options scan of 25–26 February 2026, graded six months on  /  written before the outcome",
    )
    panels = [("mean_rank", "WHICH WAY", "Average return percentile"), ("mean_abs_rank", "HOW FAR", "Average size-of-move percentile")]
    for p, (key, head, ylab) in enumerate(panels):
        left = 0.08 + p * 0.48
        chart = fig.add_axes((left, 0.27, 0.4, 0.43))
        text(ax, left, 0.775, head, weight="bold", color=C["accent"] if p else C["muted"])
        text(ax, left, 0.73, ylab, color=C["muted"], size=8.5)
        for i, (k, lab) in enumerate(order):
            r = o["by_bias"][k]
            v = r[key]
            face = {"Put bias": C["warning_mid"], "No edge": C["light"], "Straddle": C["indigo_mid"], "Call bias": C["accent_mid"]}[lab]
            chart.plot([i, i], [0.5, v], color=face, lw=2)
            chart.scatter([i], [v], s=42, color=face, edgecolors=C["ink"], linewidths=.6, zorder=3)
            chart.text(i, v + (0.004 if v >= 0.5 else -0.004), f"{v * 100:.1f}", ha="center", va="bottom" if v >= 0.5 else "top", size=8.5)
            chart.text(i, 0.43, f"{lab}\n{r['n']:,}", ha="center", va="top", size=8.5, color=C["ink"])
        chart.axhline(0.5, color=C["ink"], lw=0.8)
        chart.set_ylim(0.43, 0.56)
        chart.set_xlim(-0.6, 3.6)
        chart.set_xticks([])
        chart.set_yticks([0.45, 0.5, 0.55] if p == 0 else [], ["45th", "50th", "55th"] if p == 0 else [])
        chart.tick_params(length=0, pad=4)
        chart.grid(axis="y", color=C["light"], lw=0.7)
    d, m, s = o["call_minus_put_rank"], o["straddle_minus_no_edge_abs_rank"], o["score_vs_abs_move_spearman"]
    text(ax, 0.08, 0.15, f"Calls − puts: {d['observed'] * 100:+.1f} points, p = {d['p_two_sided']:.2f}".replace("-", "−"), color=C["muted"])
    text(ax, 0.56, 0.15, f"Straddle − no edge: {m['observed'] * 100:+.1f}, p = {m['p_two_sided']:.3f}", color=C["accent"])
    text(ax, 0.56, 0.105, f"Score vs move size: ρ = {s['observed']:.2f}, p = {s['p_two_sided']:.4f}", color=C["accent"])
    footer(ax, f"Source: evaluation/stories.json; {o['n']:,} companies, {o['by_bias']['Call Bias (Upside Tail)']['n']} with a call bias.")
    save(fig, "15-options-ledger")


# ------------------------------------------------------------- shortcomings


def shortcomings() -> None:
    sc = E["score_clustering"]["compounder"]
    fig, ax = canvas(
        4.8,
        "Eight ways a fluent model went wrong",
        "Measured in the project's own outputs, 2025–2026",
    )
    o = ST["options_ledger"]["by_bias"]
    total = sum(v["n"] for v in o.values())
    cards = [
        ("99.8%", "of May 2025 analyses\ndated themselves 2024\n(1,916 of 1,919)", C["amber"]),
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
        ax.add_patch(FancyBboxPatch((x, y), 0.012, 0.165, boxstyle="square,pad=0", facecolor=C["indigo"], edgecolor="none"))
        text(ax, x + 0.03, y + 0.0825, big, size=16, weight="bold", color=C["ink"])
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
        3.9,
        "A prospective test of 1,257 frozen verdicts",
        "49 extreme verdicts shown  /  primary test: all 371 BUY-type versus 252 SELL-type",
    )
    for g, (label, tickers, face) in enumerate([("STRONG BUY", buys, C["accent"]), ("STRONG SELL", sells, C["warning"])]):
        y0 = 0.78 - g * 0.33
        text(ax, 0.015, y0, f"{label}  ·  {len(tickers)}", weight="bold", color=face)
        for i, t in enumerate(tickers):
            col, row = i % 10, i // 10
            x, y = 0.015 + col * 0.098, y0 - 0.075 - row * 0.068
            rbox(ax, x, y - 0.024, 0.09, 0.05, C["paper"], face)
            text(ax, x + 0.045, y, t, ha="center", color=C["ink"], weight="bold", size=8.5)
    text(ax, 0.015, 0.105, f"Frozen 28 September 2026 · Research ledger, not recommendations · SHA-256 {s['ledger_sha256'][:16]}…", size=8.5, color=C["ink"])
    footer(ax, "Primary test fixed in advance: BUY-type minus SELL-type return rank over the following year.")
    save(fig, "17-sealed-bet")
