"""
pages/overview.py — Tab "Executive Overview"
Hiển thị bức tranh tổng quan thị trường bất động sản dựa trên dữ liệu đã lọc.

Thứ tự layout:
  1. KPI row (4 thẻ số)
  2. Bar chart Top 10 Province theo số lượng tin
  3. Histogram phân phối giá + Donut chart Area_Group  (2 cột)
  4. Bar chart Top 10 Ward theo Price_per_m2 trung bình
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from theme import (
    COLORS,
    COLOR_SEQUENCE,
    CONTINUOUS_SCALE,
    KPI_CARD_CSS,
    apply_theme,
    render_kpi_card,
    render_insight,
)


def _empty_state() -> None:
    """Hiển thị thông báo khi DataFrame trống sau khi lọc."""
    st.warning(
        "⚠️ Không có dữ liệu phù hợp với bộ lọc hiện tại. "
        "Hãy mở rộng điều kiện lọc trên sidebar.",
        icon="🔍",
    )


# ─────────────────────────────────────────────
# 1. KPI CARDS
# ─────────────────────────────────────────────

def _render_kpi_row(df: pd.DataFrame) -> None:
    """Tính và hiển thị 4 KPI card theo dữ liệu đã lọc."""
    total_listings = len(df)
    avg_price = df["Price"].mean()
    median_price = df["Price"].median()
    avg_price_m2 = df["Price_per_m2"].mean()
    num_provinces = df["Province"].nunique()

    # Inject CSS 1 lần
    st.markdown(KPI_CARD_CSS, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            render_kpi_card(
                "Tổng số tin đăng",
                f"{total_listings:,}",
                sub="bất động sản"
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            render_kpi_card(
                "Giá trung bình",
                f"{avg_price:.2f} tỷ",
                sub=f"Trung vị: {median_price:.2f} tỷ",
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            render_kpi_card(
                "Giá / m² trung bình",
                f"{avg_price_m2:.3f} tỷ/m²",
                sub=f"≈ {avg_price_m2 * 1000:.0f} triệu/m²",
            ),
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            render_kpi_card(
                "Số tỉnh / thành",
                f"{num_provinces}",
                sub="tỉnh có dữ liệu"
            ),
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# 2. BAR CHART TOP 10 PROVINCE
# ─────────────────────────────────────────────

def _render_top_province_bar(df: pd.DataFrame) -> None:
    """
    Bar chart ngang Top 10 Province theo số lượng tin đăng.
    Click vào bar → cập nhật filter Province trong session_state → rerun.
    """
    top10 = (
        df.groupby("Province", observed=True)
        .size()
        .reset_index(name="count")
        .nlargest(10, "count")
        .sort_values("count")  # Sắp xếp tăng dần để bar ngang dễ đọc
    )

    fig = px.bar(
        top10,
        x="count",
        y="Province",
        orientation="h",
        color="count",
        color_continuous_scale=CONTINUOUS_SCALE,
        labels={"count": "Số tin đăng", "Province": "Tỉnh / Thành phố"},
        hover_data={"count": ":,"},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Số tin: %{x:,}<extra></extra>",
        marker_line_width=0,
    )
    apply_theme(fig, "Top 10 Tỉnh/Thành theo số lượng tin đăng")
    fig.update_layout(height=380, yaxis_title="")

    # Dùng on_select để bắt click → drill-down filter Province
    event = st.plotly_chart(
        fig,
        width='stretch',
        on_select="rerun",
        key="overview_province_bar",
    )

    # Xử lý click: lấy tên tỉnh từ điểm được chọn và cập nhật filter
    if event and event.get("selection") and event["selection"].get("points"):
        clicked_province = event["selection"]["points"][0].get("y")
        if clicked_province:
            st.session_state["filters"]["province"] = [clicked_province]
            st.session_state["filters"]["district"] = []  # Reset huyện khi đổi tỉnh
            st.rerun()

    # Insight tự động tính bằng pandas
    if not top10.empty:
        top_prov = top10.iloc[-1]   # Hàng cuối (nhiều nhất vì đã sort tăng dần)
        pct = top_prov["count"] / len(df) * 100
        st.markdown(
            render_insight(
                f"<b>{top_prov['Province']}</b> dẫn đầu với "
                f"{top_prov['count']:,} tin ({pct:.1f}% tổng số liệu đang hiển thị)."
            ),
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# 3. HISTOGRAM GIÁ + DONUT AREA_GROUP
# ─────────────────────────────────────────────

def _render_price_hist_and_donut(df: pd.DataFrame) -> None:
    """Histogram phân phối Price và Donut tỷ trọng Area_Group song song."""
    col_hist, col_donut = st.columns([3, 2])

    # ── Histogram phân phối giá ───────────────────────────────────────────
    with col_hist:
        # Giới hạn trục x ở percentile 99 để tránh outlier cực cao kéo dài biểu đồ
        p99 = df["Price"].quantile(0.99)
        df_hist = df[df["Price"] <= p99]

        fig_hist = px.histogram(
            df_hist,
            x="Price",
            nbins=50,
            color_discrete_sequence=[COLORS["primary_light"]],
            labels={"Price": "Giá (tỷ VNĐ)", "count": "Số lượng"},
        )
        fig_hist.update_traces(
            hovertemplate="Giá: %{x:.1f} tỷ<br>Số tin: %{y:,}<extra></extra>",
            marker_line_width=0.3,
            marker_line_color="white",
        )
        # Thêm đường trung bình và trung vị
        avg = df["Price"].mean()
        med = df["Price"].median()
        fig_hist.add_vline(
            x=avg,
            line_dash="dash",
            line_color=COLORS["accent"],
            annotation_text=f"TB: {avg:.1f} tỷ",
            annotation_position="top right",
            annotation_font_color=COLORS["accent"],
        )
        fig_hist.add_vline(
            x=med,
            line_dash="dot",
            line_color=COLORS["success"],
            annotation_text=f"TV: {med:.1f} tỷ",
            annotation_position="top left",
            annotation_font_color=COLORS["success"],
        )
        apply_theme(fig_hist, "Phân phối giá bất động sản")
        fig_hist.update_layout(height=340, showlegend=False)
        st.plotly_chart(fig_hist, width='stretch', key="overview_price_hist")

        # Insight: so sánh trung bình vs trung vị để phát hiện lệch phân phối
        if avg > med * 1.1:
            st.markdown(
                render_insight(
                    f"Giá trung bình ({avg:.1f} tỷ) cao hơn trung vị ({med:.1f} tỷ) "
                    f"→ phân phối lệch phải, tồn tại nhiều bất động sản giá cao kéo TB lên."
                ),
                unsafe_allow_html=True,
            )

    # ── Donut chart tỷ trọng Area_Group ──────────────────────────────────
    with col_donut:
        area_counts = (
            df.groupby("Area_Group", observed=True)
            .size()
            .reset_index(name="count")
        )
        fig_donut = px.pie(
            area_counts,
            names="Area_Group",
            values="count",
            hole=0.55,
            color_discrete_sequence=COLOR_SEQUENCE,
        )
        fig_donut.update_traces(
            hovertemplate="<b>%{label}</b><br>%{value:,} tin (%{percent})<extra></extra>",
            textposition="outside",
            textinfo="percent+label",
        )
        apply_theme(fig_donut, "Tỷ trọng theo nhóm diện tích")
        fig_donut.update_layout(
            height=340,
            showlegend=False,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_donut, width='stretch', key="overview_area_donut")

        # Insight: nhóm diện tích chiếm tỷ trọng cao nhất
        if not area_counts.empty:
            top_group = area_counts.loc[area_counts["count"].idxmax()]
            pct = top_group["count"] / area_counts["count"].sum() * 100
            st.markdown(
                render_insight(
                    f"Nhóm <b>{top_group['Area_Group']}</b> chiếm tỷ lệ cao nhất "
                    f"({pct:.1f}% tổng tin đăng)."
                ),
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────
# 4. BAR CHART TOP 10 WARD THEO GIÁ/M²
# ─────────────────────────────────────────────

def _render_top_ward_bar(df: pd.DataFrame) -> None:
    """
    Bar chart Top 10 Ward theo giá/m² trung bình.
    Tạm thay thế "Top Project" (chưa có cột Project trong dữ liệu).
    """
    # Lọc các ward có ít nhất 5 tin để tránh ward 1–2 tin cho kết quả sai lệch
    ward_stats = (
        df.groupby(["Ward", "Province"], observed=True)
        .agg(
            avg_price_m2=("Price_per_m2", "mean"),
            count=("Price", "count"),
            avg_price=("Price", "mean"),
        )
        .reset_index()
    )
    ward_stats = ward_stats[ward_stats["count"] >= 5]
    top10_ward = ward_stats.nlargest(10, "avg_price_m2").sort_values("avg_price_m2")

    fig = px.bar(
        top10_ward,
        x="avg_price_m2",
        y="Ward",
        orientation="h",
        color="avg_price_m2",
        color_continuous_scale=CONTINUOUS_SCALE,
        hover_data={
            "Province": True,
            "count": ":,",
            "avg_price": ":.2f",
            "avg_price_m2": ":.4f",
        },
        labels={
            "avg_price_m2": "Giá/m² TB (tỷ)",
            "Ward": "Phường / Xã",
            "count": "Số tin",
            "avg_price": "Giá TB (tỷ)",
        },
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b> (%{customdata[0]})<br>"
            "Giá/m² TB: %{x:.4f} tỷ<br>"
            "Giá TB: %{customdata[2]:.2f} tỷ<br>"
            "Số tin: %{customdata[1]:,}<extra></extra>"
        ),
        marker_line_width=0,
    )
    apply_theme(fig, "Top 10 Phường/Xã theo giá/m² trung bình")
    fig.update_layout(height=380, yaxis_title="", coloraxis_showscale=False)

    st.plotly_chart(fig, width='stretch', key="overview_ward_bar")

    # Ghi chú về trạng thái tạm thời
    st.caption(
        "📌 Sẽ thay bằng **Top Project** khi có cột `Project` trong dữ liệu. "
        "Hiện dùng Top Ward (≥5 tin) làm proxy."
    )

    if not top10_ward.empty:
        top_ward = top10_ward.iloc[-1]
        st.markdown(
            render_insight(
                f"<b>{top_ward['Ward']}</b> ({top_ward['Province']}) có giá/m² "
                f"trung bình cao nhất: {top_ward['avg_price_m2']:.4f} tỷ/m² "
                f"≈ {top_ward['avg_price_m2'] * 1000:.0f} triệu/m²."
            ),
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def render(df_filtered: pd.DataFrame) -> None:
    """
    Hàm chính được gọi từ app.py để vẽ toàn bộ nội dung tab Executive Overview.

    Parameters
    ----------
    df_filtered : pd.DataFrame
        DataFrame đã qua apply_filters từ filters.py.
    """
    if df_filtered.empty:
        _empty_state()
        return

    st.markdown("### Tổng quan thị trường bất động sản")
    st.markdown(
        "Dữ liệu hiển thị theo bộ lọc hiện tại. "
        "Click vào tên tỉnh trên biểu đồ để drill-down."
    )
    st.markdown("")

    # Hiển thị các thành phần theo thứ tự
    _render_kpi_row(df_filtered)
    st.markdown("---")
    _render_top_province_bar(df_filtered)
    st.markdown("---")
    _render_price_hist_and_donut(df_filtered)
    st.markdown("---")
    _render_top_ward_bar(df_filtered)


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