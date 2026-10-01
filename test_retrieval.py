"""Quick retrieval test - run this to test ChromaDB retrieval."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.retriever import retriever

print("=" * 70)
print("RETRIEVAL TEST")
print("=" * 70)
print()

# Test queries
queries = [
    "expense ratio",
    "ELSS lock-in period",
    "minimum SIP amount",
    "riskometer level",
    "benchmark",
    "exit load",
]

for query in queries:
    print(f"Query: '{query}'")
    print("-" * 50)
    try:
        results = retriever.retrieve(query, top_k=3)
        print(f"  Retrieved {len(results)} chunks:")
        for i, r in enumerate(results, 1):
            print(f"  [{i}] Score: {r['score']:.3f} | {r['metadata']['scheme_name']} | {r['metadata']['section_title']}")
            print(f"      Text: {r['text'][:100]}...")
    except Exception as e:
        print(f"  Error: {e}")
    print()

print("=" * 70)
print("Test complete!")
