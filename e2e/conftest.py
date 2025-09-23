"""Configuration for e2e tests."""

import subprocess
import time
from pathlib import Path

# Get paths relative to this file
E2E_ROOT = Path(__file__).parent
PROJECT_ROOT = E2E_ROOT.parent
CONTROLLER_PATH = PROJECT_ROOT / "controller"

# Global controller process
controller_process = None


def start_controller():
    """Start the controller server for testing."""
    global controller_process

    controller_process = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"],
        cwd=str(CONTROLLER_PATH),
    )

    # Give it time to start up
    time.sleep(3)


def stop_controller():
    """Stop the controller server."""
    global controller_process
    if controller_process:
        controller_process.terminate()
        controller_process.wait()
        controller_process = None
