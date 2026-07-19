"""
theme.py
Bảng màu và cấu hình Plotly theme dùng chung cho toàn bộ dashboard.
Bảng màu mới: Indigo/Sky làm chủ đạo, Amber làm điểm nhấn — tương phản cao, dễ đọc trên nền tối lẫn nền sáng.
"""

import plotly.graph_objects as go

# ─────────────────────────────────────────────
# BẢNG MÀU CHÍNH — Indigo/Sky + Amber (tương phản cao, không chói)
# ─────────────────────────────────────────────

COLORS = {
    # Màu chủ đạo — Indigo đậm, tương phản tốt trên cả nền sáng/tối
    "primary":         "#4F46E5",   # indigo-600
    "primary_light":   "#818CF8",   # indigo-400
    "primary_lighter": "#E0E7FF",   # indigo-100

    # Màu điểm nhấn — Amber nổi bật, không chói mắt
    "accent":          "#F59E0B",   # amber-500
    "accent_light":    "#FBBF24",   # amber-400

    # Màu thành công
    "success":         "#10B981",   # emerald-500
    "success_light":   "#6EE7B7",   # emerald-300

    # Màu cảnh báo
    "warning":         "#EF4444",   # red-500

    # Nền và text — trung tính, tương phản rõ ràng
    "bg_card":         "#FFFFFF",
    "bg_surface":      "#F9FAFB",
    "text_primary":    "#111827",   # gray-900, đen trung tính dễ đọc
    "text_secondary":  "#4B5563",   # gray-600
    "text_muted":      "#9CA3AF",   # gray-400

    # Đường lưới — xám nhạt, không lấn át data
    "grid":            "#E5E7EB",
}

# Dãy màu rời rạc — tương phản tốt, không bị lẫn vào nhau
COLOR_SEQUENCE = [
    "#4F46E5",   # indigo
    "#F59E0B",   # amber
    "#10B981",   # emerald
    "#EC4899",   # pink
    "#0EA5E9",   # sky
    "#8B5CF6",   # violet
    "#EF4444",   # red
    "#14B8A6",   # teal
    "#84CC16",   # lime
    "#64748B",   # slate
]

# Color scale liên tục — trắng nhạt → indigo đậm (sáng, dễ phân biệt giá trị)
CONTINUOUS_SCALE = [
    [0.0,  "#E0E7FF"],   # indigo-100
    [0.25, "#A5B4FC"],   # indigo-300
    [0.5,  "#6366F1"],   # indigo-500
    [0.75, "#4F46E5"],   # indigo-600
    [1.0,  "#312E81"],   # indigo-900
]

# Diverging scale — indigo ↔ trắng ↔ amber (dễ đọc, không xanh-đỏ khó phân biệt)
DIVERGING_SCALE = [
    [0.0,  "#4F46E5"],   # indigo
    [0.5,  "#FFFFFF"],
    [1.0,  "#F59E0B"],   # amber
]


# ─────────────────────────────────────────────
# FONT & LAYOUT
# ─────────────────────────────────────────────

FONT_FAMILY = "'Inter', 'Roboto', 'Segoe UI', sans-serif"
FONT_SIZE_BASE = 13
FONT_SIZE_TITLE = 15


def get_layout_template() -> dict:
    """
    Trả về dict cấu hình layout dùng chung cho mọi biểu đồ Plotly.
    Áp dụng bằng cách: fig.update_layout(**get_layout_template())
    """
    return dict(
        font=dict(family=FONT_FAMILY, size=FONT_SIZE_BASE, color=COLORS["text_primary"]),
        paper_bgcolor="rgba(0,0,0,0)",   # Nền trong suốt để hoà vào Streamlit
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor=COLORS["grid"],
            borderwidth=1,
            font=dict(size=12, color=COLORS["text_primary"]),
        ),
        xaxis=dict(
            gridcolor=COLORS["grid"],
            zerolinecolor=COLORS["grid"],
            tickfont=dict(size=12, color=COLORS["text_secondary"]),
        ),
        yaxis=dict(
            gridcolor=COLORS["grid"],
            zerolinecolor=COLORS["grid"],
            tickfont=dict(size=12, color=COLORS["text_secondary"]),
        ),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor=COLORS["primary"],
            font=dict(size=12, family=FONT_FAMILY, color=COLORS["text_primary"]),
        ),
    )


def apply_theme(fig: go.Figure, title: str = "") -> go.Figure:
    """
    Áp dụng theme chuẩn vào một Figure Plotly.
    Trả về fig đã được cập nhật để tiện chain method.

    Parameters
    ----------
    fig : go.Figure
    title : str
        Tiêu đề biểu đồ (để trống nếu không cần).
    """
    layout_kwargs = get_layout_template()
    if title:
        layout_kwargs["title"] = dict(
            text=title,
            font=dict(size=FONT_SIZE_TITLE, color=COLORS["primary"], family=FONT_FAMILY),
            x=0,
            xanchor="left",
            pad=dict(l=5),
        )
    fig.update_layout(**layout_kwargs)
    return fig


# ─────────────────────────────────────────────
# CSS MÀU SẮC KPI CARD (inject vào Streamlit qua st.markdown)
# ─────────────────────────────────────────────

KPI_CARD_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

/* Nền chính: trắng | Sidebar: tối */
[data-testid="stAppViewContainer"] {
    background-color: #FFFFFF;
}
[data-testid="stHeader"] {
    background-color: rgba(255,255,255,0);
}
[data-testid="stSidebar"] {
    background-color: #111827;
}
[data-testid="stSidebar"] * {
    color: #E5E7EB !important;
}
[data-testid="stSidebar"] label {
    color: #E5E7EB !important;
}
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] > div {
    background-color: #1F2937;
    border-color: #374151;
    color: #E5E7EB;
}
[data-testid="stSidebar"] hr {
    border-color: #374151;
}

/* KPI card — nền trắng, viền indigo, bóng nhẹ */
.kpi-card {
    background: #FFFFFF;
    border-left: 4px solid #4F46E5;
    border-radius: 10px;
    padding: 16px 20px;
    box-shadow: 0 2px 12px rgba(79,70,229,0.15);
    margin-bottom: 8px;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
.kpi-label {
    font-size: 11px;
    font-weight: 700;
    color: #4B5563;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 26px;
    font-weight: 700;
    color: #4F46E5;
    line-height: 1.2;
}
.kpi-sub {
    font-size: 12px;
    color: #9CA3AF;
    margin-top: 3px;
}

/* Insight bar — nền amber nhạt, viền amber đậm */
.insight-text {
    font-size: 12.5px;
    color: #111827;
    font-style: italic;
    background: #FEF3C7;
    border-left: 3px solid #F59E0B;
    border-radius: 0 6px 6px 0;
    padding: 7px 12px;
    margin: 6px 0 14px 0;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
</style>
"""


def render_kpi_card(label: str, value: str, sub: str = "") -> str:
    """Tạo HTML cho 1 KPI card."""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """


def render_insight(text: str) -> str:
    """Tạo HTML cho 1 dòng insight text dưới biểu đồ."""
    return f'<div class="insight-text">💡 {text}</div>'