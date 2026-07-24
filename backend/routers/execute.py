import ast
import io
import os
import re
import json
import base64
import traceback
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

class CodeSyntaxError(CodeValidationError):
    """Lỗi cú pháp code (ast.parse thất bại). Khác lỗi bảo mật (import/hàm cấm):
    đây là lỗi AI có thể tự sửa, nên được đối xử như lỗi runtime chứ không reject."""
    pass

def validate_code(code: str) -> None:
    """Duyệt AST để chặn import ngoài whitelist và các hàm nguy hiểm (open, exec, eval...).

    Raise CodeSyntaxError nếu code sai cú pháp, CodeValidationError nếu vi phạm bảo mật.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise CodeSyntaxError(f"Code có lỗi cú pháp: {exc}")

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


def _persist_one(obj, result_dir: str, stem: str) -> tuple[str, str]:
    """Ghi MỘT artifact xuống đĩa với tên file bắt đầu bằng `stem`.
    Trả về (result_type, tên_file).
    - DataFrame -> .data.json (records)
    - plotly Figure -> .chart.json (to_json)
    - matplotlib Figure -> .image.png (savefig trực tiếp)
    - còn lại -> .text.txt
    """
    module = type(obj).__module__ or ""
    type_name = type(obj).__name__

    if type_name == "DataFrame":
        fname = f"{stem}.data.json"
        with open(os.path.join(result_dir, fname), "w", encoding="utf-8") as f:
            json.dump(obj.to_dict(orient="records"), f, ensure_ascii=False)
        return "dataframe", fname
    if module.startswith("plotly"):
        fname = f"{stem}.chart.json"
        with open(os.path.join(result_dir, fname), "w", encoding="utf-8") as f:
            f.write(obj.to_json())
        return "chart", fname
    if module.startswith("matplotlib"):
        fname = f"{stem}.image.png"
        obj.savefig(
            os.path.join(result_dir, fname),
            format="png", bbox_inches="tight", dpi=120,
        )
        return "image", fname

    fname = f"{stem}.text.txt"
    with open(os.path.join(result_dir, fname), "w", encoding="utf-8") as f:
        f.write(str(obj))
    return "text", fname


def _as_parts(result) -> list[tuple[str, object]] | None:
    """Nếu `result` là container gồm nhiều thành phần (dict/list/tuple), trả về
    list (tên, object) bỏ qua các phần None; ngược lại trả None (artifact đơn).
    Khóa dict được dùng làm tiêu đề hiển thị của từng thành phần."""
    if isinstance(result, dict):
        return [(str(k), v) for k, v in result.items() if v is not None]
    if isinstance(result, (list, tuple)):
        return [(f"Kết quả {i + 1}", v) for i, v in enumerate(result) if v is not None]
    return None


def _persist_result(request_id: str, result) -> str | None:
    """
    Ghi kết quả xuống đĩa và trả về result_type.
    Luôn ghi kèm manifest.json mô tả từng thành phần [{name, type, file}].
    - 0 thành phần  -> None
    - 1 thành phần  -> chính type của thành phần đó (chart/dataframe/image/text)
    - >1 thành phần -> "multi"
    """
    if result is None:
        return None

    result_dir = _safe_result_dir(request_id)
    os.makedirs(result_dir, exist_ok=True)

    parts = _as_parts(result)
    if parts is None:
        parts = [("Kết quả", result)]

    manifest = []
    for i, (name, obj) in enumerate(parts):
        ptype, fname = _persist_one(obj, result_dir, f"part{i}")
        manifest.append({"name": name, "type": ptype, "file": fname})

    with open(os.path.join(result_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)

    if not manifest:
        return None
    if len(manifest) == 1:
        return manifest[0]["type"]
    return "multi"


def _load_part(result_dir: str, entry: dict) -> dict:
    """Đọc lại payload của một thành phần theo manifest entry, trả về
    {name, type, data} với data đúng shape frontend cần."""
    ptype = entry["type"]
    path = os.path.join(result_dir, entry["file"])
    if ptype == "image":
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
    elif ptype == "dataframe":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:  # chart (JSON string) | text
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
    return {"name": entry.get("name"), "type": ptype, "data": data}


def _load_result_data(result_dir: str) -> tuple[str | None, object]:
    """Đọc lại payload từ đĩa, trả về (result_type, result_data) đúng shape frontend cần.
    Với "multi", result_data là list [{name, type, data}]."""
    manifest_path = os.path.join(result_dir, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        parts = [_load_part(result_dir, entry) for entry in manifest]
        if not parts:
            return None, None
        if len(parts) == 1:
            return parts[0]["type"], parts[0]["data"]
        return "multi", parts

    # Fallback cho kết quả cũ lưu trước khi có manifest (tên file cố định).
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

def _decode_plotly_array(value) -> list:
    """Plotly serialize mảng số thành {"dtype":"f8","bdata":"<base64>"} (little-endian),
    có thể kèm "shape" cho mảng 2D (heatmap/surface). Trả về list (hoặc list lồng list
    nếu 2D) số thật; nếu value đã là list/None thì trả nguyên."""
    if value is None:
        return []
    if isinstance(value, dict) and "bdata" in value:
        import numpy as np
        dtype = value.get("dtype", "f8")
        arr = np.frombuffer(base64.b64decode(value["bdata"]), dtype=f"<{dtype}")
        shape = value.get("shape")
        if shape:
            dims = tuple(int(s) for s in str(shape).replace(" ", "").split(","))
            arr = arr.reshape(dims)
        return arr.tolist()
    return list(value)


def _plotly_axis_title(node) -> str:
    """Rút text tiêu đề từ layout.xaxis / yaxis / layout (title có thể là str hoặc dict)."""
    if not isinstance(node, dict):
        return ""
    title = node.get("title")
    if isinstance(title, dict):
        return title.get("text", "") or ""
    if isinstance(title, str):
        return title
    return ""


# Các key mang dữ liệu của mọi loại trace plotly, theo thứ tự ưu tiên hiển thị.
# bar/scatter/line: x,y | pie: labels,values | heatmap/surface: x,y,z
# polar: r,theta | geo/map: lat,lon | ternary: a,b,c | funnel/waterfall: x,y
_PLOTLY_ARRAY_KEYS = (
    "labels", "values", "x", "y", "z",
    "r", "theta", "lat", "lon", "a", "b", "c", "text",
)


def _fmt_cell(v) -> str:
    """Làm gọn số thực khi in ra cho LLM."""
    if isinstance(v, float):
        return str(round(v, 3))
    return str(v)

def _col_stats(values: list) -> tuple[str, set[int]]:
    """Trả về (mô tả thống kê, tập index cần giữ lại: vị trí max & min).
    Chỉ tính trên phần tử số; nếu không có số trả ("", set())."""
    nums = [(i, v) for i, v in enumerate(values) if isinstance(v, (int, float))]
    if not nums:
        return "", set()
    imax, vmax = max(nums, key=lambda t: t[1])
    imin, vmin = min(nums, key=lambda t: t[1])
    mean = sum(v for _, v in nums) / len(nums)
    desc = (f"min={_fmt_cell(vmin)}, max={_fmt_cell(vmax)}, "
            f"mean={_fmt_cell(mean)}, n={len(nums)}")
    return desc, {imax, imin}
    
def _sample_indices(total: int, keep: set[int], max_rows: int) -> list[int]:
    """Chọn tối đa max_rows index đại diện để feed vào LLM"""
    if total <= max_rows:
        return list(range(total))
    idx = set(keep)
    idx.add(0)
    idx.add(total - 1)
    # rải đều phần còn lại
    remaining = max_rows - len(idx)
    if remaining > 0:
        step = total / remaining
        idx.update(int(i * step) for i in range(remaining))
    return sorted(i for i in idx if 0 <= i < total)[:max_rows]


def _summarize_plotly_trace(tr: dict, x_title: str, y_title: str, max_rows: int) -> str:
    """Tóm tắt MỘT trace bất kỳ thành text: tự dò các mảng dữ liệu đang có,
    giải mã, rồi in dạng bảng cột. Xử lý riêng z 2D (heatmap/surface)."""
    ttype = tr.get("type") or "scatter"
    name = tr.get("name") or ttype

    # Nhãn cột thân thiện: x/y dùng tiêu đề trục, còn lại dùng chính tên key.
    label_map = {"x": x_title, "y": y_title}

    cols: dict[str, list] = {}
    for key in _PLOTLY_ARRAY_KEYS:
        if tr.get(key) is not None:
            cols[key] = _decode_plotly_array(tr[key])

    if not cols:
        return f"Chuỗi '{name}' (loại {ttype}): không có dữ liệu số để trích xuất."

    # z 2D (heatmap/surface): dump cả ma trận sẽ quá dài -> tóm tắt kích thước + thống kê.
    z = cols.get("z")
    if z and isinstance(z[0], list):
        import numpy as np
        zarr = np.array(z, dtype=float)
        xs = cols.get("x") or list(range(zarr.shape[1]))
        ys = cols.get("y") or list(range(zarr.shape[0]))
        return (
            f"Chuỗi '{name}' (loại {ttype}, ma trận {zarr.shape[0]}x{zarr.shape[1]}):\n"
            f"  Trục {x_title}: {', '.join(_fmt_cell(v) for v in xs[:max_rows])}\n"
            f"  Trục {y_title}: {', '.join(_fmt_cell(v) for v in ys[:max_rows])}\n"
            f"  Giá trị z: min={_fmt_cell(float(zarr.min()))}, "
            f"max={_fmt_cell(float(zarr.max()))}, mean={_fmt_cell(float(zarr.mean()))}"
        )

    # Trường hợp 1D: zip các cột theo hàng.
    keys = list(cols.keys())
    stat_lines = []
    keep: set[int] = set()
    for k in keys:
        desc, kidx = _col_stats(cols[k])
        if desc:
            stat_lines.append(f"  Thống kê {label_map.get(k, k)}: {desc}")
        keep |= kidx
    header_cols = " | ".join(label_map.get(k, k) for k in keys)
    total = max(len(cols[k]) for k in keys)
    sel = _sample_indices(total, keep, max_rows)
    rows = []
    prev = None
    for i in sel:
        cells = [_fmt_cell(cols[k][i]) if i < len(cols[k]) else "" for k in keys]
        # đánh dấu chỗ nhảy cách (không liên tục) cho LLM biết đã bỏ đoạn giữa
        if prev is not None and i > prev + 1:
            rows.append("  ...")
        rows.append("  - " + " | ".join(cells))
        prev = i

    header = f"Chuỗi '{name}' (loại {ttype}) [{header_cols}]:"
    parts = [header]
    if stat_lines:
        parts.extend(stat_lines)
    parts.extend(rows)
    if total > len(sel):
        parts.append(f"  (đã sample {len(sel)}/{total} điểm)")
    return "\n".join(parts)



def _summarize_one(result_type: str | None, data, max_rows: int) -> tuple[str, str | None]:
    """Tóm tắt MỘT thành phần thành (text, base64_png_or_None)."""
    if result_type == "image":
        # data là base64 PNG
        return "Kết quả là một biểu đồ. Hãy phân tích hình ảnh kèm theo.", data
    if result_type == "dataframe":
        df = pd.DataFrame(data)
        return f"Bảng kết quả ({len(df)} dòng):\n{df.head(max_rows).to_markdown(index=False)}", None
    if result_type == "chart":
        # Giải mã chart Plotly cho LLM đọc số
        fig = json.loads(data)
        layout = fig.get("layout", {})
        x_title = _plotly_axis_title(layout.get("xaxis")) or "x"
        y_title = _plotly_axis_title(layout.get("yaxis")) or "y"
        chart_title = _plotly_axis_title(layout) or ""  # layout.title cùng shape

        blocks = [
            _summarize_plotly_trace(tr, x_title, y_title, max_rows)
            for tr in fig.get("data", [])
        ]

        header = f"Dữ liệu biểu đồ '{chart_title}':" if chart_title else "Dữ liệu biểu đồ:"
        return header + "\n" + "\n".join(blocks), None
    if result_type == "text":
        return f"Kết quả: {data}", None
    return "Không có kết quả.", None


def _result_for_llm(request_id: str, max_rows: int = 30) -> tuple[str, str | None]:
    """Returns (text_summary, base64_png_or_None).
    Với "multi": ghép tóm tắt từng thành phần, lấy ảnh đầu tiên (nếu có)."""
    result_dir = _safe_result_dir(request_id)
    result_type, data = _load_result_data(result_dir)

    if result_type == "multi":
        texts: list[str] = []
        image: str | None = None
        for part in data:
            text, img = _summarize_one(part["type"], part["data"], max_rows)
            label = part.get("name") or ""
            texts.append(f"### {label}\n{text}" if label else text)
            if image is None and img is not None:
                image = img
        return "\n\n".join(texts), image

    return _summarize_one(result_type, data, max_rows)

# Filename gán cho code người dùng khi compile/exec, để lọc traceback đúng frame.
_USER_CODE_FILENAME = "<user_code>"


def _format_user_traceback(code: str, exc: BaseException) -> str:
    """Dựng thông báo lỗi cho LLM sửa code: giữ lại traceback thuộc code người dùng
    (frame '<user_code>') kèm số dòng và dòng code tương ứng.

    Trả về nhiều dòng, ví dụ:
        Traceback (dòng lỗi trong code):
          Dòng 30: result_df.loc['Phân khúc giá phổ biến', ...] = popular_segment_str
        TypeError: Invalid value '4-6 tỷ (4 tin)' for dtype 'float64'
    """
    code_lines = code.splitlines()
    frames = []
    for frame in traceback.extract_tb(exc.__traceback__):
        if frame.filename != _USER_CODE_FILENAME:
            continue  # bỏ frame trong execute.py, chỉ giữ code do model sinh
        lineno = frame.lineno or 0
        src = frame.line or (code_lines[lineno - 1].strip() if 0 < lineno <= len(code_lines) else "")
        frames.append(f"  Dòng {lineno}: {src}")

    final = f"{type(exc).__name__}: {exc}"
    if not frames:
        return final  # không có frame '<user_code>' (vd lỗi ngoài exec) -> fallback 1 dòng
    return "Traceback (dòng lỗi trong code):\n" + "\n".join(frames) + "\n" + final


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
            # Compile với filename <user_code> để traceback code người dùng
            exec(compile(code, _USER_CODE_FILENAME, "exec"), safe_globals)
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
            "error": _format_user_traceback(code, exc),
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
    except CodeSyntaxError as exc:
        error_msg = str(exc)
        _update_log_status(request.request_id, status="error",
                           result_summary=error_msg, executed_code=request.code)
        return ExecuteResult(request_id=request.request_id, success=False, error=error_msg)

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

    try:
        output = queue.get(timeout=EXECUTE_TIMEOUT_SECONDS)
    except Empty:
        timed_out = process.is_alive()
        if timed_out:
            process.terminate()
        process.join()
        if timed_out:
            error_msg = f"Code chạy quá {EXECUTE_TIMEOUT_SECONDS}s và đã bị hủy (timeout)."
        else:
            error_msg = "Process con thoát bất thường (có thể do lỗi hệ thống / segfault)."
        _update_log_status(
            request.request_id, status="error",
            result_summary=error_msg, executed_code=request.code,
        )
        return ExecuteResult(request_id=request.request_id, success=False, error=error_msg)

    # Đã rút được kết quả, chờ child kết thúc gọn (đừng để join treo vô hạn).
    process.join(timeout=5)
    if process.is_alive():
        process.terminate()
        process.join()

    success = output["success"]
    error = output.get("error")
    logs = output.get("logs", "")

    if success and output.get("result_type") is None and not logs.strip():
        success = False
        error = (
            "Code chạy xong nhưng không gán biến `result` và cũng không in ra gì "
            "- không có kết quả để hiển thị."
        )

    status = "executed" if success else "error"
    summary = error or f"Kết quả dạng: {output.get('result_type')}"
    _update_log_status(
        request.request_id, status=status,
        result_summary=summary, executed_code=request.code,
    )

    # Response chỉ mang meta data. 
    # Load result_data qua GET /execute/result/{request_id}
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


def _update_log_status(
    request_id: str,
    status: str,
    result_summary: str,
    executed_code: str | None = None,
) -> None:
    """Cập nhật lại log entry gốc (đã tạo lúc gọi AI API) với kết quả thực thi."""
    entry = get_log_entry(request_id)
    if entry is None:
        # edge case: execute được gọi mà không qua AI API trước đó
        entry = LogEntry(
            request_id=request_id,
            prompt="(không rõ, không có log AI gốc)",
            code="",
            executed_code=executed_code,
            explanation="",
            result_summary=result_summary,
            status=status,
            timestamp=datetime.now().isoformat(),
        )
    else:
        entry.executed_code = executed_code
        entry.status = status
        entry.result_summary = result_summary
        entry.timestamp = datetime.now().isoformat()

    save_log_entry(entry)