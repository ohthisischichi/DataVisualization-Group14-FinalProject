from __future__ import annotations

from typing import Any

import requests

from services.api_config import BACKEND_BASE_URL


LOGS_COLLECTION_URL = f"{BACKEND_BASE_URL}/logs/"


def fetch_logs(request_id: str | None = None) -> list[dict[str, Any]]:
	if request_id:
		url = f"{BACKEND_BASE_URL}/logs/{request_id}"
		response = requests.get(url, timeout=30)
		response.raise_for_status()
		data = response.json()
		if isinstance(data, list):
			return data
		return [data]

	response = requests.get(LOGS_COLLECTION_URL, timeout=30)
	response.raise_for_status()
	data = response.json()
	if isinstance(data, list):
		return data
	if isinstance(data, dict):
		for key in ("items", "logs", "data", "results"):
			value = data.get(key)
			if isinstance(value, list):
				return value
		return [data]
	return []
