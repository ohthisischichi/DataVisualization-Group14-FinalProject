from __future__ import annotations

import pandas as pd
import streamlit as st


def render_trends_tab() -> None:
	st.subheader("Trend Lab")
	st.caption("Khung thu nghiem xu huong va gia lap ket qua phan tich.")

	trend_df = pd.DataFrame(
		{
			"quarter": ["Q1", "Q2", "Q3", "Q4"],
			"demand_index": [91, 98, 105, 110],
			"supply_index": [88, 90, 94, 97],
		}
	)

	st.area_chart(trend_df.set_index("quarter"))
	st.dataframe(trend_df, use_container_width=True, hide_index=True)