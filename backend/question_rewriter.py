"""
Question Rewriter for Mutual Fund FAQ Assistant.

Uses conversation context to rewrite follow-up questions
before retrieval. Resolves pronouns and references like
"its", "that fund", "what about fees?" using prior context.
"""

import logging
from typing import List, Dict, Optional

from backend.llm import llm_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Question Rewriter
# =============================================================================

class QuestionRewriter:
    """Rewrites follow-up questions using conversation context."""

    def __init__(self):
        """Initialize the question rewriter."""
        self.llm = llm_service

    def needs_rewriting(self, question: str, history: List[Dict]) -> bool:
        """
        Check if a question likely needs rewriting based on context.

        Args:
            question: The user's question.
            history: Conversation history.

        Returns:
            True if the question likely contains references that need resolution.
        """
        if not history:
            return False

        # Common patterns that indicate follow-up questions
        follow_up_patterns = [
            "its", "it's", "their", "them", "they",
            "this fund", "that fund", "the fund",
            "what about", "how about", "and", "also",
            "what is its", "what's its", "tell me more",
            "more about", "what about its", "how about its",
            "same", "similarly", "compared to",
        ]

        question_lower = question.lower()

        # Check if question is very short (likely a follow-up)
        if len(question.split()) <= 3:
            return True

        # Check for follow-up patterns
        for pattern in follow_up_patterns:
            if pattern in question_lower:
                return True

        return False

    def rewrite(
        self,
        question: str,
        history: List[Dict],
    ) -> str:
        """
        Rewrite a follow-up question using conversation context.

        Args:
            question: The user's original question.
            history: Conversation history.

        Returns:
            Rewritten question with resolved references.
        """
        if not history:
            return question

        if not self.needs_rewriting(question, history):
            return question

        # Build context from history
        context_parts = []
        for msg in history[-6:]:  # Use last 6 messages for context
            role_label = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role_label}: {msg['content']}")

        context = "\n".join(context_parts)

        # Build rewrite prompt
        rewrite_prompt = f"""You are a question rewriter for a mutual fund FAQ assistant.

Given the conversation context and a follow-up question, rewrite the question to be self-contained by resolving any references (pronouns, "this fund", "its", etc.) using the context.

Rules:
1. If the question is already self-contained, return it unchanged.
2. If the question contains references, resolve them using the context.
3. Return ONLY the rewritten question, nothing else.
4. Keep the rewritten question concise and clear.

Conversation Context:
{context}

Follow-up Question: {question}

Rewritten Question:"""

        try:
            if self.llm is None:
                logger.warning("LLM service not available, returning original question")
                return question

            response = self.llm.client.chat.completions.create(
                model=self.llm.default_model,
                messages=[{"role": "user", "content": rewrite_prompt}],
                temperature=0.1,
                max_tokens=100,
            )

            rewritten = response.choices[0].message.content.strip()

            # Clean up the response (remove quotes if present)
            rewritten = rewritten.strip('"').strip("'")

            if rewritten and rewritten != question:
                logger.info(f"Rewritten: '{question}' -> '{rewritten}'")
                return rewritten

            return question

        except Exception as e:
            logger.warning(f"Question rewriting failed: {e}")
            return question

    def rewrite_if_needed(
        self,
        question: str,
        history: List[Dict],
    ) -> str:
        """
        Rewrite question only if it needs it.

        Args:
            question: The user's question.
            history: Conversation history.

        Returns:
            Original or rewritten question.
        """
        if not self.needs_rewriting(question, history):
            return question

        return self.rewrite(question, history)


# =============================================================================
# Singleton Instance
# =============================================================================

question_rewriter = QuestionRewriter()
