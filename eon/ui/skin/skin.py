#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Erebus Observatory Network -- visual skin for the Streamlit app.

Implements the global look from the Claude Design handoff (Geist / Geist Mono /
Fraunces type, oklch navy palette, sidebar brand, card-style metrics, pills,
restyled buttons / inputs / tables / tabs) as a CSS overlay on top of
Streamlit's native widgets, plus a custom in-app dark/light toggle.

Nothing here changes app behaviour; it only restyles what is already rendered.
"""

import streamlit as st

# Session-state key backing the custom dark/light toggle.
_THEME_KEY = "eon_theme"
_DARK_LABEL = "🌙 Dark"
_LIGHT_LABEL = "☀️ Light"

# ── Design palettes (transcribed from the Claude Design styles.css) ──────────
# Light theme variables.
_LIGHT_VARS = """
  --bg:        oklch(0.985 0.004 260);
  --bg-1:      #ffffff;
  --bg-2:      oklch(0.965 0.006 260);
  --bg-3:      oklch(0.945 0.008 260);
  --bg-input:  oklch(0.985 0.004 260);
  --bd:        oklch(0.905 0.010 260);
  --bd-strong: oklch(0.830 0.012 260);
  --fg:        oklch(0.19 0.035 260);
  --fg-mid:    oklch(0.42 0.025 260);
  --fg-dim:    oklch(0.58 0.018 260);
  --fg-faint:  oklch(0.72 0.012 260);
  --accent:    oklch(0.46 0.18 250);
  --accent-bg: oklch(0.94 0.04 250);
  --accent-fg: oklch(0.34 0.20 250);
  --success:    oklch(0.50 0.16 148);
  --success-bg: oklch(0.94 0.06 148);
  --danger:     oklch(0.54 0.22 27);
  --danger-bg:  oklch(0.95 0.05 27);
  --warning:    oklch(0.62 0.16 65);
  --warning-bg: oklch(0.96 0.05 75);
  --violet:     oklch(0.48 0.18 295);
  --violet-bg:  oklch(0.95 0.04 295);
  --shadow-1: 0 1px 0 rgba(15, 23, 42, 0.04), 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-2: 0 1px 0 rgba(15, 23, 42, 0.04), 0 4px 16px -4px rgba(15, 23, 42, 0.08);
  --logo-bg:   oklch(0.13 0.04 260);
  --logo-fg:   oklch(0.98 0.005 260);
  --ring:      0 0 0 3px oklch(0.46 0.18 250 / 0.18);
"""

# Dark theme variables.
_DARK_VARS = """
  --bg:        oklch(0.155 0.026 262);
  --bg-1:      oklch(0.195 0.028 262);
  --bg-2:      oklch(0.220 0.030 262);
  --bg-3:      oklch(0.250 0.030 262);
  --bg-input:  oklch(0.215 0.030 262);
  --bd:        oklch(0.305 0.028 262);
  --bd-strong: oklch(0.380 0.030 262);
  --fg:        oklch(0.965 0.005 260);
  --fg-mid:    oklch(0.78 0.012 260);
  --fg-dim:    oklch(0.62 0.018 260);
  --fg-faint:  oklch(0.48 0.020 260);
  --accent:    oklch(0.78 0.14 240);
  --accent-bg: oklch(0.32 0.12 245);
  --accent-fg: oklch(0.86 0.12 240);
  --success:    oklch(0.78 0.16 148);
  --success-bg: oklch(0.30 0.10 148);
  --danger:     oklch(0.72 0.18 27);
  --danger-bg:  oklch(0.30 0.12 27);
  --warning:    oklch(0.82 0.14 75);
  --warning-bg: oklch(0.32 0.10 75);
  --violet:     oklch(0.78 0.14 295);
  --violet-bg:  oklch(0.30 0.12 295);
  --shadow-1: 0 1px 0 rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3);
  --shadow-2: 0 1px 0 rgba(0,0,0,0.4), 0 8px 24px -8px rgba(0,0,0,0.6);
  --logo-bg:   oklch(0.10 0.04 260);
  --logo-fg:   oklch(0.98 0.005 260);
  --ring:      0 0 0 3px oklch(0.78 0.14 240 / 0.30);
"""

# Brand mark redrawn in SVG (theme-aware via currentColor / vars).
_BRAND_SVG = """
<svg viewBox="0 0 40 40" width="26" height="26" fill="none">
  <path d="M12 8 L20 4 L28 8 L28 32 L20 36 L12 32 Z" stroke="var(--logo-fg)" stroke-width="1.4" stroke-linejoin="round" opacity="0.55"/>
  <path d="M16 13 L20 11 L24 13 L24 27 L20 29 L16 27 Z" stroke="var(--logo-fg)" stroke-width="1" stroke-linejoin="round" opacity="0.35"/>
  <circle cx="20" cy="14" r="2.3" fill="oklch(0.96 0.10 240)"/>
  <circle cx="20" cy="14" r="4" fill="oklch(0.78 0.16 240)" opacity="0.4"/>
  <path d="M19 18 L19 26 M21 18 L21 26 M17 22 L23 22" stroke="var(--logo-fg)" stroke-width="1.2" stroke-linecap="round" opacity="0.7"/>
</svg>
"""

# ── Static design system CSS, mapped onto Streamlit's DOM ────────────────────
# (No f-string: braces are literal CSS.)
_STATIC_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500;600&family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&display=swap');

/* ── Base canvas & typography ───────────────────────────────────────────── */
html, body, .stApp, [class*="st-"] {
  font-family: 'Geist', ui-sans-serif, system-ui, -apple-system, sans-serif;
  letter-spacing: -0.005em;
}
.stApp {
  background: var(--bg) !important;
  color: var(--fg) !important;
}
.stApp, .main, [data-testid="stMain"] { background: var(--bg) !important; }
[data-testid="stMainBlockContainer"], .block-container {
  padding-top: 3rem;
  max-width: 1180px;
}
[data-testid="stHeader"] {
  background: transparent !important;
  backdrop-filter: blur(8px);
}

/* Subtle accent glow in the top-right corner, like the design. */
.stApp::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(ellipse 800px 600px at 100% 0%, var(--accent-bg), transparent 70%);
  opacity: 0.30;
  z-index: 0;
}

/* Headings: Fraunces display serif. */
.stApp h1, .stApp h2, .stApp h3 {
  font-family: 'Fraunces', 'Geist', serif !important;
  letter-spacing: -0.02em;
  color: var(--fg) !important;
}
.stApp h1 { font-weight: 600; font-size: 2.3rem; line-height: 1.05; }
.stApp h2 { font-weight: 600; font-size: 1.35rem; }
.stApp h3 { font-weight: 600; font-size: 1.1rem; }
.stApp p, .stApp li, .stApp label, [data-testid="stMarkdownContainer"] { color: var(--fg); }
.stApp a { color: var(--accent); }
.stApp code, .stApp pre, .stCode, [data-testid="stCode"] {
  font-family: 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace !important;
}
.stCaption, [data-testid="stCaptionContainer"], small { color: var(--fg-dim) !important; }
hr, [data-testid="stMarkdownContainer"] hr { border-color: var(--bd) !important; }

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--bg-1) !important;
  border-right: 1px solid var(--bd);
}
[data-testid="stSidebar"] * { color: var(--fg) !important; }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span { color: var(--fg-mid) !important; }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover { background: var(--bg-2); border-radius: 8px; }

/* Brand block injected at the top of the sidebar. */
.eon-brand {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 4px 16px; margin-bottom: 8px;
  border-bottom: 1px solid var(--bd);
}
.eon-brand .mark {
  width: 40px; height: 40px; border-radius: 10px;
  background: var(--logo-bg);
  display: grid; place-items: center; position: relative; overflow: hidden; flex-shrink: 0;
}
.eon-brand .mark::before {
  content: ""; position: absolute; inset: 0;
  background:
    radial-gradient(circle at 70% 28%, oklch(0.78 0.14 240 / 0.7), transparent 38%),
    radial-gradient(circle at 70% 28%, oklch(0.92 0.10 240 / 1), transparent 8%);
}
.eon-brand .mark svg { position: relative; z-index: 1; }
.eon-brand .txt { display: flex; flex-direction: column; line-height: 1; }
.eon-brand .name {
  font-family: 'Fraunces', serif; font-weight: 700; font-size: 17px;
  letter-spacing: -0.01em; color: var(--fg) !important;
}
.eon-brand .sub {
  font-family: 'Geist Mono', monospace; font-size: 9px; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--fg-faint) !important; margin-top: 5px;
}

/* ── Buttons ────────────────────────────────────────────────────────────── */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
  border: 1px solid var(--bd-strong) !important;
  background: var(--bg-1) !important;
  color: var(--fg) !important;
  font-weight: 500 !important;
  border-radius: 8px !important;
  box-shadow: var(--shadow-1);
  transition: background 0.12s, transform 0.12s;
}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
  background: var(--bg-2) !important;
  transform: translateY(-1px);
  color: var(--fg) !important;
}
/* Primary / accent buttons. */
.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
}
.stButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
  filter: brightness(1.08);
}

/* ── Inputs / selects / textareas ───────────────────────────────────────── */
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input,
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
  background: var(--bg-input) !important;
  border: 1px solid var(--bd) !important;
  border-radius: 8px !important;
  color: var(--fg) !important;
}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: var(--ring) !important;
}
.stTextInput input, .stNumberInput input { font-family: 'Geist Mono', monospace !important; }
[data-baseweb="popover"] [role="listbox"] { background: var(--bg-1) !important; border: 1px solid var(--bd) !important; }

/* ── Metrics → KPI cards ────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  padding: 16px 18px;
  border: 1px solid var(--bd);
  border-radius: 12px;
  background: var(--bg-1);
  box-shadow: var(--shadow-1);
}
[data-testid="stMetricLabel"] {
  font-size: 11px !important; font-weight: 600 !important;
  letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-faint) !important;
}
[data-testid="stMetricValue"] {
  font-family: 'Geist Mono', monospace !important;
  font-weight: 600 !important; color: var(--fg) !important;
  letter-spacing: -0.02em; font-variant-numeric: tabular-nums;
}
[data-testid="stMetricDelta"] { font-family: 'Geist Mono', monospace !important; }

/* ── Tabs ───────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid var(--bd); gap: 4px; }
.stTabs [data-baseweb="tab"] { color: var(--fg-dim) !important; font-weight: 500; }
.stTabs [data-baseweb="tab"]:hover { color: var(--fg) !important; }
.stTabs [aria-selected="true"] { color: var(--fg) !important; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--accent) !important; }

/* ── Containers: expanders, dataframes, tables, alerts ──────────────────── */
[data-testid="stExpander"] details {
  border: 1px solid var(--bd) !important;
  border-radius: 12px !important;
  background: var(--bg-1) !important;
  box-shadow: var(--shadow-1);
}
[data-testid="stExpander"] summary { color: var(--fg) !important; }
[data-testid="stDataFrame"], [data-testid="stTable"] {
  border: 1px solid var(--bd);
  border-radius: 12px;
  overflow: hidden;
  background: var(--bg-1);
}
[data-testid="stTable"] th {
  font-size: 10.5px !important; font-weight: 600 !important;
  letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--fg-faint) !important; background: var(--bg-2) !important;
  border-bottom: 1px solid var(--bd) !important;
}
[data-testid="stTable"] td { border-bottom: 1px solid var(--bd) !important; color: var(--fg) !important; }
[data-testid="stAlert"], [data-testid="stNotification"] {
  border: 1px solid var(--bd) !important;
  border-radius: 12px !important;
  background: var(--bg-2) !important;
  color: var(--fg) !important;
}
[data-testid="stForm"] {
  border: 1px solid var(--bd) !important;
  border-radius: 12px !important;
  background: var(--bg-1) !important;
}

/* ── Custom dark/light toggle (styled st.radio) ─────────────────────────── */
.eon-theme-toggle [role="radiogroup"] {
  display: inline-flex; background: var(--bg-2); border: 1px solid var(--bd);
  padding: 3px; border-radius: 9px; gap: 2px; flex-direction: row;
}
.eon-theme-toggle [role="radiogroup"] label {
  margin: 0 !important; padding: 5px 12px !important; border-radius: 6px;
  cursor: pointer; font-size: 12.5px !important; color: var(--fg-mid) !important;
}
.eon-theme-toggle [role="radiogroup"] label:has(input:checked) {
  background: var(--bg-1); color: var(--fg) !important;
  box-shadow: var(--shadow-1); border: 1px solid var(--bd);
}
.eon-theme-toggle [role="radiogroup"] label > div:first-child { display: none; }  /* hide radio dot */

/* ── Scrollbars ─────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bd); border-radius: 6px; border: 2px solid var(--bg); background-clip: content-box; }
::-webkit-scrollbar-thumb:hover { background: var(--bd-strong); border: 2px solid var(--bg); background-clip: content-box; }
"""


def _current_theme() -> str:
    """Return the active theme label, defaulting to dark on first load."""
    return st.session_state.get(_THEME_KEY, _DARK_LABEL)


def _render_sidebar_chrome() -> None:
    """Render the brand mark and dark/light toggle in the sidebar."""
    with st.sidebar:
        st.markdown(
            f"""
            <div class="eon-brand">
              <div class="mark">{_BRAND_SVG}</div>
              <div class="txt">
                <span class="name">Erebus</span>
                <span class="sub">Observatory Network</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="eon-theme-toggle">', unsafe_allow_html=True)
        st.radio(
            "Theme",
            options=[_DARK_LABEL, _LIGHT_LABEL],
            horizontal=True,
            label_visibility="collapsed",
            key=_THEME_KEY,
        )
        st.markdown("</div>", unsafe_allow_html=True)


def apply_skin() -> None:
    """
    Apply the Erebus design system to the current page.

    Injects theme variables (driven by the in-app dark/light toggle) plus the
    static design CSS, then renders the sidebar brand + toggle. Safe to call at
    the top of any page; it is idempotent per rerun and purely cosmetic.
    """
    theme_vars = _DARK_VARS if _current_theme() == _DARK_LABEL else _LIGHT_VARS

    # Theme variables applied to both :root and .stApp so descendants resolve
    # them from the themed scope regardless of Streamlit's own light/dark mode.
    st.markdown(
        f"<style>:root, .stApp {{{theme_vars}}}</style>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<style>{_STATIC_CSS}</style>", unsafe_allow_html=True)

    _render_sidebar_chrome()
