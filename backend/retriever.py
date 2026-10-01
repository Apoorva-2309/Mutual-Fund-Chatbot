"""
Retriever for Mutual Fund FAQ Assistant.

Retrieves relevant chunks from ChromaDB using cosine similarity.
Embeds the user's query using the same model as the chunks,
then fetches the top-K most similar chunks.
"""

import logging
from typing import List, Dict, Optional

from sentence_transformers import SentenceTransformer

from ingestion.embedder import get_chroma_collection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.3
DEFAULT_TOP_K = 5


# =============================================================================
# Retriever Class
# =============================================================================

class Retriever:
    """Retrieves relevant chunks from ChromaDB using cosine similarity."""

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ):
        """
        Initialize the retriever.

        Args:
            model_name: Sentence-transformers model name.
            similarity_threshold: Minimum similarity score for results.
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold

        # Load embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        logger.info(f"Model loaded. Vector dimensions: {self.model.get_sentence_embedding_dimension()}")

        # Get ChromaDB collection
        self.collection = get_chroma_collection()
        logger.info(f"ChromaDB collection ready with {self.collection.count()} chunks")

    def embed_query(self, text: str) -> List[float]:
        """
        Encode a text query into a vector.

        Args:
            text: User query text.

        Returns:
            384-dimensional vector as a list of floats.
        """
        embedding = self.model.encode(text)
        return embedding.tolist()

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict]:
        """
        Retrieve top-K most relevant chunks for a query.

        Args:
            query: User query text.
            top_k: Number of results to return.

        Returns:
            List of chunk dictionaries with text, score, and metadata.

        Raises:
            ValueError: If ChromaDB is empty.
        """
        # Check if collection is empty
        if self.collection.count() == 0:
            raise ValueError(
                "ChromaDB is empty. Run ingestion first: python ingestion/ingest.py"
            )

        # Embed the query
        query_embedding = self.embed_query(query)

        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k * 2, self.collection.count()),  # Fetch extra for deduplication
            include=["documents", "metadatas", "distances"],
        )

        if not results or not results.get("documents") or not results["documents"][0]:
            logger.warning(f"No results found for query: {query}")
            return []

        # Process results
        chunks = []
        seen_sources = set()

        for doc, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # Convert distance to similarity score (cosine distance -> similarity)
            # ChromaDB returns cosine distance, so similarity = 1 - distance
            similarity = 1 - distance

            # Filter by similarity threshold
            if similarity < self.similarity_threshold:
                continue

            # Deduplicate by source_url (keep highest-scoring chunk per source)
            source_url = metadata.get("source_url", "")
            if source_url in seen_sources:
                continue
            seen_sources.add(source_url)

            chunks.append(
                {
                    "text": doc,
                    "score": similarity,
                    "metadata": {
                        "scheme_name": metadata.get("scheme_name", ""),
                        "source_url": source_url,
                        "section_title": metadata.get("section_title", ""),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "last_updated": metadata.get("last_updated", ""),
                    },
                }
            )

            # Stop once we have top_k results
            if len(chunks) >= top_k:
                break

        logger.info(f"Retrieved {len(chunks)} chunks for query: {query[:50]}...")
        return chunks


# =============================================================================
# Singleton Instance
# =============================================================================

retriever = Retriever()
