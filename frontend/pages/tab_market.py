from __future__ import annotations

import pandas as pd
import streamlit as st


def render_market_tab() -> None:
	st.subheader("Market Pulse")
	st.caption("Theo doi bien dong gia va thanh khoan theo phan khuc.")

	segment_df = pd.DataFrame(
		{
			"segment": ["Apartment", "Townhouse", "Land", "Villa"],
			"avg_price": [39.2, 47.1, 34.8, 68.3],
			"volume": [820, 410, 1200, 170],
		}
	)

	left_col, right_col = st.columns(2)
	with left_col:
		st.markdown("#### Avg Price by Segment")
		st.bar_chart(segment_df.set_index("segment")["avg_price"])
	with right_col:
		st.markdown("#### Listing Volume")
		st.bar_chart(segment_df.set_index("segment")["volume"])

	st.dataframe(segment_df, use_container_width=True, hide_index=True)