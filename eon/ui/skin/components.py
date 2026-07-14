#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Erebus design components for Streamlit.

Each helper renders (or returns) the design system's own HTML/CSS so the output
is pixel-faithful to the Claude Design handoff. Block-level helpers render via
``st.markdown``; inline helpers (``pill``, ``status_pill``) return HTML strings
meant to be embedded inside table cells or other components.

All helpers are presentation-only: callers pass already-computed real data.
"""

from html import escape
from typing import Iterable, List, Optional, Sequence, Tuple, Union

import streamlit as st

# ── status → pill tone/label map (mirrors the design's StatusPill) ───────────
_STATUS_MAP = {
    "completed": ("success", "Completed"),
    "complete": ("success", "Completed"),
    "running": ("accent", "Running"),
    "in_progress": ("accent", "Running"),
    "failed": ("danger", "Failed"),
    "error": ("danger", "Failed"),
    "queued": ("warning", "Queued"),
    "pending": ("warning", "Queued"),
    "scheduled": ("warning", "Scheduled"),
    "paused": ("default", "Paused"),
    "interrupted": ("warning", "Interrupted"),
    "cancelled": ("default", "Cancelled"),
    "canceled": ("default", "Cancelled"),
    "cached": ("violet", "Cached"),
}


def _md(html: str) -> None:
    """Render an HTML fragment inside the scoped ``.eon`` design context."""
    st.markdown(f'<div class="eon">{html}</div>', unsafe_allow_html=True)


# ── Inline helpers (return strings) ──────────────────────────────────────────
def pill(text: str, tone: str = "default", dot: bool = False) -> str:
    """Return a pill/badge HTML string."""
    cls = "pill" if tone == "default" else f"pill {tone}"
    dot_html = '<span class="dot"></span>' if dot else ""
    return f'<span class="{cls}">{dot_html}{escape(str(text))}</span>'


def status_pill(status: str) -> str:
    """Return a status pill HTML string for a run/result status."""
    tone, label = _STATUS_MAP.get(str(status).lower(), ("warning", str(status).title()))
    return pill(label, tone=tone, dot=True)


def tick(text: str) -> str:
    """Return a monospace ticker token."""
    return f'<span class="tick">{escape(str(text))}</span>'


# ── Block helpers (render) ───────────────────────────────────────────────────
def page_header(
    title: str,
    eyebrow: Optional[str] = None,
    desc: Optional[str] = None,
    actions_html: str = "",
) -> None:
    """Render the design page header (eyebrow + serif title + description)."""
    eb = f'<div class="eyebrow">{escape(eyebrow)}</div>' if eyebrow else ""
    ds = f'<div class="desc">{escape(desc)}</div>' if desc else ""
    actions = f'<div class="row" style="gap:8px">{actions_html}</div>' if actions_html else ""
    _md(
        f'<div class="page-h"><div>{eb}<h1>{escape(title)}</h1>{ds}</div>{actions}</div>'
    )


def section_h(title: str, num: Optional[str] = None, right_html: str = "") -> None:
    """Render a section divider header with optional number and right content."""
    num_html = f'<span class="num">{escape(num)}</span>' if num else ""
    _md(
        f'<div class="section-h"><div class="center" style="gap:12px">{num_html}'
        f'<h2>{escape(title)}</h2></div><div class="center" style="gap:8px">{right_html}</div></div>'
    )


def kpi_grid(items: Sequence[dict], columns: int = 4) -> None:
    """
    Render a KPI card grid.

    Each item: {label, value, suffix?, delta?, delta_dir? ('up'|'down'), unit?}.
    """
    cells = []
    for it in items:
        unit = it.get("unit")
        unit_html = f'<span class="dim mono" style="font-size:10px">{escape(str(unit))}</span>' if unit else ""
        suffix = it.get("suffix")
        suffix_html = (
            f'<span style="font-size:14px;color:var(--fg-dim);margin-left:4px">{escape(str(suffix))}</span>'
            if suffix
            else ""
        )
        delta = it.get("delta")
        delta_html = (
            f'<div class="delta {it.get("delta_dir", "")}">{escape(str(delta))}</div>' if delta else ""
        )
        cells.append(
            f'<div class="kpi"><div class="lbl"><span>{escape(str(it.get("label", "")))}</span>{unit_html}</div>'
            f'<div class="val">{escape(str(it.get("value", "")))}{suffix_html}</div>{delta_html}</div>'
        )
    _md(
        f'<div class="kpi-grid" style="grid-template-columns:repeat({columns},1fr)">'
        + "".join(cells)
        + "</div>"
    )


def html_table(
    columns: Sequence[Union[str, Tuple[str, Optional[int]]]],
    rows: Iterable[Sequence[str]],
    empty: str = "No rows.",
) -> None:
    """
    Render a dense design table.

    ``columns`` entries are either a header string or a ``(header, width_px)``
    tuple. ``rows`` is an iterable of cell sequences; cells are raw HTML (use
    ``escape`` / ``pill`` / ``tick`` to build them).
    """
    head_cells = []
    for col in columns:
        if isinstance(col, (tuple, list)):
            label, width = col[0], col[1] if len(col) > 1 else None
        else:
            label, width = col, None
        style = f' style="width:{width}px"' if width else ""
        head_cells.append(f"<th{style}>{escape(str(label))}</th>")

    body_rows = []
    for r in rows:
        body_rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")

    if not body_rows:
        body_rows.append(
            f'<tr><td colspan="{len(list(columns))}" class="dim" '
            f'style="text-align:center;padding:28px">{escape(empty)}</td></tr>'
        )

    _md(
        '<div class="card" style="overflow:hidden;padding:0"><table class="tbl"><thead><tr>'
        + "".join(head_cells)
        + "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
    )


def card_open(title: Optional[str] = None, sub: Optional[str] = None, right_html: str = "") -> None:
    """Open a design card; pair with ``card_close``. Body content goes between."""
    head = ""
    if title or right_html:
        sub_html = f'<div class="card-sub">{escape(sub)}</div>' if sub else ""
        title_html = (
            f'<div><div class="card-title">{escape(title)}</div>{sub_html}</div>' if title else "<div></div>"
        )
        head = f'<div class="card-head">{title_html}<div class="row" style="gap:8px">{right_html}</div></div>'
    st.markdown(f'<div class="eon"><div class="card">{head}<div class="card-body">', unsafe_allow_html=True)


def card_close() -> None:
    """Close a card opened with ``card_open``."""
    st.markdown("</div></div></div>", unsafe_allow_html=True)


def verdict_card(grade: str, score, text: str, label: str = "Erebus Verdict") -> None:
    """Render the accent verdict card."""
    _md(
        f'<div class="verdict"><div class="eyebrow" style="margin-bottom:8px">{escape(label)}</div>'
        f'<div class="row" style="gap:12px;align-items:baseline">'
        f'<span class="grade">{escape(str(grade))}</span>'
        f'<span class="mono" style="font-size:12px;color:var(--accent-fg)">{escape(str(score))}</span></div>'
        f'<div style="font-size:13px;line-height:1.55;margin-top:12px;color:var(--accent-fg)">{escape(text)}</div></div>'
    )


def segment_bars(items: Sequence[dict]) -> None:
    """
    Render horizontal segment/composition bars.

    Each item: {name, pct (0-100), amount?, yoy?, color?}.
    """
    palette = [
        "oklch(0.62 0.18 245)",
        "oklch(0.62 0.18 145)",
        "oklch(0.62 0.18 75)",
        "oklch(0.62 0.18 295)",
        "oklch(0.55 0.02 260)",
    ]
    rows = []
    for i, s in enumerate(items):
        color = s.get("color", palette[i % len(palette)])
        pct = float(s.get("pct", 0))
        amt = s.get("amount", "")
        yoy = s.get("yoy", "")
        yoy_color = "var(--success)" if str(yoy).startswith("+") else "var(--danger)"
        yoy_html = (
            f'<div class="tnum" style="width:70px;text-align:right;font-size:12.5px;color:{yoy_color}">{escape(str(yoy))}</div>'
            if yoy
            else ""
        )
        amt_html = (
            f'<div class="tnum" style="width:90px;text-align:right;font-size:13.5px">{escape(str(amt))}</div>'
            if amt
            else ""
        )
        rows.append(
            f'<div class="row" style="align-items:center;gap:14px">'
            f'<div style="width:200px;font-weight:500;font-size:13.5px">{escape(str(s.get("name", "")))}</div>'
            f'<div class="grow"><div class="segbar-track"><div class="segbar-fill" style="width:{pct}%;background:{color}"></div></div></div>'
            f'{amt_html}<div class="tnum dim" style="width:54px;text-align:right;font-size:12px">{pct:.1f}%</div>{yoy_html}</div>'
        )
    _md('<div class="col" style="gap:14px">' + "".join(rows) + "</div>")


def bar_chart(values: Sequence[float], labels: Sequence[str] = (), height: int = 160) -> None:
    """Render a simple accent bar chart (e.g. runs per day)."""
    mx = max(values) if values else 1
    bars = "".join(
        f'<div class="col" style="flex:1;gap:2px;justify-content:flex-end;height:100%">'
        f'<div style="background:var(--accent);height:{(v / mx * height) if mx else 0:.0f}px;border-radius:2px"></div></div>'
        for v in values
    )
    lbls = ""
    if labels:
        lbls = (
            '<div class="row" style="justify-content:space-between;margin-top:8px">'
            + "".join(f'<span class="dim mono" style="font-size:10.5px">{escape(str(l))}</span>' for l in labels)
            + "</div>"
        )
    _md(
        f'<div class="row" style="align-items:flex-end;gap:4px;height:{height}px">{bars}</div>{lbls}'
    )


def progress_strip(done: int, total: int, current: int = None) -> None:
    """Render a per-item batch progress strip (cells coloured by state)."""
    cells = []
    for i in range(total):
        if i < done:
            c = "var(--success)"
        elif current is not None and i == current:
            c = "var(--accent)"
        else:
            c = "var(--bg-3)"
        glow = "box-shadow:0 0 0 2px var(--accent),0 0 12px var(--accent)" if (current is not None and i == current) else ""
        cells.append(
            f'<div style="flex:1;height:22px;background:{c};border-radius:4px;{glow}"></div>'
        )
    _md('<div class="row" style="gap:3px">' + "".join(cells) + "</div>")


def divider() -> None:
    """Render a hairline divider."""
    _md('<div class="divider"></div>')
