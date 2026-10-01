# Architecture Document
## Mutual Fund FAQ Assistant — Facts-Only RAG Chatbot

| Field | Detail |
|---|---|
| **Document Name** | MF FAQ Assistant — Architecture |
| **Version** | 1.0 |
| **Date** | 2026-10-01 |
| **Status** | Draft |
| **Parent Doc** | [PRD.md](./PRD.md) |

---

## 1. System Overview

The MF FAQ Assistant is a **Retrieval-Augmented Generation (RAG)** system that answers factual mutual fund questions using only official public sources. It follows a two-phase architecture:

1. **Ingestion Pipeline** — runs once (or on-demand) to build the knowledge base
2. **Query Pipeline** — runs per user question to generate cited, facts-only answers

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SYSTEM ARCHITECTURE                          │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   INGESTION PIPELINE (Offline)                 │  │
│  │                                                               │  │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────────┐  │  │
│  │  │  Load   │──▶│  Chunk  │──▶│  Embed  │──▶│   Store in   │  │  │
│  │  │  Pages  │   │  Text   │   │ (MiniLM)│   │   ChromaDB   │  │  │
│  │  └─────────┘   └─────────┘   └─────────┘   └──────────────┘  │  │
│  │       │              │              │               │          │  │
│  │       ▼              ▼              ▼               ▼          │  │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────────┐  │  │
│  │  │Groww    │   │Section- │   │384-dim  │   │  Persistent  │  │  │
│  │  │HTML/PDF │   │aware    │   │vectors  │   │  Vector DB   │  │  │
│  │  │Sources  │   │chunks   │   │         │   │  (disk)      │  │  │
│  │  └─────────┘   └─────────┘   └─────────┘   └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    QUERY PIPELINE (Online)                    │  │
│  │                                                               │  │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────────┐  │  │
│  │  │  User   │──▶│  Embed  │──▶│Retrieve │──▶│  LLM Generate│  │  │
│  │  │ Question│   │ (MiniLM)│   │Top-K    │   │  (Groq API) │  │  │
│  │  └─────────┘   └─────────┘   └─────────┘   └──────────────┘  │  │
│  │       │              │              │               │          │  │
│  │       ▼              ▼              ▼               ▼          │  │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────────┐  │  │
│  │  │  Query  │   │384-dim  │   │Cosine   │   │  Answer +    │  │  │
│  │  │  Text   │   │vector   │   │similarity│   │  Citation    │  │  │
│  │  └─────────┘   └─────────┘   └─────────┘   └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                        UI LAYER                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  Welcome Line  │  3 Example Questions  │  Disclaimer   │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         UI LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Welcome     │  │  Example     │  │  Disclaimer Banner       │  │
│  │  Message     │  │  Questions   │  │  "Facts-only. No advice" │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│                    ┌─────────────────┐                              │
│                    │  Chat Interface │                              │
│                    │  (HTML/JS)      │                              │
│                    └────────┬────────┘                              │
└─────────────────────────────┼───────────────────────────────────────┘
                              │ HTTP POST /ask
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                            │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  POST /ask                                                     │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │ │
│  │  │  Input       │  │  Advice      │  │  Response            │ │ │
│  │  │  Validation  │─▶│  Detection   │─▶│  Formatter           │ │ │
│  │  │  (No PII)    │  │  (Keyword +  │  │  (Citation +         │ │ │
│  │  │              │  │   LLM check) │  │   Timestamp)         │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                      │
│                              ▼                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  GET /health  │  GET /sources  │  GET /examples               │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RAG ORCHESTRATION LAYER                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Query Pipeline                                                │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────┐ │ │
│  │  │  Query     │─▶│  Embed     │─▶│  Retrieve  │─▶│  LLM    │ │ │
│  │  │  Processor │  │  Question  │  │  Top-K     │  │  Call   │ │ │
│  │  └────────────┘  └────────────┘  └────────────┘  └─────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌────────────────┐ ┌──────────────────────────┐
│  EMBEDDING       │ │  VECTOR DB     │ │  LLM SERVICE             │
│  SERVICE         │ │  (ChromaDB)    │ │  (Groq API)             │
│                  │ │                │ │                          │
│  all-MiniLM-     │ │  Persistent    │ │  llama-3.3-70b-          │
│  L6-v2           │ │  to disk       │ │  versatile               │
│  (384-dim)       │ │                │ │  (or mixtral-8x7b)       │
│  Local, no API   │ │  Cosine        │ │                          │
│  key             │ │  similarity    │ │  API key in .env         │
└──────────────────┘ └────────────────┘ └──────────────────────────┘
```

### 2.2 Component Descriptions

| Component | Responsibility | Technology | Location |
|-----------|---------------|------------|----------|
| **UI Layer** | Render welcome, examples, disclaimer; capture user input; display answers | HTML/CSS/JS or Streamlit | `frontend/` |
| **API Layer** | Validate input (no PII), detect advice queries, format responses | FastAPI | `backend/main.py` |
| **Query Processor** | Clean and normalize user questions | Python | `backend/query_processor.py` |
| **Embedding Service** | Convert text to 384-dim vectors | `sentence-transformers/all-MiniLM-L6-v2` | `backend/embedder.py` |
| **Vector DB** | Store and retrieve chunks via cosine similarity | ChromaDB (persisted) | `data/chroma_db/` |
| **LLM Service** | Generate answers from retrieved context | Groq API | `backend/llm.py` |
| **Ingestion Pipeline** | Load, chunk, embed, store source pages | Python scripts | `ingestion/` |

---

## 3. Data Flow

### 3.1 Ingestion Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INGESTION DATA FLOW                              │
│                                                                     │
│  Step 1: LOAD                                                       │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐   │
│  │  Groww      │     │  AMC/SEBI/  │     │  SID/KIM PDFs       │   │
│  │  HTML Pages │     │  AMFI Pages │     │  (if needed)        │   │
│  └──────┬──────┘     └──────┬──────┘     └──────────┬──────────┘   │
│         │                   │                       │               │
│         ▼                   ▼                       ▼               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  requests + BeautifulSoup (HTML)  │  pypdf (PDF)            │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                            │                                        │
│  Step 2: CHUNK            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Section-aware chunking strategy                            │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  For each document:                                  │   │   │
│  │  │  1. Identify sections (expense ratio, exit load,     │   │   │
│  │  │     riskometer, benchmark, SIP, lock-in, etc.)       │   │   │
│  │  │  2. Split into chunks of ~300-500 tokens             │   │   │
│  │  │  3. Add overlap of ~50-80 tokens between chunks       │   │   │
│  │  │  4. Attach metadata to each chunk                    │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                            │                                        │
│  Step 3: EMBED            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  sentence-transformers/all-MiniLM-L6-v2                     │   │
│  │  Input: chunk text → Output: 384-dim vector                 │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                            │                                        │
│  Step 4: STORE           ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ChromaDB (persisted to disk)                               │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  Collection: "mf_faq"                                 │   │   │
│  │  │  Each record:                                         │   │   │
│  │  │    id: chunk_id (UUID)                                │   │   │
│  │  │    embedding: [384-dim vector]                        │   │   │
│  │  │    document: chunk text                               │   │   │
│  │  │    metadata: {scheme_name, source_url,                │   │   │
│  │  │               section_title, chunk_id,                │   │   │
│  │  │               last_updated}                           │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Output: chunks.txt (readable backup of all chunks + metadata)      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Query Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      QUERY DATA FLOW                                 │
│                                                                     │
│  Step 1: RECEIVE                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  User types question in UI                                  │   │
│  │  POST /ask  { "question": "What is the expense ratio..." }  │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                            │                                        │
│  Step 2: VALIDATE           ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Input Validation                                           │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  1. Check for PII (PAN, Aadhaar, phone, email, etc.)  │   │   │
│  │  │  2. If PII detected → reject with error message       │   │   │
│  │  │  3. Check question length (min 5 chars)               │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                            │                                        │
│  Step 3: ADVICE DETECTION   ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Advice Query Detection                                     │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  Keyword-based pre-filter:                           │   │   │
│  │  │    "should I", "buy", "sell", "best fund",           │   │   │
│  │  │    "recommend", "portfolio", "invest in"             │   │   │
│  │  │                                                      │   │   │
│  │  │  If advice-type → return refusal + educational link  │   │   │
│  │  │  (skip retrieval + LLM)                              │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                            │                                        │
│  Step 4: EMBED QUESTION     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  sentence-transformers/all-MiniLM-L6-v2                     │   │
│  │  Input: user question → Output: 384-dim vector              │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                            │                                        │
│  Step 5: RETRIEVE           ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ChromaDB Similarity Search                                 │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  Query: 384-dim question vector                       │   │   │
│  │  │  Search: cosine similarity over all chunk vectors     │   │   │
│  │  │  Return: Top-K chunks (K=3-5) with metadata           │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                            │                                        │
│  Step 6: GENERATE           ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Groq LLM API Call                                          │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  System Prompt: facts-only rules                      │   │   │
│  │  │  Context: top-K retrieved chunks                      │   │   │
│  │  │  Question: user query                                 │   │   │
│  │  │  Output: answer + citation                            │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                            │                                        │
│  Step 7: FORMAT RESPONSE    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Response Formatter                                         │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  1. Extract answer text from LLM response             │   │   │
│  │  │  2. Extract source URLs from chunk metadata           │   │   │
│  │  │  3. Append "Last updated from sources: [date]"       │   │   │
│  │  │  4. Return JSON: {answer, sources, timestamp}        │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                            │                                        │
│                            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  UI displays answer + citation links + disclaimer           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Component Design

### 4.1 Ingestion Pipeline

#### 4.1.1 Data Loader

```
┌─────────────────────────────────────────────────────────────────────┐
│  DATA LOADER                                                        │
│                                                                     │
│  Input: List of source URLs (Groww, AMC, SEBI, AMFI)               │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  HTML Sources (Groww)                                       │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  1. requests.get(url)                                 │   │   │
│  │  │  2. BeautifulSoup(html, 'html.parser')                │   │   │
│  │  │  3. Extract relevant sections:                        │   │   │
│  │  │     - Scheme overview                                 │   │   │
│  │  │     - Expense ratio table                            │   │   │
│  │  │     - Exit load structure                             │   │   │
│  │  │     - Riskometer                                     │   │   │
│  │  │     - Benchmark                                       │   │   │
│  │  │     - Minimum SIP                                     │   │   │
│  │  │     - Lock-in period                                 │   │   │
│  │  │  4. Clean text (remove nav, footer, ads)             │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  PDF Sources (SID/KIM — if needed)                          │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  1. pypdf.PdfReader(pdf_path)                         │   │   │
│  │  │  2. Extract text page by page                         │   │   │
│  │  │  3. Identify sections by headers                      │   │   │
│  │  │  4. Clean and normalize text                          │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Output: List of {scheme_name, source_url, section_title, text}    │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.1.2 Chunker

```
┌─────────────────────────────────────────────────────────────────────┐
│  CHUNKER                                                            │
│                                                                     │
│  Strategy: Section-Aware Sliding Window                             │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Parameters:                                                │   │
│  │  - Chunk size: 400 tokens (~300 characters)                 │   │
│  │  - Overlap: 60 tokens (~45 characters)                      │   │
│  │  - Tokenizer: NLTK word_tokenize (approximate)             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Algorithm:                                                 │   │
│  │  For each document:                                         │   │
│  │    1. Split into sentences                                  │   │
│  │    2. Group sentences into chunks of ≤400 tokens            │   │
│  │    3. If a section boundary is detected (e.g., "Expense    │   │
│  │       Ratio", "Exit Load"), start a new chunk               │   │
│  │    4. Add overlap: last 60 tokens of previous chunk         │   │
│  │       become first 60 tokens of next chunk                  │   │
│  │    5. Attach metadata to each chunk                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Metadata per chunk:                                        │   │
│  │  {                                                           │   │
│  │    "chunk_id": "uuid4",                                     │   │
│  │    "scheme_name": "HDFC Large Cap Fund",                    │   │
│  │    "source_url": "https://groww.in/...",                    │   │
│  │    "section_title": "Expense Ratio",                        │   │
│  │    "chunk_index": 0,                                        │   │
│  │    "last_updated": "2026-10-01"                            │   │
│  │  }                                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Output: chunks.txt (human-readable) + chunks.json (structured)    │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.1.3 Embedder

```
┌─────────────────────────────────────────────────────────────────────┐
│  EMBEDDER                                                           │
│                                                                     │
│  Model: sentence-transformers/all-MiniLM-L6-v2                      │
│  Dimensions: 384                                                    │
│  Runtime: Local (no API key)                                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Process:                                                   │   │
│  │  1. Load model once at startup                              │   │
│  │  2. For each chunk:                                         │   │
│  │     embedding = model.encode(chunk.text)                    │   │
│  │  3. Store embedding + metadata in ChromaDB                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Performance: ~100 chunks/second on CPU                            │
│  Total chunks (est.): 5 schemes × ~20 chunks = ~100 chunks         │
│  Ingestion time: ~2 seconds                                        │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.1.4 Vector Store

```
┌─────────────────────────────────────────────────────────────────────┐
│  VECTOR STORE (ChromaDB)                                            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Configuration:                                             │   │
│  │  - Client: PersistentClient(path="data/chroma_db")          │   │
│  │  - Collection: "mf_faq"                                     │   │
│  │  - Distance metric: cosine                                  │   │
│  │  - Embedding function: all-MiniLM-L6-v2                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Schema:                                                    │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  id: TEXT (UUID, primary key)                         │   │   │
│  │  │  embedding: LIST[FLOAT] (384-dim)                     │   │   │
│  │  │  document: TEXT (chunk text)                          │   │   │
│  │  │  metadata: {                                          │   │   │
│  │  │    scheme_name: TEXT,                                 │   │   │
│  │  │    source_url: TEXT,                                  │   │   │
│  │  │    section_title: TEXT,                               │   │   │
│  │  │    chunk_index: INT,                                  │   │   │
│  │  │    last_updated: TEXT                                 │   │   │
│  │  │  }                                                    │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Persistence: Data saved to disk; ingestion runs once              │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Query Pipeline

#### 4.2.1 Query Processor

```
┌─────────────────────────────────────────────────────────────────────┐
│  QUERY PROCESSOR                                                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 1: Normalize                                          │   │
│  │  - Lowercase                                                │   │
│  │  - Remove extra whitespace                                  │   │
│  │  - Remove special characters (keep alphanumeric + spaces)   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 2: PII Detection                                      │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  Patterns to detect:                                 │   │   │
│  │  │  - PAN: [A-Z]{5}[0-9]{4}[A-Z]                         │   │   │
│  │  │  - Aadhaar: [0-9]{12}                                 │   │   │
│  │  │  - Phone: [0-9]{10} or +91[0-9]{10}                   │   │   │
│  │  │  - Email: [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+            │   │   │
│  │  │  - Account number: [0-9]{9,}                          │   │   │
│  │  │                                                      │   │   │
│  │  │  If PII detected → reject with message:               │   │   │
│  │  │  "Please do not share personal information..."       │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 3: Advice Query Detection                             │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  Keyword-based pre-filter:                           │   │   │
│  │  │  advice_keywords = [                                 │   │   │
│  │  │    "should i", "buy", "sell", "best fund",           │   │   │
│  │  │    "recommend", "portfolio", "invest in",            │   │   │
│  │  │    "which fund", "good fund", "top fund",            │   │   │
│  │  │    "worth", "profit", "guaranteed"                   │   │   │
│  │  │  ]                                                   │   │   │
│  │  │                                                      │   │   │
│  │  │  If any keyword found → mark as advice query          │   │   │
│  │  │  (LLM also has refusal prompt as backup)             │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Output: Cleaned query + is_advice flag                             │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2.2 Retriever

```
┌─────────────────────────────────────────────────────────────────────┐
│  RETRIEVER                                                          │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Process:                                                   │   │
│  │  1. Embed user question using all-MiniLM-L6-v2              │   │
│  │  2. Query ChromaDB with cosine similarity                   │   │
│  │  3. Return top-K chunks (K=5)                              │   │
│  │  4. Deduplicate by source_url (keep best-scoring chunk)     │   │
│  │  5. Return chunks with metadata                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Retrieval Parameters:                                      │   │
│  │  - Top-K: 5                                                 │   │
│  │  - Similarity threshold: 0.3 (filter low-relevance chunks)  │   │
│  │  - Deduplication: by source_url                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Output: List of {text, metadata, score} for top-K chunks          │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2.3 LLM Generator

```
┌─────────────────────────────────────────────────────────────────────┐
│  LLM GENERATOR (Groq API)                                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Model Options:                                             │   │
│  │  - Primary: llama-3.3-70b-versatile                         │   │
│  │  - Fallback: mixtral-8x7b-32768                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  API Configuration:                                         │   │
│  │  - API key: stored in .env (GROQ_API_KEY)                   │   │
│  │  - Temperature: 0.1 (low for factual consistency)           │   │
│  │  - Max tokens: 200 (enough for ≤3 sentence answer)         │   │
│  │  - Timeout: 10 seconds                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Prompt Template:                                           │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  SYSTEM:                                              │   │   │
│  │  │  You are a facts-only mutual fund FAQ assistant.     │   │   │
│  │  │  Answer using ONLY the provided context.              │   │   │
│  │  │  Rules:                                               │   │   │
│  │  │  1. Answer in ≤3 sentences.                           │   │   │
│  │  │  2. Include ≥1 source citation from context.          │   │   │
│  │  │  3. If asked for advice, decline politely and         │   │   │
│  │  │     provide: https://www.amfiindia.com/investor-     │   │   │
│  │  │     education                                        │   │   │
│  │  │  4. Do NOT compute or compare returns.                │   │   │
│  │  │  5. End with: "Last updated from sources: [date]"    │   │   │
│  │  │                                                       │   │   │
│  │  │  USER:                                                │   │   │
│  │  │  Context:                                             │   │   │
│  │  │  {retrieved_chunks}                                   │   │   │
│  │  │                                                       │   │   │
│  │  │  Question: {user_question}                            │   │   │
│  │  │                                                       │   │   │
│  │  │  Answer:                                              │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Output: Generated answer text                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 API Layer

#### 4.3.1 Endpoints

```
┌─────────────────────────────────────────────────────────────────────┐
│  API ENDPOINTS (FastAPI)                                            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  POST /ask                                                  │   │
│  │  ─────────────────────────────────────────────────────────  │   │
│  │  Request:                                                   │   │
│  │  {                                                          │   │
│  │    "question": "What is the expense ratio of HDFC Large    │   │
│  │                Cap Fund?"                                   │   │
│  │  }                                                          │   │
│  │                                                             │   │
│  │  Response (success):                                        │   │
│  │  {                                                          │   │
│  │    "answer": "The expense ratio of HDFC Large Cap Fund     │   │
│  │               Direct Growth is 0.75% (as of Oct 2026).     │   │
│  │               Last updated from sources: 2026-10-01",        │   │
│  │    "sources": [                                            │   │
│  │      "https://groww.in/mutual-funds/hdfc-large-cap-..."    │   │
│  │    ],                                                      │   │
│  │    "is_advice": false,                                     │   │
│  │    "timestamp": "2026-10-01T12:00:00Z"                     │   │
│  │  }                                                          │   │
│  │                                                             │   │
│  │  Response (advice refusal):                                 │   │
│  │  {                                                          │   │
│  │    "answer": "I can only provide factual information,      │   │
│  │               not investment advice. Please refer to       │   │
│  │               AMFI's investor education resources.",       │   │
│  │    "sources": [                                            │   │
│  │      "https://www.amfiindia.com/investor-education"       │   │
│  │    ],                                                      │   │
│  │    "is_advice": true,                                      │   │
│  │    "timestamp": "2026-10-01T12:00:00Z"                     │   │
│  │  }                                                          │   │
│  │                                                             │   │
│  │  Response (PII detected):                                   │   │
│  │  {                                                          │   │
│  │    "error": "Please do not share personal information...",  │   │
│  │    "code": "PII_DETECTED"                                   │   │
│  │  }                                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  GET /health                                                │   │
│  │  ─────────────────────────────────────────────────────────  │   │
│  │  Response: {"status": "ok", "chunks_loaded": 100}          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  GET /sources                                               │   │
│  │  ─────────────────────────────────────────────────────────  │   │
│  │  Response: List of all source URLs in the corpus            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  GET /examples                                              │   │
│  │  ─────────────────────────────────────────────────────────  │   │
│  │  Response: 3 example questions for the UI                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.4 UI Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│  UI LAYER (HTML/CSS/JS or Streamlit)                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │  Welcome: "Hi! I can answer factual questions about   │  │   │
│  │  │  HDFC mutual fund schemes. Facts-only. No advice."   │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │                                                             │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │  Example Questions (clickable):                      │  │   │
│  │  │  • "What is the expense ratio of HDFC Large Cap Fund?"│  │   │
│  │  │  • "What is the ELSS lock-in period?"                 │  │   │
│  │  │  • "How do I download a capital-gains statement?"    │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │                                                             │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │  [Input field]                              [Send]   │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │                                                             │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │  Answer:                                              │  │   │
│  │  │  The expense ratio of HDFC Large Cap Fund Direct      │  │   │
│  │  │  Growth is 0.75% (as of Oct 2026).                    │  │   │
│  │  │  Last updated from sources: 2026-10-01               │  │   │
│  │  │                                                       │  │   │
│  │  │  Sources:                                             │  │   │
│  │  │  [1] https://groww.in/mutual-funds/hdfc-large-cap... │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │                                                             │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │  Disclaimer: "Facts-only. No investment advice."      │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Data Model

### 5.1 Chunk Schema

```json
{
  "chunk_id": "uuid4-string",
  "scheme_name": "HDFC Large Cap Fund",
  "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
  "section_title": "Expense Ratio",
  "chunk_index": 0,
  "text": "The expense ratio of HDFC Large Cap Fund Direct Growth is 0.75%...",
  "last_updated": "2026-10-01"
}
```

### 5.2 Response Schema

```json
{
  "answer": "The expense ratio of HDFC Large Cap Fund Direct Growth is 0.75% (as of Oct 2026). Last updated from sources: 2026-10-01",
  "sources": [
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
  ],
  "is_advice": false,
  "timestamp": "2026-10-01T12:00:00Z"
}
```

### 5.3 Refusal Response Schema

```json
{
  "answer": "I can only provide factual information, not investment advice. Please refer to AMFI's investor education resources.",
  "sources": [
    "https://www.amfiindia.com/investor-education"
  ],
  "is_advice": true,
  "timestamp": "2026-10-01T12:00:00Z"
}
```

---

## 6. Deployment Architecture

### 6.1 Local Development

```
┌─────────────────────────────────────────────────────────────────────┐
│  LOCAL DEPLOYMENT                                                   │
│                                                                     │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐   │
│  │  Browser    │────▶│  FastAPI    │────▶│  ChromaDB          │   │
│  │  (UI)       │◀────│  Server     │◀────│  (data/chroma_db)  │   │
│  └─────────────┘     └──────┬──────┘     └─────────────────────┘   │
│                             │                                       │
│                             ▼                                       │
│                      ┌─────────────┐                                │
│                      │  Groq API   │                                │
│                      │  (External) │                                │
│                      └─────────────┘                                │
│                                                                     │
│  Commands:                                                          │
│  1. python ingestion/ingest.py    # One-time ingestion              │
│  2. uvicorn backend.main:app      # Start API server                │
│  3. open frontend/index.html      # Open UI in browser              │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 File Structure

```
RAG-Chatbot-Grow/
├── PRD.md                          # Product requirements
├── architecture.md                 # This document
├── README.md                       # Setup instructions
├── .env                            # API keys (not in Git)
├── .gitignore                      # Ignore .env, data/chroma_db, etc.
│
├── ingestion/
│   ├── ingest.py                   # Main ingestion script
│   ├── loader.py                   # HTML/PDF loading
│   ├── chunker.py                  # Chunking logic
│   └── embedder.py                 # Embedding + ChromaDB storage
│
├── backend/
│   ├── main.py                     # FastAPI app
│   ├── query_processor.py          # Query normalization + PII check
│   ├── retriever.py                # ChromaDB retrieval
│   ├── llm.py                      # Groq API integration
│   └── models.py                   # Pydantic models
│
├── frontend/
│   ├── index.html                  # Main UI
│   ├── style.css                   # Styles
│   └── app.js                      # Frontend logic
│
├── data/
│   ├── chroma_db/                  # ChromaDB persistent storage
│   ├── chunks.txt                  # Human-readable chunks
│   └── chunks.json                 # Structured chunks
│
├── sources/
│   └── source_list.csv             # List of source URLs
│
├── tests/
│   ├── test_ingestion.py
│   ├── test_query.py
│   └── sample_qa.json              # Sample Q&A pairs
│
└── requirements.txt                # Python dependencies
```

---

## 7. Error Handling

### 7.1 Error Scenarios

| Scenario | Handling | User Message |
|----------|----------|--------------|
| PII detected in query | Reject before processing | "Please do not share personal information (PAN, Aadhaar, phone, email)." |
| Empty query | Reject | "Please enter a question." |
| Query too short (<5 chars) | Reject | "Please enter a more specific question." |
| No relevant chunks found | Fallback response | "I couldn't find relevant information. Try rephrasing your question." |
| Groq API timeout | Retry once, then fallback | "Service temporarily unavailable. Please try again." |
| Groq API rate limit | Retry with backoff | "Service temporarily unavailable. Please try again in a moment." |
| ChromaDB not found | Prompt ingestion | "Knowledge base not found. Please run ingestion first." |
| Advice query detected | Refusal + educational link | "I can only provide factual information, not investment advice..." |

### 7.2 Retry Logic

```
┌─────────────────────────────────────────────────────────────────────┐
│  RETRY LOGIC (Groq API)                                             │
│                                                                     │
│  Max retries: 2                                                     │
│  Backoff: exponential (1s, 2s)                                      │
│                                                                     │
│  Attempt 1 → Fail → Wait 1s                                         │
│  Attempt 2 → Fail → Wait 2s                                         │
│  Attempt 3 → Fail → Return fallback message                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. Security Considerations

| # | Measure | Implementation |
|---|---------|----------------|
| S1 | API key storage | `.env` file, loaded via `python-dotenv`, never committed to Git |
| S2 | PII filtering | Regex-based detection in query processor; reject before processing |
| S3 | Input validation | Pydantic models for request/response validation |
| S4 | No data persistence | User queries are not stored or logged |
| S5 | HTTPS (if deployed) | Use HTTPS for any deployed instance |
| S6 | Rate limiting | Optional: SlowAPI for rate limiting on API endpoints |

---

## 9. Performance Optimization

| # | Optimization | Impact |
|---|--------------|--------|
| P1 | Load embedding model once at startup | Avoids ~2s model load per query |
| P2 | Persist ChromaDB to disk | Ingestion runs once, not per restart |
| P3 | Limit top-K to 5 chunks | Reduces LLM context size and latency |
| P4 | Low temperature (0.1) | Faster, more deterministic LLM responses |
| P5 | Max tokens 200 | Limits LLM generation time |
| P6 | Deduplicate chunks by source | Reduces redundant context |

**Expected Performance:**
- Ingestion: ~2 seconds (one-time)
- Query latency: <5 seconds (including LLM call)
- UI load: <2 seconds

---

## 10. Testing Strategy

### 10.1 Unit Tests

| Component | Test Cases |
|-----------|------------|
| Loader | Test HTML parsing, PDF extraction |
| Chunker | Test chunk size, overlap, metadata |
| Embedder | Test vector dimensions, model loading |
| Query Processor | Test PII detection, advice detection |
| Retriever | Test similarity search, top-K results |
| LLM | Test prompt formatting, response parsing |

### 10.2 Integration Tests

| Flow | Test Cases |
|------|------------|
| Ingestion → Query | Ingest pages, then query and verify answer |
| Advice Refusal | Send advice query, verify refusal message |
| PII Rejection | Send query with PII, verify rejection |

### 10.3 Sample Q&A Tests

| # | Query | Expected Behavior |
|---|-------|-------------------|
| 1 | "What is the expense ratio of HDFC Large Cap Fund?" | Returns expense ratio + citation |
| 2 | "What is the ELSS lock-in period?" | Returns 3-year lock-in + citation |
| 3 | "Should I buy HDFC Small Cap Fund?" | Refuses + educational link |
| 4 | "My PAN is ABCDE1234F" | Rejects with PII message |
| 5 | "How do I download a capital-gains statement?" | Returns steps + citation |

---

## 11. Monitoring & Logging

### 11.1 Logs

```
┌─────────────────────────────────────────────────────────────────────┐
│  LOGGING STRATEGY                                                   │
│                                                                     │
│  Level: INFO (production), DEBUG (development)                     │
│                                                                     │
│  Logged events:                                                     │
│  - Ingestion start/end                                              │
│  - Ingestion stats (chunks created, errors)                        │
│  - Query received (text, is_advice flag)                           │
│  - Retrieval results (top-K scores)                                │
│  - LLM call (model, latency, token count)                          │
│  - Errors (with stack trace)                                       │
│                                                                     │
│  NOT logged:                                                        │
│  - User PII (detected and rejected)                                │
│  - API keys                                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.2 Health Check

```
GET /health

Response:
{
  "status": "ok",
  "chunks_loaded": 100,
  "embedding_model": "all-MiniLM-L6-v2",
  "llm_model": "llama-3.3-70b-versatile",
  "chroma_db_path": "data/chroma_db"
}
```

---

## 12. Future Enhancements

| # | Enhancement | Priority | Description |
|---|-------------|----------|-------------|
| F1 | Multi-AMC support | P2 | Extend corpus to other AMCs (ICICI, SBI, Axis) |
| F2 | Real-time data refresh | P2 | Scheduled re-ingestion of source pages |
| F3 | Conversation memory | P3 | Multi-turn conversations with context |
| F4 | Feedback mechanism | P3 | Thumbs up/down on answers for quality tracking |
| F5 | Multi-language support | P3 | Answer in Hindi and other regional languages |
| F6 | Mobile-responsive UI | P2 | Optimize UI for mobile devices |
| F7 | Caching layer | P3 | Cache frequent queries to reduce latency |
| F8 | Streaming responses | P3 | Stream LLM output token by token |

---

## 13. Dependencies

### 13.1 Python Packages

```
# requirements.txt

# Core
fastapi==0.104.1
uvicorn==0.24.0
python-dotenv==1.0.0
pydantic==2.5.0

# RAG
sentence-transformers==2.2.2
chromadb==0.4.18
langchain==0.0.340  # Optional, if using LangChain

# Data Loading
requests==2.31.0
beautifulsoup4==4.12.2
pypdf==3.17.1

# LLM
groq==0.1.0

# Utilities
nltk==3.8.1
numpy==1.26.2
```

### 13.2 External Services

| Service | Purpose | API Key Required |
|---------|---------|------------------|
| Groq API | LLM generation | Yes (in `.env`) |
| sentence-transformers | Embedding model | No (local) |
| ChromaDB | Vector storage | No (local) |

---

## 14. Glossary

| Term | Definition |
|------|------------|
| **RAG** | Retrieval-Augmented Generation — combining retrieval with LLM generation |
| **Chunk** | A small piece of text from a source document, used for retrieval |
| **Embedding** | A numerical vector representation of text |
| **Vector DB** | A database optimized for storing and searching vectors |
| **Cosine Similarity** | A measure of similarity between two vectors (1 = identical) |
| **Top-K** | The K most relevant results from a search |
| **PII** | Personally Identifiable Information |
| **AMC** | Asset Management Company |
| **ELSS** | Equity Linked Savings Scheme (tax-saving MF with 3-year lock-in) |
| **SID** | Scheme Information Document |
| **KIM** | Key Information Memorandum |
| **Riskometer** | SEBI-mandated visual risk indicator for MF schemes |

---

*End of Document*
