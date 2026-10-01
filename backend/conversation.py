"""
Conversation Memory for Mutual Fund FAQ Assistant.

Stores the last 10 messages per session and provides context
for rewriting follow-up questions before retrieval.
"""

import logging
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

MAX_MESSAGES = 10  # Maximum messages to keep per session


# =============================================================================
# Conversation Store
# =============================================================================

class ConversationStore:
    """In-memory store for conversation history."""

    def __init__(self, max_messages: int = MAX_MESSAGES):
        """
        Initialize the conversation store.

        Args:
            max_messages: Maximum number of messages to keep per session.
        """
        self.max_messages = max_messages
        # session_id -> list of messages
        self.conversations: Dict[str, List[Dict]] = defaultdict(list)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """
        Add a message to the conversation history.

        Args:
            session_id: Unique session identifier.
            role: "user" or "assistant".
            content: Message content.
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }

        self.conversations[session_id].append(message)

        # Keep only the last N messages
        if len(self.conversations[session_id]) > self.max_messages:
            self.conversations[session_id] = self.conversations[session_id][-self.max_messages:]

        logger.debug(f"Added {role} message to session {session_id}. Total: {len(self.conversations[session_id])}")

    def get_history(self, session_id: str) -> List[Dict]:
        """
        Get conversation history for a session.

        Args:
            session_id: Unique session identifier.

        Returns:
            List of messages (oldest first).
        """
        return list(self.conversations.get(session_id, []))

    def get_context_string(self, session_id: str, max_messages: Optional[int] = None) -> str:
        """
        Get conversation history as a formatted string.

        Args:
            session_id: Unique session identifier.
            max_messages: Maximum number of messages to include (from the end).

        Returns:
            Formatted conversation context string.
        """
        history = self.get_history(session_id)
        if max_messages:
            history = history[-max_messages:]

        if not history:
            return ""

        context_parts = []
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role_label}: {msg['content']}")

        return "\n".join(context_parts)

    def clear_session(self, session_id: str) -> None:
        """
        Clear conversation history for a session.

        Args:
            session_id: Unique session identifier.
        """
        if session_id in self.conversations:
            del self.conversations[session_id]
            logger.info(f"Cleared conversation for session {session_id}")

    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self.conversations)


# =============================================================================
# Singleton Instance
# =============================================================================

conversation_store = ConversationStore()
