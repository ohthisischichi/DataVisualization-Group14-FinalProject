"""
filters.py
Render sidebar filter dùng chung cho toàn bộ dashboard.
Tất cả filter lưu vào st.session_state["filters"] để các tab và AI chat module đọc.
"""

import pandas as pd
import streamlit as st
from typing import Any


def _init_filters(df: pd.DataFrame) -> None:
    """
    Khởi tạo giá trị mặc định cho filters trong session_state nếu chưa tồn tại.
    Gọi 1 lần khi app khởi động.
    """
    if "filters" not in st.session_state:
        st.session_state["filters"] = {
            "province": [],
            "district": [],
            "price_segment": [],
            "area_group": [],
            "legal_status": [],
            "furniture_state": [],
            "price_range": (float(df["Price"].min()), float(df["Price"].max())),
            "area_range": (float(df["Area"].min()), float(df["Area"].max())),
        }


def _reset_filters(df: pd.DataFrame) -> None:
    """
    Xóa toàn bộ filter, đặt lại về giá trị mặc định (hiển thị toàn bộ dữ liệu).
    KHÔNG set trực tiếp session_state của widget - chỉ set filters dict và dùng st.rerun()
    """
    price_min = float(df["Price"].min())
    price_max = float(df["Price"].max())
    area_min = float(df["Area"].min())
    area_max = float(df["Area"].max())

    # CHỈ set filters dict, không set widget keys
    st.session_state["filters"] = {
        "province": [],
        "district": [],
        "price_segment": [],
        "area_group": [],
        "legal_status": [],
        "furniture_state": [],
        "price_range": (price_min, price_max),
        "area_range": (area_min, area_max),
    }
    
    # Xóa drill-down tỉnh đang chọn (tab Geographic)
    st.session_state.pop("geo_selected_province", None)
    
    # Rerun để widget lấy giá trị mới từ filters dict
    st.rerun()


def render_sidebar_filters(df: pd.DataFrame) -> None:
    """
    Vẽ toàn bộ widget filter trên sidebar.
    Không dùng st.form — widget cập nhật realtime, tự động trigger rerun.
    Kết quả lưu vào st.session_state["filters"].

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame gốc (chưa lọc) để tính các giá trị min/max và danh sách lựa chọn.
    """
    _init_filters(df)
    f = st.session_state["filters"]  # Tham chiếu đến dict filter hiện tại

    with st.sidebar:
        st.markdown("## Bộ lọc dữ liệu")
        st.markdown("---")

        # ── 1. TỈNH/THÀNH (Province) ──────────────────────────────────────────
        all_provinces = sorted(df["Province"].dropna().unique().tolist())
        selected_provinces: list[str] = st.multiselect(
            label="Tỉnh / Thành phố",
            options=all_provinces,
            default=f["province"],
            placeholder="Chọn tỉnh/thành",
            key="filter_province",
            help="Chọn một hoặc nhiều tỉnh. Quận/huyện bên dưới sẽ tự cập nhật.",
        )
        f["province"] = selected_provinces

        # ── 2. QUẬN/HUYỆN — drill-down theo Province đã chọn ─────────────────
        if selected_provinces:
            district_pool = sorted(
                df[df["Province"].isin(selected_provinces)]["District"]
                .dropna()
                .unique()
                .tolist()
            )
            # Nếu district đang chọn không còn trong pool mới → tự xoá
            valid_districts = [d for d in f["district"] if d in district_pool]

            selected_districts: list[str] = st.multiselect(
                label="Quận / Huyện",
                options=district_pool,
                default=valid_districts,
                placeholder="Chọn quận/huyện",
                key="filter_district",
                help="Danh sách quận/huyện tự lọc theo tỉnh đã chọn phía trên.",
            )
            f["district"] = selected_districts
        else:
            # Chưa chọn tỉnh → disabled
            st.multiselect(
                label="Quận / Huyện",
                options=[],
                default=[],
                disabled=True,
                placeholder="Hãy chọn tỉnh/thành trước",
                key="filter_district_disabled",
            )
            f["district"] = []  # Reset district khi chưa chọn tỉnh

        st.markdown("---")

        # ── 3. PHÂN KHÚC GIÁ ─────────────────────────────────────────────────
        price_seg_options = ["<4 tỷ", "4-6 tỷ", "6-8 tỷ", "8-10 tỷ", ">10 tỷ"]
        selected_price_seg: list[str] = st.multiselect(
            label="Phân khúc giá",
            options=price_seg_options,
            default=f["price_segment"],
            placeholder="Tất cả phân khúc",
            key="filter_price_segment",
        )
        f["price_segment"] = selected_price_seg

        # ── 4. NHÓM DIỆN TÍCH ────────────────────────────────────────────────
        area_group_options = ["<30 m²", "30-50 m²", "50-70 m²", "70-90 m²", ">90 m²"]
        selected_area_group: list[str] = st.multiselect(
            label="Nhóm diện tích",
            options=area_group_options,
            default=f["area_group"],
            placeholder="Tất cả nhóm diện tích",
            key="filter_area_group",
        )
        f["area_group"] = selected_area_group

        st.markdown("---")

        # ── 5. TÌNH TRẠNG PHÁP LÝ ────────────────────────────────────────────
        legal_options = sorted(df["Legal status"].dropna().unique().tolist())
        selected_legal: list[str] = st.multiselect(
            label="Tình trạng pháp lý",
            options=legal_options,
            default=f["legal_status"],
            placeholder="Tất cả tình trạng pháp lý",
            key="filter_legal_status",
        )
        f["legal_status"] = selected_legal

        # ── 6. TÌNH TRẠNG NỘI THẤT ───────────────────────────────────────────
        furniture_options = sorted(df["Furniture state"].dropna().unique().tolist())
        selected_furniture: list[str] = st.multiselect(
            label="Tình trạng nội thất",
            options=furniture_options,
            default=f["furniture_state"],
            placeholder="Tất cả tình trạng nội thất",
            key="filter_furniture_state",
        )
        f["furniture_state"] = selected_furniture

        st.markdown("---")

        # ── 7. KHOẢNG GIÁ (slider) ───────────────────────────────────────────
        price_min_global = float(df["Price"].min())
        price_max_global = float(df["Price"].max())
        # Đảm bảo giá trị hiện tại trong khoảng hợp lệ
        cur_price = f["price_range"]
        cur_price = (
            max(price_min_global, cur_price[0]),
            min(price_max_global, cur_price[1]),
        )
        selected_price_range: tuple[float, float] = st.slider(
            label="Khoảng giá (tỷ VNĐ)",
            min_value=price_min_global,
            max_value=price_max_global,
            value=cur_price,
            step=0.5,
            format="%.1f tỷ",
            key="filter_price_range",
        )
        f["price_range"] = selected_price_range

        # ── 8. KHOẢNG DIỆN TÍCH (slider) ─────────────────────────────────────
        area_min_global = float(df["Area"].min())
        area_max_global = float(df["Area"].max())
        cur_area = f["area_range"]
        cur_area = (
            max(area_min_global, cur_area[0]),
            min(area_max_global, cur_area[1]),
        )
        selected_area_range: tuple[float, float] = st.slider(
            label="Khoảng diện tích (m²)",
            min_value=area_min_global,
            max_value=area_max_global,
            value=cur_area,
            step=5.0,
            format="%.0f m²",
            key="filter_area_range",
        )
        f["area_range"] = selected_area_range

        st.markdown("---")

        # ── NÚT RESET ─────────────────────────────────────────────────────────
        if st.button("Đặt lại bộ lọc", use_container_width=True, type="secondary"):
            _reset_filters(df)


def apply_filters(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    """
    Áp dụng bộ filter lưu trong session_state lên DataFrame gốc.
    Trả về DataFrame đã lọc — DataFrame gốc không bị thay đổi.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame gốc.
    filters : dict
        Dict filter từ st.session_state["filters"].

    Returns
    -------
    pd.DataFrame
        Subset của df sau khi áp dụng tất cả điều kiện filter.
    """
    mask = pd.Series(True, index=df.index)  # Bắt đầu với tất cả True

    # Lọc theo tỉnh
    if filters.get("province"):
        mask &= df["Province"].isin(filters["province"])

    # Lọc theo huyện
    if filters.get("district"):
        mask &= df["District"].isin(filters["district"])

    # Lọc theo phân khúc giá
    if filters.get("price_segment"):
        mask &= df["Price_Segment"].isin(filters["price_segment"])

    # Lọc theo nhóm diện tích
    if filters.get("area_group"):
        mask &= df["Area_Group"].isin(filters["area_group"])

    # Lọc theo tình trạng pháp lý
    if filters.get("legal_status"):
        mask &= df["Legal status"].isin(filters["legal_status"])

    # Lọc theo tình trạng nội thất
    if filters.get("furniture_state"):
        mask &= df["Furniture state"].isin(filters["furniture_state"])

    # Lọc theo khoảng giá (slider)
    if filters.get("price_range"):
        lo, hi = filters["price_range"]
        mask &= df["Price"].between(lo, hi)

    # Lọc theo khoảng diện tích (slider)
    if filters.get("area_range"):
        lo, hi = filters["area_range"]
        mask &= df["Area"].between(lo, hi)

    return df[mask].copy()