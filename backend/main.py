"""
FastAPI Application for Mutual Fund FAQ Assistant.

Endpoints:
- POST /ask: Answer a question using RAG
- GET /health: Health check
- GET /sources: List all source URLs
- GET /examples: Get example questions
"""

import logging
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from backend.models import AskRequest, AskResponse, ErrorResponse, HealthResponse
from backend.query_processor import query_processor
from backend.retriever import retriever
from backend.llm import llm_service
from backend.formatter import formatter
from backend.conversation import conversation_store
from backend.question_rewriter import question_rewriter
from ingestion.embedder import get_chroma_collection, ingest_to_chroma
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="MF FAQ Assistant",
    description="Facts-only mutual fund FAQ assistant using RAG",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Endpoints
# =============================================================================

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Answer a question using RAG with conversation memory.

    Process:
    1. Validate query (PII, length)
    2. Check for advice queries
    3. Rewrite follow-up questions using conversation context
    4. Retrieve relevant chunks
    5. Generate answer with LLM
    6. Store messages in conversation history
    7. Format and return response
    """
    session_id = request.session_id
    logger.info(f"Received question: {request.question[:50]}... [session: {session_id}]")

    # Step 1: Process query
    result = query_processor.process(request.question)

    # Check for PII
    if result["has_pii"]:
        logger.warning(f"PII detected: {result['pii_type']}")
        raise HTTPException(status_code=400, detail=formatter.format_pii_error())

    # Check for empty/short query
    if not result["is_valid"]:
        logger.warning(f"Invalid query: {result['error']}")
        raise HTTPException(status_code=400, detail=formatter.format_empty_query_error())

    # Check for advice query
    if result["is_advice"]:
        logger.info("Advice query detected, returning refusal")
        response = formatter.format_refusal()
        # Store in conversation
        conversation_store.add_message(session_id, "user", request.question)
        conversation_store.add_message(session_id, "assistant", response["answer"])
        return response

    # Step 2: Get conversation history and rewrite question if needed
    history = conversation_store.get_history(session_id)
    original_question = result["normalized"]
    rewritten_question = question_rewriter.rewrite_if_needed(original_question, history)

    if rewritten_question != original_question:
        logger.info(f"Question rewritten: '{original_question}' -> '{rewritten_question}'")

    # Step 3: Retrieve chunks
    try:
        chunks = retriever.retrieve(rewritten_question)
    except ValueError as e:
        logger.error(f"Retrieval error: {e}")
        raise HTTPException(status_code=500, detail=formatter.format_service_error())

    if not chunks:
        logger.warning("No chunks retrieved")
        raise HTTPException(status_code=404, detail=formatter.format_no_results_error())

    # Step 4: Generate answer
    if llm_service is None:
        logger.error("LLM service not initialized")
        raise HTTPException(status_code=500, detail=formatter.format_service_error())

    answer = llm_service.generate_with_retry(rewritten_question, chunks)

    # Step 5: Extract sources
    sources = [chunk["metadata"]["source_url"] for chunk in chunks]

    # Step 6: Store messages in conversation history
    conversation_store.add_message(session_id, "user", request.question)
    conversation_store.add_message(session_id, "assistant", answer)

    # Step 7: Format response
    return formatter.format_answer(answer, sources)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    collection = get_chroma_collection()
    return HealthResponse(
        status="ok",
        chunks_loaded=collection.count(),
        embedding_model="all-MiniLM-L6-v2",
        llm_model="llama-3.3-70b-versatile",
    )


@app.get("/sources")
async def get_sources():
    """Get all source URLs."""
    sources = [
        "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
        "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
    ]
    return {"sources": sources}


@app.get("/examples")
async def get_examples():
    """Get example questions for the UI."""
    examples = [
        "What is the expense ratio of HDFC Large Cap Fund?",
        "What is the ELSS lock-in period?",
        "How do I download a capital-gains statement?",
    ]
    return {"examples": examples}


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors (e.g., empty question)."""
    logger.warning(f"Validation error: {exc}")
    raise HTTPException(status_code=400, detail=formatter.format_empty_query_error())


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}")
    raise HTTPException(status_code=500, detail=formatter.format_service_error())


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    collection = get_chroma_collection()

    if collection.count() == 0:
        logger.info("ChromaDB is empty. Running initial ingestion...")
        ingest_to_chroma()
    else:
        logger.info(
            "ChromaDB already contains %s chunks.",
            collection.count(),
        )

    uvicorn.run(app, host="0.0.0.0", port=8000)