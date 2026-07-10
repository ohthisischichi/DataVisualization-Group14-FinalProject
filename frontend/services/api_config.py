from __future__ import annotations

import os


BACKEND_BASE_URL = os.getenv(
	"BACKEND_BASE_URL",
	"https://decidable-lumping-delighted.ngrok-free.dev",
).rstrip("/")
