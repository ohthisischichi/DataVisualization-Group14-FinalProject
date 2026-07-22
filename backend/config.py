import os

# Ollama config
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")

# Allowed library
ALLOWED_IMPORTS = {
    "pandas",
    "numpy",
    "matplotlib",
    "matplotlib.pyplot",
    "plotly",
    "plotly.express",
    "plotly.graph_objects",
    "math",
    "statistics",
    "json",
}

EXECUTE_TIMEOUT_SECONDS = 15

# Logs config
LOG_DB_PATH = os.getenv("LOG_DB_PATH", "storage/logs.db")

# Dataset config
_ROOT_DATASET = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data", "processed", "house_price_clean.csv"))
_FALLBACK_DATASET = "storage/house_price_clean.csv"
DATASET_PATH = os.getenv("DATASET_PATH", _ROOT_DATASET if os.path.exists(_ROOT_DATASET) else _FALLBACK_DATASET)

# Results config: lưu kết quả thực thi theo request_id
RESULTS_DIR = os.getenv("RESULTS_DIR", "storage/results")