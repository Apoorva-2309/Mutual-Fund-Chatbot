"""
Chunker for Mutual Fund Scheme Data.

Splits loaded scheme text into section-aware chunks with metadata.
Each chunk is a small piece of text that can be embedded and stored
in the vector database for retrieval.

Chunking Strategy:
- Chunk size: 400 tokens (approximate using word count * 1.3)
- Overlap: 60 tokens between consecutive chunks
- Section-aware: when a new section_title is detected, start a new chunk
"""

import json
import logging
import os
import uuid
from datetime import date
from typing import List, Dict
from collections import defaultdict

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize

from ingestion.loader import load_all_schemes, save_raw_sections

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Chunking Parameters
# =============================================================================

CHUNK_SIZE_TOKENS = 400       # Target tokens per chunk
OVERLAP_TOKENS = 60           # Overlap between consecutive chunks
TOKENS_PER_WORD = 1.3         # Approximation: 1 word ≈ 1.3 tokens
MIN_CHUNK_LENGTH = 10        # Minimum characters for a valid chunk


# =============================================================================
# Helper Functions
# =============================================================================

def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text.

    Uses word count * 1.3 as an approximation.

    Args:
        text: Input text.

    Returns:
        Estimated token count.
    """
    words = word_tokenize(text)
    return int(len(words) * TOKENS_PER_WORD)


def get_current_date() -> str:
    """Get current date in YYYY-MM-DD format."""
    return date.today().isoformat()


# =============================================================================
# Chunker Class
# =============================================================================

class MFChunker:
    """Chunks mutual fund scheme text into section-aware chunks."""

    def __init__(
        self,
        chunk_size_tokens: int = CHUNK_SIZE_TOKENS,
        overlap_tokens: int = OVERLAP_TOKENS,
    ):
        """
        Initialize the chunker.

        Args:
            chunk_size_tokens: Target tokens per chunk.
            overlap_tokens: Overlap between consecutive chunks.
        """
        self.chunk_size_tokens = chunk_size_tokens
        self.overlap_tokens = overlap_tokens
        self.current_date = get_current_date()

    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using NLTK.

        Args:
            text: Input text.

        Returns:
            List of sentences.
        """
        try:
            sentences = sent_tokenize(text)
        except LookupError:
            # Fallback if NLTK data is not available
            logger.warning("NLTK punkt not found, using simple sentence split")
            sentences = text.split(". ")
            sentences = [s.strip() + "." for s in sentences if s.strip()]
        return sentences

    def chunk_section(self, section: Dict) -> List[Dict]:
        """
        Chunk a single section into multiple chunks.

        Args:
            section: Dictionary with 'scheme_name', 'source_url',
                      'section_title', 'text'.

        Returns:
            List of chunk dictionaries.
        """
        scheme_name = section["scheme_name"]
        source_url = section["source_url"]
        section_title = section["section_title"]
        text = section["text"]

        # Split into sentences
        sentences = self.split_into_sentences(text)
        if not sentences:
            return []

        chunks = []
        current_chunk_sentences = []
        current_token_count = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_tokens = estimate_tokens(sentence)

            # If adding this sentence exceeds chunk size, save current chunk
            if current_token_count + sentence_tokens > self.chunk_size_tokens and current_chunk_sentences:
                # Create chunk from current sentences
                chunk_text = " ".join(current_chunk_sentences)
                if len(chunk_text) >= MIN_CHUNK_LENGTH:
                    chunk = {
                        "chunk_id": str(uuid.uuid4()),
                        "scheme_name": scheme_name,
                        "source_url": source_url,
                        "section_title": section_title,
                        "chunk_index": chunk_index,
                        "text": chunk_text,
                        "last_updated": self.current_date,
                    }
                    chunks.append(chunk)
                    chunk_index += 1

                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk_sentences)
                current_chunk_sentences = overlap_sentences + [sentence]
                current_token_count = estimate_tokens(" ".join(current_chunk_sentences))
            else:
                current_chunk_sentences.append(sentence)
                current_token_count += sentence_tokens

        # Don't forget the last chunk
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            if len(chunk_text) >= MIN_CHUNK_LENGTH:
                chunk = {
                    "chunk_id": str(uuid.uuid4()),
                    "scheme_name": scheme_name,
                    "source_url": source_url,
                    "section_title": section_title,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "last_updated": self.current_date,
                }
                chunks.append(chunk)

        return chunks

    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """
        Get the last few sentences that fit within the overlap token limit.

        Args:
            sentences: List of sentences from the previous chunk.

        Returns:
            List of sentences for overlap.
        """
        overlap_sentences = []
        total_tokens = 0

        # Add sentences from the end until we reach overlap limit
        for sentence in reversed(sentences):
            sentence_tokens = estimate_tokens(sentence)
            if total_tokens + sentence_tokens > self.overlap_tokens:
                break
            overlap_sentences.insert(0, sentence)
            total_tokens += sentence_tokens

        return overlap_sentences

    def chunk_all_sections(self, sections: List[Dict]) -> List[Dict]:
        """
        Chunk all sections from all schemes.

        Args:
            sections: List of section dictionaries from load_all_schemes().

        Returns:
            List of all chunk dictionaries.
        """
        all_chunks = []

        for section in sections:
            chunks = self.chunk_section(section)
            all_chunks.extend(chunks)
            logger.debug(
                f"  {section['scheme_name']} / {section['section_title']}: "
                f"{len(chunks)} chunks"
            )

        logger.info(f"Total chunks created: {len(all_chunks)}")
        return all_chunks


# =============================================================================
# File Writers
# =============================================================================

def save_chunks_to_txt(chunks: List[Dict], filepath: str = "data/chunks.txt") -> None:
    """
    Save chunks to a human-readable text file.

    Args:
        chunks: List of chunk dictionaries.
        filepath: Output file path.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        for i, chunk in enumerate(chunks):
            f.write(f"Chunk {i + 1}\n")
            f.write(f"Scheme: {chunk['scheme_name']}\n")
            f.write(f"Section: {chunk['section_title']}\n")
            f.write(f"Source: {chunk['source_url']}\n")
            f.write(f"Last Updated: {chunk['last_updated']}\n")
            f.write(f"Text: {chunk['text']}\n")
            f.write("---\n\n")

    logger.info(f"Saved {len(chunks)} chunks to {filepath}")


def save_chunks_to_json(chunks: List[Dict], filepath: str = "data/chunks.json") -> None:
    """
    Save chunks to a JSON file.

    Args:
        chunks: List of chunk dictionaries.
        filepath: Output file path.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(chunks)} chunks to {filepath}")


# =============================================================================
# Convenience Functions
# =============================================================================

def chunk_all_schemes() -> List[Dict]:
    """
    Load all schemes and chunk them.

    Returns:
        List of all chunk dictionaries.
    """
    sections = load_all_schemes()

    # Save raw sections for inspection
    save_raw_sections(sections)

    chunker = MFChunker()
    chunks = chunker.chunk_all_sections(sections)

    # Save to files
    save_chunks_to_txt(chunks)
    save_chunks_to_json(chunks)

    return chunks


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Run the chunker and print statistics."""
    print("=" * 70)
    print("Mutual Fund FAQ Assistant — Chunker")
    print("=" * 70)
    print()

    # Load sections
    print("Loading sections...")
    sections = load_all_schemes()
    print(f"Loaded {len(sections)} sections")
    print()

    # Chunk sections
    print("Chunking sections...")
    chunker = MFChunker()
    chunks = chunker.chunk_all_sections(sections)
    print()

    # Save to files
    print("Saving chunks to files...")
    save_chunks_to_txt(chunks)
    save_chunks_to_json(chunks)
    print()

    # Print statistics
    print("-" * 70)
    print("STATISTICS")
    print("-" * 70)

    # Chunks per scheme
    scheme_counts = defaultdict(int)
    for chunk in chunks:
        scheme_counts[chunk["scheme_name"]] += 1

    print("\nChunks per scheme:")
    for scheme_name, count in scheme_counts.items():
        print(f"  {scheme_name}: {count} chunks")

    # Average chunk size
    if chunks:
        avg_size = sum(len(c["text"]) for c in chunks) / len(chunks)
        print(f"\nAverage chunk size: {avg_size:.0f} characters")
        print(f"Total chunks: {len(chunks)}")

    print()
    print("Output files:")
    print("  - data/chunks.txt (human-readable)")
    print("  - data/chunks.json (structured JSON)")
    print()
    print("Next step: Run embedder to create vectors and store in ChromaDB.")
    print("  python -c \"from ingestion.embedder import ingest_to_chroma; ingest_to_chroma()\"")
    print()


if __name__ == "__main__":
    main()
