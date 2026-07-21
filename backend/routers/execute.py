import ast
import io
import os
import re
import json
import base64
import contextlib
import multiprocessing
from queue import Empty
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, HTTPException

from config import ALLOWED_IMPORTS, EXECUTE_TIMEOUT_SECONDS, DATASET_PATH, RESULTS_DIR
from schemas import ExecuteRequest, ExecuteResult
from routers.logs import save_log_entry, get_log_entry, LogEntry

router = APIRouter(tags=["Execute"])


FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__",
    "input", "globals", "locals", "vars", "getattr", "setattr", "delattr",
}

# Keep __import__ for standard 'import' statements to work, 
# but block explicit __import__() calls using AST validator.
_RUNTIME_REQUIRED_BUILTINS = {"__import__"}


class CodeValidationError(Exception):
    pass


def validate_code(code: str) -> None:
    """Duyệt AST để chặn import ngoài whitelist và các hàm nguy hiểm (open, exec, eval...).

    Raise CodeValidationError nếu vi phạm.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise CodeValidationError(f"Code có lỗi cú pháp: {exc}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in {m.split(".")[0] for m in ALLOWED_IMPORTS}:
                    raise CodeValidationError(f"Thư viện không được phép: {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] not in {m.split(".")[0] for m in ALLOWED_IMPORTS}:
                raise CodeValidationError(f"Thư viện không được phép: {node.module}")

        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise CodeValidationError(f"Hàm không được phép sử dụng: {node.id}")

        elif isinstance(node, ast.Attribute):
            # Chặn kiểu os.system, subprocess.run, shutil.rmtree, v.v.
            if isinstance(node.value, ast.Name) and node.value.id in {"os", "sys", "subprocess", "shutil", "socket"}:
                raise CodeValidationError(f"Truy cập module nguy hiểm: {node.value.id}.{node.attr}")


def _safe_result_dir(request_id: str) -> str:
    """Đường dẫn thư mục kết quả của request_id; chỉ cho phép chữ, số, '-', '_'
    để tránh path traversal."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", request_id or ""):
        raise ValueError(f"request_id không hợp lệ: {request_id!r}")
    return os.path.join(RESULTS_DIR, request_id)


def _persist_result(request_id: str, result) -> str | None:
    """
    Ghi kết quả xuống đĩa theo từng loại và trả về result_type.
    - DataFrame -> data.json (records)
    - plotly Figure -> chart.json (to_json)
    - matplotlib Figure -> image.png (savefig trực tiếp, không qua base64 trong RAM)
    - còn lại -> text.txt
    """
    if result is None:
        return None

    module = type(result).__module__ or ""
    type_name = type(result).__name__
    result_dir = _safe_result_dir(request_id)
    os.makedirs(result_dir, exist_ok=True)

    if type_name == "DataFrame":
        with open(os.path.join(result_dir, "data.json"), "w", encoding="utf-8") as f:
            json.dump(result.to_dict(orient="records"), f, ensure_ascii=False)
        return "dataframe"
    if module.startswith("plotly"):
        with open(os.path.join(result_dir, "chart.json"), "w", encoding="utf-8") as f:
            f.write(result.to_json())
        return "chart"
    if module.startswith("matplotlib"):
        result.savefig(
            os.path.join(result_dir, "image.png"),
            format="png", bbox_inches="tight", dpi=120,
        )
        return "image"

    with open(os.path.join(result_dir, "text.txt"), "w", encoding="utf-8") as f:
        f.write(str(result))
    return "text"


def _load_result_data(result_dir: str) -> tuple[str | None, object]:
    """Đọc lại payload từ đĩa, trả về (result_type, result_data) đúng shape frontend cần."""
    chart_path = os.path.join(result_dir, "chart.json")
    image_path = os.path.join(result_dir, "image.png")
    data_path = os.path.join(result_dir, "data.json")
    text_path = os.path.join(result_dir, "text.txt")

    if os.path.exists(chart_path):
        with open(chart_path, "r", encoding="utf-8") as f:
            return "chart", f.read()
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            return "image", base64.b64encode(f.read()).decode("ascii")
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            return "dataframe", json.load(f)
    if os.path.exists(text_path):
        with open(text_path, "r", encoding="utf-8") as f:
            return "text", f.read()
    return None, None


def _run_in_subprocess(code: str, dataset_path: str, request_id: str, queue: multiprocessing.Queue) -> None:
    """
    Hàm chạy trong process con: load dataset vào biến df, exec code,
    bắt output/print và kết quả (biến 'result' nếu code có định nghĩa),
    gửi kết quả về qua queue.
    """
    import pandas as pd  # noqa: F401  (nạp lại trong subprocess)
    import numpy as np   # noqa: F401

    # Ghi đè show để lưu fingure thay vì mở tab trình duyệt / cửa sổ GUI.
    _captured = {"fig": None}
    try:
        import plotly.express as px  # noqa: F401
        import plotly.graph_objects as go  # noqa: F401

        def _plotly_show(self, *args, **kwargs):
            _captured["fig"] = self
        go.Figure.show = _plotly_show
    except ImportError:
        pass
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: F401

        plt.show = lambda *args, **kwargs: None
    except ImportError:
        pass

    try:
        df = pd.read_csv(dataset_path)
    except Exception as exc:
        queue.put({"success": False, "error": f"Không load được dataset: {exc}", "logs": ""})
        return

    safe_globals = {
        "__builtins__": {
            name: getattr(__builtins__, name)
            for name in dir(__builtins__)
            if name not in FORBIDDEN_NAMES or name in _RUNTIME_REQUIRED_BUILTINS
        } if not isinstance(__builtins__, dict) else {
            k: v for k, v in __builtins__.items()
            if k not in FORBIDDEN_NAMES or k in _RUNTIME_REQUIRED_BUILTINS
        },
        "pd": pd,
        "np": np,
        "df": df,
    }
    if "px" in dir():
        safe_globals["px"] = px
    if "go" in dir():
        safe_globals["go"] = go
    if "plt" in dir():
        safe_globals["plt"] = plt

    stdout_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buffer):
            exec(code, safe_globals)
        result = safe_globals.get("result")

        # Fallback khi model chỉ gọi fig.show()/plt.show() mà không gán `result`.
        if result is None:
            result = _captured["fig"]        # figure bắt được từ fig.show()
        if result is None:
            # Quét globals tìm một Figure plotly/matplotlib bất kỳ đã tạo.
            for value in safe_globals.values():
                module = type(value).__module__ or ""
                if type(value).__name__ == "Figure" and (
                    module.startswith("plotly") or module.startswith("matplotlib")
                ):
                    result = value
                    break
        if result is None and "plt" in dir() and plt.get_fignums():
            result = plt.gcf()

        # Ghi kết qủa vào ổ cứng
        result_type = _persist_result(request_id, result)

        queue.put({
            "success": True,
            "result_type": result_type,
            "logs": stdout_buffer.getvalue(),
            "error": None,
        })
    except Exception as exc:
        queue.put({
            "success": False,
            "result_type": None,
            "logs": stdout_buffer.getvalue(),
            "error": f"{type(exc).__name__}: {exc}",
        })


@router.post("/run", response_model=ExecuteResult)
async def execute_code(request: ExecuteRequest):
    """
    Endpoint chính của Execute API.
    Chỉ thực thi khi approved = true.
    """
    if not request.approved:
        raise HTTPException(status_code=400, detail="Code chưa được phê duyệt (approved = false).")

    # validate code trước khi chạy
    try:
        validate_code(request.code)
    except CodeValidationError as exc:
        error_msg = str(exc)
        _update_log_status(request.request_id, status="rejected", result_summary=error_msg)
        raise HTTPException(status_code=422, detail=error_msg)

    # chạy code trong process con riêng
    queue: multiprocessing.Queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=_run_in_subprocess,
        args=(request.code, DATASET_PATH, request.request_id, queue),
    )
    process.start()

    # Phải ĐỌC queue TRƯỚC khi join: pipe có buffer giới hạn nên payload lớn sẽ
    # chặn child, join() trước rồi mới get() là deadlock.
    try:
        output = queue.get(timeout=EXECUTE_TIMEOUT_SECONDS)
    except Empty:
        # Còn sống mà chưa trả kết quả => timeout. Đã chết mà queue rỗng => thoát bất thường (segfault / lỗi hệ thống, không kịp put gì lên queue).
        timed_out = process.is_alive()
        if timed_out:
            process.terminate()
        process.join()
        if timed_out:
            error_msg = f"Code chạy quá {EXECUTE_TIMEOUT_SECONDS}s và đã bị hủy (timeout)."
        else:
            error_msg = "Process con thoát bất thường (có thể do lỗi hệ thống / segfault)."
        _update_log_status(request.request_id, status="error", result_summary=error_msg)
        return ExecuteResult(request_id=request.request_id, success=False, error=error_msg)

    # Đã rút được kết quả, chờ child kết thúc gọn (đừng để join treo vô hạn).
    process.join(timeout=5)
    if process.is_alive():
        process.terminate()
        process.join()

    success = output["success"]
    error = output.get("error")
    logs = output.get("logs", "")

    # Code chạy trót lọt nhưng không gán `result` và cũng không print gì => màn hình
    # trống. Báo lỗi rõ ràng thay vì "thành công" im lặng, để phân biệt được
    # "model viết sai contract" với "model viết code lỗi".
    if success and output.get("result_type") is None and not logs.strip():
        success = False
        error = (
            "Code chạy xong nhưng không gán biến `result` và cũng không in ra gì "
            "- không có kết quả để hiển thị."
        )

    status = "executed" if success else "error"
    summary = error or f"Kết quả dạng: {output.get('result_type')}"
    _update_log_status(request.request_id, status=status, result_summary=summary)

    # Không trả result_data ở đây: payload nằm trên đĩa, frontend load qua
    # GET /execute/result/{request_id}. Response này chỉ mang meta gọn nhẹ.
    return ExecuteResult(
        request_id=request.request_id,
        success=success,
        result_type=output.get("result_type"),
        result_data=None,
        logs=logs,
        error=error,
    )


@router.get("/result/{request_id}", response_model=ExecuteResult)
async def get_result(request_id: str):
    """
    Load lại kết quả đã lưu trên đĩa theo request_id (chart/ảnh/bảng/text).
    """
    try:
        result_dir = _safe_result_dir(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not os.path.isdir(result_dir):
        raise HTTPException(status_code=404, detail="Không tìm thấy kết quả cho request_id này.")

    result_type, result_data = _load_result_data(result_dir)
    if result_type is None:
        raise HTTPException(status_code=404, detail="Không có payload kết quả trên đĩa.")

    return ExecuteResult(
        request_id=request_id,
        success=True,
        result_type=result_type,
        result_data=result_data,
    )


def _update_log_status(request_id: str, status: str, result_summary: str) -> None:
    """Cập nhật lại log entry gốc (đã tạo lúc gọi AI API) với kết quả thực thi."""
    entry = get_log_entry(request_id)
    if entry is None:
        # edge case: execute được gọi mà không qua AI API trước đó
        entry = LogEntry(
            request_id=request_id,
            prompt="(không rõ, không có log AI gốc)",
            code="",
            explanation="",
            result_summary=result_summary,
            status=status,
            timestamp=datetime.now().isoformat(),
        )
    else:
        entry.status = status
        entry.result_summary = result_summary
        entry.timestamp = datetime.now().isoformat()

    save_log_entry(entry)