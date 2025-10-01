"""
Persistent Redis worker for ROAM - listens to job queue and executes code.
"""

import redis
import json
import sys
import traceback
import importlib
import time
import os
from typing import Any, Dict


class PersistentWorker:
    """Persistent worker that listens to Redis job queue."""
    
    def __init__(self):
        redis_host = os.getenv('REDIS_HOST', 'redis.roam-controller.svc.cluster.local')
        self.redis = redis.Redis(host=redis_host, port=6379, db=0)
        self.job_queue = 'roam:jobs'
        print(f"🔥 Worker starting - listening to {redis_host}:6379")
        
    def start(self):
        """Start listening for jobs."""
        print("🚀 Persistent worker ready - waiting for jobs...")
        
        while True:
            try:
                # Blocking pop from job queue (wait forever)
                job_data = self.redis.blpop(self.job_queue, timeout=0)
                if job_data:
                    job_json = job_data[1].decode('utf-8')
                    job = json.loads(job_json)
                    print(f"📋 Received job: {job.get('task_id', 'unknown')}")
                    self.execute_job(job)
                    
            except KeyboardInterrupt:
                print("👋 Worker shutting down...")
                break
            except Exception as e:
                print(f"❌ Worker error: {e}")
                time.sleep(1)  # Brief pause before retrying
                
    def execute_job(self, job: Dict[str, Any]):
        """Execute a job and publish result to Redis."""
        task_id = job.get('task_id')
        result_channel = f"roam:results:{task_id}"
        
        try:
            # Execute the code
            code = job.get('code', '')
            if not code:
                raise ValueError("No code provided in job")
                
            print(f"🔧 Executing code for task {task_id}")
            result = self.execute_code(code)
            
            # Publish success result
            result_data = {
                "success": True,
                "return_value": result,
                "stdout": "",
                "stderr": None
            }
            
            self.redis.publish(result_channel, json.dumps(result_data))
            print(f"✅ Job {task_id} completed successfully")
            
        except Exception as e:
            # Publish error result
            error_data = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "stdout": "",
                "stderr": None
            }
            
            self.redis.publish(result_channel, json.dumps(error_data))
            print(f"❌ Job {task_id} failed: {e}")
            
    def execute_code(self, code: str) -> Any:
        """Execute Python code and return result."""
        # Create execution environment
        exec_globals = {"__name__": "__main__"}
        exec_locals = {}
        
        # Execute the code
        exec(code, exec_globals, exec_locals)
        
        # Try to get result from last line
        lines = code.strip().split('\n')
        last_line = lines[-1].strip()
        
        # If last line looks like an expression, try to evaluate it
        if last_line and not last_line.startswith(('import ', 'from ', 'def ', 'class ', 'if ', 'for ', 'while ', 'with ', 'try:')):
            try:
                return eval(last_line, exec_globals, exec_locals)
            except Exception:
                # If eval fails, check if there's a 'result' variable
                return exec_locals.get('result', None)
        
        # Check for 'result' variable in locals
        return exec_locals.get('result', None)


if __name__ == "__main__":
    worker = PersistentWorker()
    worker.start()