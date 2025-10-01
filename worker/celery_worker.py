"""
Celery worker for executing remote code.
"""

import json
import tempfile
import subprocess
import sys
from celery import Celery
from typing import Any, Dict
import redis

# Initialize Celery
app = Celery("roam-worker")
app.conf.update(
    broker_url="redis://redis.roam-controller.svc.cluster.local:6379/0",
    result_backend="redis://redis.roam-controller.svc.cluster.local:6379/0",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Redis client for publishing results
redis_client = redis.Redis(
    host="redis.roam-controller.svc.cluster.local", port=6379, db=0
)


@app.task(bind=True)
def execute_code(self, code: str, result_channel: str) -> Dict[str, Any]:
    """
    Execute Python code and publish result to Redis channel.

    Args:
        code: Python code to execute
        result_channel: Redis channel to publish result to

    Returns:
        Task result metadata
    """
    try:
        # Create a temporary file with the user code
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            # Wrapper that captures both stdout and return value
            wrapper_code = f"""
import sys
import json
import traceback
from io import StringIO

# Capture stdout
old_stdout = sys.stdout
sys.stdout = captured_output = StringIO()

try:
    # User code execution
    exec_globals = {{"__name__": "__main__"}}
    exec_locals = {{}}
    
    # Execute the user code
{code}
    
    # Try to get the return value from the last expression
    # This is a bit hacky but works for simple cases
    lines = {repr(code)}.strip().split('\\n')
    last_line = lines[-1].strip()
    
    if last_line and not last_line.startswith(('import ', 'from ', 'def ', 'class ', 'if ', 'for ', 'while ', 'with ', 'try:')):
        # Last line might be an expression, try to evaluate it
        try:
            return_value = eval(last_line, exec_globals, exec_locals)
        except:
            return_value = None
    else:
        return_value = None
    
    # Get captured stdout
    stdout_content = captured_output.getvalue()
    
    result = {{
        "success": True,
        "return_value": return_value,
        "stdout": stdout_content,
        "stderr": None
    }}
    
except Exception as e:
    result = {{
        "success": False,
        "error": str(e),
        "traceback": traceback.format_exc(),
        "stdout": captured_output.getvalue() if 'captured_output' in locals() else "",
        "stderr": None
    }}

finally:
    sys.stdout = old_stdout

print(json.dumps(result))
"""
            f.write(wrapper_code)
            f.flush()

            # Execute the wrapper script
            result = subprocess.run(
                [sys.executable, f.name], capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                # Parse the result JSON
                try:
                    execution_result = json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    execution_result = {
                        "success": False,
                        "error": "Failed to parse execution result",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }
            else:
                execution_result = {
                    "success": False,
                    "error": f"Process failed with code {result.returncode}",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

            # Publish result to Redis channel for SSE
            redis_client.publish(result_channel, json.dumps(execution_result))

            return {
                "task_id": self.request.id,
                "channel": result_channel,
                "success": execution_result["success"],
            }

    except Exception as e:
        error_result = {"success": False, "error": str(e), "traceback": str(e)}
        redis_client.publish(result_channel, json.dumps(error_result))

        return {
            "task_id": self.request.id,
            "channel": result_channel,
            "success": False,
            "error": str(e),
        }


if __name__ == "__main__":
    app.start()
