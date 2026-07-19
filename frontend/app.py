from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable

import streamlit as st
import pandas as pd
import numpy as np

from components.chat import render_chat_panel
from components.code_editor import render_code_editor_panel
from components.log_view import render_log_panel
from components.result_view import render_result_panel
from services.ai_api import generate_ai_response
from services.execute_api import execute_approved_code
from services.logs_api import fetch_logs
from filters import render_sidebar_filters, apply_filters, _init_filters


APP_TITLE = "AI Frontend Dashboard"
APP_SUBTITLE = "Dashboard 4 tab với AI popup để chat, duyệt code, và xem kết quả"

DEFAULT_PROMPT = (
    "Dựa trên tab và bộ lọc hiện tại, hãy đề xuất một phân tích ngắn gọn cho dữ liệu house_price_clean. "
    "Chỉ dùng các cột có thật trong schema, viết code Python rõ ràng để xử lý hoặc trực quan hóa df, "
    "và giải thích ngắn gọn bằng tiếng Việt."
)

DEFAULT_CODE = '''# Giải thích: Chuẩn bị dữ liệu đã được duyệt để hiển thị bảng và biểu đồ.
import pandas as pd

# Giải thích: Tạo bảng tổng hợp giả lập từ dữ liệu địa phương.
summary = pd.DataFrame(
    {
        "province": ["Hanoi", "Ho Chi Minh City", "Da Nang", "Hai Phong", "Can Tho"],
        "median_price": [52.4, 61.8, 38.2, 34.7, 29.9],
    }
)

# Giải thích: Sắp xếp để biểu đồ và bảng dễ đọc hơn.
summary = summary.sort_values("median_price", ascending=False).reset_index(drop=True)
result = summary
'''


def _load_renderer(module_filename: str, function_name: str) -> Callable:
    module_path = Path(__file__).resolve().parent / "pages" / module_filename
    module_name = f"dashboard_{module_filename.replace('.py', '')}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load dashboard module: {module_filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    renderer = getattr(module, function_name, None)
    if renderer is None:
        raise RuntimeError(f"Missing renderer {function_name} in {module_filename}")
    return renderer


# Load các hàm render từ các file tab
render_overview_tab = _load_renderer("tab_overview.py", "render")
render_market_tab = _load_renderer("tab_market.py", "render")
render_geography_tab = _load_renderer("tab_geography.py", "render")
render_trends_tab = _load_renderer("tab_trends.py", "render")


def initialize_state() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": (
                    "Tôi có thể đề xuất code theo yêu cầu, đính kèm giải thích, "
                    "và chờ bạn duyệt trước khi chạy."
                ),
            }
        ]
    if "prompt_text" not in st.session_state:
        st.session_state.prompt_text = DEFAULT_PROMPT
    if "prompt_widget" not in st.session_state:
        st.session_state.prompt_widget = DEFAULT_PROMPT
    if "generated_code" not in st.session_state:
        st.session_state.generated_code = DEFAULT_CODE
    if "code_editor_text" not in st.session_state:
        st.session_state.code_editor_text = DEFAULT_CODE
    if "code_editor_revision" not in st.session_state:
        st.session_state.code_editor_revision = 0
    if "generated_explanation" not in st.session_state:
        st.session_state.generated_explanation = (
            "Đây là code mẫu để minh họa luồng AI -> duyệt -> thực thi. "
            "Bạn có thể chỉnh sửa trước khi bấm chạy."
        )
    if "approval_status" not in st.session_state:
        st.session_state.approval_status = "Chờ duyệt"
    if "current_request_id" not in st.session_state:
        st.session_state.current_request_id = None
    if "ai_status" not in st.session_state:
        st.session_state.ai_status = None
    if "execution_result" not in st.session_state:
        st.session_state.execution_result = None
    if "execution_error" not in st.session_state:
        st.session_state.execution_error = None
    if "show_ai_popup" not in st.session_state:
        st.session_state.show_ai_popup = False


def load_sample_data() -> pd.DataFrame:
    """Load dữ liệu mẫu cho dashboard."""
    np.random.seed(42)
    n = 1000

    provinces = ["Hà Nội", "TP Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ",
                 "Bình Dương", "Đồng Nai", "Bà Rịa - Vũng Tàu", "Khánh Hòa", "Quảng Ninh"]
    districts = ["Quận 1", "Quận 2", "Quận 3", "Quận 4", "Quận 5", "Quận 6", "Quận 7",
                 "Quận 8", "Quận 9", "Quận 10", "Quận 11", "Quận 12", "Bình Thạnh", "Gò Vấp"]
    wards = ["Phường 1", "Phường 2", "Phường 3", "Phường 4", "Phường 5", "Phường 6",
             "Phường 7", "Phường 8", "Phường 9", "Phường 10"]
    legal_statuses = ["Sổ đỏ", "Sổ hồng", "Hợp đồng mua bán", "Chưa có giấy tờ", "Đang chờ cấp"]
    furniture_states = ["Đầy đủ", "Cơ bản", "Không có", "Cao cấp"]
    directions = ["Đông", "Tây", "Nam", "Bắc", "Đông Nam", "Tây Bắc", "Không xác định"]

    data = {
        "Province": np.random.choice(provinces, n),
        "District": np.random.choice(districts, n),
        "Ward": np.random.choice(wards, n),
        "Area": np.random.uniform(20, 150, n),
        "Price": np.random.uniform(0.5, 25, n),
        "Legal status": np.random.choice(legal_statuses, n),
        "Furniture state": np.random.choice(furniture_states, n),
        "House direction": np.random.choice(directions, n),
        "Bedrooms": np.random.choice([1, 2, 3, 4, 5, np.nan], n, p=[0.1, 0.25, 0.3, 0.2, 0.1, 0.05]),
        "Bathrooms": np.random.choice([1, 2, 3, 4, np.nan], n, p=[0.15, 0.35, 0.3, 0.15, 0.05]),
        "Floors": np.random.choice([1, 2, 3, 4, 5, np.nan], n, p=[0.1, 0.2, 0.3, 0.2, 0.1, 0.1]),
        "Frontage": np.random.uniform(3, 15, n),
        "Access Road": np.random.uniform(2, 12, n),
    }
    df = pd.DataFrame(data)

    df["Price_per_m2"] = df["Area"].apply(lambda x: 0.02 + 0.001 * (100 - x) + np.random.uniform(-0.005, 0.005))
    df["Price_per_m2"] = df["Price_per_m2"].clip(0.005, 0.08)
    df["Price"] = df["Area"] * df["Price_per_m2"] * np.random.uniform(0.8, 1.2, n)
    df["Price"] = df["Price"].clip(0.3, 30)

    df["Area_Group"] = pd.cut(
        df["Area"],
        bins=[0, 30, 50, 70, 90, float('inf')],
        labels=["<30 m²", "30-50 m²", "50-70 m²", "70-90 m²", ">90 m²"]
    )
    df["Price_Segment"] = pd.cut(
        df["Price"],
        bins=[0, 1, 3, 5, 10, float('inf')],
        labels=["Dưới 1 tỷ", "1-3 tỷ", "3-5 tỷ", "5-10 tỷ", "Trên 10 tỷ"]
    )
    return df


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(70, 130, 180, 0.20), transparent 28%),
                radial-gradient(circle at bottom right, rgba(12, 74, 110, 0.16), transparent 30%),
                linear-gradient(180deg, #f7fbff 0%, #eef4f9 100%);
        }
        .hero-card {
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 20px;
            padding: 22px 24px;
            background: rgba(255, 255, 255, 0.78);
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
            backdrop-filter: blur(10px);
            margin-bottom: 1rem;
        }
        .status-chip {
            display: inline-block;
            padding: 0.3rem 0.7rem;
            border-radius: 999px;
            background: #0f766e;
            color: white;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .dashboard-note {
            padding: 0.55rem 0.75rem;
            border-radius: 12px;
            background: rgba(15, 118, 110, 0.1);
            color: #115e59;
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_header() -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <div style="display:flex; justify-content:space-between; gap:16px; align-items:flex-start; flex-wrap:wrap;">
                <div>
                    <h1 style="margin-bottom:0.35rem; color:#0f172a;">{APP_TITLE}</h1>
                    <p style="margin:0; color:#334155; font-size:1rem;">{APP_SUBTITLE}</p>
                </div>
                <div class="status-chip">{st.session_state.approval_status}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def request_ai_generation(prompt_text: str) -> None:
    with st.spinner("Đang gọi AI API để sinh code..."):
        response = generate_ai_response(prompt_text=prompt_text)
    st.session_state.current_request_id = response.get("request_id")
    st.session_state.generated_code = response["code"]
    st.session_state.code_editor_text = response["code"]
    st.session_state.code_editor_revision += 1
    st.session_state.generated_explanation = response["explanation"]
    st.session_state.ai_status = response.get("status")
    st.session_state.approval_status = "Chờ duyệt"
    st.session_state.execution_result = None
    st.session_state.execution_error = None
    st.session_state.chat_history.append(
        {"role": "user", "content": prompt_text}
    )
    st.session_state.chat_history.append(
        {"role": "assistant", "content": response["chat_reply"]}
    )


def approve_and_execute(code_text: str) -> None:
    st.session_state.approval_status = "Đã duyệt"
    with st.spinner("Đang thực thi code local..."):
        request_id = st.session_state.current_request_id
        if not request_id:
            raise RuntimeError("Thiếu request_id từ AI generate. Hãy generate code trước.")
        execution = execute_approved_code(request_id=request_id, code_text=code_text, approved=True)
    st.session_state.code_editor_text = code_text
    st.session_state.execution_result = execution
    st.session_state.execution_error = execution.get("error")


def reject_current_code() -> None:
    st.session_state.approval_status = "Bị từ chối"
    st.session_state.execution_result = None
    st.session_state.execution_error = None


def render_dashboard_tabs(df_filtered: pd.DataFrame) -> None:
    tab_titles = [
        "📊 Overview",
        "🎯 Market Pulse",
        "🗺️ Geo Insights",
        "🔬 Trend Lab",
    ]
    tab_overview, tab_market, tab_geo, tab_trends = st.tabs(tab_titles)

    with tab_overview:
        render_overview_tab(df_filtered)
    with tab_market:
        render_market_tab(df_filtered)
    with tab_geo:
        render_geography_tab(df_filtered)
    with tab_trends:
        render_trends_tab(df_filtered)


@st.dialog("AI Workspace", width="large")
def render_ai_popup() -> None:
    st.caption("Popup AI dùng chung cho mọi tab: chat, chỉnh sửa code, duyệt, và xem kết quả.")

    prompt_value = render_chat_panel(
        chat_history=st.session_state.chat_history,
        default_prompt=DEFAULT_PROMPT,
        on_generate=request_ai_generation,
    )
    st.session_state.prompt_text = prompt_value

    code_text = render_code_editor_panel(
        code_text=st.session_state.code_editor_text,
        explanation_text=st.session_state.generated_explanation,
        approval_status=st.session_state.approval_status,
        widget_key=f"code_editor_widget_{st.session_state.code_editor_revision}",
    )
    st.session_state.code_editor_text = code_text

    action_col_1, action_col_2, action_col_3 = st.columns(3)
    with action_col_1:
        if st.button("Approve & Execute", use_container_width=True, key="popup_approve"):
            approve_and_execute(code_text)
            st.success("Đã duyệt và thực thi code.")
    with action_col_2:
        if st.button("Reject", use_container_width=True, key="popup_reject"):
            reject_current_code()
            st.warning("Code đã bị từ chối.")
    with action_col_3:
        if st.button("Reset to Mock", use_container_width=True, key="popup_reset"):
            st.session_state.generated_code = DEFAULT_CODE
            st.session_state.code_editor_text = DEFAULT_CODE
            st.session_state.code_editor_revision += 1
            st.session_state.generated_explanation = (
                "Đã khôi phục code mock mặc định để tiếp tục demo."
            )
            st.session_state.approval_status = "Chờ duyệt"
            st.session_state.current_request_id = None
            st.session_state.execution_result = None
            st.session_state.execution_error = None
            st.info("Đã khôi phục nội dung mẫu.")

    render_result_panel(
        result=st.session_state.execution_result,
        error_message=st.session_state.execution_error,
        logs=fetch_logs(st.session_state.current_request_id) if st.session_state.current_request_id else [],
    )

    render_log_panel(logs=fetch_logs(st.session_state.current_request_id) if st.session_state.current_request_id else [])


def build_popup_trigger() -> None:
    trigger_left, trigger_right = st.columns([8.0, 1.2])
    with trigger_left:
        st.markdown(
            '<div class="dashboard-note">Dashboard có 4 tab. Bấm nút AI Assistant để mở popup chatbot ở bất kỳ tab nào.</div>',
            unsafe_allow_html=True,
        )
    with trigger_right:
        if st.button("💬 AI Assistant", use_container_width=True, key="open_ai_popup"):
            st.session_state.show_ai_popup = True

    if st.session_state.show_ai_popup:
        render_ai_popup()
        st.session_state.show_ai_popup = False


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🧠", layout="wide")
    initialize_state()
    inject_styles()
    build_header()

    # Load dữ liệu
    df = load_sample_data()

    # Khởi tạo filters
    _init_filters(df)

    # Render sidebar filters - CHỈ CÓ BỘ LỌC, KHÔNG CÓ NAVI DỌC
    render_sidebar_filters(df)

    # Lấy filters từ session_state và áp dụng
    filters = st.session_state.get("filters", {})
    df_filtered = apply_filters(df, filters)

    # AI popup trigger
    build_popup_trigger()

    # Render dashboard tabs
    render_dashboard_tabs(df_filtered)


if __name__ == "__main__":
    main()