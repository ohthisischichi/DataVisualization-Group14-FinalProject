from __future__ import annotations

import streamlit as st


def render_code_editor_panel(
	code_text: str,
	explanation_text: str,
	approval_status: str,
	widget_key: str,
) -> str:
	st.subheader("Code Editor")
	st.caption(f"Trạng thái hiện tại: {approval_status}")

	st.markdown("#### Giải thích")
	st.info(explanation_text)

	edited_code = st.text_area(
		"Mã nguồn do AI sinh ra",
		value=code_text,
		height=340,
		label_visibility="visible",
		key=widget_key,
	)

	preview_col_1, preview_col_2 = st.columns(2)
	with preview_col_1:
		st.download_button(
			"Download Code",
			data=edited_code,
			file_name="generated_code.py",
			mime="text/x-python",
			width="stretch",
		)
	with preview_col_2:
		st.code(edited_code, language="python")

	return edited_code
