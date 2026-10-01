"""
Response Formatter for Mutual Fund FAQ Assistant.

Structures API responses into consistent JSON formats for:
- Successful answers with sources
- Advice refusals
- PII detection errors
- Empty query errors
- No results errors
- Service errors
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Response Formatter Class
# =============================================================================

class ResponseFormatter:
    """Formats API responses into consistent JSON structures."""

    def __init__(self):
        """Initialize the response formatter."""
        pass

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format."""
        return datetime.now(timezone.utc).isoformat()

    def format_answer(
        self,
        answer: str,
        sources: List[str],
        is_advice: bool = False,
    ) -> Dict:
        """
        Format a successful answer response.

        Args:
            answer: The generated answer text.
            sources: List of source URLs.
            is_advice: Whether this is an advice refusal.

        Returns:
            Response dictionary.
        """
        return {
            "answer": answer,
            "sources": sources,
            "is_advice": is_advice,
            "timestamp": self._get_timestamp(),
        }

    def format_refusal(self) -> Dict:
        """
        Format an advice refusal response.

        Returns:
            Refusal response dictionary.
        """
        return {
            "answer": (
                "I can only provide factual information, not investment advice. "
                "Please refer to AMFI's investor education resources."
            ),
            "sources": ["https://www.amfiindia.com/investor-education"],
            "is_advice": True,
            "timestamp": self._get_timestamp(),
        }

    def format_pii_error(self) -> Dict:
        """
        Format a PII detection error response.

        Returns:
            Error response dictionary.
        """
        return {
            "error": (
                "Please do not share personal information "
                "(PAN, Aadhaar, phone, email)."
            ),
            "code": "PII_DETECTED",
        }

    def format_empty_query_error(self) -> Dict:
        """
        Format an empty query error response.

        Returns:
            Error response dictionary.
        """
        return {
            "error": "Please enter a question.",
            "code": "EMPTY_QUERY",
        }

    def format_no_results_error(self) -> Dict:
        """
        Format a no results error response.

        Returns:
            Error response dictionary.
        """
        return {
            "error": (
                "I couldn't find relevant information. "
                "Try rephrasing your question."
            ),
            "code": "NO_RESULTS",
        }

    def format_service_error(self) -> Dict:
        """
        Format a service error response.

        Returns:
            Error response dictionary.
        """
        return {
            "error": "Service temporarily unavailable. Please try again.",
            "code": "SERVICE_ERROR",
        }


# =============================================================================
# Singleton Instance
# =============================================================================

formatter = ResponseFormatter()
