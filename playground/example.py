"""
Example usage of the remote environment client.
"""

import asyncio
from remote_env import Env


# Create an environment pointing to your controller
env = Env(base_url="http://127.0.0.1:8001")


# Example 1: Simple function
@env.func
def add_numbers():
    return 1 + 1


async def main():
    result = await add_numbers()
    print(f"1 + 1 = {result}")
    await env.close()


if __name__ == "__main__":
    asyncio.run(main())
