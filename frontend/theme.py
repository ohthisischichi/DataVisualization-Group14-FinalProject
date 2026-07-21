"""
theme.py
Bảng màu và cấu hình Plotly theme dùng chung cho toàn bộ dashboard VREI (Vietnam Real Estate Intelligence).
Thiết kế theo chuẩn Executive Dashboard: Navy (#0B192C) chủ đạo, Royal Blue (#1D4ED8) cho charts, Amber (#F59E0B) điểm nhấn.
"""

import plotly.graph_objects as go

# ─────────────────────────────────────────────
# BẢNG MÀU CHÍNH — VREI Executive Palette
# ─────────────────────────────────────────────

COLORS = {
    # Dark Navy Header & Brand
    "header_bg":       "#0B192C",
    "header_text":     "#FFFFFF",

    # Primary Blue & Accent
    "primary":         "#1D4ED8",   # Royal Deep Blue
    "primary_light":   "#3B82F6",   # Bright Blue
    "primary_lighter": "#EFF6FF",   # Ice Blue

    # Accent Gold / Amber
    "accent":          "#F59E0B",   # Amber / Gold
    "accent_light":    "#FBBF24",   # Soft Gold

    # Status Indicators
    "success":         "#16A34A",   # Emerald Green
    "warning":         "#EF4444",   # Red

    # Neutral Surface & Text
    "bg_card":         "#FFFFFF",
    "bg_surface":      "#F8FAFC",   # Slate 50
    "bg_sidebar":      "#F1F5F9",   # Slate 100
    "text_primary":    "#0F172A",   # Slate 900
    "text_secondary":  "#334155",   # Slate 700
    "text_muted":      "#64748B",   # Slate 500

    # Gridlines & Borders
    "grid":            "#E2E8F0",   # Slate 200
}

# Dãy màu rời rạc cho charts
COLOR_SEQUENCE = [
    "#1D4ED8",   # Royal Blue
    "#2563EB",   # Medium Blue
    "#3B82F6",   # Bright Blue
    "#F59E0B",   # Amber / Gold
    "#10B981",   # Emerald Green
    "#8B5CF6",   # Purple
    "#0EA5E9",   # Sky Blue
    "#EC4899",   # Pink
    "#64748B",   # Slate Gray
]

# Color scale liên tục cho Choropleth Map và Heatmap (Blue Gradient)
CONTINUOUS_SCALE = [
    [0.0,  "#EFF6FF"],
    [0.25, "#BFDBFE"],
    [0.5,  "#3B82F6"],
    [0.75, "#1D4ED8"],
    [1.0,  "#1E3A8A"],
]

# Diverging scale
DIVERGING_SCALE = [
    [0.0,  "#1D4ED8"],
    [0.5,  "#FFFFFF"],
    [1.0,  "#F59E0B"],
]


# ─────────────────────────────────────────────
# FONT & LAYOUT
# ─────────────────────────────────────────────

FONT_FAMILY = "'Plus Jakarta Sans', 'Inter', 'Segoe UI', sans-serif"
FONT_SIZE_BASE = 12.5
FONT_SIZE_TITLE = 14.5


def get_layout_template() -> dict:
    """
    Trả về dict cấu hình layout dùng chung cho mọi biểu đồ Plotly.
    """
    return dict(
        font=dict(family=FONT_FAMILY, size=FONT_SIZE_BASE, color=COLORS["text_primary"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=15, t=40, b=10),
        legend=dict(
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=COLORS["grid"],
            borderwidth=1,
            font=dict(size=11.5, color=COLORS["text_primary"]),
        ),
        xaxis=dict(
            gridcolor=COLORS["grid"],
            zerolinecolor=COLORS["grid"],
            tickfont=dict(size=11.5, color=COLORS["text_secondary"]),
        ),
        yaxis=dict(
            gridcolor=COLORS["grid"],
            zerolinecolor=COLORS["grid"],
            tickfont=dict(size=11.5, color=COLORS["text_secondary"]),
        ),
        hoverlabel=dict(
            bgcolor="#0F172A",
            bordercolor="#0F172A",
            font=dict(size=12, family=FONT_FAMILY, color="#FFFFFF"),
        ),
    )


def apply_theme(fig: go.Figure, title: str = "") -> go.Figure:
    """
    Áp dụng theme chuẩn vào một Figure Plotly.
    """
    layout_kwargs = get_layout_template()
    if title:
        layout_kwargs["title"] = dict(
            text=f"<b>{title}</b>",
            font=dict(size=FONT_SIZE_TITLE, color=COLORS["text_primary"], family=FONT_FAMILY),
            x=0,
            xanchor="left",
            pad=dict(l=5),
        )
    fig.update_layout(**layout_kwargs)
    return fig


# ─────────────────────────────────────────────
# CSS EXECUTIVE DASHBOARD (GLOBAL & SIDEBAR)
# ─────────────────────────────────────────────

KPI_CARD_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

/* Nền chính toàn bộ app & tab content panels (Luôn là màu sáng F8FAFC) */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
div[data-testid="stTabs"],
div[data-baseweb="tab-panel"] {
    background-color: #F8FAFC !important;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
}

[data-testid="stHeader"] {
    background-color: transparent !important;
    z-index: 9999 !important;
    pointer-events: none !important;
}
[data-testid="stHeader"] * {
    pointer-events: auto !important;
}

/* Sidebar phong cách VREI clean light slate */
[data-testid="stSidebar"] {
    background-color: #F1F5F9 !important;
    border-right: 1px solid #E2E8F0 !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #1E293B;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}

[data-testid="stSidebar"] h2 {
    color: #0F172A !important;
    font-weight: 700 !important;
    font-size: 1.15rem !important;
}
[data-testid="stSidebar"] label {
    color: #475569 !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
    color: #0F172A !important;
}
[data-testid="stSidebar"] hr {
    border-color: #E2E8F0 !important;
}

/* Style cho tag trong multiselect input */
span[data-baseweb="tag"] {
    background-color: #1D4ED8 !important;
    border-radius: 6px !important;
}
span[data-baseweb="tag"] * {
    color: #FFFFFF !important;
}

/* VREI Dark Navy Header Banner */
.vrei-header {
    background: linear-gradient(135deg, #0B192C 0%, #1E293B 100%);
    border-radius: 14px;
    padding: 16px 24px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 10px 25px -5px rgba(11, 25, 44, 0.25);
}
.vrei-brand {
    display: flex;
    align-items: center;
    gap: 14px;
}
.vrei-logo {
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 800;
    font-size: 22px;
    box-shadow: 0 4px 12px rgba(29, 78, 216, 0.4);
}
.vrei-title {
    color: #FFFFFF !important;
    font-weight: 800 !important;
    font-size: 1.25rem !important;
    letter-spacing: 0.5px !important;
    line-height: 1.2 !important;
    margin: 0 !important;
}
.vrei-subtitle {
    color: #CBD5E1 !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    margin: 3px 0 0 0 !important;
}

/* Style cho riêng Thanh Tab Bar cố định ở đầu trang khi scroll */
.block-container {
    padding-top: 1rem !important;
}
div[data-baseweb="tab-list"] {
    position: sticky !important;
    top: 0px !important;
    z-index: 99999 !important;
    background-color: #0B192C !important;
    padding: 8px 16px !important;
    border-radius: 0 0 12px 12px !important;
    gap: 8px !important;
    box-shadow: 0 6px 20px rgba(11, 25, 44, 0.25) !important;
}
button[data-baseweb="tab"] {
    background-color: transparent !important;
    border: none !important;
    color: #94A3B8 !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    padding: 10px 18px !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}
button[data-baseweb="tab"]:hover {
    color: #FFFFFF !important;
    background-color: rgba(255, 255, 255, 0.08) !important;
}
button[aria-selected="true"] {
    color: #FFFFFF !important;
    background-color: rgba(255, 255, 255, 0.12) !important;
    border-bottom: 3px solid #F59E0B !important;
    font-weight: 700 !important;
}

/* Floating AI Assistant Button at bottom-right corner */
div.stButton:has(button[aria-label*="AI Assistant"]),
div[data-testid="stButton"]:has(button[aria-label*="AI Assistant"]),
div[data-testid="stElementContainer"]:has(button[aria-label*="AI Assistant"]),
div[data-testid="element-container"]:has(button[aria-label*="AI Assistant"]),
div.element-container:has(button[aria-label*="AI Assistant"]) {
    position: fixed !important;
    bottom: 24px !important;
    right: 24px !important;
    z-index: 999999 !important;
    width: auto !important;
}

div.stButton:has(button[aria-label*="AI Assistant"]) button,
div[data-testid="stButton"]:has(button[aria-label*="AI Assistant"]) button,
div[data-testid="stElementContainer"]:has(button[aria-label*="AI Assistant"]) button,
div[data-testid="element-container"]:has(button[aria-label*="AI Assistant"]) button,
div.element-container:has(button[aria-label*="AI Assistant"]) button,
button[aria-label*="AI Assistant"] {
    position: fixed !important;
    bottom: 24px !important;
    right: 24px !important;
    z-index: 999999 !important;
    border-radius: 50px !important;
    background: linear-gradient(135deg, #0B192C 0%, #1D4ED8 100%) !important;
    color: #FFFFFF !important;
    box-shadow: 0 8px 24px rgba(11, 25, 44, 0.45) !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 12px 22px !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
}

div.stButton:has(button[aria-label*="AI Assistant"]) button:hover,
div[data-testid="stButton"]:has(button[aria-label*="AI Assistant"]) button:hover,
div[data-testid="stElementContainer"]:has(button[aria-label*="AI Assistant"]) button:hover,
div[data-testid="element-container"]:has(button[aria-label*="AI Assistant"]) button:hover,
div.element-container:has(button[aria-label*="AI Assistant"]) button:hover,
button[aria-label*="AI Assistant"]:hover {
    transform: translateY(-3px) scale(1.03) !important;
    box-shadow: 0 12px 28px rgba(29, 78, 216, 0.6) !important;
    background: linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%) !important;
}

/* Thẻ KPI chuẩn Executive VREI */
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
    margin-bottom: 12px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.kpi-header {
    display: flex;
    align-items: center;
    gap: 12px;
}
.kpi-icon-box {
    width: 38px;
    height: 38px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
}
.kpi-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #64748B;
    line-height: 1.2;
}
.kpi-value {
    font-size: 1.5rem;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.2;
    margin-top: 4px;
}
.kpi-trend {
    font-size: 0.76rem;
    font-weight: 600;
    color: #16A34A;
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 4px;
}
.kpi-sub {
    font-size: 0.76rem;
    color: #94A3B8;
    margin-top: 2px;
}

/* Insight text bar */
.insight-text {
    font-size: 12.5px;
    color: #0F172A;
    font-weight: 500;
    background: #EFF6FF;
    border-left: 4px solid #1D4ED8;
    border-radius: 0 8px 8px 0;
    padding: 8px 14px;
    margin: 8px 0 16px 0;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}
</style>
"""


def render_kpi_card(
    label: str,
    value: str,
    sub: str = "",
    icon: str = "🏢",
    icon_bg: str = "#EFF6FF",
    icon_color: str = "#1D4ED8",
    trend: str = "▲ 12.6% so với kỳ trước",
) -> str:
    """Tạo HTML cho 1 VREI KPI card với icon và trend chỉ số."""
    trend_html = f'<div class="kpi-trend">{trend}</div>' if trend else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-header">
            <div class="kpi-icon-box" style="background: {icon_bg}; color: {icon_color};">
                {icon}
            </div>
            <div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>
        </div>
        {trend_html}
        {sub_html}
    </div>
    """


def render_insight(text: str) -> str:
    """Tạo HTML cho 1 dòng insight text dưới biểu đồ."""
    return f'<div class="insight-text">💡 {text}</div>'