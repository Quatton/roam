"""
Pydantic models for ROAM API.
"""

from pydantic import BaseModel


class CodeRequest(BaseModel):
    code: str


class JobResponse(BaseModel):
    task_id: str
    stream_url: str


class HealthResponse(BaseModel):
    status: str
    architecture: str


class JobStatusResponse(BaseModel):
    task_id: str
    status: str
    result: dict | None = None
    error: str | None = None
