"""
Query Processor for Mutual Fund FAQ Assistant.

Normalizes user queries, detects PII (Personally Identifiable Information),
and detects advice-type questions that should be refused.
"""

import re
import logging
from typing import Tuple, Optional, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# PII Patterns
# =============================================================================

PII_PATTERNS = [
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    ("Aadhaar", re.compile(r"\b[0-9]{12}\b")),
    ("Phone", re.compile(r"\b\+?91[0-9]{10}\b")),
    ("Email", re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")),
    ("Account Number", re.compile(r"\b[0-9]{9,}\b")),
]


# =============================================================================
# Advice Keywords
# =============================================================================

ADVICE_KEYWORDS = [
    "should i",
    "buy",
    "sell",
    "best fund",
    "recommend",
    "portfolio",
    "invest in",
    "which fund",
    "good fund",
    "top fund",
    "worth",
    "profit",
    "guaranteed",
]


# =============================================================================
# Query Processor Class
# =============================================================================

class QueryProcessor:
    """Processes user queries: normalize, detect PII, detect advice."""

    def __init__(self):
        """Initialize the query processor."""
        self.pii_patterns = PII_PATTERNS
        self.advice_keywords = ADVICE_KEYWORDS

    def normalize(self, text: str) -> str:
        """
        Normalize the input text.

        - Convert to lowercase
        - Remove extra whitespace
        - Remove special characters (keep alphanumeric, spaces, and ?!)
        - Strip leading/trailing whitespace

        Args:
            text: Raw input text.

        Returns:
            Normalized text.
        """
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove special characters (keep alphanumeric, spaces, and ?!)
        text = re.sub(r"[^a-z0-9\s?!]", "", text)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def detect_pii(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Detect PII in the text.

        Args:
            text: Input text to check.

        Returns:
            Tuple of (has_pii: bool, pii_type: str or None).
        """
        if not text:
            return False, None

        for pii_type, pattern in self.pii_patterns:
            if pattern.search(text):
                logger.warning(f"PII detected: {pii_type}")
                return True, pii_type

        return False, None

    def detect_advice(self, text: str) -> bool:
        """
        Detect if the query is asking for investment advice.

        Args:
            text: Normalized input text.

        Returns:
            True if advice query detected, False otherwise.
        """
        if not text:
            return False

        # Normalize first
        normalized = self.normalize(text)

        for keyword in self.advice_keywords:
            if keyword in normalized:
                logger.info(f"Advice query detected: keyword '{keyword}'")
                return True

        return False

    def process(self, text: str) -> Dict:
        """
        Process a user query through the full pipeline.

        Steps:
        1. Normalize the text
        2. Check for PII
        3. Check for advice keywords
        4. Return structured result

        Args:
            text: Raw user input.

        Returns:
            Dictionary with processing results:
            {
                "original": original_text,
                "normalized": normalized_text,
                "has_pii": bool,
                "pii_type": str or None,
                "is_advice": bool,
                "is_valid": bool (False if PII or too short),
                "error": str or None
            }
        """
        result = {
            "original": text,
            "normalized": "",
            "has_pii": False,
            "pii_type": None,
            "is_advice": False,
            "is_valid": True,
            "error": None,
        }

        # Check for empty input
        if not text or not text.strip():
            result["is_valid"] = False
            result["error"] = "EMPTY_QUERY"
            return result

        # Normalize
        normalized = self.normalize(text)
        result["normalized"] = normalized

        # Check minimum length
        if len(normalized) < 5:
            result["is_valid"] = False
            result["error"] = "QUERY_TOO_SHORT"
            return result

        # Check for PII
        has_pii, pii_type = self.detect_pii(text)
        result["has_pii"] = has_pii
        result["pii_type"] = pii_type

        if has_pii:
            result["is_valid"] = False
            result["error"] = "PII_DETECTED"
            return result

        # Check for advice
        is_advice = self.detect_advice(text)
        result["is_advice"] = is_advice

        return result


# =============================================================================
# Singleton Instance
# =============================================================================

query_processor = QueryProcessor()
