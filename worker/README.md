# Worker

Persistent Redis-based worker for remote code execution.

## Features

- 🔥 Persistent worker pool listening to Redis job queue
- ⚡ Fast execution without container startup overhead  
- 🔄 Handles multiple consecutive jobs
- 📊 Redis pub/sub for real-time results
- 🐍 Python code execution with proper isolation

## Architecture

```
Jobs → Redis Queue → Worker Pool → Execution → Results → SSE Stream
```

## Usage

```bash
# Start worker locally
uv run python -m roam_worker

# Deploy worker pool to k8s
kubectl apply -f ../deploy/worker/
```