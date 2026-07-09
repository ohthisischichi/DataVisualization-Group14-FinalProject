from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render_log_panel(logs: list[dict[str, Any]]) -> None:
	st.subheader("Logs")
	if not logs:
		st.caption("Chưa có log nào được ghi nhận.")
		return

	log_frame = pd.DataFrame(logs)
	st.dataframe(log_frame, use_container_width=True, hide_index=True)
