from __future__ import annotations

import streamlit as st


def render_code_editor_panel(
	code_text: str,
	explanation_text: str,
	approval_status: str,
	widget_key: str,
) -> str:
	if explanation_text:
		st.markdown(
			f"""
			<div style="
				background: rgba(139,92,246,0.1);
				border-left: 3px solid #8B5CF6;
				border-radius: 0 8px 8px 0;
				padding: 8px 12px;
				margin-bottom: 10px;
				font-size: 0.88rem;
				color: #4C1D95;
				font-style: italic;
			">💡 {explanation_text}</div>
			""",
			unsafe_allow_html=True,
		)

	edited_code = st.text_area(
		"Code (có thể chỉnh sửa)",
		value=code_text,
		height=260,
		label_visibility="collapsed",
		key=widget_key,
	)

	return edited_code
