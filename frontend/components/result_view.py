from __future__ import annotations

from typing import Any, Sequence

import pandas as pd
import streamlit as st


def _render_result_value(result: Any) -> None:
	if result is None:
		st.info("Chưa có kết quả thực thi. Hãy duyệt code để xem đầu ra.")
		return

	if isinstance(result, pd.DataFrame):
		st.dataframe(result, use_container_width=True)
		chart_source = result.copy()
		numeric_columns = chart_source.select_dtypes(include="number").columns.tolist()
		if numeric_columns:
			label_column = chart_source.columns[0]
			st.bar_chart(chart_source.set_index(label_column)[numeric_columns[0]])
		return

	if isinstance(result, dict):
		st.json(result)
		return

	if isinstance(result, Sequence) and not isinstance(result, (str, bytes)):
		st.write(result)
		return

	st.write(result)


def render_result_panel(
	result: Any,
	error_message: str | None,
	logs: list[dict[str, Any]],
) -> None:
	st.subheader("Result Viewer")
	if error_message:
		st.error(error_message)
	else:
		_render_result_value(result)

	if logs:
		with st.expander("Execution Logs", expanded=False):
			st.write(logs)
