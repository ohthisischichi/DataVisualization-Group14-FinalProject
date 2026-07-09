from __future__ import annotations

from typing import Any

import pandas as pd


def _build_mock_result() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "province": ["Hanoi", "Ho Chi Minh City", "Da Nang", "Hai Phong", "Can Tho"],
            "median_price": [52.4, 61.8, 38.2, 34.7, 29.9],
            "sample_count": [120, 150, 90, 70, 55],
        }
    )


def execute_approved_code(code_text: str) -> dict[str, Any]:
    logs: list[dict[str, Any]] = [
        {"step": 1, "message": "Nhận code đã được duyệt."},
        {"step": 2, "message": "Chạy trong chế độ mock local để an toàn cho frontend."},
    ]

    try:
        namespace: dict[str, Any] = {}
        exec(code_text, {}, namespace)
        result = namespace.get("result")
        if result is None:
            result = _build_mock_result()
            logs.append({"step": 3, "message": "Code không trả result, dùng bảng mock mặc định."})
        else:
            logs.append({"step": 3, "message": "Code đã tạo ra biến result thành công."})
        summary = "Thực thi mock hoàn tất."
        return {"result": result, "error": None, "logs": logs, "summary": summary}
    except Exception as exc:
        return {
            "result": None,
            "error": f"Lỗi khi thực thi code mock: {exc}",
            "logs": logs,
            "summary": "Thực thi mock thất bại.",
        }