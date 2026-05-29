#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stylesheet for the Erebus skin.

Holds the design-system CSS verbatim from the Claude Design handoff (so the
HTML components rendered by ``components.py`` are pixel-faithful) plus a layer
of overrides that map the same look onto Streamlit's native widgets.
"""

# ── Design palettes (transcribed from the Claude Design styles.css) ──────────
LIGHT_VARS = """
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
  --scan: oklch(0.94 0.008 260);
"""

DARK_VARS = """
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
  --scan: oklch(0.225 0.030 262);
"""


def theme_vars(dark: bool) -> str:
    """Return the CSS custom-property block for the requested theme."""
    return DARK_VARS if dark else LIGHT_VARS


# ── Design component CSS (verbatim from the handoff) ─────────────────────────
# These classes are used by the raw-HTML components and therefore render exactly
# as designed. They do not collide with Streamlit's own class names.
_DESIGN_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500;600&family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&display=swap');

.mono { font-family: 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace; letter-spacing: 0; }
.display { font-family: 'Fraunces', 'Geist', serif; font-variation-settings: 'opsz' 144; }

/* Buttons (for HTML chrome) */
.eon .btn {
  appearance: none; border: 1px solid var(--bd-strong); background: var(--bg-1);
  color: var(--fg); font-size: 13px; font-weight: 500; padding: 7px 14px;
  border-radius: 8px; cursor: pointer; display: inline-flex; align-items: center;
  gap: 8px; line-height: 1; box-shadow: var(--shadow-1);
}
.eon .btn.accent { background: var(--accent); color: #fff; border-color: var(--accent); }
.eon .btn.ghost { background: transparent; border-color: transparent; box-shadow: none; color: var(--fg-mid); }
.eon .btn.sm { padding: 5px 10px; font-size: 12px; }

/* Segmented control */
.eon .seg { display: inline-flex; background: var(--bg-2); border: 1px solid var(--bd); padding: 3px; border-radius: 9px; gap: 2px; }
.eon .seg-opt { padding: 6px 14px; font-size: 12.5px; font-weight: 500; color: var(--fg-mid); border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 7px; line-height: 1.2; }
.eon .seg-opt.on { background: var(--bg-1); color: var(--fg); box-shadow: var(--shadow-1); border: 1px solid var(--bd); padding: 5px 13px; }

/* Card */
.eon .card { background: var(--bg-1); border: 1px solid var(--bd); border-radius: 12px; box-shadow: var(--shadow-1); }
.eon .card-head { padding: 14px 18px; border-bottom: 1px solid var(--bd); display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.eon .card-title { font-size: 13.5px; font-weight: 600; color: var(--fg); }
.eon .card-sub { font-size: 12px; color: var(--fg-dim); margin-top: 2px; }
.eon .card-body { padding: 18px; }

/* Pills / badges */
.eon .pill { display: inline-flex; align-items: center; gap: 6px; padding: 2px 9px; font-size: 11px; font-weight: 500; border-radius: 100px; background: var(--bg-3); color: var(--fg-mid); font-family: 'Geist Mono', monospace; letter-spacing: 0.02em; line-height: 1.5; }
.eon .pill .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.eon .pill.success { background: var(--success-bg); color: var(--success); }
.eon .pill.danger  { background: var(--danger-bg);  color: var(--danger); }
.eon .pill.warning { background: var(--warning-bg); color: var(--warning); }
.eon .pill.accent  { background: var(--accent-bg);  color: var(--accent-fg); }
.eon .pill.violet  { background: var(--violet-bg);  color: var(--violet); }

/* Page header */
.eon .page-h { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 28px; gap: 24px; }
.eon .page-h h1 { font-family: 'Fraunces', serif; font-weight: 600; font-size: 36px; letter-spacing: -0.025em; line-height: 1.05; margin: 0 0 6px; color: var(--fg); }
.eon .page-h .desc { font-size: 14px; color: var(--fg-dim); max-width: 600px; }
.eon .eyebrow { font-family: 'Geist Mono', monospace; font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--accent); margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.eon .eyebrow::before { content: ""; width: 24px; height: 1px; background: var(--accent); display: inline-block; }

/* Section divider */
.eon .section-h { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 14px; padding-top: 8px; }
.eon .section-h h2 { margin: 0; font-size: 16px; font-weight: 600; color: var(--fg); letter-spacing: -0.01em; }
.eon .section-h .num { font-family: 'Geist Mono', monospace; color: var(--fg-faint); font-size: 11px; letter-spacing: 0.1em; }

/* Tables */
.eon table.tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.eon table.tbl th { text-align: left; font-size: 10.5px; font-weight: 600; color: var(--fg-faint); letter-spacing: 0.10em; text-transform: uppercase; padding: 10px 14px; border-bottom: 1px solid var(--bd); background: var(--bg-2); }
.eon table.tbl td { padding: 12px 14px; border-bottom: 1px solid var(--bd); color: var(--fg); vertical-align: middle; }
.eon table.tbl tr:last-child td { border-bottom: none; }
.eon table.tbl tbody tr:hover { background: var(--bg-2); }
.eon .tick { font-family: 'Geist Mono', monospace; font-weight: 600; letter-spacing: 0.02em; font-size: 13px; }
.eon .tnum { font-family: 'Geist Mono', monospace; font-variant-numeric: tabular-nums; }

/* KPI */
.eon .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 8px; }
.eon .kpi { padding: 16px 18px; border: 1px solid var(--bd); border-radius: 12px; background: var(--bg-1); box-shadow: var(--shadow-1); }
.eon .kpi .lbl { font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-faint); margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; }
.eon .kpi .val { font-family: 'Geist Mono', monospace; font-size: 24px; font-weight: 600; color: var(--fg); font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
.eon .kpi .delta { font-family: 'Geist Mono', monospace; font-size: 11.5px; color: var(--fg-dim); margin-top: 4px; }
.eon .kpi .delta.up { color: var(--success); }
.eon .kpi .delta.down { color: var(--danger); }

/* Verdict */
.eon .verdict { background: var(--accent-bg); border: 1px solid var(--accent); border-radius: 12px; padding: 18px; }
.eon .verdict .grade { font-family: 'Fraunces', serif; font-size: 40px; font-weight: 700; line-height: 1; color: var(--accent-fg); }

/* Segment bars */
.eon .segbar-track { height: 28px; background: var(--bg-2); border-radius: 6px; overflow: hidden; }
.eon .segbar-fill { height: 100%; border-radius: 6px; }

/* Misc utilities */
.eon .row { display: flex; gap: 12px; }
.eon .col { display: flex; flex-direction: column; gap: 12px; }
.eon .muted { color: var(--fg-dim); }
.eon .dim   { color: var(--fg-faint); }
.eon .grow { flex: 1; min-width: 0; }
.eon .center { display: flex; align-items: center; gap: 8px; }
.eon .divider { height: 1px; background: var(--bd); margin: 20px 0; }
.eon { color: var(--fg); }
.eon pre { background: var(--scan); border-radius: 10px; padding: 16px; font-family: 'Geist Mono', monospace; font-size: 12px; line-height: 1.6; overflow: auto; color: var(--fg); margin: 0; }
"""

# ── Streamlit native-widget overrides ────────────────────────────────────────
_STREAMLIT_CSS = """
html, body, .stApp, [class*="st-"] {
  font-family: 'Geist', ui-sans-serif, system-ui, -apple-system, sans-serif;
  letter-spacing: -0.005em;
}
.stApp, [data-testid="stMain"], [data-testid="stAppViewContainer"] { background: var(--bg) !important; color: var(--fg) !important; }
[data-testid="stMainBlockContainer"], .block-container { padding-top: 2.6rem; max-width: 1180px; }
[data-testid="stHeader"] { background: transparent !important; backdrop-filter: blur(8px); }

/* Accent glow */
.stApp::before {
  content: ""; position: fixed; inset: 0; pointer-events: none;
  background: radial-gradient(ellipse 800px 600px at 100% 0%, var(--accent-bg), transparent 70%);
  opacity: 0.30; z-index: 0;
}

/* Headings */
.stApp h1, .stApp h2, .stApp h3 { font-family: 'Fraunces', 'Geist', serif !important; letter-spacing: -0.02em; color: var(--fg) !important; }
.stApp h1 { font-weight: 600; }
.stApp p, .stApp li, .stApp label, [data-testid="stMarkdownContainer"] { color: var(--fg); }
.stApp a { color: var(--accent); }
.stApp code, .stApp pre { font-family: 'Geist Mono', ui-monospace, monospace !important; }
[data-testid="stCaptionContainer"], small { color: var(--fg-dim) !important; }
hr, [data-testid="stMarkdownContainer"] hr { border-color: var(--bd) !important; }

/* ── Sidebar: hide default nav, build custom chrome ──────────────────────── */
[data-testid="stSidebar"] { background: var(--bg-1) !important; border-right: 1px solid var(--bd); }
[data-testid="stSidebar"] * { color: var(--fg); }
[data-testid="stSidebarNav"] { display: none; }            /* default page nav */
[data-testid="stSidebarHeader"] { padding-bottom: 0; }
[data-testid="stSidebar"] [data-testid="stMainBlockContainer"] { padding-top: 1rem; }

/* Custom nav via st.page_link */
[data-testid="stSidebar"] [data-testid="stPageLink"] a,
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
  display: flex; align-items: center; gap: 12px; padding: 8px 10px; border-radius: 8px;
  color: var(--fg-mid) !important; font-size: 13.5px; font-weight: 500;
  border: 1px solid transparent; margin: 1px 0; text-decoration: none;
}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover { background: var(--bg-2); color: var(--fg) !important; }
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current],
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"].active {
  background: var(--bg-2); color: var(--fg) !important; border-color: var(--bd); box-shadow: var(--shadow-1);
}

/* Brand block */
.eon-brand { display: flex; align-items: center; gap: 12px; padding: 6px 4px 16px; margin-bottom: 8px; border-bottom: 1px solid var(--bd); }
.eon-brand .mark { width: 40px; height: 40px; border-radius: 10px; background: var(--logo-bg); display: grid; place-items: center; position: relative; overflow: hidden; flex-shrink: 0; }
.eon-brand .mark::before { content: ""; position: absolute; inset: 0; background: radial-gradient(circle at 70% 28%, oklch(0.78 0.14 240 / 0.7), transparent 38%), radial-gradient(circle at 70% 28%, oklch(0.92 0.10 240 / 1), transparent 8%); }
.eon-brand .mark svg { position: relative; z-index: 1; }
.eon-brand .txt { display: flex; flex-direction: column; line-height: 1; }
.eon-brand .name { font-family: 'Fraunces', serif; font-weight: 700; font-size: 17px; letter-spacing: -0.01em; color: var(--fg) !important; }
.eon-brand .sub { font-family: 'Geist Mono', monospace; font-size: 9px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--fg-faint) !important; margin-top: 5px; }
.eon-navsection { padding: 14px 10px 6px; font-size: 10.5px; font-weight: 600; letter-spacing: 0.10em; text-transform: uppercase; color: var(--fg-faint) !important; }

/* Topbar */
.eon-topbar { display: flex; align-items: center; justify-content: space-between; padding: 2px 2px 14px; margin-bottom: 18px; border-bottom: 1px solid var(--bd); }
.eon-crumbs { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--fg-dim); font-family: 'Geist Mono', monospace; }
.eon-crumbs .sep { opacity: 0.4; }
.eon-crumbs .cur { color: var(--fg); }
.eon-status { font-family: 'Geist Mono', monospace; font-size: 11px; color: var(--fg-dim); }

/* Buttons */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
  border: 1px solid var(--bd-strong) !important; background: var(--bg-1) !important; color: var(--fg) !important;
  font-weight: 500 !important; border-radius: 8px !important; box-shadow: var(--shadow-1); transition: background 0.12s, transform 0.12s;
}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] button:hover { background: var(--bg-2) !important; transform: translateY(-1px); color: var(--fg) !important; }
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"], [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] { background: var(--accent) !important; border-color: var(--accent) !important; color: #fff !important; }
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover { filter: brightness(1.08); }

/* Inputs / selects / textareas */
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input,
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
  background: var(--bg-input) !important; border: 1px solid var(--bd) !important; border-radius: 8px !important; color: var(--fg) !important;
}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus { border-color: var(--accent) !important; box-shadow: var(--ring) !important; }
.stTextInput input, .stNumberInput input { font-family: 'Geist Mono', monospace !important; }
[data-baseweb="popover"] [role="listbox"] { background: var(--bg-1) !important; border: 1px solid var(--bd) !important; }

/* Metrics → KPI cards */
[data-testid="stMetric"] { padding: 16px 18px; border: 1px solid var(--bd); border-radius: 12px; background: var(--bg-1); box-shadow: var(--shadow-1); }
[data-testid="stMetricLabel"] { font-size: 11px !important; font-weight: 600 !important; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-faint) !important; }
[data-testid="stMetricValue"] { font-family: 'Geist Mono', monospace !important; font-weight: 600 !important; color: var(--fg) !important; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
[data-testid="stMetricDelta"] { font-family: 'Geist Mono', monospace !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid var(--bd); gap: 4px; }
.stTabs [data-baseweb="tab"] { color: var(--fg-dim) !important; font-weight: 500; }
.stTabs [data-baseweb="tab"]:hover { color: var(--fg) !important; }
.stTabs [aria-selected="true"] { color: var(--fg) !important; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--accent) !important; }

/* Containers */
[data-testid="stExpander"] details { border: 1px solid var(--bd) !important; border-radius: 12px !important; background: var(--bg-1) !important; box-shadow: var(--shadow-1); }
[data-testid="stExpander"] summary { color: var(--fg) !important; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid var(--bd); border-radius: 12px; overflow: hidden; background: var(--bg-1); }
[data-testid="stAlert"], [data-testid="stNotification"] { border: 1px solid var(--bd) !important; border-radius: 12px !important; background: var(--bg-2) !important; color: var(--fg) !important; }
[data-testid="stForm"] { border: 1px solid var(--bd) !important; border-radius: 12px !important; background: var(--bg-1) !important; }

/* Theme toggle (styled st.radio) */
.eon-theme-toggle [role="radiogroup"] { display: inline-flex; background: var(--bg-2); border: 1px solid var(--bd); padding: 3px; border-radius: 9px; gap: 2px; flex-direction: row; }
.eon-theme-toggle [role="radiogroup"] label { margin: 0 !important; padding: 5px 12px !important; border-radius: 6px; cursor: pointer; font-size: 12.5px !important; color: var(--fg-mid) !important; }
.eon-theme-toggle [role="radiogroup"] label:has(input:checked) { background: var(--bg-1); color: var(--fg) !important; box-shadow: var(--shadow-1); border: 1px solid var(--bd); }
.eon-theme-toggle [role="radiogroup"] label > div:first-child { display: none; }

/* Scrollbars */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bd); border-radius: 6px; border: 2px solid var(--bg); background-clip: content-box; }
::-webkit-scrollbar-thumb:hover { background: var(--bd-strong); border: 2px solid var(--bg); background-clip: content-box; }
"""

STATIC_CSS = _DESIGN_CSS + _STREAMLIT_CSS
