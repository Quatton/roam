"""
SSE streaming service for ROAM.
"""

import json
from fastapi.responses import StreamingResponse
from .redis import redis_service


class StreamingService:
    """Service for Server-Sent Events streaming."""

    @staticmethod
    async def create_sse_stream(task_id: str) -> StreamingResponse:
        """Create SSE stream for task results."""

        async def event_stream():
            channel = f"roam:results:{task_id}"

            try:
                # Send initial connection message
                yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id})}\n\n"

                # Listen for messages from Redis
                for message in redis_service.listen_to_channel_sync(channel):
                    # Send the result
                    yield f"data: {json.dumps({'type': 'result', 'data': message})}\n\n"

                    # If task is complete, break the stream
                    if message.get("success") is not None:
                        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                        break

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            },
        )
