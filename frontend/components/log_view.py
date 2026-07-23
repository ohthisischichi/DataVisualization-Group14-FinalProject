from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render_log_panel(logs: list[dict[str, Any]]) -> None:
	st.subheader("Lịch sử")
	if not logs:
		st.caption("Chưa có log nào được ghi nhận.")
		return

	log_frame = pd.DataFrame(logs)
	if "timestamp" not in log_frame.columns:
		log_frame["timestamp"] = None
	st.dataframe(log_frame, width="stretch", hide_index=True)
