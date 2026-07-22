import re
import uuid
import httpx
from datetime import datetime
from fastapi import APIRouter, HTTPException

from config import OLLAMA_HOST, OLLAMA_MODEL
from schemas import AIRequest, AIResponse
from routers.logs import save_log_entry, LogEntry

router = APIRouter(tags=["AI"])


DATA_DESCRIPTION = """Bộ dữ liệu (biến `df`, kiểu pandas.DataFrame) chứa ~30.229 tin rao bán \
nhà/bất động sản tại Việt Nam, thu thập từ các trang rao vặt và đã được làm sạch. \
Mỗi dòng là một tin đăng bán một căn nhà. Có cột Day biểu thị ngày trong tháng tin được đăng.

Ý nghĩa các cột (df.columns):
- Address (chuỗi): địa chỉ đầy đủ của bất động sản, ví dụ "Dự án The Empire - Vinhomes Ocean Park 2, Xã Long Hưng, Văn Giang, Hưng Yên".
- Area (số thực, đơn vị m²): diện tích sàn. Khoảng phổ biến 3–595, trung vị ~56 m².
- Frontage (số thực, đơn vị mét): chiều rộng mặt tiền căn nhà. Trung vị ~4.5 m.
- Access Road (số thực, đơn vị mét): độ rộng đường/ngõ trước nhà. Trung vị ~6 m.
- House direction (phân loại): hướng nhà. Giá trị: Đông, Tây, Nam, Bắc, Đông - Nam, Đông - Bắc, Tây - Nam, Tây - Bắc, hoặc "Không xác định" (đa số bị thiếu).
- Balcony direction (phân loại): hướng ban công, cùng tập giá trị như House direction, phần lớn là "Không xác định".
- Bedrooms (số thực): số phòng ngủ. Khoảng 1–9, trung vị 3.
- Bathrooms (số thực): số phòng tắm/vệ sinh. Khoảng 1–9, trung vị 3.
- Legal status (phân loại): tình trạng pháp lý. Giá trị: "Đã có sổ" (đa số), "Hợp đồng mua bán", "Không xác định".
- Furniture state (phân loại): tình trạng nội thất. Giá trị: "Đầy đủ", "Cơ bản", "Không xác định".
- Price (số thực, ĐƠN VỊ TỶ ĐỒNG): giá rao bán. Khoảng 1.0–11.5, trung vị ~5.9 (tức 5.9 tỷ đồng). Đây là cột mục tiêu chính khi phân tích giá.
- Day (số thực/nguyên): ngày đăng tin trong tháng.
- Province (phân loại): tỉnh/thành phố. Nhiều nhất: Hồ Chí Minh, Hà Nội, Bình Dương, Đà Nẵng, Đồng Nai...
- District (phân loại): quận/huyện, tách ra từ Address.
- Detail (chuỗi): phần mô tả/tên dự án tách ra từ Address.
- Price_per_m2 (số thực, đơn vị tỷ đồng/m²): giá trên mỗi mét vuông = Price / Area. Trung vị ~0.10 (tức ~100 triệu/m²).
- Area_Group (phân loại): nhóm diện tích đã chia sẵn. Giá trị: "<30 m²", "30-50 m²", "50-70 m²", "70-90 m²", ">90 m²".
- Price_Segment (phân loại): phân khúc giá đã chia sẵn. Giá trị: "<4 tỷ", "4-6 tỷ", "6-8 tỷ", "8-10 tỷ", ">10 tỷ".

Lưu ý khi viết code:
- Giá tính bằng TỶ ĐỒNG, diện tích bằng m². Khi hiển thị nên ghi rõ đơn vị.
- Các cột phân loại có thể chứa giá trị "Không xác định" (nghĩa là thiếu dữ liệu) — cân nhắc loại bỏ khi thống kê hướng nhà, pháp lý, nội thất.
- Có thể lọc theo Province/District để phù hợp bối cảnh dashboard người dùng đang xem.
"""


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

Mô tả bộ dữ liệu:
{data_description}

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
        data_description=DATA_DESCRIPTION,
        current_tab=ctx.current_tab if ctx else "N/A",
        province=ctx.selected_province if ctx else "N/A",
        district=ctx.selected_district if ctx else "N/A",
        filters=ctx.active_filters if ctx and ctx.active_filters else "Không có",
    )
    return f"{system_prompt}\n\nYêu cầu người dùng: {request.prompt}"


# Bắt một khối fence ```<lang> ... ```; group("lang") là nhãn (có thể rỗng),
# group("body") là nội dung bên trong.
_FENCE_RE = re.compile(
    r"```[ \t]*(?P<lang>[a-zA-Z0-9_+-]*)[ \t]*\r?\n(?P<body>.*?)```",
    re.DOTALL,
)

_CODE_LANGS = {"code", "python", "py", "python3"}
_EXPLANATION_LANGS = {"explanation", "explain", "giaithich", "text"}


def parse_model_output(raw_text: str) -> tuple[str, str]:
    """
    Tách code và explanation ra khỏi output thô của model.

    Kỳ vọng format có ```code ... ``` và ```explanation ... ```, nhưng model local
    (Qwen) thường không tuân thủ chặt: có thể dùng ```python, ```py hoặc ``` trơn.
    Vì vậy, duyệt TẤT CẢ các khối fence:
      - Khối có nhãn code/python/py -> gán vào code.
      - Khối có nhãn explanation/... -> gán vào explanation.
      - Khối không nhãn -> nếu chưa có code thì coi là code (fallback phổ biến).
    Phần văn bản ngoài mọi fence được dùng làm explanation nếu không có khối
    explanation tường minh.
    """
    code = ""
    explanation = ""

    blocks = list(_FENCE_RE.finditer(raw_text))

    for m in blocks:
        lang = m.group("lang").lower()
        body = m.group("body").strip()
        if lang in _CODE_LANGS:
            if not code:
                code = body
        elif lang in _EXPLANATION_LANGS:
            if not explanation:
                explanation = body
        elif not lang and not code:
            # Khối fence trơn không nhãn: nhiều khả năng là code.
            code = body

    if not explanation:
        # Không có khối explanation tường minh -> lấy phần text nằm ngoài mọi fence.
        text_outside = _FENCE_RE.sub("", raw_text).strip()
        explanation = text_outside if text_outside else raw_text.strip()

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

    # DEBUG: in raw response ra console + ghi ra file để soi khi code bị rỗng.
    print("=" * 60)
    print(f"[AI raw response] request_id={request_id}")
    print(raw_text)
    print("=" * 60, flush=True)
    try:
        with open("storage/last_raw_response.txt", "w", encoding="utf-8") as f:
            f.write(f"request_id: {request_id}\nprompt: {request.prompt}\n")
            f.write("=" * 60 + "\n")
            f.write(raw_text)
    except OSError:
        pass

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