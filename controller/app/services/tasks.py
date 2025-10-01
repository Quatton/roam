"""
Task execution service for ROAM.
"""

import uuid
import json
import asyncio
from .redis import redis_service
from ..models import JobResponse, CodeRequest


class TaskService:
    """Service for managing task execution."""

    @staticmethod
    async def submit_task(request: CodeRequest) -> JobResponse:
        """Submit a task for execution via persistent worker queue."""
        task_id = str(uuid.uuid4())

        # Create job for persistent worker
        job_data = {
            "task_id": task_id,
            "code": request.code,
            "timestamp": asyncio.get_event_loop().time(),
        }

        # Push job to Redis queue for persistent workers
        redis_service.client.lpush("roam:jobs", json.dumps(job_data))
        print(f"📤 Queued job {task_id} for persistent workers")

        return JobResponse(task_id=task_id, stream_url=f"/stream/{task_id}")

    @staticmethod
    async def _simulate_task(code: str, result_channel: str) -> None:
        """Simulate task execution for testing without Celery worker."""
        await asyncio.sleep(1)  # Simulate processing time

        try:
            # Execute the code locally for testing
            exec_globals = {"__name__": "__main__"}
            exec(code, exec_globals)

            # Try to get result from last line
            lines = code.strip().split("\n")
            last_line = lines[-1].strip()

            if last_line and not last_line.startswith(
                ("import ", "from ", "def ", "class ")
            ):
                try:
                    return_value = eval(last_line, exec_globals)
                except Exception:
                    return_value = None
            else:
                return_value = None

            result = {
                "success": True,
                "return_value": return_value,
                "stdout": "",
                "stderr": None,
            }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "traceback": str(e),
                "stdout": "",
                "stderr": None,
            }

        # Publish to Redis channel
        redis_service.publish(result_channel, result)

    @staticmethod
    def get_task_status(task_id: str) -> dict:
        """Get task status from Redis (fallback method)."""
        try:
            result_key = f"roam:result:{task_id}"
            result = redis_service.get(result_key)

            if result:
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "result": json.loads(result),
                }
            else:
                return {"task_id": task_id, "status": "running"}
        except Exception as e:
            return {"task_id": task_id, "status": "error", "error": str(e)}
