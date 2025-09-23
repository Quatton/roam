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

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        """
        Initialize the environment with a base URL.

        Args:
            base_url: The base URL of the remote execution server
        """
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient()

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def func(self, fn: Callable[..., Any]) -> Any:
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

    async def _execute_remote(self, fn: Callable, *args, **kwargs) -> Any:
        """
        Execute a function remotely by sending its source code.

        Args:
            fn: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the remote execution
        """
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

        # Build the execution code
        if args or kwargs:
            # Convert args and kwargs to string representation
            args_str = ", ".join(repr(arg) for arg in args)
            kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
            call_args = ", ".join(filter(None, [args_str, kwargs_str]))
            execution_code = f"{clean_source}\n\n{fn.__name__}({call_args})"
        else:
            execution_code = f"{clean_source}\n\n{fn.__name__}()"

        # Send to remote server
        try:
            response = await self._client.post(
                f"{self.base_url}/eval", json={"code": execution_code}
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise RemoteExecutionError(result["error"])

            return result.get("result")

        except httpx.RequestError as e:
            raise RemoteExecutionError(f"Request failed: {e}")
        except httpx.HTTPStatusError as e:
            raise RemoteExecutionError(
                f"HTTP error {e.response.status_code}: {e.response.text}"
            )


class RemoteExecutionError(Exception):
    """Exception raised when remote execution fails."""

    pass
