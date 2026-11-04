"""Shared Streamlit look-and-feel for TokenWise — dark blue theme."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
  --tw-bg: #070b16;
  --tw-bg-2: #0c1528;
  --tw-panel: #121c33;
  --tw-panel-2: #182440;
  --tw-ink: #e8eefc;
  --tw-muted: #9aabc8;
  --tw-accent: #3b82f6;
  --tw-accent-2: #60a5fa;
  --tw-line: rgba(148, 163, 184, 0.22);
}

html, body, [class*="css"] {
  font-family: 'DM Sans', sans-serif;
  color: var(--tw-ink) !important;
}

.stApp {
  background:
    radial-gradient(1000px 520px at 12% -8%, rgba(37, 99, 235, 0.28) 0%, transparent 55%),
    radial-gradient(800px 480px at 100% 0%, rgba(14, 165, 233, 0.16) 0%, transparent 50%),
    linear-gradient(180deg, #070b16 0%, #0b1224 45%, #0a162e 100%) !important;
  color: var(--tw-ink);
}

/* Main text readable on dark blue */
.stApp, .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
.stText, .stCaption, label, [data-testid="stWidgetLabel"] p,
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {
  color: var(--tw-ink) !important;
}

.stCaption, [data-testid="stCaptionContainer"] {
  color: var(--tw-muted) !important;
}

h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
  font-family: 'Space Grotesk', sans-serif !important;
  letter-spacing: -0.02em;
  color: #f1f5ff !important;
}

a { color: #93c5fd !important; }

/* Sidebar */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #050a14 0%, #0d1b36 55%, #102447 100%) !important;
  border-right: 1px solid var(--tw-line);
}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
  color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stCaption {
  color: #94a3b8 !important;
}
[data-testid="stSidebar"] .stButton > button {
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(96, 165, 250, 0.35);
  color: #f8fafc !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(59, 130, 246, 0.35);
  border-color: #60a5fa;
}

/* Chat + metrics */
div[data-testid="stChatMessage"] {
  background: rgba(18, 28, 51, 0.92);
  border: 1px solid var(--tw-line);
  border-radius: 16px;
  padding: 0.55rem 0.85rem;
  color: var(--tw-ink) !important;
}
div[data-testid="stChatMessage"] p,
div[data-testid="stChatMessage"] span {
  color: var(--tw-ink) !important;
}

div[data-testid="stMetric"] {
  background: rgba(18, 28, 51, 0.92);
  border: 1px solid var(--tw-line);
  border-radius: 14px;
  padding: 0.75rem 0.9rem;
}
div[data-testid="stMetric"] label,
[data-testid="stMetricLabel"] {
  color: var(--tw-muted) !important;
}
[data-testid="stMetricValue"] {
  color: #f8fafc !important;
}

/* Containers / expanders / tabs */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(18, 28, 51, 0.55);
  border-color: var(--tw-line) !important;
}
[data-testid="stExpander"] {
  background: rgba(18, 28, 51, 0.7);
  border: 1px solid var(--tw-line);
  border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
  color: var(--tw-muted) !important;
}
.stTabs [aria-selected="true"] {
  color: #f1f5ff !important;
}

/* Inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div,
.stNumberInput input, .stChatInput textarea {
  background-color: #0f1a30 !important;
  color: #f1f5ff !important;
  border-color: var(--tw-line) !important;
}
.stChatInput > div {
  background: #0f1a30 !important;
  border-color: var(--tw-line) !important;
}

/* Buttons */
.stButton > button {
  color: #f1f5ff !important;
  border-color: rgba(96, 165, 250, 0.35);
  background: rgba(24, 36, 64, 0.9);
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
  border: none !important;
  color: #ffffff !important;
  font-weight: 600;
}
.stButton > button[kind="primary"]:hover {
  filter: brightness(1.08);
}

/* Dataframes / alerts */
[data-testid="stDataFrame"], .stAlert {
  color: var(--tw-ink) !important;
}

/* Slider label */
.stSlider label, .stSlider p { color: var(--tw-ink) !important; }

.tw-hero { padding: 0.4rem 0 0.9rem 0; }
.tw-brand {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2.1rem;
  font-weight: 700;
  margin: 0;
  color: #f8fbff !important;
  background: linear-gradient(120deg, #93c5fd, #60a5fa 45%, #38bdf8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.tw-sub {
  color: #b6c4de !important;
  margin: 0.25rem 0 0 0;
  font-size: 1.02rem;
}
.tw-pill {
  display: inline-block;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.2);
  color: #bfdbfe !important;
  font-size: 0.8rem;
  font-weight: 600;
  margin-bottom: 0.6rem;
}
.tw-meter-wrap {
  background: #1e293b;
  border-radius: 999px;
  height: 14px;
  overflow: hidden;
  margin: 0.4rem 0 0.2rem 0;
}
.tw-meter-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #2563eb, #22d3ee);
  transition: width 0.6s ease;
}
.tw-card-label {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #9aabc8 !important;
  margin-bottom: 0.15rem;
}
.tw-meter-value {
  font-weight: 700;
  color: #7dd3fc !important;
  font-size: 1.15rem;
}
</style>
"""


def inject() -> None:
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, pill: str | None = None) -> None:
    import streamlit as st
    pill_html = f'<div class="tw-pill">{pill}</div>' if pill else ""
    st.markdown(
        f"""
        <div class="tw-hero">
          {pill_html}
          <p class="tw-brand">{title}</p>
          <p class="tw-sub">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def savings_meter(percent: int, label: str) -> None:
    import streamlit as st
    pct = max(0, min(100, int(percent)))
    st.markdown(
        f"""
        <div class="tw-card-label">Savings vs {label}</div>
        <div class="tw-meter-wrap"><div class="tw-meter-fill" style="width:{pct}%"></div></div>
        <div class="tw-meter-value">{pct}% cheaper</div>
        """,
        unsafe_allow_html=True,
    )
