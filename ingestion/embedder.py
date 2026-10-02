"""
Embedder and Vector Store for Mutual Fund FAQ Chunks.

Converts text chunks into 384-dimensional vectors using
sentence-transformers/all-MiniLM-L6-v2 and stores them in ChromaDB
for similarity-based retrieval.
"""

import logging
import os
from typing import List, Dict, Optional, Tuple

import chromadb
from sentence_transformers import SentenceTransformer

from ingestion.chunker import chunk_all_schemes


# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_DB_PATH = "data/chroma_db"
COLLECTION_NAME = "mf_faq"

# Small batch size to reduce RAM usage on machines with limited memory.
EMBED_BATCH_SIZE = 4


# =============================================================================
# Embedder Class
# =============================================================================

class MFEmbedder:
    """Embeds chunks and stores them in ChromaDB."""

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        db_path: str = CHROMA_DB_PATH,
        collection_name: str = COLLECTION_NAME,
    ):
        """
        Initialize the embedder.

        Args:
            model_name: Sentence-transformers model name.
            db_path: Path to ChromaDB persistent storage.
            collection_name: Name of the ChromaDB collection.
        """

        self.model_name = model_name
        self.db_path = db_path
        self.collection_name = collection_name

        # ---------------------------------------------------------------------
        # Load embedding model
        # ---------------------------------------------------------------------

        logger.info(f"Loading embedding model: {model_name}")

        self.model = SentenceTransformer(model_name)

        logger.info(
            "Model loaded. Vector dimensions: %s",
            self.model.get_sentence_embedding_dimension(),
        )

        # ---------------------------------------------------------------------
        # Set up ChromaDB
        # ---------------------------------------------------------------------

        os.makedirs(db_path, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=db_path
        )

        # ---------------------------------------------------------------------
        # Get or create collection
        # ---------------------------------------------------------------------

        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            "ChromaDB collection '%s' ready at %s",
            collection_name,
            db_path,
        )

    # =========================================================================
    # Collection Helpers
    # =========================================================================

    def is_populated(self) -> bool:
        """Check if the collection already has data."""

        return self.collection.count() > 0

    def get_collection_count(self) -> int:
        """Get the number of chunks currently stored."""

        return self.collection.count()

    # =========================================================================
    # Embedding
    # =========================================================================

    def embed_chunks(
        self,
        chunks: List[Dict],
    ) -> Tuple[List[str], List[List[float]], List[Dict], List[str]]:
        """
        Embed chunks in small batches to reduce memory usage.

        Args:
            chunks: List of chunk dictionaries.

        Returns:
            Tuple containing:
                ids
                embeddings
                metadatas
                documents
        """

        ids: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict] = []
        documents: List[str] = []

        if not chunks:
            logger.warning("No chunks received for embedding.")
            return ids, embeddings, metadatas, documents

        logger.info(
            "Embedding %s chunks with batch size %s",
            len(chunks),
            EMBED_BATCH_SIZE,
        )

        # ---------------------------------------------------------------------
        # Process chunks in small batches
        # ---------------------------------------------------------------------

        for start in range(0, len(chunks), EMBED_BATCH_SIZE):

            batch_chunks = chunks[
                start:start + EMBED_BATCH_SIZE
            ]

            batch_texts = [
                chunk["text"]
                for chunk in batch_chunks
            ]

            logger.info(
                "Embedding chunks %s-%s of %s",
                start + 1,
                min(
                    start + EMBED_BATCH_SIZE,
                    len(chunks),
                ),
                len(chunks),
            )

            # Encode a small batch instead of encoding every chunk separately.
            batch_embeddings = self.model.encode(
                batch_texts,
                batch_size=EMBED_BATCH_SIZE,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            # -----------------------------------------------------------------
            # Store results from this batch
            # -----------------------------------------------------------------

            for chunk, embedding in zip(
                batch_chunks,
                batch_embeddings,
            ):

                ids.append(
                    chunk["chunk_id"]
                )

                embeddings.append(
                    embedding.tolist()
                )

                documents.append(
                    chunk["text"]
                )

                metadatas.append(
                    {
                        "scheme_name": chunk["scheme_name"],
                        "source_url": chunk["source_url"],
                        "section_title": chunk["section_title"],
                        "chunk_index": chunk["chunk_index"],
                        "last_updated": chunk["last_updated"],
                    }
                )

        logger.info(
            "Finished embedding %s chunks",
            len(embeddings),
        )

        return (
            ids,
            embeddings,
            metadatas,
            documents,
        )

    # =========================================================================
    # Store Chunks
    # =========================================================================

    def store_chunks(
        self,
        chunks: List[Dict],
    ) -> int:
        """
        Embed and store chunks in ChromaDB.

        Args:
            chunks: List of chunk dictionaries.

        Returns:
            Number of chunks stored.
        """

        if not chunks:
            logger.warning("No chunks to store.")
            return 0

        (
            ids,
            embeddings,
            metadatas,
            documents,
        ) = self.embed_chunks(chunks)

        # ---------------------------------------------------------------------
        # Add embeddings to ChromaDB
        # ---------------------------------------------------------------------

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

        logger.info(
            "Stored %s chunks in ChromaDB",
            len(chunks),
        )

        return len(chunks)

    # =========================================================================
    # Query
    # =========================================================================

    def query(
        self,
        query_text: str,
        n_results: int = 5,
    ) -> Optional[Dict]:
        """
        Query the vector store.

        Args:
            query_text: Search query.
            n_results: Number of results to return.

        Returns:
            ChromaDB query results or None if collection is empty.
        """

        if self.collection.count() == 0:

            logger.warning(
                "ChromaDB collection is empty."
            )

            return None

        # ---------------------------------------------------------------------
        # Encode the user's query
        # ---------------------------------------------------------------------

        query_embedding = self.model.encode(
            query_text,
            convert_to_numpy=True,
        ).tolist()

        # ---------------------------------------------------------------------
        # Search ChromaDB
        # ---------------------------------------------------------------------

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(
                n_results,
                self.collection.count(),
            ),
        )

        return results


# =============================================================================
# Singleton Instance
# =============================================================================

_embedder: Optional[MFEmbedder] = None


def get_embedder() -> MFEmbedder:
    """
    Get or create the singleton embedder instance.

    Returns:
        MFEmbedder instance.
    """

    global _embedder

    if _embedder is None:
        _embedder = MFEmbedder()

    return _embedder


def get_chroma_collection():
    """
    Get the ChromaDB collection for querying.

    Returns:
        ChromaDB collection object.
    """

    embedder = get_embedder()

    return embedder.collection


# =============================================================================
# Ingestion Function
# =============================================================================

def ingest_to_chroma(
    force: bool = False,
) -> int:
    """
    Run the full ingestion pipeline:

        load → chunk → embed → store

    Args:
        force: If True, clear existing ChromaDB data and re-embed.

    Returns:
        Number of chunks embedded.
    """

    embedder = get_embedder()

    # -------------------------------------------------------------------------
    # Check if already populated
    # -------------------------------------------------------------------------

    if embedder.is_populated() and not force:

        count = embedder.get_collection_count()

        logger.info(
            "ChromaDB already populated with %s chunks. "
            "Skipping ingestion.",
            count,
        )

        logger.info(
            "Use force=True to re-embed."
        )

        return count

    # -------------------------------------------------------------------------
    # Force mode: clear existing collection
    # -------------------------------------------------------------------------

    if embedder.is_populated() and force:

        logger.info(
            "Force mode: clearing existing ChromaDB data."
        )

        embedder.chroma_client.delete_collection(
            COLLECTION_NAME
        )

        embedder.collection = (
            embedder.chroma_client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        )

    # -------------------------------------------------------------------------
    # Load and chunk data
    # -------------------------------------------------------------------------

    logger.info(
        "Loading and chunking scheme data..."
    )

    chunks = chunk_all_schemes()

    logger.info(
        "Created %s chunks",
        len(chunks),
    )

    if not chunks:

        logger.warning(
            "No chunks were created. Nothing to embed."
        )

        return 0

    # -------------------------------------------------------------------------
    # Embed and store
    # -------------------------------------------------------------------------

    logger.info(
        "Embedding chunks and storing in ChromaDB..."
    )

    count = embedder.store_chunks(
        chunks
    )

    logger.info(
        "Ingestion complete. Total chunks in ChromaDB: %s",
        embedder.get_collection_count(),
    )

    return count


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Run the embedder and print results."""

    print("=" * 70)
    print(
        "Mutual Fund FAQ Assistant — Embedder & Vector Store"
    )
    print("=" * 70)
    print()

    # -------------------------------------------------------------------------
    # Run ingestion
    # -------------------------------------------------------------------------

    count = ingest_to_chroma()

    print()

    # -------------------------------------------------------------------------
    # Get embedder
    # -------------------------------------------------------------------------

    embedder = get_embedder()

    # -------------------------------------------------------------------------
    # Collection information
    # -------------------------------------------------------------------------

    print("-" * 70)
    print("COLLECTION INFO")
    print("-" * 70)

    print(
        f"Collection name: {COLLECTION_NAME}"
    )

    print(
        f"Collection count: {embedder.get_collection_count()}"
    )

    print(
        f"Embedding model: {EMBEDDING_MODEL_NAME}"
    )

    print(
        "Vector dimensions: "
        f"{embedder.model.get_sentence_embedding_dimension()}"
    )

    print(
        f"DB path: {CHROMA_DB_PATH}"
    )

    print()

    # -------------------------------------------------------------------------
    # Test query
    # -------------------------------------------------------------------------

    print("-" * 70)
    print("SAMPLE QUERY TEST")
    print("-" * 70)

    test_query = "expense ratio"

    print(
        f"Query: '{test_query}'"
    )

    print()

    results = embedder.query(
        test_query,
        n_results=2,
    )

    if results and results.get("documents"):

        for i, (
            doc,
            metadata,
            distance,
        ) in enumerate(
            zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ):

            print(
                f"Result {i + 1}:"
            )

            print(
                f"  Distance: {distance:.4f}"
            )

            print(
                "  Scheme: "
                f"{metadata.get('scheme_name', 'N/A')}"
            )

            print(
                "  Section: "
                f"{metadata.get('section_title', 'N/A')}"
            )

            print(
                "  Text: "
                f"{doc[:150]}..."
            )

            print()

    else:

        print(
            "No results found."
        )

        print()

    print(
        "Next step: Run the main ingestion script."
    )

    print(
        "  python -m ingestion.ingest"
    )

    print()


if __name__ == "__main__":
    main()