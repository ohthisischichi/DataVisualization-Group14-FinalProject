from __future__ import annotations

from typing import Any

import requests

from services.api_config import BACKEND_BASE_URL


EXECUTE_RUN_URL = f"{BACKEND_BASE_URL}/execute/run"


def execute_approved_code(request_id: str, code_text: str, approved: bool = True) -> dict[str, Any]:
	payload = {
		"request_id": request_id,
		"code": code_text,
		"approved": approved,
	}
	response = requests.post(EXECUTE_RUN_URL, json=payload, timeout=60)
	response.raise_for_status()
	return response.json()
