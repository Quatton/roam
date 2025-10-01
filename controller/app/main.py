"""
ROAM Controller - Clean FastAPI app with Redis + Celery + SSE
"""

from fastapi import FastAPI
from .models import CodeRequest, JobResponse, HealthResponse, JobStatusResponse
from .services import TaskService, StreamingService

app = FastAPI(
    title="ROAM Controller",
    description="Run On Another Machine - Remote execution with Redis + Celery + SSE",
    version="2.0.0",
)


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Kubernetes-compatible health check endpoint."""
    return HealthResponse(status="ok", architecture="redis_celery_sse")


@app.post("/job", response_model=JobResponse)
async def submit_job(request: CodeRequest):
    """
    Submit code for remote execution using Celery.
    Returns SSE stream URL for real-time results.
    """
    return await TaskService.submit_task(request)


@app.get("/stream/{task_id}")
async def stream_results(task_id: str):
    """
    Server-Sent Events stream for real-time task results.
    """
    return await StreamingService.create_sse_stream(task_id)


@app.get("/job/{task_id}/status", response_model=JobStatusResponse)
async def get_job_status(task_id: str):
    """
    Get current status of a task (fallback if SSE not available).
    """
    status_data = TaskService.get_task_status(task_id)
    return JobStatusResponse(**status_data)


# Legacy endpoints for backward compatibility
@app.post("/execute")
async def execute_code_legacy(request: CodeRequest):
    """Legacy endpoint - redirects to new job-based system."""
    job_response = await submit_job(request)

    return {
        "message": "Use /job endpoint with SSE streaming for better experience",
        "job": job_response,
    }


@app.get("/health")
async def health_legacy():
    """Legacy health endpoint - redirects to /healthz."""
    return await health_check()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
