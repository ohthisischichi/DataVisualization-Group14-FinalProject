from __future__ import annotations

import sys
from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests

_BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from model_parsing import parse_model_output


AI_GENERATE_URL = "https://decidable-lumping-delighted.ngrok-free.dev/ai/generate"
DATA_PATH = Path(__file__).resolve().parents[2] / "Data" / "processed" / "house_price_clean.csv"


@lru_cache(maxsize=1)
def _load_dataset_schema() -> dict[str, Any]:
    data_frame = pd.read_csv(DATA_PATH)
    columns: list[dict[str, Any]] = []
    for column_name in data_frame.columns:
        series = data_frame[column_name]
        if pd.api.types.is_integer_dtype(series):
            column_type = "integer"
        elif pd.api.types.is_float_dtype(series):
            column_type = "float"
        else:
            column_type = "text"

        column_info: dict[str, Any] = {
            "name": column_name,
            "type": column_type,
            "non_null_count": int(series.notna().sum()),
        }
        if column_type == "text":
            unique_values = series.dropna().astype(str).value_counts().head(5).index.tolist()
            column_info["sample_values"] = unique_values
        columns.append(column_info)

    selected_preview_columns = [column for column in ["Province", "District", "Ward", "Area", "Price", "Price_per_m2", "Area_Group", "Price_Segment"] if column in data_frame.columns]
    preview_records = data_frame[selected_preview_columns].head(5).to_dict(orient="records") if selected_preview_columns else []

    return {
        "dataset_name": DATA_PATH.name,
        "table_name": "house_price_clean",
        "description": "Bảng dữ liệu nhà đất đã làm sạch, đã được tự động đọc từ file CSV và chỉ giữ đúng các cột thực có trong dữ liệu.",
        "columns": columns,
        "preview": preview_records,
    }


def _build_column_aliases(table_schema: dict[str, Any]) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for column in table_schema.get("columns", []):
        column_name = column["name"]
        normalized_name = column_name.lower()

        if column_name == "Address":
            alias_list = ["địa chỉ", "address"]
        elif column_name == "Area":
            alias_list = ["diện tích", "area"]
        elif column_name == "Frontage":
            alias_list = ["mặt tiền", "frontage"]
        elif column_name == "Access Road":
            alias_list = ["đường vào", "access road"]
        elif column_name == "House direction":
            alias_list = ["hướng nhà", "house direction"]
        elif column_name == "Balcony direction":
            alias_list = ["hướng ban công", "balcony direction"]
        elif column_name == "Floors":
            alias_list = ["số tầng", "floors"]
        elif column_name == "Bedrooms":
            alias_list = ["số phòng ngủ", "bedrooms"]
        elif column_name == "Bathrooms":
            alias_list = ["số phòng tắm", "bathrooms"]
        elif column_name == "Legal status":
            alias_list = ["pháp lý", "tình trạng pháp lý", "legal status"]
        elif column_name == "Furniture state":
            alias_list = ["nội thất", "tình trạng nội thất", "furniture state"]
        elif column_name == "Price":
            alias_list = ["giá", "price"]
        elif column_name == "Province":
            alias_list = ["tỉnh", "thành phố", "province"]
        elif column_name == "District":
            alias_list = ["quận huyện", "quận", "huyện", "district"]
        elif column_name == "Ward":
            alias_list = ["phường xã", "phường", "xã", "ward"]
        elif column_name == "Detail":
            alias_list = ["chi tiết", "detail"]
        elif column_name == "Price_per_m2":
            alias_list = ["giá trên m2", "giá/m2", "price per m2", "price_per_m2"]
        elif column_name == "Area_Group":
            alias_list = ["nhóm diện tích", "area group", "area_group"]
        elif column_name == "Price_Segment":
            alias_list = ["nhóm giá", "price segment", "price_segment"]
        else:
            alias_list = [normalized_name]

        aliases[column_name] = alias_list

    return aliases


@dataclass(slots=True)
class AIResponse:
    request_id: str | None
    code: str
    explanation: str
    status: str | None
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
    return AIResponse(request_id=None, code=code, explanation=explanation, status="mock", chat_reply=chat_reply, raw={})


def generate_ai_response(prompt_text: str) -> dict[str, Any]:
    table_schema = _load_dataset_schema()
    column_aliases = _build_column_aliases(table_schema)
    payload = {
        "prompt": prompt_text,
        "context": {
            "source": "frontend",
            "mode": "mock_fallback_enabled",
            "table_schema": table_schema,
            "column_aliases": column_aliases,
            "frontend_instruction": (
                "Frontend chỉ cung cấp prompt người dùng và ngữ cảnh dashboard. Ưu tiên code bám sát tab, "
                "bộ lọc, và chỉ dùng các cột thật trong schema."
            ),
        },
    }
    try:
        response = requests.post(AI_GENERATE_URL, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
        fallback = _build_fallback_response(prompt_text)

        raw_text = data.get("response") or data.get("thinking")
        if raw_text:
            code, explanation = parse_model_output(raw_text)
        else:
            code = data.get("code") or data.get("generated_code")
            explanation = data.get("explanation") or data.get("message")

        code = code or fallback.code
        explanation = explanation or fallback.explanation

        chat_reply = data.get("chat_reply") or data.get("assistant_reply") or explanation
        return {
            "request_id": data.get("request_id"),
            "code": code,
            "explanation": explanation,
            "status": data.get("status"),
            "chat_reply": chat_reply,
            "raw": data,
        }
    except Exception:
        fallback = _build_fallback_response(prompt_text)
        return {
            "request_id": fallback.request_id,
            "code": fallback.code,
            "explanation": fallback.explanation,
            "status": fallback.status,
            "chat_reply": fallback.chat_reply,
            "raw": fallback.raw,
        }