from __future__ import annotations

import pandas as pd
import streamlit as st


def render_overview_tab() -> None:
	st.subheader("Overview")
	st.caption("Buc tranh tong quan thi truong nha dat theo dashboard mock.")

	kpi_col_1, kpi_col_2, kpi_col_3 = st.columns(3)
	kpi_col_1.metric("Median Price", "45.2", "+2.1%")
	kpi_col_2.metric("Listings", "3,820", "+184")
	kpi_col_3.metric("Active Provinces", "24", "+1")

	trend_df = pd.DataFrame(
		{
			"month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
			"median_price": [40.1, 41.4, 42.6, 43.0, 44.5, 45.2],
		}
	)
	st.line_chart(trend_df.set_index("month"))