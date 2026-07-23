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
from services.ai_api import generate_ai_response, fix_ai_response, interpret_result
from services.execute_api import execute_approved_code
from services.logs_api import fetch_logs
from filters import render_sidebar_filters, apply_filters, _init_filters
from data_loader import load_data


from theme import KPI_CARD_CSS, AI_POPUP_CSS


DATASET_PATH = Path(__file__).resolve().parent.parent / "Data" / "processed" / "house_price_clean.csv"

APP_TITLE = "Nhóm 14"
HEADER_TITLE= "PHÂN TÍCH THỊ TRƯỜNG BẤT ĐỘNG SẢN VIỆT NAM"
APP_SUBTITLE = "VIETNAM REAL ESTATE INTELLIGENCE"

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
		# Bắt đầu với tin nhắn chào của Assistant (không có mock code)
		st.session_state.chat_history = [
			{
				"role": "assistant",
				"content": "Xin chào! Hãy nhập yêu cầu phân tích bên dưới và tôi sẽ sinh code cho bạn.",
			}
		]
	if "prompt_text" not in st.session_state:
		st.session_state.prompt_text = ""
	if "prompt_widget" not in st.session_state:
		st.session_state.prompt_widget = ""
	if "generated_code" not in st.session_state:
		st.session_state.generated_code = ""
	if "code_editor_text" not in st.session_state:
		st.session_state.code_editor_text = ""
	if "code_editor_revision" not in st.session_state:
		st.session_state.code_editor_revision = 0
	if "generated_explanation" not in st.session_state:
		st.session_state.generated_explanation = ""
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
	if "answer_text" not in st.session_state:
		st.session_state.answer_text = None
	if "show_ai_popup" not in st.session_state:
		st.session_state.show_ai_popup = False


def inject_styles() -> None:
    st.markdown(KPI_CARD_CSS, unsafe_allow_html=True)
    st.markdown(AI_POPUP_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <style>
        .status-chip {
            display: inline-block;
            padding: 0.35rem 0.85rem;
            border-radius: 999px;
            background: rgba(245, 158, 11, 0.2);
            color: #F59E0B;
            border: 1px solid rgba(245, 158, 11, 0.4);
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .dashboard-note {
            padding: 0.65rem 0.85rem;
            border-radius: 10px;
            background: #EFF6FF;
            border-left: 4px solid #1D4ED8;
            color: #1E3A8A;
            font-size: 0.88rem;
            font-weight: 500;
            margin-bottom: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_header() -> None:
    st.markdown(
        f"""
        <div class="vrei-header">
            <div class="vrei-brand">
                <div class="vrei-logo">🏢</div>
                <div>
                    <h1 class="vrei-title">{HEADER_TITLE}</h1>
                </div>
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


def request_ai_fix(error_msg: str, broken_code: str) -> None:
    """Gọi /ai/fix để sinh lại code khi execution thất bại."""
    with st.spinner("⏳ AI đang phân tích lỗi và sinh lại code..."):
        request_id = st.session_state.current_request_id
        response = fix_ai_response(
            request_id=request_id,
            code_text=broken_code,
            error=error_msg,
        )
    st.session_state.current_request_id = response.get("request_id")
    st.session_state.generated_code = response["code"]
    st.session_state.code_editor_text = response["code"]
    st.session_state.code_editor_revision += 1
    st.session_state.generated_explanation = response["explanation"]
    st.session_state.ai_status = response.get("status")
    st.session_state.approval_status = "Chờ duyệt"
    st.session_state.execution_result = None
    st.session_state.execution_error = None
    # Thêm tin nhắn thông báo vào chat
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": (
            f"Hệ thống gặp lỗi khi thực hiện lệnh vừa rồi:\n"
            f"```\n{error_msg}\n```\n"
            f"Đang tự động tạo lại đoạn code mới để khắc phục, bạn vui lòng xem code bên dưới nhé!"
        ),
    })


def approve_and_execute(code_text: str) -> None:
    st.session_state.approval_status = "Đang thực thi"
    with st.spinner("Đang thực thi code..."):
        request_id = st.session_state.current_request_id
        if not request_id:
            raise RuntimeError("Thiếu request_id từ AI generate. Hãy generate code trước.")
        execution = execute_approved_code(request_id=request_id, code_text=code_text, approved=True)
    st.session_state.code_editor_text = code_text
    st.session_state.execution_result = execution
    error_msg = execution.get("error")
    st.session_state.execution_error = error_msg
    st.session_state.answer_text = None

    if not execution.get("success") or error_msg:
        # --- Execution lỗi: gọi AI sửa tự động ---
        st.session_state.approval_status = "Lỗi - Đang sửa"
        request_ai_fix(
            error_msg=error_msg or "Không có kết quả hợp lệ",
            broken_code=code_text,
        )
        return

    # --- Thành công: sinh câu trả lời ---
    st.session_state.approval_status = "Đã duyệt"
    try:
        with st.spinner("Đang diễn giải kết quả..."):
            st.session_state.answer_text = interpret_result(request_id)
    except Exception as exc:
        st.session_state.answer_text = None
        st.warning(f"Không tạo được câu trả lời: {exc}")
        
    # Lưu kết quả vào tin nhắn AI cuối cùng trong lịch sử để giữ lại khi chat tiếp
    for i in range(len(st.session_state.chat_history)-1, -1, -1):
        if st.session_state.chat_history[i].get("role") == "assistant":
            st.session_state.chat_history[i]["execution_result"] = execution
            st.session_state.chat_history[i]["answer_text"] = st.session_state.answer_text
            st.session_state.chat_history[i]["executed_code"] = code_text
            break


def reject_current_code() -> None:
    st.session_state.approval_status = "Bị từ chối"
    st.session_state.execution_result = None
    st.session_state.execution_error = None
    st.session_state.answer_text = None
    
    # Lưu lại code bị từ chối vào tin nhắn AI cuối cùng trong lịch sử
    for i in range(len(st.session_state.chat_history)-1, -1, -1):
        if st.session_state.chat_history[i].get("role") == "assistant":
            st.session_state.chat_history[i]["rejected_code"] = st.session_state.code_editor_text
            break


def render_dashboard_tabs(df_filtered: pd.DataFrame) -> None:
    tab_titles = [
        "Tổng quan",
        "Phân tích địa lý",
        "Yếu tố ảnh hưởng giá",
        "Phân khúc thị trường",
    ]
    tab_overview, tab_geo, tab_trends, tab_market = st.tabs(tab_titles)

    with tab_overview:
        render_overview_tab(df_filtered)
    with tab_geo:
        render_geography_tab(df_filtered)
    with tab_trends:
        render_trends_tab(df_filtered)
    with tab_market:
        render_market_tab(df_filtered)


@st.dialog("Trợ lý AI", width="large")
def render_ai_popup() -> None:
    # --- KHỞI TẠO BỐ CỤC ---
    chat_container = st.container()
    spinner_container = st.container()

    # --- CSS Tối ưu vị trí spinner thành bong bóng chat AI ---
    st.markdown(
        """
        <style>
        /* Tùy chỉnh giao diện khối spinner */
        div[data-testid="stSpinner"] {
            padding: 10px 16px;
            background: #F3F4F6;
            border-radius: 20px; /* Tròn đều các góc */
            color: #1F2937;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid #E5E7EB;
            width: fit-content;
        }
        
        /* Căn giữa container bọc ngoài spinner */
        div:has(> div[data-testid="stSpinner"]) {
            display: flex;
            justify-content: center;
            width: 100%;
        }
        /* Căn chỉnh icon quay quay bên trong cho cân đối */
        div[data-testid="stSpinner"] > div {
            margin-bottom: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── XỬ LÝ ACTIONS (Cho vào spinner_container để hiển thị phía dưới lịch sử) ──
    with spinner_container:
        pending_action = st.session_state.get("popup_pending_action")
        if pending_action:
            if pending_action == "generate":
                st.session_state.popup_pending_action = None
                request_ai_generation(st.session_state.prompt_text)
            elif pending_action == "approve":
                st.session_state.popup_pending_action = None
                approve_and_execute(st.session_state.pending_code_text)
            elif pending_action == "reject":
                st.session_state.popup_pending_action = None
                reject_current_code()

    # ── Lịch sử hội thoại ──────────────────────────────────────────────
    with chat_container:
        for idx, message in enumerate(st.session_state.chat_history):
            role = message.get("role", "assistant")
            content = message.get("content", "")
        
            # Render bong bóng chat bằng HTML thuần để đảm bảo UI chính xác 100%
            if content:
                safe_content = content.replace('\n', '<br>')
                if role == "user":
                    html = f"""
                    <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; align-items: flex-start; gap: 12px; width: 100%;">
                        <div style="background: linear-gradient(135deg, #1D4ED8, #2563EB); color: white; padding: 12px 18px; border-radius: 20px 20px 0px 20px; max-width: 75%; box-shadow: 0 4px 6px rgba(29, 78, 216, 0.2); font-size: 0.95rem; line-height: 1.5;">
                            {safe_content}
                        </div>
                        <div style="width: 36px; height: 36px; border-radius: 50%; background-color: #F97316; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; flex-shrink: 0; box-shadow: 0 2px 4px rgba(249, 115, 22, 0.3);">
                            U
                        </div>
                    </div>
                    """
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    html = f"""
                    <div style="display: flex; justify-content: flex-start; margin-bottom: 20px; align-items: flex-start; gap: 12px; width: 100%;">
                        <div style="width: 36px; height: 36px; border-radius: 50%; background-color: #1D4ED8; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; flex-shrink: 0; box-shadow: 0 2px 4px rgba(29, 78, 216, 0.3);">
                            AI
                        </div>
                        <div style="background: #F3F4F6; color: #1F2937; padding: 12px 18px; border-radius: 20px 20px 20px 0px; max-width: 75%; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border: 1px solid #E5E7EB; font-size: 0.95rem; line-height: 1.5;">
                            {safe_content}
                        </div>
                    </div>
                    """
                    st.markdown(html, unsafe_allow_html=True)

            # Với tin nhắn AI cuối cùng: hiện code editor + nút / trạng thái (thụt lề một chút cho đẹp)
            is_last  = idx == len(st.session_state.chat_history) - 1
            is_ai    = role == "assistant"
            has_code = bool(st.session_state.generated_code)
            status   = st.session_state.approval_status

            if is_ai:
                with st.container():
                    st.markdown('<div style="padding-left: 48px; margin-bottom: 20px;">', unsafe_allow_html=True)
                    # Render các widget tương tác chỉ cho tin nhắn cuối
                    if is_last:
                        # ── Trạng thái: AI đang sửa lỗi (đang chờ backend) ──
                        if status == "Lỗi - Đang sửa":
                            st.markdown(
                                """
                                <div style="
                                    display:flex; align-items:center; gap:10px;
                                    background:#FEF3C7; border:1px solid #F59E0B;
                                    border-radius:10px; padding:12px 16px;
                                    margin-top:8px;
                                ">
                                    <span style="font-size:1.5rem">⏳</span>
                                    <span style="color:#92400E; font-weight:600; font-size:0.95rem;">
                                        Đang chờ AI sinh lại code, vui lòng đợi...
                                    </span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        # ── Trạng thái: Chờ duyệt (có code để review) ──
                        elif status == "Chờ duyệt" and has_code:
                            code_text = render_code_editor_panel(
                                code_text=st.session_state.code_editor_text,
                                explanation_text=st.session_state.generated_explanation,
                                approval_status=status,
                                widget_key=f"code_editor_widget_{st.session_state.code_editor_revision}",
                            )
                            st.session_state.code_editor_text = code_text

                            def handle_approve(code):
                                st.session_state.pending_code_text = code
                                st.session_state.popup_pending_action = "approve"

                            def handle_reject():
                                st.session_state.popup_pending_action = "reject"

                            btn_col1, btn_col2, _ = st.columns([1, 1, 2])
                            with btn_col1:
                                st.markdown('<span id="btn-approve-marker"></span>', unsafe_allow_html=True)
                                st.button("Chấp nhận", use_container_width=True, key="popup_approve", on_click=handle_approve, args=(code_text,))
                            with btn_col2:
                                st.markdown('<span id="btn-reject-marker"></span>', unsafe_allow_html=True)
                                st.button("Từ chối", use_container_width=True, key="popup_reject", on_click=handle_reject)

                        # ── Trạng thái: Bị từ chối ──
                        elif status == "Bị từ chối":
                            st.markdown(
                                """
                                <div style="
                                    background:#FEF2F2; border:1px solid #EF4444;
                                    border-radius:10px; padding:10px 14px;
                                    color:#991B1B; font-size:0.9rem;
                                ">
                                    ❌ Code đã bị từ chối. Nhập yêu cầu mới bên dưới để bắt đầu lại.
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                    # ── Hiển thị kết quả thực thi (cho cả lịch sử và tin hiện tại) ──
                    ans_text = message.get("answer_text") if not (is_last and status == "Đã duyệt") else st.session_state.answer_text
                    exec_res = message.get("execution_result") if not (is_last and status == "Đã duyệt") else st.session_state.execution_result
                    exec_code = message.get("executed_code") if not (is_last and status == "Đã duyệt") else (st.session_state.code_editor_text if status == "Đã duyệt" else None)
                    rej_code = message.get("rejected_code") if not (is_last and status == "Bị từ chối") else (st.session_state.code_editor_text if status == "Bị từ chối" else None)
                
                    if ans_text or exec_res or exec_code or rej_code:
                        if exec_code:
                            st.markdown("**Code đã chạy  (Chấp nhận):**")
                            st.code(exec_code, language="python")
                        elif rej_code:
                            st.markdown("**Code đã bỏ qua (Từ chối):**")
                            st.code(rej_code, language="python")
                        
                        if ans_text:
                            st.markdown(f"**📊 Kết quả phân tích:**\n\n{ans_text}")
                        if exec_res:
                            render_result_panel(
                                result=exec_res,
                                error_message=exec_res.get("error"),
                                logs=fetch_logs(exec_res.get("request_id")) if exec_res.get("request_id") else [],
                            )

                    st.markdown('</div>', unsafe_allow_html=True)

    # ── Khung nhập liệu ────────────────────────────────────────────────
    st.divider()
    # Ẩn input khi đang chờ AI sửa
    if st.session_state.approval_status == "Lỗi - Đang sửa":
        st.info("⏳ AI đang tự động phân tích và sửa lỗi. Kết quả sẽ hiện ngay khi xong.")
    else:
        prompt_value = st.text_area(
            label="prompt",
            height=80,
            placeholder="Nhập yêu cầu phân tích... (VD: Vẽ biểu đồ giá nhà trung bình theo quận)",
            key="prompt_widget",
            label_visibility="collapsed",
        )
        
        def handle_generate():
            val = st.session_state.prompt_widget
            if val and val.strip():
                st.session_state.prompt_text = val.strip()
                st.session_state.popup_pending_action = "generate"
                st.session_state.prompt_widget = "" # Xoá input sau khi gửi

        _, col_gen = st.columns([3, 1])
        with col_gen:
            st.markdown('<span id="btn-generate-marker"></span>', unsafe_allow_html=True)
            st.button("Tạo mã nguồn", use_container_width=True, key="btn_generate", on_click=handle_generate)



def build_popup_trigger() -> None:
    st.markdown('<span id="btn-ai-popup-marker"></span>', unsafe_allow_html=True)
    if st.button("💬", use_container_width=True, key="open_ai_popup"):
        st.session_state.show_ai_popup = True

    if st.session_state.show_ai_popup:
        render_ai_popup()
        st.session_state.show_ai_popup = False


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🧠", layout="wide")
    initialize_state()
    inject_styles()

    # Load dữ liệu
    if DATASET_PATH.exists():
        df = load_data(DATASET_PATH)
    # else:
    #     df = load_sample_data()

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