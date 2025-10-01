"""
SSE-based environment decorator for ROAM.
"""

import inspect
from functools import wraps
from typing import Any, Callable, TypeVar
import httpx
import json
import asyncio
import logging
from urllib.parse import urljoin

logger = logging.getLogger("remote_env")

F = TypeVar("F", bound=Callable[..., Any])


class Env:
    """Environment decorator factory for remote code execution using SSE."""

    def __init__(
        self,
        should_run_locally: bool | Callable[[], bool] = False,
        base_url: str = "http://127.0.0.1:8000",
    ):
        """
        Initialize the environment with a base URL.

        Args:
            base_url: The base URL of the remote execution server
            should_run_locally: Whether to run functions locally or remotely
        """
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient()
        self.local = should_run_locally

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def fn(self, fn: Callable[..., Any]) -> Any:
        """
        Decorator that marks a function for remote execution.

        Args:
            fn: The function to be executed remotely

        Returns:
            A wrapper function that executes the original function remotely
        """

        # Always return an async function that can be awaited
        @wraps(fn)
        async def async_wrapper(*args, **kwargs):
            return await self._execute_remote(fn, *args, **kwargs)

        # For convenience, also add a sync method
        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            try:
                # Check if we're already in an async context
                asyncio.get_running_loop()
                # If we get here, we're in an async context
                raise RuntimeError(
                    "Cannot call sync version from async context. Use 'await' instead."
                )
            except RuntimeError as e:
                if "no running event loop" in str(e):
                    # No running loop, we can create one
                    return asyncio.run(self._execute_remote(fn, *args, **kwargs))
                else:
                    # Re-raise the "already in async context" error
                    raise

        # Attach sync method to async wrapper for convenience
        async_wrapper.sync = sync_wrapper  # type: ignore

        return async_wrapper  # type: ignore

    def should_run_locally(self) -> bool:
        """Determine if the function should run locally."""
        if callable(self.local):
            return self.local()
        return self.local

    async def _execute_remote(self, fn: Callable, *args, **kwargs) -> Any:
        """
        Execute a function remotely using Redis + Celery + SSE.

        Args:
            fn: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the remote execution
        """
        if self.should_run_locally():
            return fn(*args, **kwargs)

        import textwrap

        # Get the function source code and remove indentation
        source_lines = inspect.getsource(fn)
        source_lines = textwrap.dedent(source_lines).strip()

        # Remove decorator lines (lines starting with @)
        lines = source_lines.split("\n")
        func_lines = []
        found_def = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("@"):
                continue  # Skip decorator lines
            elif stripped.startswith("def ") or found_def:
                found_def = True
                func_lines.append(line)

        clean_source = "\n".join(func_lines).strip()

        # Build the execution code - return the result instead of printing
        if args or kwargs:
            # Convert args and kwargs to string representation
            args_str = ", ".join(repr(arg) for arg in args)
            kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
            call_args = ", ".join(filter(None, [args_str, kwargs_str]))
            execution_code = f"{clean_source}\n\n# Call the function and capture result\nresult = {fn.__name__}({call_args})"
        else:
            execution_code = f"{clean_source}\n\n# Call the function and capture result\nresult = {fn.__name__}()"

        try:
            # Submit job to controller
            job_response = await self._client.post(
                f"{self.base_url}/job", json={"code": execution_code}
            )
            job_response.raise_for_status()
            job_data = job_response.json()
            stream_url = job_data["stream_url"]

            # Connect to SSE stream for real-time results
            return await self._stream_result(stream_url)

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            raise RuntimeError(
                f"Remote execution failed: {e}\nDetails: {error_details}"
            )

    async def _stream_result(self, stream_url: str) -> Any:
        """
        Connect to SSE stream and wait for execution result.

        Args:
            stream_url: The SSE endpoint URL

        Returns:
            The execution result
        """
        full_url = urljoin(self.base_url, stream_url)
        logger.debug(f"🔗 Connecting to SSE stream: {full_url}")

        async with self._client.stream("GET", full_url, timeout=30.0) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type")

                        if event_type == "connected":
                            logger.debug(f"🔗 Connected to task {event.get('task_id')}")
                            continue

                        elif event_type == "result":
                            result_data = event.get("data", {})

                            if result_data.get("success"):
                                # Successfully executed - return the actual result
                                return result_data.get("return_value")
                            else:
                                # Execution failed
                                error_msg = result_data.get("error", "Unknown error")
                                traceback = result_data.get("traceback", "")
                                raise RuntimeError(
                                    f"Remote execution failed: {error_msg}\n{traceback}"
                                )

                        elif event_type == "complete":
                            # Stream completed but no result received
                            raise RuntimeError("Task completed but no result received")

                        elif event_type == "error":
                            error_msg = event.get("error", "Unknown streaming error")
                            raise RuntimeError(f"Streaming error: {error_msg}")

                    except json.JSONDecodeError:
                        # Skip malformed JSON
                        continue

        # If we reach here, stream ended without a result
        raise RuntimeError("Stream ended without receiving result")
