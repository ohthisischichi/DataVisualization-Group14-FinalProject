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
DATASET_PATH = os.getenv("DATASET_PATH", "storage/house_price_clean.csv")