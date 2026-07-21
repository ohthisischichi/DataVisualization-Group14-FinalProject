import re

# ```lang\n body ``` : group("lang") là nhãn ngôn ngữ (có thể rỗng),
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
