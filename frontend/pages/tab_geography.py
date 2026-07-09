from __future__ import annotations

import pandas as pd
import streamlit as st


def render_geography_tab() -> None:
	st.subheader("Geo Insights")
	st.caption("So sanh cac khu vuc theo gia trung vi va toc do tang truong.")

	geo_df = pd.DataFrame(
		{
			"province": ["Hanoi", "Ho Chi Minh City", "Da Nang", "Hai Phong", "Can Tho"],
			"median_price": [52.4, 61.8, 38.2, 34.7, 29.9],
			"growth_rate": [4.1, 3.7, 2.8, 2.3, 1.9],
		}
	)

	st.bar_chart(geo_df.set_index("province")["median_price"])
	st.dataframe(geo_df, use_container_width=True, hide_index=True)