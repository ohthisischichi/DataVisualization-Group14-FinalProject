from typing import Any, Optional
from pydantic import BaseModel, Field

# AI API

class DashboardContext(BaseModel):
    """Ngữ cảnh hiện tại của dashboard"""
    current_tab: Optional[str] = Field(None, description="Tab hiện tại, vd: 'Price Drivers'")
    selected_province: Optional[str] = None
    selected_district: Optional[str] = None
    active_filters: Optional[dict] = Field(default_factory=dict)


class AIRequest(BaseModel):
    prompt: str = Field(..., description="Câu hỏi / yêu cầu của người dùng")
    context: Optional[DashboardContext] = None


class AIResponse(BaseModel):
    request_id: str
    code: str
    explanation: str
    status: str = "pending_approval"  # code luôn ở trạng thái chờ duyệt, KHÔNG tự chạy

class InterpretRequest(BaseModel):
    request_id: str

class InterpretResponse(BaseModel):
    request_id: str
    answer: str



#  Execute API 

class ExecuteRequest(BaseModel):
    request_id: str = Field(..., description="ID liên kết với request AI gốc, để ghi log xuyên suốt")
    code: str = Field(..., description="Code đã được người dùng xem/chỉnh sửa và approve")
    approved: bool = Field(..., description="Phải = true thì mới được thực thi")


class ExecuteResult(BaseModel):
    request_id: str
    success: bool
    result_type: Optional[str] = None   # "chart" | "dataframe" | "image" | "text" | None
    result_data: Optional[Any] = None   # JSON của chart (plotly) hoặc dataframe (records) hoặc text
    logs: str = ""
    error: Optional[str] = None


# Logs API 

class LogEntry(BaseModel):
    request_id: str
    prompt: str
    code: str
    explanation: str
    result_summary: Optional[str] = None
    status: str  # "pending_approval" | "executed" | "rejected" | "error"
    timestamp: str