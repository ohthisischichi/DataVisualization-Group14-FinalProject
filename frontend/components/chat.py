from __future__ import annotations

from typing import Callable, Sequence

import streamlit as st


def render_chat_panel(
	chat_history: Sequence[dict[str, str]],
	default_prompt: str,
	on_generate: Callable[[str], None],
) -> str:
	st.subheader("Trợ lý AI")
	st.caption("Nhập yêu cầu, xem lịch sử hội thoại, và tạo mã nguồn theo ngữ cảnh hiện tại.")

	for message in chat_history:
		with st.chat_message(message.get("role", "assistant")):
			st.markdown(message.get("content", ""))

	prompt_value = st.text_area(
		"Yêu cầu AI",
		height=140,
		placeholder="Mô tả rõ phân tích bạn muốn AI sinh code cho dữ liệu nhà đất...",
		key="prompt_widget",
	)

	action_col_1, action_col_2 = st.columns([1, 1])
	with action_col_1:
		st.markdown('<span id="btn-generate-marker"></span>', unsafe_allow_html=True)
		if st.button("Tạo mã nguồn", width="stretch"):
			if prompt_value.strip():
				on_generate(prompt_value.strip())
			else:
				st.warning("Vui lòng nhập yêu cầu trước khi sinh code.")
	with action_col_2:
		if st.button("Sử dụng yêu cầu mặc định", width="stretch"):
			st.session_state.prompt_widget = default_prompt
			st.rerun()

	return prompt_value
