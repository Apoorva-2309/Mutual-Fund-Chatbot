# MF FAQ Assistant — Facts-Only RAG Chatbot

A **Retrieval-Augmented Generation (RAG)** chatbot that answers factual questions about HDFC mutual fund schemes using only official public sources. Every answer includes a source citation. No investment advice.

---

## Features

- **Facts-only Q&A** — Answers factual queries about expense ratios, exit loads, minimum SIP, lock-in periods, riskometer, benchmarks, and more
- **Source citations** — Every answer includes at least one source link for verifiability
- **Advice refusal** — Politely declines investment advice and redirects to AMFI investor education
- **PII protection** — Detects and rejects personally identifiable information (PAN, Aadhaar, phone, email)
- **No performance claims** — Does not compute or compare returns; links to official factsheets
- **Tiny web UI** — Clean, responsive interface with example questions and disclaimer
- **Local embedding** — Uses `sentence-transformers/all-MiniLM-L6-v2` (no API key needed)
- **Persistent vector DB** — ChromaDB stores embeddings on disk; ingestion runs once

---

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Embedding Model** | `sentence-transformers/all-MiniLM-L6-v2` | Local, no API key, 384-dim vectors |
| **Vector DB** | ChromaDB | Persisted to disk; ingestion runs once |
| **LLM** | Groq API | `llama-3.3-70b-versatile` (fallback: `mixtral-8x7b-32768`) |
| **Backend** | FastAPI | REST API with CORS support |
| **Frontend** | HTML/CSS/JS | Vanilla JavaScript, no frameworks |
| **Data Loading** | `requests` + `BeautifulSoup4` | HTML parsing from Groww |
| **Chunking** | NLTK | Section-aware chunking with overlap |

---

## Project Structure

```
RAG-Chatbot-Grow/
├── PRD.md                          # Product requirements
├── architecture.md                 # System architecture
├── implementation.md               # Phase-wise implementation guide
├── README.md                       # This file
├── .env                            # Environment variables (GROQ_API_KEY)
├── .gitignore                      # Git ignore rules
├── requirements.txt                # Python dependencies
│
├── ingestion/                      # Data ingestion pipeline
│   ├── __init__.py
│   ├── loader.py                   # Load HTML from Groww
│   ├── chunker.py                  # Chunk text with metadata
│   ├── embedder.py                 # Embed chunks → ChromaDB
│   └── ingest.py                   # Main ingestion script
│
├── backend/                        # API and query pipeline
│   ├── __init__.py
│   ├── main.py                     # FastAPI application
│   ├── models.py                   # Pydantic models
│   ├── query_processor.py          # Normalize, PII detection, advice detection
│   ├── retriever.py                # ChromaDB similarity search
│   ├── llm.py                      # Groq API integration
│   └── formatter.py                # Response formatting
│
├── frontend/                       # Web UI
│   ├── index.html                  # Main HTML
│   ├── style.css                   # Styles
│   └── app.js                      # Frontend logic
│
├── data/                           # Data storage
│   ├── raw_sections.json           # Raw loaded sections
│   ├── chunks.json                 # Chunked data with metadata
│   ├── chunks.txt                  # Human-readable chunks
│   ├── chunks_with_embeddings.txt  # Chunks + embedding vectors
│   └── chroma_db/                  # ChromaDB persistent storage
│
├── sources/                        # Source data
│   └── source_list.csv             # List of source URLs
│
└── tests/                          # Tests
    ├── test_integration.py         # Integration tests
    └── sample_qa.json              # Sample Q&A pairs
```

---

## Setup Instructions

### Prerequisites

- **Python 3.10+**
- **Groq API key** — Get one free at [console.groq.com](https://console.groq.com)

### Installation

1. **Clone or download the project**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the project root:
   ```
   GROQ_API_KEY=gsk_your_actual_key_here
   ```

4. **Run ingestion (one-time):**
   ```bash
   python ingestion/ingest.py
   ```
   This will:
   - Fetch 5 HDFC scheme pages from Groww
   - Chunk the data into ~31 chunks
   - Embed chunks using `all-MiniLM-L6-v2`
   - Store in ChromaDB at `data/chroma_db/`

5. **Start the API server:**
   ```bash
   uvicorn backend.main:app --reload
   ```
   Server runs at `http://localhost:8000`

6. **Open the UI:**
   Open `frontend/index.html` in your browser, or serve it:
   ```bash
   python -m http.server 8080 --directory frontend
   ```
   Then visit `http://localhost:8080`

---

## API Documentation

### POST /ask

Answer a question using RAG.

**Request:**
```json
{
  "question": "What is the expense ratio of HDFC Large Cap Fund?"
}
```

**Response (success):**
```json
{
  "answer": "The expense ratio of HDFC Large Cap Fund Direct Growth is 1.03%...",
  "sources": ["https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"],
  "is_advice": false,
  "timestamp": "2026-10-01T12:00:00Z"
}
```

**Response (advice refusal):**
```json
{
  "answer": "I can only provide factual information, not investment advice...",
  "sources": ["https://www.amfiindia.com/investor-education"],
  "is_advice": true,
  "timestamp": "2026-10-01T12:00:00Z"
}
```

**Response (PII detected):**
```json
{
  "error": "Please do not share personal information (PAN, Aadhaar, phone, email).",
  "code": "PII_DETECTED"
}
```

### GET /health

Health check.

**Response:**
```json
{
  "status": "ok",
  "chunks_loaded": 31,
  "embedding_model": "all-MiniLM-L6-v2",
  "llm_model": "llama-3.3-70b-versatile"
}
```

### GET /sources

List all source URLs.

**Response:**
```json
{
  "sources": [
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    ...
  ]
}
```

### GET /examples

Get example questions.

**Response:**
```json
{
  "examples": [
    "What is the expense ratio of HDFC Large Cap Fund?",
    "What is the ELSS lock-in period?",
    "How do I download a capital-gains statement?"
  ]
}
```

---

## Sample Q&A

| Question | Answer | Source |
|----------|--------|--------|
| What is the expense ratio of HDFC Large Cap Fund? | 1.03% (as of Oct 2026) | [Groww](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) |
| What is the ELSS lock-in period? | 3 years | [Groww](https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth) |
| What is the minimum SIP for HDFC Small Cap Fund? | ₹100 | [Groww](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth) |
| Should I buy HDFC Small Cap Fund? | *Advice refusal* — see AMFI investor education | [AMFI](https://www.amfiindia.com/investor-education) |

---

## Known Limitations

- **Single AMC** — Only covers HDFC Mutual Fund schemes (5 schemes)
- **Static data** — Data is ingested once; no real-time updates
- **LLM dependency** — Requires Groq API key for answer generation
- **No conversation memory** — Each query is independent
- **Web-only** — No mobile app
- **English only** — No multi-language support

---

## Disclaimer

> **Facts-only. No investment advice.**

This assistant provides factual information from official sources only. It does not recommend any scheme or provide investment advice. Please consult a SEBI-registered investment advisor before making investment decisions.

---

## License

MIT License — Free to use, modify, and distribute.

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

## Quick Reference

```bash
# Setup
pip install -r requirements.txt

# Ingestion (run once)
python ingestion/ingest.py

# Start server
uvicorn backend.main:app --reload

# Run tests
pytest tests/ -v

# Serve frontend
python -m http.server 8080 --directory frontend
```
