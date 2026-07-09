from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


AI_GENERATE_URL = "https://decidable-lumping-delighted.ngrok-free.dev/ai/generate"


@dataclass(slots=True)
class AIResponse:
    code: str
    explanation: str
    chat_reply: str
    raw: dict[str, Any]


def _build_fallback_response(prompt_text: str) -> AIResponse:
    code = f'''# Giải thích: Mẫu code fallback khi AI API chưa sẵn sàng.
prompt = {prompt_text!r}

# Giải thích: Trả lại prompt để chứng minh luồng dữ liệu end-to-end.
result = {{"prompt": prompt, "status": "mock_response"}}
'''
    explanation = (
        "AI API chưa phản hồi hoặc chưa có định dạng phù hợp. "
        "Frontend đang dùng response mẫu để bạn vẫn có thể duyệt và thử luồng UI."
    )
    chat_reply = (
        "Tôi đã tạo một response mẫu an toàn để demo frontend. "
        "Bạn có thể thay endpoint thật sau khi backend sẵn sàng."
    )
    return AIResponse(code=code, explanation=explanation, chat_reply=chat_reply, raw={})


def generate_ai_response(prompt_text: str) -> dict[str, Any]:
    payload = {
        "prompt": prompt_text,
        "context": {
            "source": "frontend",
            "mode": "mock_fallback_enabled",
        },
    }
    try:
        response = requests.post(AI_GENERATE_URL, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
        code = data.get("code") or data.get("generated_code") or _build_fallback_response(prompt_text).code
        explanation = data.get("explanation") or data.get("message") or _build_fallback_response(prompt_text).explanation
        chat_reply = data.get("chat_reply") or data.get("assistant_reply") or explanation
        return {
            "code": code,
            "explanation": explanation,
            "chat_reply": chat_reply,
            "raw": data,
        }
    except Exception:
        fallback = _build_fallback_response(prompt_text)
        return {
            "code": fallback.code,
            "explanation": fallback.explanation,
            "chat_reply": fallback.chat_reply,
            "raw": fallback.raw,
        }