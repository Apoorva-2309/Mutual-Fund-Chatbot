# Implementation Guide
## Mutual Fund FAQ Assistant — Facts-Only RAG Chatbot

| Field | Detail |
|---|---|
| **Document Name** | MF FAQ Assistant — Implementation Guide |
| **Version** | 1.0 |
| **Date** | 2026-10-01 |
| **Status** | Draft |
| **Parent Docs** | [PRD.md](./PRD.md) · [architecture.md](./architecture.md) |

---

## How to Use This Document

This guide is designed to be used with **Cursor** (or any AI coding assistant). Each phase provides:

1. **Objective** — what to build
2. **Files to create** — exact file paths
3. **Step-by-step instructions** — what to tell Cursor
4. **Code templates** — starter code to paste into Cursor
5. **Verification** — how to test the phase

### Cursor Prompt Strategy

For each phase, you have two options:

**Option A: Guided (Recommended for first run)**
> Paste the "Cursor Prompt" block into Cursor. It will generate the code. Review, then paste the "Verification" block to test.

**Option B: Manual (For customization)**
> Follow the step-by-step instructions and code templates to write files yourself, asking Cursor for help on specific parts.

---

## Phase 0: Project Setup

### Objective
Initialize the project structure, install dependencies, and configure environment variables.

### Files to Create
```
RAG-Chatbot-Grow/
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

### Cursor Prompt for Phase 0

```
Set up a Python project at the current directory with the following:

1. Create a .gitignore file that ignores:
   - .env
   - data/chroma_db/
   - __pycache__/
   - *.pyc
   - .venv/
   - chunks.txt
   - chunks.json

2. Create a requirements.txt with these dependencies:
   - fastapi==0.104.1
   - uvicorn==0.24.0
   - python-dotenv==1.0.0
   - pydantic==2.5.0
   - sentence-transformers==2.2.2
   - chromadb==0.4.18
   - requests==2.31.0
   - beautifulsoup4==4.12.2
   - pypdf==3.17.1
   - groq==0.1.0
   - nltk==3.8.1
   - numpy==1.26.2

3. Create a .env file with:
   GROQ_API_KEY=your_api_key_here

4. Create the following directory structure:
   - ingestion/
   - backend/
   - frontend/
   - data/
   - sources/
   - tests/

5. Create an empty __init__.py in ingestion/ and backend/

Do NOT install dependencies yet. Just create the files and directories.
```

### Verification
```bash
# Check directory structure
dir /s /b

# Expected output should show:
# .env
# .gitignore
# requirements.txt
# ingestion/
# backend/
# frontend/
# data/
# sources/
# tests/
```

---

## Phase 1: Data Ingestion — Loader

### Objective
Build the data loader that fetches and parses HTML pages from Groww for the 5 HDFC schemes.

### Files to Create
```
ingestion/__init__.py
ingestion/loader.py
```

### Cursor Prompt for Phase 1

```
Create a Python module ingestion/loader.py that loads mutual fund scheme data from Groww HTML pages.

Requirements:
1. Define a list of 5 source URLs for HDFC schemes:
   - HDFC Large Cap Fund: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
   - HDFC Equity Fund (Flexi Cap): https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
   - HDFC ELSS Tax Saver Fund: https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
   - HDFC Small Cap Fund: https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth
   - HDFC Balanced Advantage Fund: https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth

2. For each URL, fetch the HTML using requests with a User-Agent header.

3. Parse the HTML using BeautifulSoup and extract these sections:
   - Scheme overview / description
   - Expense ratio
   - Exit load structure
   - Riskometer level
   - Benchmark
   - Minimum SIP amount
   - Lock-in period (for ELSS)
   - Fund manager details
   - Asset allocation

4. Clean the extracted text: remove extra whitespace, nav elements, footer, ads, scripts.

5. Return a list of dictionaries, each containing:
   - scheme_name: str
   - source_url: str
   - section_title: str
   - text: str

6. Handle errors gracefully: if a page fails to load, log the error and continue with remaining pages.

7. Add a main() function that loads all pages and prints a summary (number of sections per scheme).

Use type hints and docstrings. Import from ingestion.loader import load_all_schemes for external use.
```

### Verification
```bash
# Test the loader
python -c "from ingestion.loader import load_all_schemes; data = load_all_schemes(); print(f'Loaded {len(data)} sections'); [print(f'  {d[\"scheme_name\"]}: {d[\"section_title\"]}') for d in data[:5]]"

# Expected: Should print loaded sections for all 5 schemes
```

---

## Phase 2: Data Ingestion — Chunker

### Objective
Build the chunker that splits loaded text into section-aware chunks with metadata.

### Files to Create
```
ingestion/chunker.py
```

### Cursor Prompt for Phase 2

```
Create a Python module ingestion/chunker.py that chunks mutual fund text data.

Requirements:
1. Import the load_all_schemes function from ingestion.loader.

2. Define a chunking strategy:
   - Chunk size: 400 tokens (approximate using word count * 1.3)
   - Overlap: 60 tokens between consecutive chunks
   - Section-aware: when a new section_title is detected, start a new chunk

3. For each section from load_all_schemes():
   a. Split text into sentences using nltk.sent_tokenize
   b. Group sentences into chunks of approximately 400 tokens
   c. Add overlap: last 60 tokens of previous chunk become first 60 tokens of next chunk
   d. Attach metadata to each chunk

4. Each chunk should be a dictionary with:
   - chunk_id: str (use uuid4)
   - scheme_name: str
   - source_url: str
   - section_title: str
   - chunk_index: int (0-based index within the section)
   - text: str
   - last_updated: str (current date in YYYY-MM-DD format)

5. Save all chunks to two files:
   - data/chunks.txt: human-readable format (one chunk per block, separated by "---")
   - data/chunks.json: JSON array of all chunk dictionaries

6. Add a main() function that runs the chunking and prints statistics:
   - Total chunks created
   - Chunks per scheme
   - Average chunk size

Use type hints and docstrings. Import from ingestion.chunker import chunk_all_schemes for external use.
```

### Verification
```bash
# Test the chunker
python -c "from ingestion.chunker import chunk_all_schemes; chunks = chunk_all_schemes(); print(f'Created {len(chunks)} chunks'); print(f'First chunk keys: {list(chunks[0].keys())}')"

# Check output files
type data\chunks.txt
type data\chunks.json

# Expected: chunks.txt should show readable chunks separated by "---"
# Expected: chunks.json should be valid JSON with all chunk metadata
```

---

## Phase 3: Data Ingestion — Embedder & Vector Store

### Objective
Build the embedder that converts chunks to vectors and stores them in ChromaDB.

### Files to Create
```
ingestion/embedder.py
```

### Cursor Prompt for Phase 3

```
Create a Python module ingestion/embedder.py that embeds chunks and stores them in ChromaDB.

Requirements:
1. Import the chunk_all_schemes function from ingestion.chunker.

2. Use sentence-transformers/all-MiniLM-L6-v2 as the embedding model.
   - Load the model once at module level (or lazily with caching)
   - The model produces 384-dimensional vectors

3. Set up ChromaDB:
   - Use PersistentClient with path="data/chroma_db"
   - Create or get a collection named "mf_faq"
   - Use cosine similarity as the distance metric

4. For each chunk:
   a. Encode the chunk text using the embedding model
   b. Store in ChromaDB with:
      - id: chunk_id
      - embedding: the 384-dim vector
      - document: chunk text
      - metadata: {scheme_name, source_url, section_title, chunk_index, last_updated}

5. Before storing, check if chunks already exist in the collection.
   - If collection has items, skip ingestion (log "ChromaDB already populated")
   - If empty, run full ingestion

6. Add a function get_chroma_collection() that returns the ChromaDB collection for querying.

7. Add a main() function that runs the embedding and prints:
   - Number of chunks embedded
   - ChromaDB collection count
   - Sample query test (search for "expense ratio" and print top result)

Use type hints and docstrings. Import from ingestion.embedder import ingest_to_chroma, get_chroma_collection for external use.
```

### Verification
```bash
# Test the embedder
python -c "from ingestion.embedder import ingest_to_chroma; ingest_to_chroma()"

# Expected: Should print embedding progress and final count

# Test retrieval
python -c "from ingestion.embedder import get_chroma_collection; c = get_chroma_collection(); print(f'Collection count: {c.count()}'); results = c.query(query_texts=['expense ratio'], n_results=2); print(f'Top result: {results[\"documents\"][0][0][:100]}')"

# Expected: Collection count should match number of chunks
# Expected: Top result should be related to expense ratio
```

---

## Phase 4: Data Ingestion — Main Script

### Objective
Create the main ingestion script that orchestrates the full pipeline.

### Files to Create
```
ingestion/ingest.py
```

### Cursor Prompt for Phase 4

```
Create a Python script ingestion/ingest.py that orchestrates the full ingestion pipeline.

Requirements:
1. Import load_all_schemes from ingestion.loader
2. Import chunk_all_schemes from ingestion.chunker
3. Import ingest_to_chroma from ingestion.embedder

4. Create a main() function that:
   a. Prints "Starting ingestion pipeline..."
   b. Calls load_all_schemes() and prints number of sections loaded
   c. Calls chunk_all_schemes() and prints number of chunks created
   d. Calls ingest_to_chroma() and prints number of chunks embedded
   e. Prints "Ingestion complete!"

5. Add error handling: if any step fails, print the error and exit gracefully.

6. Add a --force flag (using argparse) that re-embeds even if ChromaDB already has data.

7. Make the script executable with: python ingestion/ingest.py

Use type hints and docstrings.
```

### Verification
```bash
# Run full ingestion
python ingestion/ingest.py

# Expected output:
# Starting ingestion pipeline...
# Loaded X sections from 5 schemes
# Created Y chunks
# Embedded Y chunks in ChromaDB
# Ingestion complete!

# Run with force flag
python ingestion/ingest.py --force

# Expected: Should re-embed all chunks
```

---

## Phase 5: Query Processor

### Objective
Build the query processor that normalizes queries, detects PII, and detects advice-type questions.

### Files to Create
```
backend/__init__.py
backend/query_processor.py
```

### Cursor Prompt for Phase 5

```
Create a Python module backend/query_processor.py that processes user queries.

Requirements:

1. Define PII_PATTERNS as a list of regex patterns:
   - PAN: r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'
   - Aadhaar: r'\b[0-9]{12}\b'
   - Phone: r'\b\+?91[0-9]{10}\b'
   - Email: r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-Z]{2,}\b'
   - Account number: r'\b[0-9]{9,}\b'

2. Define ADVICE_KEYWORDS as a list:
   ["should i", "buy", "sell", "best fund", "recommend", "portfolio", 
    "invest in", "which fund", "good fund", "top fund", "worth", 
    "profit", "guaranteed"]

3. Create a class QueryProcessor with these methods:

   a. normalize(text: str) -> str:
      - Convert to lowercase
      - Remove extra whitespace
      - Remove special characters (keep alphanumeric, spaces, and ?!)
      - Strip leading/trailing whitespace

   b. detect_pii(text: str) -> tuple[bool, str]:
      - Check text against all PII_PATTERNS
      - Return (True, pattern_name) if PII found
      - Return (False, "") if no PII found

   c. detect_advice(text: str) -> bool:
      - Check if any ADVICE_KEYWORDS appear in the normalized text
      - Return True if advice query detected

   d. process(text: str) -> dict:
      - Normalize the text
      - Check for PII
      - Check for advice
      - Return a dictionary:
        {
          "original": original_text,
          "normalized": normalized_text,
          "has_pii": bool,
          "pii_type": str or None,
          "is_advice": bool,
          "is_valid": bool (False if PII or too short),
          "error": str or None
        }

4. Add a singleton instance: query_processor = QueryProcessor()

Use type hints and docstrings. Import from backend.query_processor import query_processor for external use.
```

### Verification
```bash
# Test the query processor
python -c "
from backend.query_processor import query_processor as qp

# Test normalization
print(qp.normalize('  What is the EXPENSE RATIO?  '))

# Test PII detection
print(qp.detect_pii('My PAN is ABCDE1234F'))
print(qp.detect_pii('What is the expense ratio?'))

# Test advice detection
print(qp.detect_advice('should I buy HDFC fund'))
print(qp.detect_advice('what is the expense ratio'))

# Test full processing
print(qp.process('What is the expense ratio of HDFC Large Cap Fund?'))
print(qp.process('My PAN is ABCDE1234F'))
print(qp.process('Should I buy HDFC Small Cap Fund?'))
"

# Expected: All tests should pass with correct outputs
```

---

## Phase 6: Retriever

### Objective
Build the retriever that fetches top-K chunks from ChromaDB.

### Files to Create
```
backend/retriever.py
```

### Cursor Prompt for Phase 6

```
Create a Python module backend/retriever.py that retrieves relevant chunks from ChromaDB.

Requirements:

1. Import get_chroma_collection from ingestion.embedder
2. Import SentenceTransformer from sentence_transformers

3. Create a class Retriever with:

   a. __init__(self):
      - Load the embedding model: sentence-transformers/all-MiniLM-L6-v2
      - Get the ChromaDB collection using get_chroma_collection()

   b. embed_query(self, text: str) -> list[float]:
      - Encode the text using the embedding model
      - Return the 384-dim vector as a list

   c. retrieve(self, query: str, top_k: int = 5) -> list[dict]:
      - Embed the query
      - Query ChromaDB with cosine similarity
      - Filter results with similarity score >= 0.3
      - Deduplicate by source_url (keep highest-scoring chunk per source)
      - Return top_k chunks as list of dictionaries:
        [
          {
            "text": str,
            "score": float,
            "metadata": {
              "scheme_name": str,
              "source_url": str,
              "section_title": str,
              "chunk_index": int,
              "last_updated": str
            }
          }
        ]

4. Add a singleton instance: retriever = Retriever()

5. Handle the case where ChromaDB is empty:
   - Raise a clear error: "ChromaDB is empty. Run ingestion first: python ingestion/ingest.py"

Use type hints and docstrings. Import from backend.retriever import retriever for external use.
```

### Verification
```bash
# Test the retriever
python -c "
from backend.retriever import retriever

# Test embedding
vector = retriever.embed_query('expense ratio')
print(f'Vector dimensions: {len(vector)}')

# Test retrieval
results = retriever.retrieve('What is the expense ratio of HDFC Large Cap Fund?')
print(f'Retrieved {len(results)} chunks')
for r in results:
    print(f'  Score: {r[\"score\"]:.3f} | Scheme: {r[\"metadata\"][\"scheme_name\"]} | Section: {r[\"metadata\"][\"section_title\"]}')
    print(f'  Text: {r[\"text\"][:100]}...')
"

# Expected: Vector should be 384-dim
# Expected: Should retrieve relevant chunks with scores >= 0.3
```

---

## Phase 7: LLM Service

### Objective
Build the LLM service that calls Groq API to generate answers.

### Files to Create
```
backend/llm.py
```

### Cursor Prompt for Phase 7

```
Create a Python module backend/llm.py that integrates with the Groq API.

Requirements:

1. Import os, dotenv, and groq
2. Load environment variables using dotenv.load_dotenv()
3. Get GROQ_API_KEY from environment variables

4. Create a class LLMService with:

   a. __init__(self):
      - Initialize Groq client with API key
      - Set default model: "llama-3.3-70b-versatile"
      - Set fallback model: "mixtral-8x7b-32768"

   b. build_prompt(self, question: str, context_chunks: list[dict]) -> str:
      - Build a prompt following this template:
        SYSTEM: You are a facts-only mutual fund FAQ assistant. Answer using ONLY the provided context. Rules: 1. Answer in ≤3 sentences. 2. Include at least one source citation from the context. 3. If asked for advice, decline politely and provide: https://www.amfiindia.com/investor-education 4. Do NOT compute or compare returns. 5. End with: "Last updated from sources: [date]"
        
        Context:
        [chunk 1 text] (Source: [source_url])
        [chunk 2 text] (Source: [source_url])
        ...
        
        Question: {question}
        
        Answer:

   c. generate(self, question: str, context_chunks: list[dict]) -> str:
      - Build the prompt
      - Call Groq API with temperature=0.1, max_tokens=200
      - Return the generated text
      - Handle errors: retry once with fallback model, then raise

   d. generate_with_retry(self, question: str, context_chunks: list[dict]) -> str:
      - Try generate() up to 2 times
      - On failure, wait 1 second and retry
      - On final failure, return a fallback message

5. Add a singleton instance: llm_service = LLMService()

6. Handle missing API key:
   - If GROQ_API_KEY is not set, raise a clear error with instructions

Use type hints and docstrings. Import from backend.llm import llm_service for external use.
```

### Verification
```bash
# Test the LLM service (requires GROQ_API_KEY in .env)
python -c "
from backend.llm import llm_service

# Test prompt building
chunks = [
    {'text': 'The expense ratio of HDFC Large Cap Fund is 0.75%.', 'metadata': {'source_url': 'https://groww.in/test'}}
]
prompt = llm_service.build_prompt('What is the expense ratio?', chunks)
print('Prompt built successfully')
print(prompt[:200])

# Test generation
answer = llm_service.generate('What is the expense ratio of HDFC Large Cap Fund?', chunks)
print(f'Answer: {answer}')
"

# Expected: Prompt should follow the template
# Expected: Answer should be factual with citation
```

---

## Phase 8: Response Formatter

### Objective
Build the response formatter that structures the API response.

### Files to Create
```
backend/formatter.py
```

### Cursor Prompt for Phase 8

```
Create a Python module backend/formatter.py that formats API responses.

Requirements:

1. Import datetime

2. Create a class ResponseFormatter with:

   a. format_answer(self, answer: str, sources: list[str], is_advice: bool = False) -> dict:
      - Return a dictionary:
        {
          "answer": answer,
          "sources": sources,
          "is_advice": is_advice,
          "timestamp": current ISO 8601 timestamp
        }

   b. format_refusal(self) -> dict:
      - Return a refusal response:
        {
          "answer": "I can only provide factual information, not investment advice. Please refer to AMFI's investor education resources.",
          "sources": ["https://www.amfiindia.com/investor-education"],
          "is_advice": True,
          "timestamp": current ISO 8601 timestamp
        }

   c. format_pii_error(self) -> dict:
      - Return a PII error response:
        {
          "error": "Please do not share personal information (PAN, Aadhaar, phone, email).",
          "code": "PII_DETECTED"
        }

   d. format_empty_query_error(self) -> dict:
      - Return an empty query error:
        {
          "error": "Please enter a question.",
          "code": "EMPTY_QUERY"
        }

   e. format_no_results_error(self) -> dict:
      - Return a no results error:
        {
          "error": "I couldn't find relevant information. Try rephrasing your question.",
          "code": "NO_RESULTS"
        }

   f. format_service_error(self) -> dict:
      - Return a service error:
        {
          "error": "Service temporarily unavailable. Please try again.",
          "code": "SERVICE_ERROR"
        }

3. Add a singleton instance: formatter = ResponseFormatter()

Use type hints and docstrings. Import from backend.formatter import formatter for external use.
```

### Verification
```bash
# Test the formatter
python -c "
from backend.formatter import formatter

# Test answer formatting
resp = formatter.format_answer('Test answer.', ['https://example.com'])
print(resp)

# Test refusal formatting
resp = formatter.format_refusal()
print(resp)

# Test PII error
resp = formatter.format_pii_error()
print(resp)
"

# Expected: All responses should have correct structure
```

---

## Phase 9: API Layer

### Objective
Build the FastAPI backend with all endpoints.

### Files to Create
```
backend/main.py
backend/models.py
```

### Cursor Prompt for Phase 9

```
Create a FastAPI application in backend/main.py with the following:

1. Create backend/models.py with Pydantic models:
   - AskRequest: { question: str }
   - AskResponse: { answer: str, sources: list[str], is_advice: bool, timestamp: str }
   - ErrorResponse: { error: str, code: str }
   - HealthResponse: { status: str, chunks_loaded: int, embedding_model: str, llm_model: str }

2. Create backend/main.py with FastAPI app:

   a. Import all necessary modules:
      - FastAPI, HTTPException from fastapi
      - AskRequest, AskResponse from backend.models
      - query_processor from backend.query_processor
      - retriever from backend.retriever
      - llm_service from backend.llm
      - formatter from backend.formatter
      - get_chroma_collection from ingestion.embedder

   b. Create FastAPI app with title="MF FAQ Assistant"

   c. POST /ask endpoint:
      - Receive AskRequest
      - Process query using query_processor.process()
      - If has_pii: return formatter.format_pii_error() with status 400
      - If not valid (too short): return formatter.format_empty_query_error() with status 400
      - If is_advice: return formatter.format_refusal()
      - Otherwise:
        - Retrieve chunks using retriever.retrieve()
        - If no chunks: return formatter.format_no_results_error() with status 404
        - Generate answer using llm_service.generate_with_retry()
        - Extract source URLs from chunk metadata
        - Return formatter.format_answer()

   d. GET /health endpoint:
      - Return HealthResponse with:
        - status: "ok"
        - chunks_loaded: collection.count()
        - embedding_model: "all-MiniLM-L6-v2"
        - llm_model: "llama-3.3-70b-versatile"

   e. GET /sources endpoint:
      - Return list of all source URLs (hardcoded list of 5 Groww URLs)

   f. GET /examples endpoint:
      - Return list of 3 example questions:
        - "What is the expense ratio of HDFC Large Cap Fund?"
        - "What is the ELSS lock-in period?"
        - "How do I download a capital-gains statement?"

   g. Add CORS middleware to allow all origins (for local development)

   h. Add error handlers for generic exceptions

3. Make the app runnable with: uvicorn backend.main:app --reload

Use type hints and docstrings.
```

### Verification
```bash
# Start the server
uvicorn backend.main:app --reload

# Test health endpoint
curl http://localhost:8000/health

# Test ask endpoint
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d "{\"question\": \"What is the expense ratio of HDFC Large Cap Fund?\"}"

# Test advice refusal
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d "{\"question\": \"Should I buy HDFC Small Cap Fund?\"}"

# Test PII rejection
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d "{\"question\": \"My PAN is ABCDE1234F\"}"

# Test sources endpoint
curl http://localhost:8000/sources

# Test examples endpoint
curl http://localhost:8000/examples
```

---

## Phase 10: Frontend UI

### Objective
Build the tiny web UI with welcome message, example questions, and disclaimer.

### Files to Create
```
frontend/index.html
frontend/style.css
frontend/app.js
```

### Cursor Prompt for Phase 10

```
Create a tiny web UI for the MF FAQ Assistant with three files:

1. frontend/index.html:
   - Create a clean, centered layout with max-width 800px
   - Header: "MF FAQ Assistant"
   - Welcome message: "Hi! I can answer factual questions about HDFC mutual fund schemes. Facts-only. No advice."
   - Example questions section with 3 clickable buttons:
     * "What is the expense ratio of HDFC Large Cap Fund?"
     * "What is the ELSS lock-in period?"
     * "How do I download a capital-gains statement?"
   - Input field with placeholder "Ask a question..." and a Send button
   - Answer display area (initially hidden)
   - Disclaimer at bottom: "Facts-only. No investment advice."
   - Link to style.css and app.js

2. frontend/style.css:
   - Clean, modern design with a blue/green color scheme
   - Centered layout with padding
   - Example questions as clickable cards/buttons
   - Answer area with light background
   - Source links styled as clickable badges
   - Responsive design (works on mobile)
   - Disclaimer in small, muted text

3. frontend/app.js:
   - Function to send question to API (POST http://localhost:8000/ask)
   - Function to display answer with source links
   - Function to handle example question clicks
   - Function to handle Enter key in input field
   - Loading state while waiting for response
   - Error handling (display error messages)
   - Auto-scroll to answer after response

Make the UI look professional and trustworthy. Use vanilla JavaScript (no frameworks).
```

### Verification
```bash
# Open frontend/index.html in browser
# Or serve with Python:
python -m http.server 8080 --directory frontend

# Test:
# 1. Welcome message should be visible
# 2. 3 example questions should be clickable
# 3. Clicking an example should send the question and show answer
# 4. Typing a question and pressing Enter should work
# 5. Answer should show source links
# 6. Disclaimer should be visible at bottom
```

---

## Phase 11: Integration Testing

### Objective
Test the full pipeline end-to-end with sample queries.

### Files to Create
```
tests/test_integration.py
tests/sample_qa.json
```

### Cursor Prompt for Phase 11

```
Create integration tests and sample Q&A data:

1. tests/sample_qa.json:
   Create a JSON file with 10 sample Q&A pairs:
   [
     {
       "question": "What is the expense ratio of HDFC Large Cap Fund?",
       "expected_type": "factual",
       "expected_keywords": ["expense", "ratio"]
     },
     {
       "question": "What is the ELSS lock-in period?",
       "expected_type": "factual",
       "expected_keywords": ["lock-in", "3 years"]
     },
     {
       "question": "What is the minimum SIP amount for HDFC Small Cap Fund?",
       "expected_type": "factual",
       "expected_keywords": ["minimum", "SIP"]
     },
     {
       "question": "What is the riskometer level of HDFC Balanced Advantage Fund?",
       "expected_type": "factual",
       "expected_keywords": ["riskometer", "moderate"]
     },
     {
       "question": "What is the benchmark of HDFC Equity Fund?",
       "expected_type": "factual",
       "expected_keywords": ["benchmark", "Nifty"]
     },
     {
       "question": "How do I download a capital-gains statement?",
       "expected_type": "factual",
       "expected_keywords": ["download", "statement"]
     },
     {
       "question": "Should I buy HDFC Small Cap Fund?",
       "expected_type": "advice",
       "expected_keywords": ["advice"]
     },
     {
       "question": "Which fund is best for long-term investment?",
       "expected_type": "advice",
       "expected_keywords": ["advice"]
     },
     {
       "question": "My PAN is ABCDE1234F",
       "expected_type": "pii",
       "expected_keywords": ["personal information"]
     },
     {
       "question": "What is the exit load for HDFC ELSS Tax Saver Fund?",
       "expected_type": "factual",
       "expected_keywords": ["exit load"]
     }
   ]

2. tests/test_integration.py:
   Create pytest integration tests:
   - Test health endpoint returns 200
   - Test ask endpoint with factual question returns answer with sources
   - Test ask endpoint with advice question returns refusal
   - Test ask endpoint with PII returns error
   - Test ask endpoint with empty question returns error
   - Test sources endpoint returns list of URLs
   - Test examples endpoint returns 3 questions
   - Test full pipeline: process query → retrieve → generate → format

Use pytest and requests libraries. Add proper error handling and timeouts.
```

### Verification
```bash
# Run integration tests
pytest tests/test_integration.py -v

# Expected: All tests should pass
```

---

## Phase 12: Documentation

### Objective
Create the README and finalize all documentation.

### Files to Create
```
README.md
sources/source_list.csv
```

### Cursor Prompt for Phase 12

```
Create documentation files:

1. sources/source_list.csv:
   Create a CSV file with columns: scheme_name, source_url, description
   Include all 5 HDFC scheme URLs from the PRD.

2. README.md:
   Create a comprehensive README with:
   - Project title and description
   - Features list
   - Tech stack table
   - Project structure (tree diagram)
   - Setup instructions:
     * Prerequisites (Python 3.10+, Groq API key)
     * Installation steps
     * Environment variable setup
     * Running ingestion
     * Starting the server
     * Opening the UI
   - API documentation (endpoints with examples)
   - Sample Q&A section
   - Known limitations
   - Disclaimer
   - License (MIT)

Make the README professional and easy to follow.
```

### Verification
```bash
# Check all files exist
dir /s /b

# Verify README renders correctly
# Open README.md in a markdown viewer
```

---

## Phase 13: Final Testing & Demo

### Objective
Run final end-to-end tests and prepare demo.

### Files to Create
```
tests/final_test.py
demo_script.py
```

### Cursor Prompt for Phase 13

```
Create final testing and demo scripts:

1. tests/final_test.py:
   Create a comprehensive final test that:
   - Starts with health check
   - Tests all 10 sample queries from sample_qa.json
   - Validates response structure for each query type
   - Measures and reports response latency
   - Generates a test report with pass/fail status
   - Exits with non-zero code if any test fails

2. demo_script.py:
   Create a demo script that:
   - Runs the server in a subprocess
   - Waits for server to be ready
   - Sends 5 representative questions
   - Prints formatted output showing Q&A pairs
   - Measures and displays response times
   - Shuts down the server gracefully

Make both scripts executable and well-documented.
```

### Verification
```bash
# Run final tests
python tests/final_test.py

# Expected: All tests pass, report generated

# Run demo
python demo_script.py

# Expected: 5 Q&A pairs displayed with sources and timestamps
```

---

## Quick Reference: File Checklist

| Phase | File | Status |
|-------|------|--------|
| 0 | `.env` | ☐ |
| 0 | `.gitignore` | ☐ |
| 0 | `requirements.txt` | ☐ |
| 1 | `ingestion/loader.py` | ☐ |
| 2 | `ingestion/chunker.py` | ☐ |
| 3 | `ingestion/embedder.py` | ☐ |
| 4 | `ingestion/ingest.py` | ☐ |
| 5 | `backend/query_processor.py` | ☐ |
| 6 | `backend/retriever.py` | ☐ |
| 7 | `backend/llm.py` | ☐ |
| 8 | `backend/formatter.py` | ☐ |
| 9 | `backend/main.py` | ☐ |
| 9 | `backend/models.py` | ☐ |
| 10 | `frontend/index.html` | ☐ |
| 10 | `frontend/style.css` | ☐ |
| 10 | `frontend/app.js` | ☐ |
| 11 | `tests/test_integration.py` | ☐ |
| 11 | `tests/sample_qa.json` | ☐ |
| 12 | `README.md` | ☐ |
| 12 | `sources/source_list.csv` | ☐ |
| 13 | `tests/final_test.py` | ☐ |
| 13 | `demo_script.py` | ☐ |

---

## Quick Reference: Commands

```bash
# Setup
pip install -r requirements.txt

# Ingestion (run once)
python ingestion/ingest.py

# Start server
uvicorn backend.main:app --reload

# Run tests
pytest tests/ -v

# Run demo
python demo_script.py

# Serve frontend (optional)
python -m http.server 8080 --directory frontend
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `GROQ_API_KEY not found` | Add `GROQ_API_KEY=your_key` to `.env` |
| `ChromaDB is empty` | Run `python ingestion/ingest.py` |
| `Port 8000 in use` | Use `uvicorn backend.main:app --port 8001` |
| `CORS errors` | Check CORS middleware in `backend/main.py` |
| `NLTK data missing` | Run `python -c "import nltk; nltk.download('punkt')"` |
| `sentence-transformers slow first run` | Model downloads on first use; subsequent runs are fast |

---

*End of Document*
