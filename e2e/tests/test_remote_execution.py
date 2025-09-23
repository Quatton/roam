"""
End-to-end tests for remote code execution.
"""

import pytest
from remote_env import Env
import sys
from pathlib import Path

# Add parent directory to path for conftest import
sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import start_controller, stop_controller


def setup_module():
    """Start the controller server before running tests."""
    start_controller()


def teardown_module():
    """Stop the controller server after tests."""
    stop_controller()


@pytest.mark.asyncio
async def test_basic_math_operation():
    """Test basic math operation through remote execution."""
    async with Env(base_url="http://127.0.0.1:8001") as env:

        @env.func
        def add_numbers():
            return 1 + 1

        result = await add_numbers()
        assert result == 2


@pytest.mark.asyncio
async def test_function_with_arguments():
    """Test function with arguments."""
    async with Env(base_url="http://127.0.0.1:8001") as env:

        @env.func
        def multiply(a, b):
            return a * b

        result = await multiply(3, 4)
        assert result == 12


@pytest.mark.asyncio
async def test_function_with_kwargs():
    """Test function with keyword arguments."""
    async with Env(base_url="http://127.0.0.1:8001") as env:

        @env.func
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = await greet("World", greeting="Hi")
        assert result == "Hi, World!"


@pytest.mark.asyncio
async def test_complex_computation():
    """Test more complex computation."""
    async with Env(base_url="http://127.0.0.1:8001") as env:

        @env.func
        def fibonacci(n):
            if n <= 1:
                return n
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b

        result = await fibonacci(10)
        assert result == 55  # 10th Fibonacci number


def test_sync_wrapper():
    """Test that synchronous functions work using .sync() method."""
    env = Env(base_url="http://127.0.0.1:8001")

    @env.func
    def simple_calc():
        return 5 * 5

    # Use the sync method for non-async contexts
    result = simple_calc.sync()
    assert result == 25


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling for invalid code."""
    async with Env(base_url="http://127.0.0.1:8001") as env:

        @env.func
        def divide_by_zero():
            return 1 / 0

        with pytest.raises(Exception) as exc_info:
            await divide_by_zero()

        assert "division by zero" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
