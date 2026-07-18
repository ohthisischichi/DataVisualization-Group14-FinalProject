import uuid
import httpx
from datetime import datetime
from fastapi import APIRouter, HTTPException

from config import OLLAMA_HOST, OLLAMA_MODEL
from schemas import AIRequest, AIResponse
from routers.logs import save_log_entry, LogEntry

router = APIRouter(tags=["AI"])


SYSTEM_PROMPT_TEMPLATE = """Bạn là trợ lý phân tích dữ liệu bất động sản Việt Nam.
Bạn CHỈ được:
- Đề xuất ý tưởng phân tích
- Viết code Python để xử lý/trực quan hóa dữ liệu đã có sẵn (biến `df`)
- Giải thích code bằng ngôn ngữ tự nhiên

Bạn TUYỆT ĐỐI KHÔNG được:
- Tự thêm số liệu không có trong dataset
- Tự ý thay đổi dữ liệu gốc (không ghi đè file, không xóa dòng ngoài yêu cầu)
- Import bất kỳ thư viện nào ngoài: pandas, numpy, matplotlib, plotly, math, statistics
- Gọi các hàm nguy hiểm: open(), exec(), eval(), os, sys, subprocess, socket, __import__

Ngữ cảnh dashboard hiện tại:
- Tab đang xem: {current_tab}
- Tỉnh/thành đang chọn: {province}
- Quận/huyện đang chọn: {district}
- Bộ lọc đang áp dụng: {filters}

Luôn trả lời theo đúng format:
```code
<code python>
```
```explanation
<giải thích ngắn gọn bằng tiếng Việt, có comment trong code>
```
"""


def build_prompt(request: AIRequest) -> str:
    ctx = request.context
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        current_tab=ctx.current_tab if ctx else "N/A",
        province=ctx.selected_province if ctx else "N/A",
        district=ctx.selected_district if ctx else "N/A",
        filters=ctx.active_filters if ctx and ctx.active_filters else "Không có",
    )
    return f"{system_prompt}\n\nYêu cầu người dùng: {request.prompt}"


def parse_model_output(raw_text: str) -> tuple[str, str]:
    """
    Tách code và explanation ra khỏi output thô của model.
    Kỳ vọng model trả về theo format có ```code ... ``` và ```explanation ... ```.
    Nếu model không tuân thủ đúng format, fallback: coi toàn bộ là explanation, code rỗng.
    """
    code = ""
    explanation = raw_text.strip()

    if "```code" in raw_text:
        try:
            code_block = raw_text.split("```code", 1)[1]
            code = code_block.split("```", 1)[0].strip()
        except IndexError:
            code = ""

    if "```explanation" in raw_text:
        try:
            exp_block = raw_text.split("```explanation", 1)[1]
            explanation = exp_block.split("```", 1)[0].strip()
        except IndexError:
            pass

    return code, explanation


@router.post("/generate", response_model=AIResponse)
async def generate_code(request: AIRequest):
    """
    Endpoint chính của AI API.
    """
    full_prompt = build_prompt(request)
    request_id = str(uuid.uuid4())

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": full_prompt,
                    "stream": False,
                    "think": False,
                    "options": {"num_ctx": 16384},
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Không gọi được model Qwen local: {exc}")

    raw_text = data.get("response") or data.get("thinking") or ""
    code, explanation = parse_model_output(raw_text)

    # Ghi log ngay khi generate code, trước khi được duyệt
    save_log_entry(
        LogEntry(
            request_id=request_id,
            prompt=request.prompt,
            code=code,
            explanation=explanation,
            result_summary=None,
            status="pending_approval",
            timestamp=datetime.now().isoformat(),
        )
    )

    return AIResponse(
        request_id=request_id,
        code=code,
        explanation=explanation,
        status="pending_approval",
    )