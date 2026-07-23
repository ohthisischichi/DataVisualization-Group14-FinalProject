```bash
ollama serve > ollama.log 2>&1 &


curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:7b","prompt":"test"}'

nix-shell
uvicorn main:app --host 0.0.0.0 --port 8000 --reload


```

# AI Backend documentation

A FastAPI service that turns natural-language questions into sandboxed Python over a Vietnamese house-price dataset, with a human-in-the-loop approval flow.

## Architecture

Toàn bộ luồng gồm 5 giai đoạn. Mỗi giai đoạn được mô tả bằng một sơ đồ riêng bên dưới.

### 1. Generate - sinh code từ câu hỏi

```mermaid
flowchart LR
    Client["Client (dashboard)"] -- "prompt + context" --> Gen["POST /ai/generate"]
    Gen -- "build_prompt" --> Ollama{{"Ollama (local LLM)"}}
    Ollama -- "raw text" --> Parse["parse_model_output<br/>(code + explanation)"]
    Parse -- "status = pending_approval" --> DB[("SQLite log")]
    Parse -- "AIResponse" --> Client
```

### 2. Approve & Execute - duyệt và thực thi

```mermaid
flowchart LR
    Client["Client"] -- "review / edit" --> Approve{"approved = true?"}
    Approve -- "no" --> Reject["HTTP 400"]
    Approve -- "yes" --> Run["POST /execute/run"]
    Run --> Validate{"validate_code<br/>(AST whitelist)"}
    Validate -- "invalid → 422" --> LogRej["log: rejected"] --> DB[("SQLite log")]
    Validate -- "valid" --> Sandbox["subprocess sandbox<br/>load df · exec · timeout 15s"]
    Sandbox -- "chart/dataframe/image/text" --> Storage[("storage/results/{id}")]
    Sandbox -- "status = executed / error" --> DB
    Sandbox -- "ExecuteResult (metadata + logs)" --> Client
```

### 3. Fetch result - lấy dữ liệu kết quả

```mermaid
flowchart LR
    Client["Client"] -- "GET /execute/result/{id}" --> Res["/execute/result"]
    Storage[("storage/results/{id}")] -- "load payload" --> Res
    Res -- "chart / dataframe / image / text" --> Client
```

### 4. Fix - sửa code khi chạy lỗi

```mermaid
flowchart LR
    Client["Client<br/>(received failed/error code)"] -- "on error: POST /ai/fix" --> Fix["/ai/fix"]
    Fix --> Ollama{{"Ollama (local LLM)"}}
    Ollama -- "corrected code" --> Fix
    Fix -- "new request_id<br/>status = pending_approval" --> DB[("SQLite log")]
    Fix -. "re-approve (→ giai đoạn 2)" .-> Client
```

### 5. Interpret - diễn giải kết quả

```mermaid
flowchart LR
    Client["Client"] -- "POST /ai/interpret" --> Int["/ai/interpret"]
    Storage[("storage/results/{id}")] -- "result_for_llm<br/>(data + image/chart/dataframe)" --> Int
    Int --> Ollama{{"Ollama (local LLM)"}}
    Ollama -- "natural-language answer" --> Client
```


## API Reference

### Health

* **`GET /health`** - Liveness probe. Returns `{"status": "ok"}`.

### AI (`/ai`)

* **`POST /ai/generate`** → `AIResponse`
Generates Python code and an explanation from a natural-language prompt and optional dashboard context. The result is returned with `status = "pending_approval"` and logged immediately. The code is not executed yet.
* **`POST /ai/interpret`** → `InterpretResponse`
Produces a natural-language answer for a completed execution, grounded strictly in the persisted result (including chart data and rendered images).
* **`POST /ai/fix`** → `AIResponse`
Given a failed `request_id`, the executed code, and the error message, generates corrected code with a new `request_id`.

### Execute (`/execute`)

* **`POST /execute/run`** → `ExecuteResult`
Executes the approved code (`approved = true` is mandatory; otherwise `400`). Code is validated by AST inspection before execution and run in an isolated subprocess. The response contains only metadata and logs; the payload is retrieved separately. Returns `422` when validation fails.
* **`GET /execute/result/{request_id}`** → `ExecuteResult`
Loads the persisted result for a request. `result_type` is one of `chart` (Plotly JSON), `image` (base64 PNG), `dataframe` (records), `text`, or `multi`. For `multi` (when the code returns a `dict`/`list` of several artifacts), `result_data` is a list of `{name, type, data}` parts, each `data` shaped like the corresponding single-artifact payload.

### Logs (`/logs`)

* **`GET /logs/{request_id}`** → `LogEntry`
Retrieve a single log entry.
* **`GET /logs/?limit=50`** → `list[LogEntry]`
List recent entries, most recent first.