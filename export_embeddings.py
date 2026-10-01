"""
Export chunks and their embeddings to a readable txt file.

Usage:
    python export_embeddings.py
"""

import logging
from ingestion.embedder import get_chroma_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_to_txt(output_path: str = "data/chunks_with_embeddings.txt"):
    """Export all chunks with their embedding vectors to a txt file."""
    collection = get_chroma_collection()
    count = collection.count()

    if count == 0:
        logger.error("ChromaDB is empty. Run ingestion first.")
        return

    # Get all records
    results = collection.get(include=["documents", "metadatas", "embeddings"])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("CHUNKS WITH EMBEDDINGS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total chunks: {count}\n")
        f.write(f"Embedding dimensions: {len(results['embeddings'][0])}\n\n")

        for i, (doc, metadata, embedding) in enumerate(
            zip(results["documents"], results["metadatas"], results["embeddings"])
        ):
            f.write("-" * 80 + "\n")
            f.write(f"CHUNK {i + 1}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Scheme: {metadata.get('scheme_name', 'N/A')}\n")
            f.write(f"Section: {metadata.get('section_title', 'N/A')}\n")
            f.write(f"Source: {metadata.get('source_url', 'N/A')}\n")
            f.write(f"Last Updated: {metadata.get('last_updated', 'N/A')}\n")
            f.write(f"\nTEXT:\n{doc}\n")
            f.write(f"\nEMBEDDING (384-dim vector):\n")
            # Write embedding in rows of 10 values for readability
            for j in range(0, len(embedding), 10):
                row = embedding[j : j + 10]
                f.write("  " + " ".join(f"{v:8.4f}" for v in row) + "\n")
            f.write("\n")

    logger.info(f"Exported {count} chunks with embeddings to {output_path}")


if __name__ == "__main__":
    export_to_txt()
