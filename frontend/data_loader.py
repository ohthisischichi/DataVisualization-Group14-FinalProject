"""
data_loader.py
Chịu trách nhiệm đọc và cache dữ liệu từ file CSV.
Không ghi đè hoặc sửa dữ liệu gốc.
"""

import pandas as pd
import streamlit as st
from pathlib import Path


# Thứ tự và kiểu dữ liệu chuẩn của các cột trong bộ dữ liệu
COLUMN_DTYPES: dict = {
    "Address": "object",
    "Area": "float64",
    "Frontage": "float64",
    "Access Road": "float64",
    "House direction": "object",
    "Balcony direction": "object",
    "Floors": "float64",
    "Bedrooms": "float64",
    "Bathrooms": "float64",
    "Legal status": "object",
    "Furniture state": "object",
    "Price": "float64",
    "Province": "object",
    "District": "object",
    "Ward": "object",
    "Detail": "object",
    "Price_per_m2": "float64",
    "Area_Group": "object",
    "Price_Segment": "object",
    "Latitude": "float64",
    "Longitude": "float64",
}

# Thứ tự hiển thị các nhóm diện tích (dùng để sắp xếp trục biểu đồ)
AREA_GROUP_ORDER = ["<30 m²", "30-50 m²", "50-70 m²", "70-90 m²", ">90 m²"]

# Thứ tự hiển thị các phân khúc giá
PRICE_SEGMENT_ORDER = ["<4 tỷ", "4-6 tỷ", "6-8 tỷ", "8-10 tỷ", ">10 tỷ"]


@st.cache_data(show_spinner="Đang tải dữ liệu bất động sản...")
def load_data(path: str | Path) -> pd.DataFrame:
    """
    Đọc file CSV và trả về DataFrame với đúng kiểu dữ liệu.
    Dùng st.cache_data để chỉ đọc 1 lần trong suốt phiên làm việc.

    Parameters
    ----------
    path : str | Path
        Đường dẫn tới file house_price_clean.csv

    Returns
    -------
    pd.DataFrame
        DataFrame đã được xử lý kiểu dữ liệu, sẵn sàng để lọc và phân tích.
    """
    df = pd.read_csv(path, dtype=COLUMN_DTYPES, encoding="utf-8")

    # Chuyển các cột phân loại sang Categorical để tiết kiệm bộ nhớ và hỗ trợ sắp xếp
    df["Area_Group"] = pd.Categorical(
        df["Area_Group"], categories=AREA_GROUP_ORDER, ordered=True
    )
    df["Price_Segment"] = pd.Categorical(
        df["Price_Segment"], categories=PRICE_SEGMENT_ORDER, ordered=True
    )

    return df


def get_numeric_columns(df: pd.DataFrame) -> list[str]:
    """Trả về danh sách cột số dùng cho correlation heatmap."""
    return [
        col for col in [
            "Area", "Frontage", "Access Road", "Floors",
            "Bedrooms", "Bathrooms", "Price", "Price_per_m2"
        ]
        if col in df.columns
    ]
