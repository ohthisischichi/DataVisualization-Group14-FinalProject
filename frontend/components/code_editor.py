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
				background: rgba(59, 130, 246, 0.1);
				border-left: 3px solid #3B82F6;
				border-radius: 0 8px 8px 0;
				padding: 8px 12px;
				margin-bottom: 10px;
				font-size: 0.88rem;
				color: #1E40AF;
				font-style: italic;
			">💡 {explanation_text}</div>
			""",
			unsafe_allow_html=True,
		)

	from code_editor import code_editor
	editor_dict = code_editor(
		code_text,
		lang="python",
		theme="light",
		key=widget_key,
		options={"showLineNumbers": True, "showGutter": True}
	)
	
	if editor_dict and isinstance(editor_dict, dict) and "text" in editor_dict and editor_dict["text"]:
		return editor_dict["text"]
	return code_text
