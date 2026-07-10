from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import ai, execute, logs
from routers.logs import init_db

app = FastAPI(
    title="AI Backend - House Price Dashboard",
    description="API AI cho dashboard",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai.router, prefix="/ai")
app.include_router(execute.router, prefix="/execute")
app.include_router(logs.router, prefix="/logs")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
async def health_check():
    """Test xem server có sống không"""
    return {"status": "ok"}