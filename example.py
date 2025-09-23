"""
Example usage of the roam client.
"""

import asyncio
from roam_client import Env


async def main():
    # Create an environment pointing to your controller
    env = Env(base_url="http://127.0.0.1:8001")

    # Example 1: Simple function
    @env.func
    def add_numbers():
        return 1 + 1

    result = await add_numbers()
    print(f"1 + 1 = {result}")

    # Example 2: Function with arguments
    @env.func
    def multiply(a, b):
        return a * b

    result = await multiply(5, 6)
    print(f"5 * 6 = {result}")

    # Example 3: Using sync method (for non-async contexts)
    @env.func
    def divide(a, b):
        return a / b

    # You can also call it synchronously using .sync()
    # result = divide.sync(10, 2)  # Uncomment if not in async context

    # Example 4: Complex computation
    @env.func
    def fibonacci(n):
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    result = await fibonacci(15)
    print(f"15th Fibonacci number: {result}")

    await env.close()


def sync_example():
    """Example of using the sync method for non-async contexts."""
    env = Env(base_url="http://127.0.0.1:8001")

    @env.func
    def calculate():
        return 42 * 42

    # Use .sync() method when not in async context
    result = calculate.sync()
    print(f"Sync calculation: {result}")


if __name__ == "__main__":
    print("=== Async Example ===")
    asyncio.run(main())

    print("\n=== Sync Example ===")
    sync_example()
