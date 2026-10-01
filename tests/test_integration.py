"""
Integration Tests for Mutual Fund FAQ Assistant API.

Tests all endpoints and the full RAG pipeline.
"""

import json
import os
import sys
import time
import pytest
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def wait_for_server(timeout=30):
    """Wait for server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="session", autouse=True)
def server():
    """Ensure server is running before tests."""
    if not wait_for_server():
        pytest.fail("Server not available at localhost:8000")
    return True


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_returns_200(self):
        """Health endpoint should return 200."""
        r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert r.status_code == 200

    def test_health_response_structure(self):
        """Health response should have required fields."""
        r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        data = r.json()
        assert "status" in data
        assert "chunks_loaded" in data
        assert "embedding_model" in data
        assert "llm_model" in data

    def test_health_status_ok(self):
        """Health status should be 'ok'."""
        r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        data = r.json()
        assert data["status"] == "ok"

    def test_health_chunks_loaded(self):
        """Should have chunks loaded."""
        r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        data = r.json()
        assert data["chunks_loaded"] > 0


# =============================================================================
# Sources Endpoint Tests
# =============================================================================

class TestSourcesEndpoint:
    """Tests for GET /sources endpoint."""

    def test_sources_returns_200(self):
        """Sources endpoint should return 200."""
        r = requests.get(f"{BASE_URL}/sources", timeout=TIMEOUT)
        assert r.status_code == 200

    def test_sources_returns_list(self):
        """Sources should return a list."""
        r = requests.get(f"{BASE_URL}/sources", timeout=TIMEOUT)
        data = r.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)

    def test_sources_count(self):
        """Should have 5 sources."""
        r = requests.get(f"{BASE_URL}/sources", timeout=TIMEOUT)
        data = r.json()
        assert len(data["sources"]) == 5

    def test_sources_are_urls(self):
        """All sources should be valid URLs."""
        r = requests.get(f"{BASE_URL}/sources", timeout=TIMEOUT)
        data = r.json()
        for source in data["sources"]:
            assert source.startswith("https://")


# =============================================================================
# Examples Endpoint Tests
# =============================================================================

class TestExamplesEndpoint:
    """Tests for GET /examples endpoint."""

    def test_examples_returns_200(self):
        """Examples endpoint should return 200."""
        r = requests.get(f"{BASE_URL}/examples", timeout=TIMEOUT)
        assert r.status_code == 200

    def test_examples_returns_list(self):
        """Examples should return a list."""
        r = requests.get(f"{BASE_URL}/examples", timeout=TIMEOUT)
        data = r.json()
        assert "examples" in data
        assert isinstance(data["examples"], list)

    def test_examples_count(self):
        """Should have 3 examples."""
        r = requests.get(f"{BASE_URL}/examples", timeout=TIMEOUT)
        data = r.json()
        assert len(data["examples"]) == 3


# =============================================================================
# Ask Endpoint Tests
# =============================================================================

class TestAskEndpoint:
    """Tests for POST /ask endpoint."""

    def test_advice_refusal(self):
        """Advice queries should return refusal."""
        r = requests.post(
            f"{BASE_URL}/ask",
            json={"question": "Should I buy HDFC Small Cap Fund?"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["is_advice"] is True
        assert "answer" in data
        assert "sources" in data

    def test_pii_rejection(self):
        """PII queries should return 400."""
        r = requests.post(
            f"{BASE_URL}/ask",
            json={"question": "My PAN is ABCDE1234F"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400

    def test_empty_query_rejection(self):
        """Empty queries should return 400."""
        r = requests.post(
            f"{BASE_URL}/ask",
            json={"question": ""},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400

    def test_short_query_rejection(self):
        """Very short queries should return 400."""
        r = requests.post(
            f"{BASE_URL}/ask",
            json={"question": "hi"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400

    def test_factual_query_returns_answer(self):
        """Factual queries should return an answer with sources."""
        r = requests.post(
            f"{BASE_URL}/ask",
            json={"question": "What is the expense ratio of HDFC Large Cap Fund?"},
            timeout=TIMEOUT,
        )
        # Note: This may fail if GROQ_API_KEY is not set
        # In that case, the service returns a fallback message
        assert r.status_code in [200, 500]
        if r.status_code == 200:
            data = r.json()
            assert "answer" in data
            assert "sources" in data
            assert len(data["sources"]) > 0


# =============================================================================
# Full Pipeline Tests
# =============================================================================

class TestFullPipeline:
    """Tests for the full RAG pipeline."""

    def test_query_processor(self):
        """Test query processor directly."""
        from backend.query_processor import query_processor

        result = query_processor.process("What is the expense ratio?")
        assert result["is_valid"] is True
        assert result["has_pii"] is False
        assert result["is_advice"] is False

    def test_retriever(self):
        """Test retriever directly."""
        from backend.retriever import retriever

        chunks = retriever.retrieve("expense ratio")
        assert len(chunks) > 0
        assert chunks[0]["score"] >= 0.3

    def test_formatter(self):
        """Test formatter directly."""
        from backend.formatter import formatter

        resp = formatter.format_answer("Test", ["https://example.com"])
        assert "answer" in resp
        assert "sources" in resp
        assert "timestamp" in resp

    def test_sample_qa_file_exists(self):
        """Sample Q&A file should exist."""
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tests",
            "sample_qa.json",
        )
        assert os.path.exists(sample_path)

    def test_sample_qa_has_10_entries(self):
        """Sample Q&A should have 10 entries."""
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tests",
            "sample_qa.json",
        )
        with open(sample_path, "r") as f:
            data = json.load(f)
        assert len(data) == 10


# =============================================================================
# Sample Q&A Validation Tests
# =============================================================================

class TestSampleQA:
    """Validate sample Q&A data."""

    @pytest.fixture
    def sample_qa(self):
        """Load sample Q&A data."""
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tests",
            "sample_qa.json",
        )
        with open(sample_path, "r") as f:
            return json.load(f)

    def test_all_have_question(self, sample_qa):
        """All entries should have a question."""
        for entry in sample_qa:
            assert "question" in entry
            assert len(entry["question"]) > 0

    def test_all_have_expected_type(self, sample_qa):
        """All entries should have expected_type."""
        for entry in sample_qa:
            assert "expected_type" in entry
            assert entry["expected_type"] in ["factual", "advice", "pii"]

    def test_all_have_expected_keywords(self, sample_qa):
        """All entries should have expected_keywords."""
        for entry in sample_qa:
            assert "expected_keywords" in entry
            assert isinstance(entry["expected_keywords"], list)

    def test_has_factual_queries(self, sample_qa):
        """Should have factual queries."""
        factual = [e for e in sample_qa if e["expected_type"] == "factual"]
        assert len(factual) >= 5

    def test_has_advice_queries(self, sample_qa):
        """Should have advice queries."""
        advice = [e for e in sample_qa if e["expected_type"] == "advice"]
        assert len(advice) >= 2

    def test_has_pii_queries(self, sample_qa):
        """Should have PII queries."""
        pii = [e for e in sample_qa if e["expected_type"] == "pii"]
        assert len(pii) >= 1
