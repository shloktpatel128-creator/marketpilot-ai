"""
Premium fintech design system — MarketPilot AI.
Awwwards / Apple / Linear inspired dark theme.
"""

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
BG_PRIMARY = "#070B18"
BG_SECONDARY = "#0F172A"
BG_CARD = "#131E35"
BORDER = "rgba(255,255,255,0.06)"
ACCENT_RED = "#C1123E"
ACCENT_CHERRY = "#E63963"
ACCENT_NAVY = "#1B2C52"
ACCENT_BLUE = "#3B82F6"
TEXT_PRIMARY = "#F8FAFC"
TEXT_SECONDARY = "#94A3B8"
GREEN = "#10B981"
YELLOW = "#FBBF24"
RED = "#EF4444"

# Legacy aliases for charts
ACCENT_GREEN = GREEN
ACCENT_YELLOW = YELLOW
ACCENT_PURPLE = "#8B5CF6"
TEXT_MUTED = TEXT_SECONDARY

CHART_HEIGHT_MAIN = 580
CHART_HEIGHT_SUB = 400

CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", color=TEXT_PRIMARY, size=12),
    margin=dict(l=12, r=12, t=40, b=12),
    hovermode="x unified",
    hoverlabel=dict(bgcolor=BG_CARD, bordercolor=BORDER, font=dict(color=TEXT_PRIMARY)),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        borderwidth=0,
        orientation="h",
        yanchor="bottom", y=1.01,
        xanchor="right", x=1,
        font=dict(size=11, color=TEXT_SECONDARY),
    ),
    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, showline=False),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, showline=False),
)


def inject_custom_css() -> str:
    """Inject premium dashboard CSS — hides Streamlit chrome, adds glass/animations."""
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ===== BASE ===== */
    .stApp {{
        background: {BG_PRIMARY};
        background-image:
            radial-gradient(ellipse 80% 50% at 50% -20%, rgba(230,57,99,0.12), transparent),
            radial-gradient(ellipse 60% 40% at 100% 0%, rgba(59,130,246,0.08), transparent),
            linear-gradient(180deg, {BG_PRIMARY} 0%, {BG_SECONDARY} 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: {TEXT_PRIMARY};
    }}

    #MainMenu, footer, header {{visibility: hidden; height: 0;}}
    .block-container {{
        padding: 1.5rem 2rem 3rem 2rem !important;
        max-width: 100% !important;
        animation: mpFadeIn 0.6s ease-out;
    }}

    @keyframes mpFadeIn {{
        from {{ opacity: 0; transform: translateY(12px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes mpSlideIn {{
        from {{ opacity: 0; transform: translateX(-16px); }}
        to   {{ opacity: 1; transform: translateX(0); }}
    }}
    @keyframes mpGlow {{
        0%, 100% {{ box-shadow: 0 0 20px rgba(230,57,99,0.15); }}
        50%      {{ box-shadow: 0 0 32px rgba(230,57,99,0.28); }}
    }}
    @keyframes mpShimmer {{
        0%   {{ background-position: -200% 0; }}
        100% {{ background-position: 200% 0; }}
    }}

    /* ===== SIDEBAR ===== */
    section[data-testid="stSidebar"] {{
        background: rgba(15,23,42,0.85) !important;
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border-right: 1px solid {BORDER};
        animation: mpSlideIn 0.5s ease-out;
    }}
    section[data-testid="stSidebar"] > div {{
        padding-top: 1.5rem;
    }}
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] label {{
        color: {TEXT_SECONDARY};
    }}

    /* Hide default sidebar collapse button styling issues */
    [data-testid="collapsedControl"] {{
        color: {TEXT_SECONDARY};
    }}

    /* ===== GLASS CARDS ===== */
    .mp-glass {{
        background: rgba(19,30,53,0.75);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid {BORDER};
        border-radius: 20px;
        padding: 24px 28px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.04);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }}
    .mp-glass:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.35), 0 0 24px rgba(230,57,99,0.08);
    }}

    /* ===== METRIC CARDS ===== */
    .mp-metric-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 16px;
        margin: 24px 0;
    }}
    .mp-metric-card {{
        background: rgba(19,30,53,0.8);
        backdrop-filter: blur(16px);
        border: 1px solid {BORDER};
        border-radius: 20px;
        padding: 20px 22px;
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
        animation: mpFadeIn 0.5s ease-out backwards;
    }}
    .mp-metric-card:nth-child(1) {{ animation-delay: 0.05s; }}
    .mp-metric-card:nth-child(2) {{ animation-delay: 0.1s; }}
    .mp-metric-card:nth-child(3) {{ animation-delay: 0.15s; }}
    .mp-metric-card:nth-child(4) {{ animation-delay: 0.2s; }}
    .mp-metric-card:nth-child(5) {{ animation-delay: 0.25s; }}
    .mp-metric-card:nth-child(6) {{ animation-delay: 0.3s; }}
    .mp-metric-card:hover {{
        transform: translateY(-4px);
        border-color: rgba(230,57,99,0.25);
        box-shadow: 0 16px 48px rgba(0,0,0,0.3), 0 0 24px rgba(230,57,99,0.12);
    }}
    .mp-metric-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(230,57,99,0.4), transparent);
    }}
    .mp-metric-label {{
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {TEXT_SECONDARY};
        margin-bottom: 8px;
    }}
    .mp-metric-value {{
        font-size: 1.65rem;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        letter-spacing: -0.02em;
        line-height: 1.2;
    }}
    .mp-metric-delta {{
        font-size: 0.82rem;
        font-weight: 500;
        margin-top: 4px;
    }}
    .mp-up {{ color: {GREEN}; }}
    .mp-down {{ color: {RED}; }}
    .mp-neutral {{ color: {YELLOW}; }}

    /* ===== TOP BAR ===== */
    .mp-topbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 12px 0 20px 0;
        border-bottom: 1px solid {BORDER};
        margin-bottom: 8px;
        animation: mpFadeIn 0.4s ease-out;
    }}
    .mp-search {{
        flex: 1;
        max-width: 480px;
        background: rgba(19,30,53,0.6);
        border: 1px solid {BORDER};
        border-radius: 999px;
        padding: 10px 20px;
        color: {TEXT_SECONDARY};
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .mp-search kbd {{
        background: rgba(255,255,255,0.06);
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.75rem;
        margin-left: auto;
    }}
    .mp-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }}
    .mp-badge-paper {{
        background: rgba(59,130,246,0.15);
        border: 1px solid rgba(59,130,246,0.3);
        color: {ACCENT_BLUE};
    }}
    .mp-badge-open {{
        background: rgba(16,185,129,0.12);
        border: 1px solid rgba(16,185,129,0.3);
        color: {GREEN};
    }}
    .mp-badge-closed {{
        background: rgba(193,18,62,0.12);
        border: 1px solid rgba(193,18,62,0.3);
        color: {ACCENT_CHERRY};
    }}
    .mp-avatar {{
        width: 36px; height: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, {ACCENT_CHERRY}, {ACCENT_RED});
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 0.85rem; color: white;
        box-shadow: 0 4px 12px rgba(230,57,99,0.3);
    }}

    /* ===== TICKER HEADER ===== */
    .mp-ticker-header {{
        display: flex;
        flex-wrap: wrap;
        align-items: flex-end;
        justify-content: space-between;
        gap: 20px;
        padding: 28px 0 8px 0;
    }}
    .mp-ticker-name {{
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: {TEXT_PRIMARY};
        margin: 0;
        line-height: 1.1;
    }}
    .mp-ticker-meta {{
        font-size: 0.88rem;
        color: {TEXT_SECONDARY};
        margin-top: 6px;
    }}
    .mp-star {{ color: {YELLOW}; font-size: 1.2rem; cursor: pointer; }}

    /* ===== SIGNAL CARD (CHERRY) ===== */
    .mp-signal-card {{
        background: linear-gradient(145deg, rgba(193,18,62,0.35) 0%, rgba(19,30,53,0.9) 60%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(230,57,99,0.25);
        border-radius: 20px;
        padding: 28px;
        animation: mpGlow 4s ease-in-out infinite;
        margin-bottom: 20px;
    }}
    .mp-signal-action {{
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 8px 0;
    }}
    .mp-signal-buy {{ color: {GREEN}; }}
    .mp-signal-sell {{ color: {RED}; }}
    .mp-signal-hold {{ color: {YELLOW}; }}

    /* ===== NAV ITEMS (sidebar HTML) ===== */
    .mp-logo {{
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        color: {ACCENT_CHERRY};
        text-transform: uppercase;
        margin-bottom: 4px;
    }}
    .mp-logo-title {{
        font-size: 1.15rem;
        font-weight: 800;
        color: {TEXT_PRIMARY};
        letter-spacing: -0.02em;
        margin-bottom: 24px;
    }}
    .mp-nav-divider {{
        height: 1px;
        background: {BORDER};
        margin: 20px 0;
    }}
    .mp-watchlist-item {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 12px;
        border-radius: 12px;
        margin-bottom: 4px;
        transition: background 0.2s;
        cursor: pointer;
    }}
    .mp-watchlist-item:hover {{
        background: rgba(255,255,255,0.04);
    }}
    .mp-wl-ticker {{ font-weight: 600; color: {TEXT_PRIMARY}; font-size: 0.9rem; }}
    .mp-wl-name {{ font-size: 0.75rem; color: {TEXT_SECONDARY}; }}
    .mp-wl-price {{ text-align: right; font-weight: 600; font-size: 0.88rem; }}

    /* ===== PAPER ACCOUNT CARD ===== */
    .mp-paper-card {{
        background: linear-gradient(160deg, {ACCENT_NAVY} 0%, rgba(19,30,53,0.95) 100%);
        border: 1px solid {BORDER};
        border-radius: 20px;
        padding: 20px;
        margin-top: 16px;
    }}
    .mp-paper-row {{
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        font-size: 0.85rem;
    }}
    .mp-paper-label {{ color: {TEXT_SECONDARY}; }}
    .mp-paper-value {{ color: {TEXT_PRIMARY}; font-weight: 600; }}

    /* ===== LOWER GRID ===== */
    .mp-grid-2 {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 20px;
        margin-top: 24px;
    }}
    .mp-grid-3 {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 16px;
        margin-top: 20px;
    }}
    .mp-section-title {{
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: {TEXT_SECONDARY};
        margin-bottom: 16px;
    }}
    .mp-card-title {{
        font-size: 1rem;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin-bottom: 12px;
    }}

    /* ===== NEWS ===== */
    .mp-news-item {{
        padding: 16px;
        border-radius: 16px;
        border: 1px solid {BORDER};
        margin-bottom: 12px;
        transition: all 0.25s ease;
        background: rgba(19,30,53,0.5);
    }}
    .mp-news-item:hover {{
        border-color: rgba(230,57,99,0.2);
        transform: translateX(4px);
    }}
    .mp-news-headline {{
        font-weight: 600;
        color: {TEXT_PRIMARY};
        font-size: 0.92rem;
        line-height: 1.4;
        margin-bottom: 8px;
    }}
    .mp-news-meta {{
        font-size: 0.75rem;
        color: {TEXT_SECONDARY};
    }}

    /* ===== AI ANALYSIS ===== */
    .mp-ai-rec {{
        font-size: 1.5rem;
        font-weight: 800;
        margin: 12px 0;
    }}
    .mp-factor {{
        padding: 8px 12px;
        border-radius: 10px;
        margin-bottom: 6px;
        font-size: 0.85rem;
    }}
    .mp-factor-bull {{ background: rgba(16,185,129,0.1); border-left: 3px solid {GREEN}; color: {TEXT_PRIMARY}; }}
    .mp-factor-bear {{ background: rgba(239,68,68,0.1); border-left: 3px solid {RED}; color: {TEXT_PRIMARY}; }}
    .mp-stat-row {{
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid {BORDER};
        font-size: 0.88rem;
    }}

    /* ===== STREAMLIT OVERRIDES ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background: transparent;
        border-bottom: 1px solid {BORDER};
        padding-bottom: 0;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        border: none;
        border-radius: 12px 12px 0 0;
        color: {TEXT_SECONDARY};
        font-weight: 600;
        font-size: 0.85rem;
        padding: 12px 20px;
        transition: all 0.2s;
    }}
    .stTabs [aria-selected="true"] {{
        background: rgba(230,57,99,0.1) !important;
        color: {ACCENT_CHERRY} !important;
        border-bottom: 2px solid {ACCENT_CHERRY} !important;
    }}

    .stButton > button {{
        border-radius: 999px !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.25s cubic-bezier(0.4,0,0.2,1) !important;
        border: 1px solid {BORDER} !important;
        background: rgba(19,30,53,0.8) !important;
        color: {TEXT_PRIMARY} !important;
    }}
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {ACCENT_CHERRY} 0%, {ACCENT_RED} 100%) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 20px rgba(230,57,99,0.35) !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px rgba(230,57,99,0.45) !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        border-color: rgba(230,57,99,0.3) !important;
    }}

    div[data-testid="stMetric"] {{
        background: rgba(19,30,53,0.7);
        border: 1px solid {BORDER};
        border-radius: 20px;
        padding: 20px;
    }}
    div[data-testid="stMetric"] label {{ color: {TEXT_SECONDARY} !important; font-size: 0.75rem !important; }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: {TEXT_PRIMARY} !important;
        font-weight: 700 !important;
    }}

    .stDataFrame {{ border-radius: 16px; border: 1px solid {BORDER}; overflow: hidden; }}

    div[data-testid="stExpander"] {{
        background: rgba(19,30,53,0.5);
        border: 1px solid {BORDER};
        border-radius: 16px;
    }}

    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {{
        background: rgba(19,30,53,0.8) !important;
        border-color: {BORDER} !important;
        border-radius: 12px !important;
        color: {TEXT_PRIMARY} !important;
    }}

    /* Plotly chart container */
    .js-plotly-plot {{ border-radius: 20px; overflow: hidden; }}

    /* Loading skeleton */
    .mp-skeleton {{
        background: linear-gradient(90deg, rgba(19,30,53,0.5) 25%, rgba(255,255,255,0.06) 50%, rgba(19,30,53,0.5) 75%);
        background-size: 200% 100%;
        animation: mpShimmer 1.5s infinite;
        border-radius: 20px;
        height: 120px;
    }}

    /* Hide streamlit deploy button */
    .stDeployButton {{ display: none; }}

    /* Nav button styling in sidebar */
    div[data-testid="stSidebar"] .stButton > button {{
        width: 100%;
        text-align: left;
        justify-content: flex-start;
        border-radius: 12px !important;
        padding: 10px 16px !important;
        margin-bottom: 4px;
    }}

    @media (max-width: 768px) {{
        .block-container {{ padding: 1rem !important; }}
        .mp-metric-grid {{ grid-template-columns: repeat(2, 1fr); }}
        .mp-ticker-name {{ font-size: 1.5rem; }}
    }}
    </style>
    """
