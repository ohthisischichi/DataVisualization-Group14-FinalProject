from __future__ import annotations

from typing import Any, Sequence

import pandas as pd
import streamlit as st
import plotly.io as pio


def _render_result_value(result: Any) -> None:
	if result is None:
		st.info("Chưa có kết quả thực thi. Hãy duyệt code để xem đầu ra.")
		return

	if isinstance(result, dict):
		if "success" in result or "result_type" in result or "result_data" in result:
			st.markdown(f"**Thành công:** {result.get('success')}")
			if result.get("result_type") is not None:
				st.markdown(f"**Loại kết quả:** {result.get('result_type')}")
			result_data = result.get("result_data")
			if result.get("result_type") == "image" and isinstance(result_data, str):
				import base64
				st.image(base64.b64decode(result_data), width="stretch")
			elif result.get("result_type") == "chart" and isinstance(result_data, str):
				st.plotly_chart(pio.from_json(result_data), width="stretch")
			elif isinstance(result_data, pd.DataFrame):
				st.dataframe(result_data, width="stretch")
			elif isinstance(result_data, dict):
				st.json(result_data)
			elif isinstance(result_data, Sequence) and not isinstance(result_data, (str, bytes)):
				st.write(result_data)
			elif result_data is not None:
				st.write(result_data)
			logs = result.get("logs")
			if logs:
				with st.expander("Nhật ký thực thi", expanded=False):
					st.write(logs)
			if result.get("error"):
				st.error(result.get("error"))
			return

	if isinstance(result, pd.DataFrame):
		st.dataframe(result, width="stretch")
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
	st.subheader("Bộ hiển thị kết quả")
	if error_message:
		st.error(error_message)
	else:
		_render_result_value(result)

	if logs:
		with st.expander("Nhật ký thực thi", expanded=False):
			st.write(logs)
