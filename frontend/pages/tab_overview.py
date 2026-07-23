"""
pages/overview.py — Tab "Executive Overview"
Hiển thị bức tranh tổng quan thị trường bất động sản dựa trên dữ liệu đã lọc.

Thứ tự layout:
  1. KPI row (4 thẻ số)
  2. Bar chart Top 10 Province theo số lượng tin
  3. Histogram phân phối giá + Donut chart Area_Group  (2 cột)
  4. Bar chart Top 10 District theo Price_per_m2 trung bình
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
    """Tính và hiển thị 4 KPI card gọn gàng (chỉ có tiêu đề và số liệu)."""
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
                f"{total_listings:,}"
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            render_kpi_card(
                "Giá trung bình",
                f"{avg_price:.2f} tỷ"
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            render_kpi_card(
                "Giá / m² trung bình",
                f"{avg_price_m2:.3f} tỷ/m²"
            ),
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            render_kpi_card(
                "Số tỉnh / thành",
                f"{num_provinces}"
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

    custom_bluescale = [
        [0.0, "#92BEF0"],  # Đáy bắt đầu bằng xanh dương sáng (Blue 300) thay vì trắng
        [0.5, "#3B82F6"],  # Giữa là xanh tươi
        [1.0, "#163CA5"],  # Đỉnh là xanh đậm hoàng gia
    ]

    fig = px.bar(
        top10,
        x="count",
        y="Province",
        orientation="h",
        color="count",
        color_continuous_scale=custom_bluescale, # <--- Dùng scale mới
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
            color_discrete_sequence=["#1D4ED8"],
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
            annotation_text=f"  TB: {avg:.1f} tỷ",
            annotation_position="top right",
            annotation_font_color=COLORS["accent"],
        )
        fig_hist.add_vline(
            x=med,
            line_dash="dot",
            line_color=COLORS["success"],
            annotation_text=f"TV: {med:.1f} tỷ  ",
            annotation_position="top left",
            annotation_font_color=COLORS["success"],
        )
        apply_theme(fig_hist, "Phân phối giá bất động sản")
        fig_hist.update_yaxes(title_text="Số lượng")
        fig_hist.update_layout(
            height=340, 
            showlegend=False,
            yaxis=dict(range=[0, 1800]) # Kéo dài trục y tối đa lên 1700
        )
        st.plotly_chart(fig_hist, width='stretch', key="overview_price_hist")

        # Insight: so sánh trung bình vs trung vị để phát hiện lệch phân phối
        if avg > med * 1.1:
            st.markdown(
                render_insight(
                    f"Giá trung bình ({avg:.1f} tỷ) cao hơn trung vị ({med:.1f} tỷ) "
                    f"-> phân phối lệch phải, tồn tại nhiều bất động sản giá cao kéo TB lên."
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
        
        # Cấu hình để hiển thị phần trăm (%) ở bên trong và đẩy tên nhãn ra ngoài/legend
        fig_donut.update_traces(
            hovertemplate="<b>%{label}</b><br>%{value:,} tin (%{percent})<extra></extra>",
            textposition="inside",          # Đặt chữ phần trăm nằm bên trong các lát cắt
            textinfo="percent",             # Chỉ hiển thị phần trăm (%) bên trong
            textfont=dict(size=12, color="white"), # Màu chữ trắng cho dễ nhìn trên nền màu
        )
        
        apply_theme(fig_donut, "Tỷ trọng theo nhóm diện tích")
        fig_donut.update_layout(
            height=340,
            showlegend=True,                # Bật chú thích (legend) màu sắc ở phía ngoài
            legend=dict(
                orientation="v",            # Sắp xếp chú thích theo chiều dọc bên phải
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02
            ),
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
# 4. AREA/BAR CHART XU HƯỚNG SỐ TIN & GIÁ THEO THỜI GIAN (DAY)
# ─────────────────────────────────────────────
def _render_area_chart_time_trends(df: pd.DataFrame) -> None:
    """
    Biểu đồ kết hợp Bar (Số lượng tin đăng) + Line (Giá trung bình)
    thể hiện xu hướng theo từng ngày trong tháng (Day).
    """
    if "Day" not in df.columns:
        st.info("Không có dữ liệu thời gian (`Day`) trong bộ dữ liệu.")
        return

    # Thống kê theo ngày
    time_stats = (
        df.groupby("Day", observed=True)
        .agg(
            count=("Price", "count"),
            avg_price=("Price", "mean"),
        )
        .reset_index()
        .sort_values("Day")
    )

    if time_stats.empty:
        st.warning("Không đủ dữ liệu thời gian để hiển thị biểu đồ.")
        return

    # Tạo biểu đồ kết hợp: Bar (số tin) + Line (giá trung bình)
    fig = go.Figure()

    # Cột: Số lượng tin đăng (trục trái)
    fig.add_trace(
        go.Bar(
            x=time_stats["Day"],
            y=time_stats["count"],
            name="Số lượng tin đăng",
            marker=dict(color="#1D4ED8", opacity=1),
            yaxis="y1",
            hovertemplate="Ngày %{x}<br>Số tin: %{y:,}<extra></extra>",
        )
    )

    # Đường: Giá trung bình (trục phải) — không fill để tránh chồng màu
    fig.add_trace(
        go.Scatter(
            x=time_stats["Day"],
            y=time_stats["avg_price"],
            name="Giá trung bình (tỷ)",
            mode="lines+markers",
            line=dict(color=COLORS["accent"], width=3, shape="spline"),
            marker=dict(size=6),
            yaxis="y2",
            hovertemplate="Ngày %{x}<br>Giá TB: %{y:.2f} tỷ<extra></extra>",
        )
    )

    # Cấu hình 2 trục tung (dual axes) để hiển thị song song Số lượng và Giá
    apply_theme(fig, "Xu hướng Số lượng Tin đăng & Giá trung bình theo Ngày")
    fig.update_layout(
        height=400,
        xaxis=dict(title="Ngày trong tháng"),
        yaxis=dict(
            title=dict(text="Số lượng tin đăng", font=dict(color=COLORS["primary"])),
            tickfont=dict(color=COLORS["primary"]),
            side="left",
        ),
        yaxis2=dict(
            title=dict(text="Giá trung bình (tỷ VNĐ)", font=dict(color=COLORS["accent"])),
            tickfont=dict(color=COLORS["accent"]),
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(
            orientation="h",      # hoặc bỏ dòng này, mặc định là dọc
            yanchor="top",
            y=1.1,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.7)",  # tùy chọn
            bordercolor="rgba(0,0,0,0.1)",    # tùy chọn
            borderwidth=1,
        ),
        hovermode="x unified",
        bargap=0.2,
    )

    st.plotly_chart(fig, width="stretch", key="overview_area_chart_time")

    # Insight tự động
    if not time_stats.empty:
        peak_count = time_stats.loc[time_stats["count"].idxmax()]
        peak_price = time_stats.loc[time_stats["avg_price"].idxmax()]
        st.markdown(
            render_insight(
                f"Thị trường đạt đỉnh nguồn cung vào <b>Ngày {int(peak_count['Day'])}</b> ({int(peak_count['count']):,} tin), "
                f"trong khi mức giá trung bình cao nhất ghi nhận vào <b>Ngày {int(peak_price['Day'])}</b> ({peak_price['avg_price']:.2f} tỷ)."
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
    st.markdown("")

    # Hiển thị các thành phần theo thứ tự
    _render_kpi_row(df_filtered)
    st.markdown("---")
    _render_area_chart_time_trends(df_filtered)
    st.markdown("---")
    _render_top_province_bar(df_filtered)
    st.markdown("---")
    _render_price_hist_and_donut(df_filtered)
    



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