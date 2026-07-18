import sqlite3
from contextlib import contextmanager
from typing import Optional

from fastapi import APIRouter
from schemas import LogEntry

from config import LOG_DB_PATH

router = APIRouter(tags=["Logs"])


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                request_id TEXT PRIMARY KEY,
                prompt TEXT,
                code TEXT,
                explanation TEXT,
                result_summary TEXT,
                status TEXT,
                timestamp TEXT
            )
            """
        )
        conn.commit()


@contextmanager
def _get_conn():
    conn = sqlite3.connect(LOG_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def save_log_entry(entry: LogEntry) -> None:
    """Insert nếu chưa có request_id, update nếu đã có (dùng UPSERT)."""
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO logs (request_id, prompt, code, explanation, result_summary, status, timestamp)
            VALUES (:request_id, :prompt, :code, :explanation, :result_summary, :status, :timestamp)
            ON CONFLICT(request_id) DO UPDATE SET
                explanation=excluded.explanation,
                result_summary=excluded.result_summary,
                status=excluded.status,
                timestamp=excluded.timestamp
            """,
            entry.model_dump(),
        )
        conn.commit()


def get_log_entry(request_id: str) -> Optional[LogEntry]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM logs WHERE request_id = ?", (request_id,)
        ).fetchone()
        if row is None:
            return None
        return LogEntry(**dict(row))


# Endpoints để Frontend / báo cáo truy vấn

@router.get("/{request_id}", response_model=LogEntry)
async def get_log(request_id: str):
    entry = get_log_entry(request_id)
    if entry is None:
        return {"detail": "Không tìm thấy log với request_id này."}
    return entry


@router.get("/", response_model=list[LogEntry])
async def list_logs(limit: int = 50):
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [LogEntry(**dict(row)) for row in rows]