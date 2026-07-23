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


import json
from pathlib import Path


@st.cache_data
def _load_vietnam_geojson() -> dict:
    """Đọc file GeoJSON ranh giới các tỉnh thành Việt Nam."""
    geojson_path = Path(__file__).resolve().parent.parent / "assets" / "vietnam_provinces.geojson"
    with open(geojson_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# 1. CHOROPLETH MAP VIỆT NAM THEO GIÁ/M²
# ─────────────────────────────────────────────

def render_province_price_overview(df: pd.DataFrame) -> str | None:
    """
    Vẽ bản đồ Choropleth Map và biểu đồ Top 15 Tỉnh/Thành phố theo Price_per_m2 trung bình.
    Hiển thị song song (side-by-side) trên 2 cột.

    Trả về tên tỉnh được click (trên bản đồ hoặc trên biểu đồ cột) để hỗ trợ drill-down.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    str | None
        Tên tỉnh được click để drill-down, hoặc None.
    """
    # Lọc bỏ các bản ghi không có thông tin tỉnh hoặc tỉnh không xác định
    df_valid = df[
        df["Province"].notna() & (df["Province"] != "Không xác định")
    ]

    prov_stats = (
        df_valid.groupby("Province", observed=True)
        .agg(
            avg_price_m2=("Price_per_m2", "mean"),
            avg_price=("Price", "mean"),
            count=("Price", "count"),
        )
        .reset_index()
    )

    if prov_stats.empty:
        st.info("Không có dữ liệu địa lý phù hợp để hiển thị bản đồ.")
        return None

    prov_stats["price_m2_million"] = prov_stats["avg_price_m2"] * 1000
    national_avg = df_valid["Price_per_m2"].mean() if not df_valid.empty else 0.0

    col_map, col_bar = st.columns([7, 5])
    clicked_province = None

    # ── 1. Choropleth Map (Bên trái) ──────────────────────────────────────────
    with col_map:
        geojson_data = _load_vietnam_geojson()
        try:
            fig_map = px.choropleth_map(
                prov_stats,
                geojson=geojson_data,
                locations="Province",
                featureidkey="properties.name",
                color="avg_price_m2",
                color_continuous_scale=CONTINUOUS_SCALE,
                center={"lat": 16.0, "lon": 106.0},
                zoom=4.5,
                map_style="carto-positron",
                labels={
                    "avg_price_m2": "Giá/m² TB (tỷ)",
                    "Province": "Tỉnh / Thành phố",
                    "avg_price": "Giá TB (tỷ)",
                    "count": "Số tin đăng",
                },
                hover_data={
                    "count": ":,",
                    "avg_price": ":.2f",
                    "avg_price_m2": ":.4f",
                    "price_m2_million": ":.1f",
                },
            )
        except AttributeError:
            # Fallback cho phiên bản Plotly cũ không có choropleth_map
            fig_map = px.choropleth_mapbox(
                prov_stats,
                geojson=geojson_data,
                locations="Province",
                featureidkey="properties.name",
                color="avg_price_m2",
                color_continuous_scale=CONTINUOUS_SCALE,
                center={"lat": 16.0, "lon": 106.0},
                zoom=4.5,
                mapbox_style="carto-positron",
                labels={
                    "avg_price_m2": "Giá/m² TB (tỷ)",
                    "Province": "Tỉnh / Thành phố",
                    "avg_price": "Giá TB (tỷ)",
                    "count": "Số tin đăng",
                },
                hover_data={
                    "count": ":,",
                    "avg_price": ":.2f",
                    "avg_price_m2": ":.4f",
                    "price_m2_million": ":.1f",
                },
            )

        fig_map.update_traces(
            hovertemplate=(
                "<b>%{location}</b><br>"
                "Giá/m² TB: %{z:.4f} tỷ (%{customdata[3]:.1f} triệu/m²)<br>"
                "Giá TB: %{customdata[1]:.2f} tỷ<br>"
                "Số tin: %{customdata[0]:,}<extra></extra>"
            ),
            marker_line_width=0.8,
            marker_line_color="#CBD5E1",
        )

        fig_map.update_coloraxes(
            colorbar_title_text="Giá/m² (tỷ)",
            colorbar_tickformat=".3f",
            colorbar_outlinewidth=0,
        )

        apply_theme(fig_map, "Bản đồ Choropleth: Giá/m² theo Tỉnh/Thành phố")
        fig_map.update_layout(
            height=540,
            margin=dict(l=10, r=10, t=45, b=10),
        )

        event_map = st.plotly_chart(
            fig_map,
            width="stretch",
            on_select="rerun",
            key="geo_province_map",
        )

        if event_map and event_map.get("selection") and event_map["selection"].get("points"):
            points = event_map["selection"]["points"]
            if points:
                pt = points[0]
                loc = pt.get("location")
                if loc:
                    clicked_province = loc
                else:
                    point_idx = pt.get("pointIndex")
                    if point_idx is not None and point_idx < len(prov_stats):
                        clicked_province = prov_stats.iloc[point_idx]["Province"]

    # ── 2. Top 15 Province Bar Chart theo Số tin đăng (Bên phải) ──────────────
    with col_bar:
        top15_prov = prov_stats.nlargest(15, "count").sort_values("count")
        fig_bar = px.bar(
            top15_prov,
            x="count",
            y="Province",
            orientation="h",
            color="count",
            color_continuous_scale=CONTINUOUS_SCALE,
            labels={
                "count": "Số tin đăng",
                "Province": "Tỉnh / Thành phố",
            },
            hover_data={
                "avg_price_m2": ":.4f",
                "avg_price": ":.2f",
                "price_m2_million": ":.1f",
            },
            text_auto=",",
        )
        fig_bar.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Số tin đăng: %{x:,}<br>"
                "Giá/m² TB: %{customdata[0]:.4f} tỷ (%{customdata[2]:.1f} triệu/m²)<br>"
                "Giá TB: %{customdata[1]:.2f} tỷ<extra></extra>"
            ),
            textposition="outside",
            marker_line_width=0,
        )
        fig_bar.update_coloraxes(showscale=False)
        apply_theme(fig_bar, "Top 15 Tỉnh/Thành phố theo Số tin đăng")
        fig_bar.update_layout(
            height=540,
            margin=dict(l=10, r=30, t=45, b=10),
            yaxis_title="",
            xaxis_title="Số lượng tin đăng",
        )

        event_bar = st.plotly_chart(
            fig_bar,
            width="stretch",
            on_select="rerun",
            key="geo_province_bar",
        )

        if not clicked_province and event_bar and event_bar.get("selection") and event_bar["selection"].get("points"):
            points = event_bar["selection"]["points"]
            if points:
                pt = points[0]
                loc = pt.get("y")
                if loc:
                    clicked_province = loc
                else:
                    point_idx = pt.get("pointIndex")
                    if point_idx is not None and point_idx < len(top15_prov):
                        clicked_province = top15_prov.iloc[point_idx]["Province"]

    st.caption(
        "🗺️ Bản đồ chỉ thể hiện dữ liệu BĐS đất liền, chưa thể hiện dữ liệu trên các đảo, quần đảo thuộc chủ quyền Việt Nam."
    )

    # Insight tự động
    if not prov_stats.empty:
        top_prov = prov_stats.nlargest(1, "avg_price_m2").iloc[0]
        pct_above = ((top_prov["avg_price_m2"] / national_avg) - 1) * 100 if national_avg > 0 else 0
        st.markdown(
            render_insight(
                f"<b>{top_prov['Province']}</b> dẫn đầu toàn quốc về giá/m² trung bình "
                f"({top_prov['avg_price_m2']:.4f} tỷ/m² ≈ {top_prov['price_m2_million']:.0f} triệu/m²), "
                f"cao hơn trung bình toàn quốc {pct_above:.1f}%."
            ),
            unsafe_allow_html=True,
        )

    return clicked_province


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
        st.markdown(f"##### Quận/Huyện tại **{province}** — Giá/m² trung bình")
    with col_back:
        if st.button("← Xem tất cả tỉnh", key="geo_back_btn", type="secondary"):
            st.session_state.pop("geo_selected_province", None)
            # Clear selected points from map and bar widgets to reset selection state
            st.session_state.pop("geo_province_map", None)
            st.session_state.pop("geo_province_bar", None)
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
                outlinewidth=0,
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

def _render_province_summary_table(df: pd.DataFrame) -> None:
    """
    Bảng tổng hợp chi tiết các chỉ số bất động sản theo từng Tỉnh/Thành phố.
    """
    st.markdown("#####  Bảng tổng hợp chỉ số thị trường theo Tỉnh / Thành phố")
    
    summary = (
        df.groupby("Province", observed=True)
        .agg(
            total_listings=("Price", "count"),
            avg_price=("Price", "mean"),
            median_price=("Price", "median"),
            avg_price_m2=("Price_per_m2", "mean"),
            avg_area=("Area", "mean"),
        )
        .reset_index()
        .sort_values(by="total_listings", ascending=False)
    )

    # Đổi tên cột hiển thị tiếng Việt thân thiện
    summary.columns = [
        "Tỉnh / Thành phố", 
        "Số tin đăng", 
        "Giá TB (tỷ)", 
        "Giá trung vị (tỷ)", 
        "Đơn giá TB (tỷ/m²)", 
        "Diện tích TB (m²)"
    ]

    st.dataframe(
        summary.style.format({
            "Số tin đăng": "{:,}",
            "Giá TB (tỷ)": "{:.2f}",
            "Giá trung vị (tỷ)": "{:.2f}",
            "Đơn giá TB (tỷ/m²)": "{:.4f}",
            "Diện tích TB (m²)": "{:.1f}",
        }),
        width="stretch",
        hide_index=True,
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

    st.markdown("### Phân tích thị trường theo địa lý")
    st.markdown(
        "Chọn từng tỉnh/thành phố để xem thêm thông tin về thị trường BĐS ở các quận/huyện của tỉnh/thành đó."
       
    )
    st.markdown("")

    # ── Phần 1: Choropleth Map Việt Nam theo Tỉnh/Thành ─────────────────────
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
    _render_province_summary_table(df_filtered)
    


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