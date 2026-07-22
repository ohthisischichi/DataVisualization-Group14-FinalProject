import uuid
import httpx
from datetime import datetime
from fastapi import APIRouter, HTTPException

from config import OLLAMA_HOST, OLLAMA_MODEL
from schemas import AIRequest, AIResponse, InterpretRequest, InterpretResponse
from routers.logs import save_log_entry, LogEntry
from model_parsing import parse_model_output
from routers.execute import _result_for_llm
from routers.logs import get_log_entry

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

QUY TẮC BẮT BUỘC VỀ KẾT QUẢ:
Code PHẢI gán kết quả cuối cùng vào một biến tên đúng là `result`.
Hệ thống CHỈ đọc biến `result`, gán vào tên khác sẽ không hiển thị được gì.
Tùy yêu cầu người dùng, `result` có thể là:
- một con số hoặc chuỗi — khi chỉ cần trả về giá trị thống kê
- một pandas DataFrame — khi cần bảng số liệu hoặc bảng so sánh
- một plotly Figure hoặc matplotlib Figure — khi người dùng cần biểu đồ
Chỉ vẽ biểu đồ khi yêu cầu thực sự cần trực quan hóa; nếu chỉ hỏi số liệu thì trả
thẳng số hoặc DataFrame, không cần vẽ.

QUY TẮC KHI DÙNG CỘT PHÂN LOẠI:
- Area_Group và Price_Segment đã được chia nhóm sẵn — dùng trực tiếp, KHÔNG tự nhóm lại.
- Chỉ dùng đúng các giá trị nhãn đã liệt kê bên dưới. KHÔNG tự đổi tên nhãn
  (ví dụ KHÔNG map "<30 m²" thành "Under 30"), vì làm vậy sẽ lệch khỏi dữ liệu thật.
- `area_groups` hay bất kỳ list Python nào chỉ được cắt bằng chỉ số nguyên,
  KHÔNG cắt bằng chuỗi. Muốn lọc theo nhãn thì dùng pandas (.reindex(), .isin()).

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

INTERPRET_SYSTEM_PROMPT = """Bạn là trợ lý phân tích dữ liệu bất động sản Việt Nam.
Người dùng đã hỏi một câu, hệ thống đã chạy code và thu được KẾT QUẢ bên dưới.
Nhiệm vụ của bạn: trả lời TRỰC TIẾP câu hỏi bằng tiếng Việt, chi tiết, rõ ràng.

QUY TẮC:
- CHỈ dùng số liệu có trong kết quả / hình ảnh bên dưới. TUYỆT ĐỐI không bịa thêm số.
- Nêu rõ con số và đơn vị (giá = tỷ đồng, diện tích = m²).
- Nếu có hình biểu đồ kèm theo, hãy đọc số liệu từ biểu đồ để trả lời.
- Không viết lại code, không giải thích code. Chỉ trả lời câu hỏi.

Câu hỏi của người dùng:
{prompt}

Kết quả thực thi:
{result_text}

Log in ra trong quá trình chạy (nếu có):
{logs}
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

async def _call_ollama(prompt: str, images: list[str] | None = None, timeout: float = 60.0) -> str:
    """Gọi model Ollama local, trả về text 'response'.
    """
    payload: dict = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "num_ctx": 16384,
            "temperature": 0.1,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        },
    }
    if images:
        payload["images"] = images

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Không gọi được model Qwen local: {exc}")

    return data.get("response") or data.get("thinking") or ""


@router.post("/generate", response_model=AIResponse)
async def generate_code(request: AIRequest):
    """
    Endpoint chính của AI API.
    """
    full_prompt = build_prompt(request)
    request_id = str(uuid.uuid4())

    raw_text = await _call_ollama(full_prompt)

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


async def interpret_execution(request_id: str, logs: str = "") -> str:
    entry = get_log_entry(request_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy log cho request_id này.")

    result_text, image_b64 = _result_for_llm(request_id)

    prompt = INTERPRET_SYSTEM_PROMPT.format(
        prompt=entry.prompt,
        result_text=result_text,
        logs=logs or "(không có)",
    )
    return await _call_ollama(
        prompt,
        images=[image_b64] if image_b64 else None,
        timeout=120.0,
    )

@router.post("/interpret", response_model=InterpretResponse)
async def interpret_result(request: InterpretRequest):
    answer = await interpret_execution(request.request_id)
    return InterpretResponse(request_id=request.request_id, answer=answer)

