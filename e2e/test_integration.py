"""
End-to-end integration tests for roam client and controller.
"""
import subprocess
import time
import pytest
from roam_client import Env


# Global controller process
controller_process = None


def setup_module():
    """Start the controller server before running tests."""
    global controller_process
    
    # Start the controller on port 8001
    controller_process = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"],
        cwd="/Users/quatton/Documents/GitHub/roam/controller"
    )
    
    # Give it time to start up
    time.sleep(3)


def teardown_module():
    """Stop the controller server after tests."""
    global controller_process
    if controller_process:
        controller_process.terminate()
        controller_process.wait()


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