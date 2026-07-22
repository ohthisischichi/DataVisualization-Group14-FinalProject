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

# Bảng màu ánh xạ đồng bộ cho phân khúc giá (Giá từ thấp đến cao hoặc cao đến đậm)
CUSTOM_COLOR_MAP = {
    "<4 tỷ": "#10B981",       # Xanh ngọc (Phân khúc thấp nhất)
    "4-6 tỷ": "#3B82F6",      # Xanh dương sáng
    "6-8 tỷ": "#2563EB",      # Xanh dương trung bình
    "8-10 tỷ": "#8B5CF6",     # Tím / Điểm nhấn trung cao
    ">10 tỷ": "#1D4ED8",      # Xanh hoàng gia đậm (Phân khúc cao cấp nhất)
}
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
div[data-testid="stMarkdownContainer"]:has(span#btn-ai-popup-marker) { display: none !important; }
div[data-testid="stElementContainer"]:has(span#btn-ai-popup-marker) { display: none !important; }

div[data-testid="stElementContainer"]:has(span#btn-ai-popup-marker) + div[data-testid="stElementContainer"] {
    position: fixed !important;
    bottom: 24px !important;
    right: 24px !important;
    z-index: 999999 !important;
    width: auto !important;
}

div[data-testid="stElementContainer"]:has(span#btn-ai-popup-marker) + div[data-testid="stElementContainer"] button {
    position: fixed !important;
    bottom: 24px !important;
    right: 24px !important;
    z-index: 999999 !important;
    width: 64px !important;
    height: 64px !important;
    border-radius: 50% !important;
    background: linear-gradient(135deg, #0B192C 0%, #1D4ED8 100%) !important;
    color: #FFFFFF !important;
    box-shadow: 0 8px 24px rgba(11, 25, 44, 0.45) !important;
    font-size: 1.75rem !important;
    padding: 0 !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    border: 2px solid rgba(255, 255, 255, 0.3) !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
}

div[data-testid="stElementContainer"]:has(span#btn-ai-popup-marker) + div[data-testid="stElementContainer"] button:hover {
    transform: translateY(-4px) scale(1.05) !important;
    box-shadow: 0 14px 32px rgba(29, 78, 216, 0.6) !important;
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

AI_POPUP_CSS = """
<style>
/* Style for the Dialog Popup */
div[data-testid="stDialog"] > div[role="dialog"] {
    background-color: #F8FAFC !important;
    border-radius: 16px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 25px 50px -12px rgba(11, 25, 44, 0.3) !important;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
}

div[data-testid="stDialog"] header {
    background: linear-gradient(135deg, #0B192C 0%, #1E293B 100%) !important;
    border-radius: 16px 16px 0 0 !important;
    padding: 20px 24px !important;
    border-bottom: 3px solid #1D4ED8 !important;
}

div[data-testid="stDialog"] header h2 {
    color: #FFFFFF !important;
    font-weight: 800 !important;
    font-size: 1.35rem !important;
    letter-spacing: 0.5px !important;
}

/* Close button inside dialog header */
div[data-testid="stDialog"] header button svg {
    fill: #FFFFFF !important;
}
div[data-testid="stDialog"] header button:hover {
    background-color: rgba(255, 255, 255, 0.1) !important;
}

/* Chat messages inside dialog */
div[data-testid="stChatMessage"] {
    background-color: transparent !important;
    border: none !important;
    padding: 8px 0 !important;
    margin-bottom: 8px !important;
    box-shadow: none !important;
}

/* User Message Bubble (Right aligned, Blue) */
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
    flex-direction: row-reverse !important;
    text-align: right !important;
}
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) div[data-testid="stChatMessageContent"] {
    background-color: #0084FF !important; /* Blue like messenger */
    color: #FFFFFF !important;
    border-radius: 18px 18px 0 18px !important;
    padding: 12px 16px !important;
    display: inline-block !important;
    max-width: 85% !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
}
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) div[data-testid="chatAvatarIcon-user"] {
    background-color: #F97316 !important; /* Orange avatar */
    border-radius: 4px !important;
    margin-left: 12px !important;
    margin-right: 0 !important;
}

/* AI Message Bubble (Left aligned, Purple) */
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
    flex-direction: row !important;
    text-align: left !important;
}
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) div[data-testid="stChatMessageContent"] {
    background-color: #8B5CF6 !important; /* Purple */
    color: #FFFFFF !important;
    border-radius: 18px 18px 18px 0 !important;
    padding: 12px 16px !important;
    display: inline-block !important;
    max-width: 90% !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
}
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) div[data-testid="stChatMessageContent"] * {
    color: #FFFFFF !important;
}
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) div[data-testid="chatAvatarIcon-assistant"] {
    background-color: #22C55E !important; /* Green avatar */
    border-radius: 4px !important;
    margin-right: 12px !important;
}

/* Text area */
div[data-testid="stTextArea"] textarea {
    border-radius: 10px !important;
    border: 1px solid #CBD5E1 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: #1D4ED8 !important;
    box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.2) !important;
}

/* Hide markers */
div[data-testid="stMarkdownContainer"]:has(span[id$="-marker"]) { display: none !important; }
div[data-testid="stElementContainer"]:has(span[id$="-marker"]) { display: none !important; margin: 0 !important; padding: 0 !important; height: 0 !important; }

/* Specific Action Buttons in Popup using adjacent sibling combinators */
div[data-testid="stElementContainer"]:has(span#btn-approve-marker) + div[data-testid="stElementContainer"] button {
    background-color: #16A34A !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    border: none !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stElementContainer"]:has(span#btn-approve-marker) + div[data-testid="stElementContainer"] button:hover {
    background-color: #15803D !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(22, 163, 74, 0.3) !important;
}

div[data-testid="stElementContainer"]:has(span#btn-reject-marker) + div[data-testid="stElementContainer"] button {
    background-color: #EF4444 !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    border: none !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stElementContainer"]:has(span#btn-reject-marker) + div[data-testid="stElementContainer"] button:hover {
    background-color: #DC2626 !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3) !important;
}

div[data-testid="stElementContainer"]:has(span#btn-reset-marker) + div[data-testid="stElementContainer"] button {
    background-color: #F8FAFC !important;
    color: #475569 !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    border: 1px solid #CBD5E1 !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stElementContainer"]:has(span#btn-reset-marker) + div[data-testid="stElementContainer"] button:hover {
    background-color: #F1F5F9 !important;
    color: #0F172A !important;
    border-color: #94A3B8 !important;
}

div[data-testid="stElementContainer"]:has(span#btn-generate-marker) + div[data-testid="stElementContainer"] button {
    background: linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%) !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    border: none !important;
}
div[data-testid="stElementContainer"]:has(span#btn-generate-marker) + div[data-testid="stElementContainer"] button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(29, 78, 216, 0.4) !important;
}

/* Chat user/assistant messages text */
div[data-testid="stChatMessageContent"] {
    color: #0F172A !important;
    font-size: 0.95rem !important;
}
</style>
"""


def render_kpi_card(
    label: str,
    value: str,
    icon: str = "🏢",
    icon_bg: str = "#EFF6FF",
    icon_color: str = "#1D4ED8",
) -> str:
    """Tạo HTML cho 1 VREI KPI card chỉ hiển thị tiêu đề và giá trị cốt lõi."""
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
    </div>
    """


def render_insight(text: str) -> str:
    """Tạo HTML cho 1 dòng insight text dưới biểu đồ."""
    return f'<div class="insight-text">💡 {text}</div>'
