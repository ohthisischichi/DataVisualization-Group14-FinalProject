"""
pages/price_drivers.py — Tab "Price Drivers"
Phân tích các yếu tố ảnh hưởng đến giá bất động sản.

Layout:
  1. Scatter Area vs Price (màu theo Province top 5, size theo Bedrooms, OLS trendline)
  2. Correlation heatmap các biến số
  3. Boxplot Price_per_m2 theo Legal status
  4. Boxplot Price_per_m2 theo Furniture state
  (Tuỳ chọn) Boxplot theo House direction
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from theme import (
    COLORS,
    COLOR_SEQUENCE,
    CONTINUOUS_SCALE,
    DIVERGING_SCALE,
    KPI_CARD_CSS,
    apply_theme,
    render_insight,
)
from data_loader import get_numeric_columns


def _empty_state() -> None:
    st.warning(
        "⚠️ Không có dữ liệu phù hợp với bộ lọc hiện tại. "
        "Hãy mở rộng điều kiện lọc trên sidebar.",
        icon="🔍",
    )


# ─────────────────────────────────────────────
# 1. SCATTER AREA vs PRICE + OLS TRENDLINE
# ─────────────────────────────────────────────

def _render_scatter_area_price(df: pd.DataFrame) -> None:
    """
    Scatter plot Area (x) vs Price (y):
    - Màu theo Province (Top 5 nhiều tin nhất, còn lại gom vào "Khác")
    - Kích thước điểm tỉ lệ với Bedrooms (xử lý NaN trước)
    - Trendline OLS tổng thể (statsmodels)
    - Giới hạn ở percentile 99 để tránh outlier kéo scale
    """
    # Lấy top 5 tỉnh theo số tin để tô màu, còn lại nhóm "Khác"
    top5_prov = df["Province"].value_counts().nlargest(5).index.tolist()
    df_plot = df.copy()
    df_plot["Province_Group"] = df_plot["Province"].apply(
        lambda p: p if p in top5_prov else "Khác"
    )

    # Xử lý Bedrooms NaN → 0 để dùng làm size (size phải >= 0)
    df_plot["Bedrooms_plot"] = df_plot["Bedrooms"].fillna(0).clip(lower=0)

    # Giới hạn outlier ở p99 cho cả Price và Area để tránh scale quá rộng
    p99_price = df_plot["Price"].quantile(0.99)
    p99_area = df_plot["Area"].quantile(0.99)
    df_plot = df_plot[
        (df_plot["Price"] <= p99_price) & (df_plot["Area"] <= p99_area)
    ]

    # Đặt thứ tự màu: "Khác" cuối cùng (màu xám)
    prov_order = top5_prov + ["Khác"]
    color_map = {p: c for p, c in zip(top5_prov, COLOR_SEQUENCE)}
    color_map["Khác"] = "#BDC3C7"  # Màu xám nhạt cho nhóm "Khác"

    fig = px.scatter(
        df_plot,
        x="Area",
        y="Price",
        color="Province_Group",
        size="Bedrooms_plot",
        size_max=18,
        # Không dùng trendline của plotly (cần statsmodels) — tự vẽ bằng numpy bên dưới
        color_discrete_map=color_map,
        category_orders={"Province_Group": prov_order},
        opacity=0.55,
        labels={
            "Area": "Diện tích (m²)",
            "Price": "Giá (tỷ VNĐ)",
            "Province_Group": "Tỉnh/Thành",
            "Bedrooms_plot": "Phòng ngủ",
        },
        hover_data={
            "Province": True,
            "Bedrooms": True,
            "Bathrooms": True,
            "Price_per_m2": ":.4f",
            "Bedrooms_plot": False,
        },
    )

    # Vẽ đường trendline bằng numpy.polyfit (hồi quy tuyến bậc 1, không cần statsmodels)
    x_vals = df_plot["Area"].to_numpy()
    y_vals = df_plot["Price"].to_numpy()
    # Loại NaN trước khi fit
    valid = ~(np.isnan(x_vals) | np.isnan(y_vals))
    if valid.sum() >= 2:
        coeffs = np.polyfit(x_vals[valid], y_vals[valid], deg=1)
        x_line = np.linspace(x_vals[valid].min(), x_vals[valid].max(), 200)
        y_line = np.polyval(coeffs, x_line)
        fig.add_trace(
            go.Scatter(
                x=x_line,
                y=y_line,
                mode="lines",
                name="Xu hướng (hồi quy tuyến)",
                line=dict(color=COLORS["accent"], width=2.5, dash="dash"),
                hovertemplate="Diện tích: %{x:.0f} m²<br>Giá dự báo: %{y:.2f} tỷ<extra>Trendline</extra>",
                showlegend=True,
            )
        )

    apply_theme(fig, "Diện tích vs Giá — màu theo Tỉnh, cỡ điểm theo số Phòng ngủ")
    fig.update_layout(height=480, legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, width='stretch', key="pd_scatter")

    # Tính hệ số tương quan để viết insight
    corr = df_plot[["Area", "Price"]].corr().iloc[0, 1]
    st.markdown(
        render_insight(
            f"Hệ số tương quan Pearson giữa Diện tích và Giá = <b>{corr:.3f}</b>. "
            f"{'Tương quan tích cực mạnh' if corr > 0.7 else 'Tương quan tích cực vừa' if corr > 0.4 else 'Tương quan yếu'} "
            f"— diện tích lớn hơn có xu hướng giá cao hơn nhưng có nhiều yếu tố khác."
        ),
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# 2. CORRELATION HEATMAP
# ─────────────────────────────────────────────

def _render_correlation_heatmap(df: pd.DataFrame) -> None:
    """
    Heatmap tương quan (Pearson) giữa các biến số:
    Area, Frontage, Access Road, Floors, Bedrooms, Bathrooms, Price, Price_per_m2.
    """
    num_cols = get_numeric_columns(df)
    df_num = df[num_cols].dropna()

    if len(df_num) < 10:
        st.info("Không đủ dữ liệu để tính ma trận tương quan.")
        return

    corr_matrix = df_num.corr(method="pearson")

    # Tạo mask tam giác trên để chỉ hiện nửa dưới (tránh trùng lặp)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    z_masked = corr_matrix.where(~mask).values

    # Tạo hover text
    hover_text = []
    for i, row_name in enumerate(corr_matrix.index):
        row_texts = []
        for j, col_name in enumerate(corr_matrix.columns):
            val = corr_matrix.iloc[i, j]
            if mask[i, j]:
                row_texts.append("")
            else:
                row_texts.append(
                    f"<b>{row_name}</b> vs <b>{col_name}</b><br>r = {val:.3f}"
                )
        hover_text.append(row_texts)

    col_labels = [
        c.replace("Access Road", "Đường").replace("Price_per_m2", "Giá/m²")
        for c in corr_matrix.columns
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z_masked,
            x=col_labels,
            y=col_labels,
            colorscale=DIVERGING_SCALE,
            zmid=0,
            zmin=-1,
            zmax=1,
            hoverinfo="text",
            text=hover_text,
            hovertemplate="%{text}<extra></extra>",
            colorbar=dict(
                title=dict(text="Pearson r"),
                tickformat=".2f",
            ),
            showscale=True,
        )
    )

    # Thêm annotation số liệu vào từng ô (chỉ nửa dưới)
    annotations = []
    for i in range(len(corr_matrix.index)):
        for j in range(len(corr_matrix.columns)):
            if not mask[i, j]:
                val = corr_matrix.iloc[i, j]
                annotations.append(
                    dict(
                        x=col_labels[j],
                        y=col_labels[i],
                        text=f"{val:.2f}",
                        showarrow=False,
                        font=dict(
                            size=11,
                            color="white" if abs(val) > 0.5 else COLORS["text_primary"],
                        ),
                    )
                )

    apply_theme(fig, "Ma trận tương quan giữa các biến số")
    fig.update_layout(height=480, annotations=annotations)
    st.plotly_chart(fig, width='stretch', key="pd_corr_heatmap")

    # Insight: cặp tương quan mạnh nhất (ngoài đường chéo)
    corr_upper = corr_matrix.where(~np.eye(len(corr_matrix), dtype=bool))
    max_corr_val = corr_upper.abs().stack().max()
    max_corr_pair = corr_upper.abs().stack().idxmax()
    st.markdown(
        render_insight(
            f"Cặp tương quan mạnh nhất: <b>{max_corr_pair[0]}</b> và "
            f"<b>{max_corr_pair[1]}</b> (r = {max_corr_val:.3f})."
        ),
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# 3. BOXPLOT THEO LEGAL STATUS
# ─────────────────────────────────────────────

def _render_boxplot_legal(df: pd.DataFrame) -> None:
    """Boxplot Price_per_m2 theo tình trạng pháp lý."""
    legal_order = sorted(df["Legal status"].dropna().unique().tolist())

    # Giới hạn outlier ở p99 để boxplot đọc được
    p99 = df["Price_per_m2"].quantile(0.99)
    df_plot = df[df["Price_per_m2"] <= p99]

    fig = px.box(
        df_plot,
        x="Legal status",
        y="Price_per_m2",
        color="Legal status",
        color_discrete_sequence=COLOR_SEQUENCE,
        category_orders={"Legal status": legal_order},
        labels={"Price_per_m2": "Giá/m² (tỷ)", "Legal status": "Tình trạng pháp lý"},
        points="outliers",  # Chỉ hiện outlier, không hiện toàn bộ điểm (dữ liệu lớn)
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Giá/m²: %{y:.4f} tỷ<extra></extra>"
        )
    )
    apply_theme(fig, "Giá/m² theo tình trạng pháp lý")
    fig.update_layout(height=380, showlegend=False)
    st.plotly_chart(fig, width='stretch', key="pd_box_legal")

    # Insight: so sánh median các nhóm
    medians = df_plot.groupby("Legal status", observed=True)["Price_per_m2"].median()
    if not medians.empty:
        top_legal = medians.idxmax()
        st.markdown(
            render_insight(
                f"Bất động sản <b>{top_legal}</b> có giá/m² trung vị cao nhất "
                f"({medians[top_legal]:.4f} tỷ/m²). "
                f"Pháp lý rõ ràng thường đi kèm giá premium."
            ),
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# 4. BOXPLOT THEO FURNITURE STATE
# ─────────────────────────────────────────────

def _render_boxplot_furniture(df: pd.DataFrame) -> None:
    """Boxplot Price_per_m2 theo tình trạng nội thất."""
    furniture_order = sorted(df["Furniture state"].dropna().unique().tolist())

    p99 = df["Price_per_m2"].quantile(0.99)
    df_plot = df[df["Price_per_m2"] <= p99]

    # Dùng màu khác để phân biệt với boxplot Legal status phía trên
    furniture_colors = [COLORS["accent"], COLORS["success"], COLORS["primary_light"]]

    fig = px.box(
        df_plot,
        x="Furniture state",
        y="Price_per_m2",
        color="Furniture state",
        color_discrete_sequence=furniture_colors,
        category_orders={"Furniture state": furniture_order},
        labels={
            "Price_per_m2": "Giá/m² (tỷ)",
            "Furniture state": "Tình trạng nội thất",
        },
        points="outliers",
    )
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Giá/m²: %{y:.4f} tỷ<extra></extra>"
    )
    apply_theme(fig, "Giá/m² theo tình trạng nội thất")
    fig.update_layout(height=380, showlegend=False)
    st.plotly_chart(fig, width='stretch', key="pd_box_furniture")

    medians = df_plot.groupby("Furniture state", observed=True)["Price_per_m2"].median()
    if not medians.empty:
        top_furn = medians.idxmax()
        st.markdown(
            render_insight(
                f"Nhóm nội thất <b>{top_furn}</b> có giá/m² trung vị cao nhất "
                f"({medians[top_furn]:.4f} tỷ/m²)."
            ),
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# 5. (TUỲ CHỌN) BOXPLOT THEO HOUSE DIRECTION
# ─────────────────────────────────────────────

def _render_boxplot_direction(df: pd.DataFrame) -> None:
    """
    Boxplot Price_per_m2 theo hướng nhà (House direction).
    Loại bỏ "Không xác định" khỏi phân tích chính,
    nhưng giữ 1 cột riêng để so sánh nếu cần.
    """
    # Tách "Không xác định" thành nhóm riêng để không pha lẫn phân tích hướng thật
    df_known = df[df["House direction"] != "Không xác định"].copy()

    if df_known.empty or df_known["House direction"].nunique() < 2:
        st.info("Không đủ dữ liệu hướng nhà xác định để vẽ boxplot.")
        return

    p99 = df_known["Price_per_m2"].quantile(0.99)
    df_plot = df_known[df_known["Price_per_m2"] <= p99]

    direction_order = sorted(df_plot["House direction"].dropna().unique().tolist())

    fig = px.box(
        df_plot,
        x="House direction",
        y="Price_per_m2",
        color="House direction",
        color_discrete_sequence=COLOR_SEQUENCE,
        category_orders={"House direction": direction_order},
        labels={
            "Price_per_m2": "Giá/m² (tỷ)",
            "House direction": "Hướng nhà",
        },
        points="outliers",
    )
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Giá/m²: %{y:.4f} tỷ<extra></extra>"
    )
    apply_theme(fig, 'Giá/m² theo hướng nhà (loại trừ "Không xác định")')
    fig.update_layout(
        height=380,
        showlegend=False,
        xaxis=dict(tickangle=30),
    )
    st.plotly_chart(fig, width='stretch', key="pd_box_direction")

    # Hiển thị số lượng "Không xác định" để người dùng nắm bối cảnh
    n_unknown = (df["House direction"] == "Không xác định").sum()
    st.caption(
        f"ℹ️ Biểu đồ loại trừ {n_unknown:,} tin đăng có hướng nhà 'Không xác định' "
        f"({n_unknown/len(df)*100:.1f}% tổng dữ liệu lọc hiện tại)."
    )

    medians = df_plot.groupby("House direction", observed=True)["Price_per_m2"].median()
    if not medians.empty:
        top_dir = medians.idxmax()
        st.markdown(
            render_insight(
                f"Nhà hướng <b>{top_dir}</b> có giá/m² trung vị cao nhất "
                f"({medians[top_dir]:.4f} tỷ/m²) trong các hướng xác định."
            ),
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def render(df_filtered: pd.DataFrame) -> None:
    """
    Hàm chính được gọi từ app.py để vẽ toàn bộ nội dung tab Price Drivers.

    Parameters
    ----------
    df_filtered : pd.DataFrame
        DataFrame đã qua apply_filters.
    """
    if df_filtered.empty:
        _empty_state()
        return

    st.markdown("### Yếu tố ảnh hưởng đến giá bất động sản")
    st.markdown(
        "Phân tích tương quan giữa các đặc trưng vật lý và pháp lý với giá/m². "
        "Dữ liệu đã cắt bỏ outlier ở percentile 99 để dễ đọc hơn."
    )
    st.markdown("")

    # ── 1. Scatter Area vs Price ──────────────────────────────────────────────
    _render_scatter_area_price(df_filtered)
    st.markdown("---")

    # ── 2. Correlation heatmap ────────────────────────────────────────────────
    _render_correlation_heatmap(df_filtered)
    st.markdown("---")

    # ── 3. Boxplot theo Legal status & Furniture state (song song 2 cột) ─────
    col_legal, col_furn = st.columns(2)
    with col_legal:
        _render_boxplot_legal(df_filtered)
    with col_furn:
        _render_boxplot_furniture(df_filtered)

    st.markdown("---")

    # ── 4. Boxplot theo House direction (tuỳ chọn — collapsible) ─────────────
    with st.expander("📐 Phân tích theo hướng nhà (tuỳ chọn)", expanded=False):
        _render_boxplot_direction(df_filtered)


# ─────────────────────────────────────────────
# BOOTSTRAP — cho phép file này chạy như native page (Streamlit multipage)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app import APP_TITLE, initialize_state, load_sample_data, render_sidebar

    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    initialize_state()
    _df = load_sample_data()
    _df_filtered = render_sidebar(_df)
    render(_df_filtered)