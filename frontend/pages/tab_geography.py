"""
pages/geographic.py — Tab "Geographic Analysis"
Phân tích giá và mật độ tin đăng theo địa lý.

Layout:
  1. Bar chart Top 15 Province theo Price_per_m2 (thay choropleth — sẽ bổ sung sau)
  2. Drill-down: Top 10 District của tỉnh được chọn (hiện khi click)
  3. Heatmap ma trận Province × Area_Group

Thiết kế để dễ swap: hàm render_province_price_overview() tách riêng,
sau này chỉ cần thay bằng bản choropleth mà không sửa phần drill-down.
"""

import pandas as pd
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


def _empty_state() -> None:
    st.warning(
        "⚠️ Không có dữ liệu phù hợp với bộ lọc hiện tại. "
        "Hãy mở rộng điều kiện lọc trên sidebar.",
        icon="🔍",
    )


# ─────────────────────────────────────────────
# 1. BAR CHART TOP 15 PROVINCE THEO GIÁ/M²
#    (Có thể swap thành choropleth sau này bằng cách thay hàm này)
# ─────────────────────────────────────────────

def render_province_price_overview(df: pd.DataFrame) -> str | None:
    """
    Vẽ Bar chart ngang Top 15 Province theo Price_per_m2 trung bình.
    Dùng color_continuous_scale để giữ cảm giác "heat" dù không phải bản đồ thật.

    Trả về tên tỉnh được click (hoặc None nếu chưa click).
    Hàm này được tách riêng để sau này chỉ cần swap thành bản choropleth
    mà không phải sửa phần drill-down District bên dưới.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    str | None
        Tên tỉnh được click để drill-down, hoặc None.
    """
    # Tổng hợp thống kê theo tỉnh
    prov_stats = (
        df.groupby("Province", observed=True)
        .agg(
            avg_price_m2=("Price_per_m2", "mean"),
            avg_price=("Price", "mean"),
            count=("Price", "count"),
        )
        .reset_index()
    )
    # Lấy top 15 theo giá/m² trung bình
    top15 = prov_stats.nlargest(15, "avg_price_m2").sort_values("avg_price_m2")

    # Tính trung bình toàn quốc (trên dữ liệu đã lọc) để vẽ đường tham chiếu
    national_avg = df["Price_per_m2"].mean()

    fig = px.bar(
        top15,
        x="avg_price_m2",
        y="Province",
        orientation="h",
        color="avg_price_m2",
        color_continuous_scale=CONTINUOUS_SCALE,
        labels={
            "avg_price_m2": "Giá/m² TB (tỷ)",
            "Province": "Tỉnh / Thành phố",
            "avg_price": "Giá TB (tỷ)",
            "count": "Số tin",
        },
        hover_data={"count": ":,", "avg_price": ":.2f", "avg_price_m2": ":.4f"},
    )

    # Đường kẻ trung bình toàn quốc để so sánh trực quan
    fig.add_vline(
        x=national_avg,
        line_dash="dash",
        line_color=COLORS["accent"],
        annotation_text=f"TB: {national_avg:.4f} tỷ/m²",
        annotation_position="top right",
        annotation_font_color=COLORS["accent"],
        annotation_font_size=11,
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Giá/m² TB: %{x:.4f} tỷ (%{x:.0f} triệu/m²)<br>"
            "Giá TB: %{customdata[1]:.2f} tỷ<br>"
            "Số tin: %{customdata[0]:,}<extra></extra>"
        ),
        marker_line_width=0,
    )
    fig.update_coloraxes(showscale=False)
    apply_theme(fig, "Top 15 Tỉnh/Thành theo giá/m² trung bình")
    fig.update_layout(height=500, yaxis_title="")

    # Bắt sự kiện click để drill-down xuống huyện
    event = st.plotly_chart(
        fig,
        width='stretch',
        on_select="rerun",
        key="geo_province_bar",
    )

    # Chú thích tạm thời (sẽ thay bản đồ sau)
    st.caption(
        "🗺️ Sẽ thay bằng **bản đồ choropleth** khi có file GeoJSON ranh giới tỉnh "
        "(`frontend/assets/vietnam_provinces.geojson`). "
        "Click vào thanh để xem chi tiết theo quận/huyện."
    )

    # Insight tự động
    if not top15.empty:
        top_prov = top15.iloc[-1]
        pct_above = (top_prov["avg_price_m2"] / national_avg - 1) * 100
        st.markdown(
            render_insight(
                f"<b>{top_prov['Province']}</b> có giá/m² trung bình cao nhất "
                f"({top_prov['avg_price_m2']:.4f} tỷ/m²), "
                f"cao hơn trung bình {pct_above:.1f}% so với toàn bộ dữ liệu đang lọc."
            ),
            unsafe_allow_html=True,
        )

    # Trả về tên tỉnh được click (nếu có)
    if event and event.get("selection") and event["selection"].get("points"):
        return event["selection"]["points"][0].get("y")
    return None


# ─────────────────────────────────────────────
# 2. DRILL-DOWN: TOP 10 DISTRICT CỦA TỈNH ĐÃ CHỌN
# ─────────────────────────────────────────────

def _render_district_drilldown(df: pd.DataFrame, province: str) -> None:
    """
    Hiển thị Top 10 District của tỉnh được chọn theo giá/m² trung bình.
    Có nút quay lại "Xem tất cả tỉnh".

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame gốc đã lọc (để tính thống kê theo huyện).
    province : str
        Tên tỉnh vừa được click trên bar chart.
    """
    col_title, col_back = st.columns([4, 1])
    with col_title:
        st.markdown(f"#### 📍 Quận/Huyện tại **{province}** — Giá/m² trung bình")
    with col_back:
        if st.button("← Xem tất cả tỉnh", key="geo_back_btn", type="secondary"):
            st.session_state.pop("geo_selected_province", None)
            st.rerun()

    # Lọc chỉ lấy huyện của tỉnh này
    df_prov = df[df["Province"] == province]
    if df_prov.empty:
        st.info(f"Không có dữ liệu cho {province} trong bộ lọc hiện tại.")
        return

    district_stats = (
        df_prov.groupby("District", observed=True)
        .agg(
            avg_price_m2=("Price_per_m2", "mean"),
            avg_price=("Price", "mean"),
            count=("Price", "count"),
        )
        .reset_index()
    )
    top10_dist = district_stats.nlargest(10, "avg_price_m2").sort_values("avg_price_m2")

    fig = px.bar(
        top10_dist,
        x="avg_price_m2",
        y="District",
        orientation="h",
        color="avg_price_m2",
        color_continuous_scale=CONTINUOUS_SCALE,
        labels={
            "avg_price_m2": "Giá/m² TB (tỷ)",
            "District": "Quận / Huyện",
        },
        hover_data={"count": ":,", "avg_price": ":.2f"},
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Giá/m² TB: %{x:.4f} tỷ<br>"
            "Giá TB: %{customdata[1]:.2f} tỷ<br>"
            "Số tin: %{customdata[0]:,}<extra></extra>"
        ),
        marker_line_width=0,
    )
    fig.update_coloraxes(showscale=False)
    apply_theme(fig, f"Top 10 Quận/Huyện tại {province}")
    fig.update_layout(height=380, yaxis_title="")
    st.plotly_chart(fig, width='stretch', key="geo_district_bar")

    if not top10_dist.empty:
        top_dist = top10_dist.iloc[-1]
        prov_avg = df_prov["Price_per_m2"].mean()
        pct = (top_dist["avg_price_m2"] / prov_avg - 1) * 100
        st.markdown(
            render_insight(
                f"<b>{top_dist['District']}</b> dẫn đầu tại {province} với giá/m² "
                f"{top_dist['avg_price_m2']:.4f} tỷ — cao hơn trung bình tỉnh {pct:.1f}%."
            ),
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# 3. HEATMAP PROVINCE × AREA_GROUP
# ─────────────────────────────────────────────

def _render_province_area_heatmap(df: pd.DataFrame) -> None:
    """
    Heatmap ma trận: Top 15 Province (theo số tin) × Area_Group.
    Giá trị ô = Price_per_m2 trung bình.
    Giúp thấy phân khúc diện tích nào ở tỉnh nào đắt nhất.
    """
    area_order = ["<30 m²", "30-50 m²", "50-70 m²", "70-90 m²", ">90 m²"]

    # Lấy top 15 tỉnh theo số tin đăng
    top15_prov = (
        df.groupby("Province", observed=True)
        .size()
        .nlargest(15)
        .index.tolist()
    )
    df_sub = df[df["Province"].isin(top15_prov)]

    # Pivot table: rows=Province, cols=Area_Group, values=Price_per_m2 trung bình
    pivot = (
        df_sub.groupby(["Province", "Area_Group"], observed=True)["Price_per_m2"]
        .mean()
        .reset_index()
        .pivot(index="Province", columns="Area_Group", values="Price_per_m2")
    )

    # Sắp xếp columns theo đúng thứ tự nhóm diện tích
    cols_present = [c for c in area_order if c in pivot.columns]
    pivot = pivot[cols_present]

    # Sắp xếp rows theo tổng giá/m² giảm dần để tỉnh đắt nhất ở trên
    pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=False).index]

    # Tạo hover text chi tiết
    hover_text = []
    for prov in pivot.index:
        row_texts = []
        for ag in cols_present:
            val = pivot.loc[prov, ag]
            if pd.notna(val):
                row_texts.append(
                    f"<b>{prov}</b><br>Diện tích: {ag}<br>Giá/m² TB: {val:.4f} tỷ"
                )
            else:
                row_texts.append(f"<b>{prov}</b><br>{ag}: không có dữ liệu")
        hover_text.append(row_texts)

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=cols_present,
            y=pivot.index.tolist(),
            colorscale=CONTINUOUS_SCALE,
            hoverinfo="text",
            text=hover_text,
            hovertemplate="%{text}<extra></extra>",
            colorbar=dict(
                title=dict(text="Giá/m² (tỷ)"),
                tickformat=".4f",
            ),
        )
    )
    apply_theme(fig, "Giá/m² trung bình: Tỉnh × Nhóm diện tích (Top 15 tỉnh)")
    fig.update_layout(
        height=500,
        xaxis=dict(title="Nhóm diện tích", tickangle=0),
        yaxis=dict(title="Tỉnh / Thành phố"),
    )
    st.plotly_chart(fig, width='stretch', key="geo_heatmap")

    # Insight: tìm ô đắt nhất trên toàn bảng
    max_val = pivot.max().max()
    max_loc = pivot.stack().idxmax()
    st.markdown(
        render_insight(
            f"Ô đắt nhất: <b>{max_loc[0]}</b> — nhóm <b>{max_loc[1]}</b> "
            f"với giá/m² trung bình {max_val:.4f} tỷ "
            f"≈ {max_val * 1000:.0f} triệu/m²."
        ),
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def render(df_filtered: pd.DataFrame) -> None:
    """
    Hàm chính được gọi từ app.py để vẽ toàn bộ nội dung tab Geographic Analysis.

    Parameters
    ----------
    df_filtered : pd.DataFrame
        DataFrame đã qua apply_filters.
    """
    if df_filtered.empty:
        _empty_state()
        return

    st.markdown("### 🗺️ Phân tích địa lý — Giá và mật độ tin đăng theo tỉnh/thành")
    st.markdown(
        "Click vào thanh bar để xem chi tiết quận/huyện (drill-down). "
        "Heatmap bên dưới cho thấy phân khúc diện tích nào ở tỉnh nào đắt nhất."
    )
    st.markdown("")

    # ── Phần 1: Bar chart Top 15 Province (có thể swap thành choropleth sau) ──
    clicked_province = render_province_price_overview(df_filtered)

    # Cập nhật session_state nếu có click mới
    if clicked_province:
        st.session_state["geo_selected_province"] = clicked_province

    st.markdown("---")

    # ── Phần 2: Drill-down theo huyện (hiện khi đã chọn tỉnh) ───────────────
    selected_prov = st.session_state.get("geo_selected_province")
    if selected_prov:
        _render_district_drilldown(df_filtered, selected_prov)
        st.markdown("---")

    # ── Phần 3: Heatmap Province × Area_Group ────────────────────────────────
    _render_province_area_heatmap(df_filtered)


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