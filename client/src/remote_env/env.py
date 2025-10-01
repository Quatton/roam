"""
Generic environment decorator factory for remote code execution.
"""

import inspect
from functools import wraps
from typing import Any, Callable, TypeVar
import httpx

F = TypeVar("F", bound=Callable[..., Any])


class Env:
    """Environment decorator factory for remote code execution."""

    def __init__(
        self,
        should_run_locally: bool | Callable[[], bool] = False,
        base_url: str = "http://127.0.0.1:8000",
    ):
        """
        Initialize the environment with a base URL.

        Args:
            base_url: The base URL of the remote execution server
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
            import asyncio

            try:
                asyncio.get_running_loop()
                # If we're already in an async context, this won't work
                raise RuntimeError(
                    "Cannot call sync version from async context. Use 'await' instead."
                )
            except RuntimeError:
                # No running loop, we can create one
                return asyncio.run(self._execute_remote(fn, *args, **kwargs))

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
        Execute a function remotely by spinning up a dedicated job container.

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

        # Build the execution code with proper output handling
        if args or kwargs:
            # Convert args and kwargs to string representation
            args_str = ", ".join(repr(arg) for arg in args)
            kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
            call_args = ", ".join(filter(None, [args_str, kwargs_str]))
            execution_code = f"{clean_source}\n\nresult = {fn.__name__}({call_args})\nprint(repr(result))"
        else:
            execution_code = (
                f"{clean_source}\n\nresult = {fn.__name__}()\nprint(repr(result))"
            )

        # Detect calling context and dependencies
        context = self._detect_context(fn)
        requirements = self._extract_requirements(context)

        # Submit job
        try:
            job_response = await self._client.post(
                f"{self.base_url}/job",
                json={
                    "code": execution_code,
                    "context": context,
                    "requirements": requirements,
                },
            )
            job_response.raise_for_status()
            job_data = job_response.json()
            job_id = job_data["job_id"]

            # Poll for completion
            return await self._wait_for_job(job_id)

        except httpx.RequestError as e:
            raise RemoteExecutionError(f"Request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise RemoteExecutionError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )

    def _detect_context(self, fn: Callable) -> dict:
        """Detect the calling context of the function."""
        import os
        from pathlib import Path

        # Get the file where the function is defined
        try:
            file_path = inspect.getfile(fn)
            file_path = os.path.abspath(file_path)
        except (TypeError, OSError):
            file_path = None

        context = {
            "function_name": fn.__name__,
            "file_path": file_path,
        }

        if file_path:
            # Look for pyproject.toml or requirements.txt in parent directories
            path = Path(file_path)
            for parent in [path.parent] + list(path.parents):
                pyproject_path = parent / "pyproject.toml"
                requirements_path = parent / "requirements.txt"

                if pyproject_path.exists():
                    context["pyproject_path"] = str(pyproject_path)
                    break
                elif requirements_path.exists():
                    context["requirements_path"] = str(requirements_path)
                    break

        return context

    def _extract_requirements(self, context: dict) -> list[str]:
        """Extract requirements from the context."""
        requirements = []

        if "pyproject_path" in context:
            # Parse pyproject.toml for dependencies
            try:
                import tomllib

                with open(context["pyproject_path"], "rb") as f:
                    pyproject = tomllib.load(f)

                deps = pyproject.get("project", {}).get("dependencies", [])
                requirements.extend(deps)
            except Exception:
                pass  # Fallback to no requirements

        elif "requirements_path" in context:
            try:
                with open(context["requirements_path"], "r") as f:
                    requirements = [
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
            except Exception:
                pass

        return requirements

    async def _wait_for_job(
        self, job_id: str, timeout: int = 300, poll_interval: int = 1
    ) -> Any:
        """Wait for a job to complete and return its result."""
        import asyncio
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = await self._client.get(f"{self.base_url}/job/{job_id}")
                response.raise_for_status()
                job_data = response.json()

                status = job_data.get("status")

                if status == "completed":
                    result = job_data.get("result")
                    # If result is a string representation, try to evaluate it
                    if isinstance(result, str):
                        try:
                            return eval(result)
                        except Exception:
                            return result
                    return result
                elif status == "failed":
                    error = job_data.get("error", "Unknown error")
                    raise RemoteExecutionError(f"Job failed: {error}")
                elif status in ["pending", "running"]:
                    await asyncio.sleep(poll_interval)
                    continue
                else:
                    raise RemoteExecutionError(f"Unknown job status: {status}")

            except httpx.RequestError as e:
                raise RemoteExecutionError(f"Failed to check job status: {e}")

        raise RemoteExecutionError(f"Job {job_id} timed out after {timeout} seconds")


class RemoteExecutionError(Exception):
    """Exception raised when remote execution fails."""

    pass
