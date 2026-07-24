from __future__ import annotations

from typing import Any

import requests

from services.api_config import BACKEND_BASE_URL


EXECUTE_RUN_URL = f"{BACKEND_BASE_URL}/execute/run"
EXECUTE_RESULT_URL = f"{BACKEND_BASE_URL}/execute/result"


def execute_approved_code(request_id: str, code_text: str, approved: bool = True) -> dict[str, Any]:
	payload = {
		"request_id": request_id,
		"code": code_text,
		"approved": approved,
	}
	# chạy code. /run chỉ trả meta (success/result_type/logs/error),
	# kết quả được backend lưu trên đĩa theo request_id.
	response = requests.post(EXECUTE_RUN_URL, json=payload, timeout=60)

	# 422 = code vi phạm quy tắc bảo mật (import/hàm cấm) -> backend từ chối.
	# Không ném exception (tránh in traceback đỏ lên UI); trả về cờ `rejected`
	# kèm lý do để frontend hiển thị nhẹ nhàng và cho user hỏi tiếp.
	if response.status_code == 422:
		try:
			detail = response.json().get("detail", "Code vi phạm quy tắc an toàn.")
		except ValueError:
			detail = "Code vi phạm quy tắc an toàn."
		return {"success": False, "rejected": True, "error": detail}

	response.raise_for_status()
	result = response.json()

	# load kết quả từ storage theo request_id.
	if result.get("success") and result.get("result_type"):
		result_resp = requests.get(f"{EXECUTE_RESULT_URL}/{request_id}", timeout=60)
		result_resp.raise_for_status()
		result["result_data"] = result_resp.json().get("result_data")

	return result
