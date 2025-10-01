"""
Example usage of the remote environment client.
"""

import os
from remote_env import Env


env = Env(
    base_url="http://roam.localtest.me",
    should_run_locally=lambda: os.getenv("IS_LOCAL", "0") == "1",
)


@env.fn
def get_system():
    import subprocess

    return subprocess.check_output("uname -a", shell=True, text=True).strip()


def main():
    print("🖥️  Here:")
    os.environ["IS_LOCAL"] = "1"
    local_info = get_system.sync()
    print(f"   {local_info}")

    print("\n✨ Somewhere else:")
    os.environ["IS_LOCAL"] = "0"
    remote_info = get_system.sync()
    print(f"   {remote_info}")


if __name__ == "__main__":
    main()
