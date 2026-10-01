"""
Pydantic Models for Mutual Fund FAQ Assistant API.

Defines request/response schemas for the FastAPI endpoints.
"""

from pydantic import BaseModel, Field
from typing import List


class AskRequest(BaseModel):
    """Request model for POST /ask endpoint."""

    question: str = Field(..., description="User's question")
    session_id: str = Field("default", description="Session ID for conversation memory")


class AskResponse(BaseModel):
    """Response model for successful answers."""

    answer: str = Field(..., description="Generated answer text")
    sources: List[str] = Field(..., description="List of source URLs")
    is_advice: bool = Field(False, description="Whether this is an advice refusal")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")


class HealthResponse(BaseModel):
    """Response model for GET /health endpoint."""

    status: str = Field(..., description="Service status")
    chunks_loaded: int = Field(..., description="Number of chunks in vector DB")
    embedding_model: str = Field(..., description="Embedding model name")
    llm_model: str = Field(..., description="LLM model name")
