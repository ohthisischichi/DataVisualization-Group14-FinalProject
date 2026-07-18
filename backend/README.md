```bash
ollama serve > ollama.log 2>&1 &


curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:7b","prompt":"test"}'

nix-shell
uvicorn main:app --host 0.0.0.0 --port 8000 --reload


```