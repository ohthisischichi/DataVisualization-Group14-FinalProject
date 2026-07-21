"""Tab "Market Segmentation".

Phân tích cơ cấu nguồn cung theo phân khúc giá, diện tích, pháp lý và nội thất.
Hàm ``render`` nhận DataFrame đã qua bộ lọc chung của dashboard.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from data_loader import AREA_GROUP_ORDER, PRICE_SEGMENT_ORDER
from theme import COLOR_SEQUENCE, COLORS, apply_theme, render_insight


REQUIRED_COLUMNS = {
    "Area_Group", "Price_Segment", "Legal status", "Furniture state",
    "Price_per_m2", "Area", "Price",
}


def _empty_state(message: str | None = None) -> None:
    st.warning(
        message or "⚠️ Không có dữ liệu phù hợp với bộ lọc hiện tại. Hãy mở rộng điều kiện lọc.",
        icon="🔍",
    )


def _clean_categories(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Loại các hàng thiếu nhãn cho biểu đồ phân khúc."""
    return df.dropna(subset=columns).copy()


def _render_area_segment_distribution(df: pd.DataFrame) -> None:
    plot_df = _clean_categories(df, ["Area_Group", "Price_Segment"])
    summary = (
        plot_df.groupby(["Area_Group", "Price_Segment"], observed=False)
        .size()
        .reset_index(name="Số tin")
    )
    summary = summary[summary["Số tin"] > 0]

    fig = px.bar(
        summary,
        x="Area_Group",
        y="Số tin",
        color="Price_Segment",
        barmode="stack",
        category_orders={"Area_Group": AREA_GROUP_ORDER, "Price_Segment": PRICE_SEGMENT_ORDER},
        color_discrete_sequence=COLOR_SEQUENCE,
        labels={"Area_Group": "Nhóm diện tích", "Price_Segment": "Phân khúc giá"},
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:,} tin<extra></extra>")
    apply_theme(fig, "Phân phối phân khúc giá theo nhóm diện tích")
    fig.update_layout(height=390, legend_title_text="Phân khúc giá")
    st.plotly_chart(fig, width="stretch", key="seg_area_price_stack")

    dominant = summary.loc[summary.groupby("Area_Group", observed=True)["Số tin"].idxmax()]
    dominant_text = "; ".join(
        f"<b>{row['Area_Group']}</b>: {row['Price_Segment']}" for _, row in dominant.iterrows()
    )
    st.markdown(render_insight(f"Phân khúc chiếm ưu thế theo diện tích — {dominant_text}."), unsafe_allow_html=True)


def _render_price_segment_pie(df: pd.DataFrame) -> None:
    summary = (
        _clean_categories(df, ["Price_Segment"])
        .groupby("Price_Segment", observed=False)
        .size()
        .reset_index(name="Số tin")
    )
    summary = summary[summary["Số tin"] > 0]

    fig = px.pie(
        summary,
        names="Price_Segment",
        values="Số tin",
        hole=0.55,
        color_discrete_sequence=COLOR_SEQUENCE,
        category_orders={"Price_Segment": PRICE_SEGMENT_ORDER},
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>%{value:,} tin (%{percent})<extra></extra>",
        textposition="outside",
        textinfo="percent+label",
    )
    apply_theme(fig, "Tỷ trọng thị trường theo phân khúc giá")
    fig.update_layout(height=390, showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch", key="seg_price_donut")


def _render_legal_segment_bar(df: pd.DataFrame) -> None:
    summary = (
        _clean_categories(df, ["Legal status", "Price_Segment"])
        .groupby(["Legal status", "Price_Segment"], observed=True)
        .size()
        .reset_index(name="Số tin")
    )
    legal_order = summary.groupby("Legal status", observed=True)["Số tin"].sum().sort_values(ascending=False).index.tolist()

    fig = px.bar(
        summary,
        x="Legal status",
        y="Số tin",
        color="Price_Segment",
        barmode="group",
        category_orders={"Legal status": legal_order, "Price_Segment": PRICE_SEGMENT_ORDER},
        color_discrete_sequence=COLOR_SEQUENCE,
        labels={"Legal status": "Tình trạng pháp lý", "Price_Segment": "Phân khúc giá"},
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:,} tin<extra></extra>")
    apply_theme(fig, "Pháp lý × phân khúc giá")
    fig.update_layout(height=390, legend_title_text="Phân khúc giá", xaxis_tickangle=-20)
    st.plotly_chart(fig, width="stretch", key="seg_legal_price_bar")


def _render_furniture_price_bar(df: pd.DataFrame) -> None:
    plot_df = _clean_categories(df, ["Furniture state", "Price_per_m2"])
    summary = (
        plot_df.groupby("Furniture state", observed=True)["Price_per_m2"]
        .mean()
        .reset_index(name="Giá TB/m²")
        .sort_values("Giá TB/m²", ascending=False)
    )
    fig = px.bar(
        summary,
        x="Furniture state",
        y="Giá TB/m²",
        color="Furniture state",
        color_discrete_sequence=COLOR_SEQUENCE,
        labels={"Furniture state": "Tình trạng nội thất", "Giá TB/m²": "Giá trung bình/m² (tỷ VNĐ)"},
        text_auto=".4f",
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Giá TB/m²: %{y:.4f} tỷ<extra></extra>")
    apply_theme(fig, "Giá trung bình/m² theo tình trạng nội thất")
    fig.update_layout(height=390, showlegend=False, xaxis_tickangle=-20)
    st.plotly_chart(fig, width="stretch", key="seg_furniture_price_bar")

    top = summary.iloc[0]
    st.markdown(
        render_insight(f"Nhóm <b>{top['Furniture state']}</b> có giá trung bình cao nhất: <b>{top['Giá TB/m²']:.4f} tỷ/m²</b>."),
        unsafe_allow_html=True,
    )


def _render_area_price_scatter(df: pd.DataFrame) -> None:
    plot_df = _clean_categories(df, ["Area", "Price", "Price_Segment"])
    # Cắt 1% ngoại lệ ở mỗi biến để ranh giới phân khúc dễ quan sát hơn.
    plot_df = plot_df[
        (plot_df["Area"] <= plot_df["Area"].quantile(0.99))
        & (plot_df["Price"] <= plot_df["Price"].quantile(0.99))
    ]
    if len(plot_df) > 5_000:
        plot_df = plot_df.sample(5_000, random_state=42)

    fig = px.scatter(
        plot_df,
        x="Area",
        y="Price",
        color="Price_Segment",
        category_orders={"Price_Segment": PRICE_SEGMENT_ORDER},
        color_discrete_sequence=COLOR_SEQUENCE,
        opacity=0.58,
        labels={"Area": "Diện tích (m²)", "Price": "Giá (tỷ VNĐ)", "Price_Segment": "Phân khúc giá"},
        hover_data={"Price_per_m2": ":.4f", "Area_Group": True},
    )
    fig.update_traces(marker=dict(size=8, line=dict(width=0)))
    apply_theme(fig, "Diện tích và giá theo phân khúc")
    fig.update_layout(height=480, legend_title_text="Phân khúc giá")
    st.plotly_chart(fig, width="stretch", key="seg_area_price_scatter")


def render(df_filtered: pd.DataFrame) -> None:
    """Hiển thị toàn bộ tab Market Segmentation từ dữ liệu đã lọc."""
    if df_filtered.empty:
        _empty_state()
        return

    missing = REQUIRED_COLUMNS.difference(df_filtered.columns)
    if missing:
        _empty_state("Thiếu cột dữ liệu để phân tích phân khúc: " + ", ".join(sorted(missing)))
        return

    st.markdown("### Phân khúc thị trường")
    st.caption("Khám phá cơ cấu nguồn cung, mức giá và ranh giới giữa các phân khúc thị trường.")

    left, right = st.columns(2)
    with left:
        _render_area_segment_distribution(df_filtered)
    with right:
        _render_price_segment_pie(df_filtered)

    st.markdown("---")
    left, right = st.columns(2)
    with left:
        _render_legal_segment_bar(df_filtered)
    with right:
        _render_furniture_price_bar(df_filtered)

    st.markdown("---")
    _render_area_price_scatter(df_filtered)


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