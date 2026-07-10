import ast
import io
import contextlib
import multiprocessing
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, HTTPException

from config import ALLOWED_IMPORTS, EXECUTE_TIMEOUT_SECONDS, DATASET_PATH
from schemas import ExecuteRequest, ExecuteResult
from routers.logs import save_log_entry, get_log_entry, LogEntry

router = APIRouter(tags=["Execute"])


FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__",
    "input", "globals", "locals", "vars", "getattr", "setattr", "delattr",
}


class CodeValidationError(Exception):
    pass


def validate_code(code: str) -> None:
    """
    Duyệt AST của code để:
    - Chặn import ngoài whitelist
    - Chặn gọi các hàm nguy hiểm (open, exec, eval, __import__, ...)
    Trả về CodeValidationError nếu vi phạm
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


def _run_in_subprocess(code: str, dataset_path: str, queue: multiprocessing.Queue) -> None:
    """
    Hàm chạy trong process con: load dataset vào biến df, exec code,
    bắt output/print và kết quả (biến 'result' nếu code có định nghĩa),
    gửi kết quả về qua queue.
    """
    import pandas as pd  # noqa: F401  (nạp lại trong subprocess)
    import numpy as np   # noqa: F401
    try:
        import plotly.express as px  # noqa: F401
        import plotly.graph_objects as go  # noqa: F401
    except ImportError:
        pass
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: F401
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
            if name not in FORBIDDEN_NAMES
        } if not isinstance(__builtins__, dict) else {
            k: v for k, v in __builtins__.items() if k not in FORBIDDEN_NAMES
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

        result_type = None
        result_data = None

        if result is not None:
            # Cố gắng nhận diện loại kết quả để trả về đúng format cho Frontend
            type_name = type(result).__name__
            if type_name == "DataFrame":
                result_type = "dataframe"
                result_data = result.to_dict(orient="records")
            elif type_name in ("Figure",):  # plotly.graph_objects.Figure
                result_type = "chart"
                result_data = result.to_json()
            else:
                result_type = "text"
                result_data = str(result)

        queue.put({
            "success": True,
            "result_type": result_type,
            "result_data": result_data,
            "logs": stdout_buffer.getvalue(),
            "error": None,
        })
    except Exception as exc:
        queue.put({
            "success": False,
            "result_type": None,
            "result_data": None,
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
        args=(request.code, DATASET_PATH, queue),
    )
    process.start()
    process.join(timeout=EXECUTE_TIMEOUT_SECONDS)

    if process.is_alive():
        process.terminate()
        process.join()
        error_msg = f"Code chạy quá {EXECUTE_TIMEOUT_SECONDS}s và đã bị hủy (timeout)."
        _update_log_status(request.request_id, status="error", result_summary=error_msg)
        return ExecuteResult(request_id=request.request_id, success=False, error=error_msg)

    if queue.empty():
        error_msg = "Process con thoát bất thường (có thể do lỗi hệ thống / segfault)."
        _update_log_status(request.request_id, status="error", result_summary=error_msg)
        return ExecuteResult(request_id=request.request_id, success=False, error=error_msg)

    output = queue.get()

    status = "executed" if output["success"] else "error"
    summary = output.get("error") or f"Kết quả dạng: {output.get('result_type')}"
    _update_log_status(request.request_id, status=status, result_summary=summary)

    return ExecuteResult(
        request_id=request.request_id,
        success=output["success"],
        result_type=output.get("result_type"),
        result_data=output.get("result_data"),
        logs=output.get("logs", ""),
        error=output.get("error"),
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