"""
Main Ingestion Pipeline Script.

Orchestrates the full data ingestion pipeline:
  Load → Chunk → Embed → Store in ChromaDB

Run this script once to build the knowledge base.
Subsequent runs will skip if ChromaDB is already populated
(unless --force is used).
"""

import argparse
import logging
import sys
import time
from typing import Optional

from ingestion.loader import load_all_schemes
from ingestion.chunker import chunk_all_schemes
from ingestion.embedder import ingest_to_chroma

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_ingestion_pipeline(force: bool = False) -> bool:
    """
    Run the full ingestion pipeline.

    Args:
        force: If True, re-embed even if ChromaDB already has data.

    Returns:
        True if successful, False otherwise.
    """
    print("=" * 70)
    print("Mutual Fund FAQ Assistant — Ingestion Pipeline")
    print("=" * 70)
    print()

    start_time = time.time()

    # Step 1: Load
    print("Step 1/4: Loading scheme data...")
    try:
        sections = load_all_schemes()
        print(f"  Loaded {len(sections)} sections from 5 schemes")
    except Exception as e:
        print(f"  ERROR: Failed to load scheme data: {e}")
        return False
    print()

    # Step 2: Chunk
    print("Step 2/4: Chunking sections...")
    try:
        chunks = chunk_all_schemes()
        print(f"  Created {len(chunks)} chunks")
    except Exception as e:
        print(f"  ERROR: Failed to chunk sections: {e}")
        return False
    print()

    # Step 3: Embed and Store
    print("Step 3/4: Embedding chunks and storing in ChromaDB...")
    try:
        count = ingest_to_chroma(force=force)
        print(f"  Embedded {count} chunks in ChromaDB")
    except Exception as e:
        print(f"  ERROR: Failed to embed chunks: {e}")
        return False
    print()

    # Step 4: Summary
    elapsed = time.time() - start_time
    print("Step 4/4: Ingestion complete!")
    print(f"  Total time: {elapsed:.1f} seconds")
    print()
    print("=" * 70)
    print("Next steps:")
    print("  1. Start the API server: uvicorn backend.main:app --reload")
    print("  2. Open the UI: frontend/index.html")
    print("  3. Test with: python -c \"from ingestion.embedder import get_chroma_collection; c = get_chroma_collection(); print(c.count())\"")
    print("=" * 70)
    print()

    return True


def main():
    """Parse arguments and run the ingestion pipeline."""
    parser = argparse.ArgumentParser(
        description="Mutual Fund FAQ Assistant — Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingestion/ingest.py              # Run ingestion (skip if already done)
  python ingestion/ingest.py --force      # Force re-ingestion
  python ingestion/ingest.py --help       # Show this help message
        """,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingestion even if ChromaDB already has data",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    success = run_ingestion_pipeline(force=args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
