"""
LLM Service for Mutual Fund FAQ Assistant.

Integrates with the Groq API to generate answers from retrieved context.
Uses openai/gpt-oss-120b as the primary model and openai/gpt-oss-20b
as fallback.
"""

import os
import time
import logging
from typing import List, Dict, Optional

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Load environment variables
load_dotenv()


# =============================================================================
# Configuration
# =============================================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEFAULT_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "openai/gpt-oss-20b"
MAX_TOKENS = 200
TEMPERATURE = 0.1
MAX_RETRIES = 2
RETRY_DELAY = 1  # seconds


# =============================================================================
# LLM Service Class
# =============================================================================

class LLMService:
    """Generates answers using the Groq API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM service.

        Args:
            api_key: Groq API key. If None, uses GROQ_API_KEY from .env.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or GROQ_API_KEY

        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY not found. "
                "Please add GROQ_API_KEY=your_api_key to .env file."
            )

        # Import groq here to avoid import errors if not installed
        try:
            from groq import Groq
        except ImportError:
            raise ImportError(
                "groq package not installed. "
                "Run: pip install groq"
            )

        self.client = Groq(api_key=self.api_key)
        self.default_model = DEFAULT_MODEL
        self.fallback_model = FALLBACK_MODEL

        logger.info(f"LLM service initialized with model: {self.default_model}")

    def build_prompt(self, question: str, context_chunks: List[Dict]) -> str:
        """
        Build a prompt for the LLM.

        Args:
            question: User's question.
            context_chunks: List of retrieved chunk dictionaries.

        Returns:
            Formatted prompt string.
        """
        # Build context string
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            text = chunk.get("text", "")
            source_url = chunk.get("metadata", {}).get("source_url", "")
            context_parts.append(f"{text}\n(Source: {source_url})")

        context_str = "\n\n".join(context_parts)

        # Build full prompt
        prompt = f"""You are a facts-only mutual fund FAQ assistant. Answer the user's question using ONLY the provided context.

Rules:
1. Answer in ≤3 sentences.
2. Answer the question directly. Do not reproduce or modify the source URL.
3. If asked for investment advice (buy/sell/portfolio), politely decline and provide this educational link: https://www.amfiindia.com/investor-education
4. Do NOT compute or compare returns. If asked about returns, link to the official factsheet.
5. End with the exact current source date provided in the context as "Last updated from sources: YYYY-MM-DD"

Context:
{context_str}

Question: {question}

Answer:"""

        return prompt

    def generate(self, question: str, context_chunks: List[Dict]) -> str:
        prompt = self.build_prompt(question, context_chunks)
        models_to_try = [self.default_model, self.fallback_model]
        last_error = None

        for model in models_to_try:
            try:
                logger.info(f"Calling Groq API with model: {model}")

                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    temperature=TEMPERATURE,
                    max_completion_tokens=500,
                    include_reasoning=False,
                )

                answer = response.choices[0].message.content or ""

                # Normalize common Unicode characters for reliable display
                answer = answer.replace("\u2011", "-")
                answer = answer.replace("\u2013", "-")
                answer = answer.replace("\u2014", "-")
                answer = answer.replace("\u00a0", " ")

                answer = answer.split("Last updated from sources:")[0].rstrip()

                answer += (
                    f"\n\nLast updated from sources: "
                    f"{context_chunks[0].get('metadata', {}).get('last_updated', '')}"
                )

                logger.info(
                    f"Generated answer ({len(answer)} chars) with model: {model}"
                )

                return answer

            except Exception as e:
                last_error = e
                logger.warning(f"Model {model} failed: {e}")
                continue

        raise Exception(f"All Groq models failed. Last error: {last_error}")
    def generate_with_retry(
        self, question: str, context_chunks: List[Dict]
    ) -> str:
        """
        Generate an answer with retry logic.

        Args:
            question: User's question.
            context_chunks: List of retrieved chunk dictionaries.

        Returns:
            Generated answer text or fallback message.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self.generate(question, context_chunks)
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)

        # All retries failed
        fallback_message = (
            "I apologize, but I'm unable to generate an answer right now. "
            "Please try again later."
        )
        logger.error(f"All {MAX_RETRIES} attempts failed. Returning fallback message.")
        return fallback_message


# =============================================================================
# Singleton Instance
# =============================================================================

try:
    llm_service = LLMService()
except ValueError as e:
    logger.warning(f"LLM service not initialized: {e}")
    llm_service = None
