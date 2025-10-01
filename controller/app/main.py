from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import uuid
from typing import Optional, Dict, Any
import json
import base64
from kubernetes import client, config
from kubernetes.client.rest import ApiException

app = FastAPI()


class CodeRequest(BaseModel):
    code: str


class JobRequest(BaseModel):
    code: str
    context: Dict[str, Any]  # File path, dependencies, etc.
    requirements: Optional[list[str]] = None


class JobResponse(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    result: Optional[Any] = None
    error: Optional[str] = None


# In-memory job storage (in production, use Redis or similar)
jobs: Dict[str, JobResponse] = {}


@app.get("/healthz")
def healthz():
    """
    Kubernetes uses this endpoint to check if our app is alive.
    If this returns a 200 OK, the pod is considered healthy.
    """
    return {"ok": True}


@app.post("/job", response_model=JobResponse)
async def submit_job(request: JobRequest):
    """Submit a job to be executed in a dedicated container."""
    job_id = str(uuid.uuid4())

    # Create job entry
    jobs[job_id] = JobResponse(
        job_id=job_id,
        status="pending",
    )

    # Start job execution in background
    asyncio.create_task(execute_job(job_id, request))

    return jobs[job_id]


@app.get("/job/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get the status and result of a job."""
    if job_id not in jobs:
        return JobResponse(job_id=job_id, status="not_found", error="Job not found")
    return jobs[job_id]


async def execute_job(job_id: str, request: JobRequest):
    """Execute a job in a dedicated Kubernetes Job."""
    try:
        jobs[job_id].status = "running"
        
        # Configure Kubernetes client (uses in-cluster config in pod)
        config.load_incluster_config()
        batch_v1 = client.BatchV1Api()
        core_v1 = client.CoreV1Api()
        
        # Encode the Python code as base64 for the configmap
        code_b64 = base64.b64encode(request.code.encode()).decode()
        
        # Create requirements command if needed
        install_cmd = ""
        if request.requirements:
            reqs = " ".join(request.requirements)
            install_cmd = f"pip install {reqs} && "
        
        # Create Kubernetes Job manifest
        job_name = f"roam-job-{job_id[:8]}"
        job_manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "namespace": "roam-controller"
            },
            "spec": {
                "ttlSecondsAfterFinished": 300,  # Clean up after 5 minutes
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [{
                            "name": "job-runner",
                            "image": "python:3.12-slim",
                            "command": ["bash", "-c"],
                            "args": [f"""
                                echo '{code_b64}' | base64 -d > /tmp/job.py &&
                                {install_cmd}python /tmp/job.py
                            """],
                            "resources": {
                                "requests": {"memory": "128Mi", "cpu": "100m"},
                                "limits": {"memory": "512Mi", "cpu": "500m"}
                            }
                        }]
                    }
                }
            }
        }
        
        # Create the job
        batch_v1.create_namespaced_job(
            namespace="roam-controller",
            body=job_manifest
        )
        
        # Wait for job completion (with timeout)
        timeout = 300  # 5 minutes
        check_interval = 2  # seconds
        elapsed = 0
        
        while elapsed < timeout:
            try:
                job_status = batch_v1.read_namespaced_job_status(
                    name=job_name,
                    namespace="roam-controller"
                )
                
                if job_status.status.succeeded:
                    # Job completed successfully, get the logs
                    pods = core_v1.list_namespaced_pod(
                        namespace="roam-controller",
                        label_selector=f"job-name={job_name}"
                    )
                    
                    if pods.items:
                        pod_name = pods.items[0].metadata.name
                        logs = core_v1.read_namespaced_pod_log(
                            name=pod_name,
                            namespace="roam-controller"
                        )
                        
                        # Try to parse output
                        try:
                            result = json.loads(logs.strip())
                        except json.JSONDecodeError:
                            result = logs.strip()
                        
                        jobs[job_id].status = "completed"
                        jobs[job_id].result = result
                        break
                    
                elif job_status.status.failed:
                    # Job failed, get error logs
                    pods = core_v1.list_namespaced_pod(
                        namespace="roam-controller",
                        label_selector=f"job-name={job_name}"
                    )
                    
                    error_msg = "Job failed"
                    if pods.items:
                        pod_name = pods.items[0].metadata.name
                        try:
                            logs = core_v1.read_namespaced_pod_log(
                                name=pod_name,
                                namespace="roam-controller"
                            )
                            error_msg = logs
                        except Exception:
                            pass
                    
                    jobs[job_id].status = "failed"
                    jobs[job_id].error = error_msg
                    break
                    
                # Job still running, wait
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                
            except ApiException as e:
                jobs[job_id].status = "failed"
                jobs[job_id].error = f"Kubernetes API error: {e}"
                break
        
        if elapsed >= timeout:
            jobs[job_id].status = "failed"
            jobs[job_id].error = f"Job timed out after {timeout} seconds"
        
        # Clean up the job (optional, since we have TTL)
        try:
            batch_v1.delete_namespaced_job(
                name=job_name,
                namespace="roam-controller"
            )
        except Exception:
            pass  # Ignore cleanup errors
            
    except Exception as e:
        jobs[job_id].status = "failed"
        jobs[job_id].error = str(e)


@app.post("/eval")
async def evaluate_code(request: CodeRequest):
    """Legacy endpoint for direct code execution."""
    try:
        # WARNING: Using exec can be dangerous and is not recommended for untrusted input.
        from typing import Any

        namespace: dict[str, Any] = {}
        exec(request.code, namespace)

        # The code should end with an expression that we can capture
        # For function calls, we'll capture the last expression
        lines = request.code.strip().split("\n")
        last_line = lines[-1].strip()

        if last_line and not last_line.startswith("#"):
            # If the last line looks like a function call or expression, evaluate it
            try:
                result = eval(last_line, namespace)
                return {"result": result}
            except Exception:
                # If eval fails, maybe it was just a statement, return the namespace
                return {"result": None}
        else:
            return {"result": None}

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
