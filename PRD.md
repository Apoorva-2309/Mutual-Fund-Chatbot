# Product Requirements Document (PRD)
## Mutual Fund FAQ Assistant — Facts-Only RAG Chatbot

| Field | Detail |
|---|---|
| **Product Name** | MF FAQ Assistant (Facts-Only Q&A) |
| **Document Version** | 1.0 |
| **Date** | 2026-10-01 |
| **Status** | Draft |
| **Author** | — |

---

## 1. Problem Statement

Retail mutual fund investors and support/content teams frequently ask repetitive factual questions about fund schemes — expense ratios, exit loads, minimum SIP amounts, lock-in periods (ELSS), riskometer levels, benchmarks, and how to download statements. Today, answering these requires manually navigating multiple official sources (AMC websites, SEBI, AMFI), which is slow and error-prone.

There is no lightweight, facts-only assistant that can answer these questions instantly with verifiable citations, while explicitly refusing to give investment advice.

---

## 2. Goals & Objectives

### Goals
- Build a **working prototype** RAG chatbot that answers factual mutual fund questions using **only official public sources**.
- Every answer includes **at least one source link** for verifiability.
- The assistant **refuses opinionated/portfolio advice** (e.g., "Should I buy/sell?") with a polite, facts-only message and an educational link.

### Objectives
| # | Objective | Success Criteria |
|---|-----------|-----------------|
| O1 | Answer factual queries accurately | ≥90% correctness on a 10-question sample set |
| O2 | Cite sources in every answer | 100% of answers include ≥1 citation link |
| O3 | Refuse non-factual questions gracefully | 100% of advice-type queries get a polite refusal + educational link |
| O4 | Keep answers concise | Answers ≤3 sentences |
| O5 | Run fully locally (except LLM API) | Embedding model + ChromaDB run offline; only Groq API calls external |

---

## 3. Target Users

| User Type | Description | Primary Need |
|-----------|-------------|--------------|
| **Retail Investors** | Individuals comparing mutual fund schemes | Quick, trustworthy facts about fees, risks, lock-ins, statements |
| **Support / Content Teams** | AMC or fintech support staff answering repetitive MF questions | Fast, consistent, citable answers to common queries |

---

## 4. Scope

### 4.1 In Scope
- **Corpus**: One AMC (HDFC Mutual Fund) with **5 schemes**:
  1. HDFC Large Cap Fund — Direct Growth
  2. HDFC Equity Fund (Flexi Cap) — Direct Growth
  3. HDFC ELSS Tax Saver Fund — Direct Plan Growth
  4. HDFC Small Cap Fund — Direct Growth
  5. HDFC Balanced Advantage Fund — Direct Growth
- **Data Sources**: Official public pages from AMC/SEBI/AMFI:
  - Scheme factsheets
  - KIM (Key Information Memorandum) / SID (Scheme Information Document)
  - Scheme FAQ pages
  - Fee/charges pages
  - Riskometer/benchmark notes
  - Statement/tax-document download guides
- **Query Types**:
  - Expense ratio
  - Exit load
  - Minimum SIP
  - ELSS lock-in period
  - Riskometer level
  - Benchmark
  - How to download capital-gains statement
- **UI**: Tiny web UI with welcome line, 3 example questions, and a "Facts-only. No investment advice." disclaimer.

### 4.2 Out of Scope
- Investment advice or portfolio recommendations
- Performance/return calculations or comparisons
- Real-time NAV tracking
- User accounts, login, or personal data storage
- Mobile app (web-only prototype)
- Multi-AMC coverage (future phase)

---

## 5. RAG Architecture

### 5.1 High-Level Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                     INGESTION PIPELINE                       │
│                                                             │
│  Public Pages → Load → Chunk → Embed → Store in ChromaDB   │
│  (HTML/PDF)    (text)  (strategy) (MiniLM)  (persisted)    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      QUERY PIPELINE                          │
│                                                             │
│  User Question → Embed → Retrieve Top-K Chunks → LLM → Answer│
│                 (MiniLM)  (ChromaDB)         (Groq)          │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Ingestion Stage

| Step | Description | Details |
|------|-------------|---------|
| **Load** | Fetch and parse public pages | HTML from Groww scheme pages; PDFs from AMC/SEBI/AMFI if needed |
| **Chunk** | Split documents into chunks | Strategy determined by AI agent after data inspection (see §5.3) |
| **Embed** | Convert chunks to vectors | `sentence-transformers/all-MiniLM-L6-v2` (384-dim, local, no API key) |
| **Store** | Persist vectors + metadata | ChromaDB, persisted to disk (ingestion runs once, not on every restart) |

### 5.3 Chunking Strategy (To Be Proposed by AI Agent)

The AI agent (Cursor / OpenCode / Claude Code) must:
1. **Inspect the data** before writing any code.
2. **Propose a chunking strategy** and explain why it suits this data.
3. **Specify**:
   - Chunk size (tokens/characters)
   - Overlap size
   - Metadata each chunk retains (e.g., `scheme_name`, `source_url`, `section_title`, `chunk_id`, `last_updated`)
4. **Save all chunks to a readable `.txt` file** for inspection.

**Preliminary recommendation** (to be validated by agent):
- **Chunk size**: 300–500 tokens
- **Overlap**: 50–80 tokens
- **Metadata**: `scheme_name`, `source_url`, `section_title`, `chunk_id`
- **Rationale**: MF factsheets have distinct sections (expense ratio table, exit load table, riskometer, benchmark). Section-aware chunking preserves context and improves retrieval precision.

### 5.4 Query Stage

| Step | Description | Details |
|------|-------------|---------|
| **Embed Question** | Convert user query to vector | Same `all-MiniLM-L6-v2` model |
| **Retrieve** | Fetch top-K most similar chunks | ChromaDB similarity search (cosine); K=3–5 |
| **LLM Generation** | Generate answer from retrieved context | Groq API (e.g., `llama-3.3-70b-versatile` or `mixtral-8x7b-32768`) |
| **Post-process** | Append citation + "Last updated from sources" | Enforced in prompt template |

### 5.5 Prompt Template (LLM)

```
You are a facts-only mutual fund FAQ assistant. Answer the user's question
using ONLY the provided context. Rules:
1. Answer in ≤3 sentences.
2. Include at least one source citation link from the context.
3. If the question asks for investment advice (buy/sell/portfolio), politely
   decline and provide this educational link: [AMFI/SEBI investor education].
4. Do NOT compute or compare returns.
5. End with: "Last updated from sources: [date]"

Context:
{retrieved_chunks}

Question: {user_question}

Answer:
```

---

## 6. Data Sources

### 6.1 Scheme Pages (Groww)

| # | Scheme | URL |
|---|--------|-----|
| 1 | HDFC Large Cap Fund — Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| 2 | HDFC Equity Fund (Flexi Cap) — Direct Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| 3 | HDFC ELSS Tax Saver Fund — Direct Plan Growth | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| 4 | HDFC Small Cap Fund — Direct Growth | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| 5 | HDFC Balanced Advantage Fund — Direct Growth | https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth |

### 6.2 Additional Official Sources (To Be Added)
- HDFC MF official website: https://www.hdfcfund.com
- SEBI: https://www.sebi.gov.in
- AMFI: https://www.amfiindia.com
- Scheme-specific SID/KIM PDFs (from AMC website)

---

## 7. Functional Requirements

### FR-1: Factual Q&A
- **Priority**: P0
- **Description**: The assistant answers factual queries about the 5 schemes (expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark, statement download).
- **Acceptance**: Given a factual query, the assistant returns a ≤3-sentence answer with ≥1 citation link.

### FR-2: Source Citation
- **Priority**: P0
- **Description**: Every answer includes at least one clear citation link to the source page.
- **Acceptance**: 100% of answers contain a clickable source URL.

### FR-3: Advice Refusal
- **Priority**: P0
- **Description**: The assistant refuses opinionated/portfolio questions (e.g., "Should I buy/sell?", "Which fund is best?") with a polite, facts-only message and a relevant educational link.
- **Acceptance**: 100% of advice-type queries get a refusal + educational link (e.g., SEBI/AMFI investor education page).

### FR-4: No Performance Claims
- **Priority**: P0
- **Description**: The assistant does not compute or compare returns. If asked about returns, it links to the official factsheet.
- **Acceptance**: No return numbers in answers; factsheet link provided instead.

### FR-5: Tiny UI
- **Priority**: P1
- **Description**: A minimal web UI with:
  - Welcome line
  - 3 example questions (clickable)
  - Disclaimer: "Facts-only. No investment advice."
- **Acceptance**: UI loads in <2s; all elements visible without scrolling.

### FR-6: "Last Updated" Timestamp
- **Priority**: P1
- **Description**: Every answer ends with "Last updated from sources: [date]".
- **Acceptance**: Timestamp present in 100% of answers.

---

## 8. Non-Functional Requirements

| # | Requirement | Target |
|---|-------------|--------|
| NFR-1 | Response latency | <5 seconds (including LLM generation) |
| NFR-2 | Availability | Local prototype; uptime not critical |
| NFR-3 | Data privacy | No PII accepted or stored (no PAN, Aadhaar, account numbers, OTPs, emails, phone numbers) |
| NFR-4 | Source integrity | Only official public pages; no screenshots of app back-end; no third-party blogs |
| NFR-5 | Portability | Runs on a single machine; no cloud deployment required |
| NFR-6 | API key security | Groq API key stored in `.env`, never committed to Git |

---

## 9. Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Embedding Model** | `sentence-transformers/all-MiniLM-L6-v2` | Local, no API key, 384-dim vectors |
| **Vector DB** | ChromaDB | Persisted to disk; ingestion runs once |
| **LLM** | Groq API | API key in `.env`; model: `llama-3.3-70b-versatile` or `mixtral-8x7b-32768` |
| **Backend** | Python (FastAPI or Flask) | Serves API endpoints |
| **Frontend** | HTML/CSS/JS (or Streamlit) | Tiny UI with welcome, examples, disclaimer |
| **Data Loading** | `requests` + `BeautifulSoup` / `pypdf` | For HTML and PDF parsing |
| **Orchestration** | LangChain or custom Python | RAG pipeline glue |

---

## 10. Constraints

| # | Constraint | Rationale |
|---|------------|-----------|
| C1 | **Public sources only** | No screenshots of app back-end; no third-party blogs as sources |
| C2 | **No PII** | Do not accept/store PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers |
| C3 | **No performance claims** | Don't compute/compare returns; link to official factsheet if asked |
| C4 | **Clarity & transparency** | Answers ≤3 sentences; "Last updated from sources:" appended |
| C5 | **API key security** | Groq API key in `.env`, never committed to Git |
| C6 | **Local embedding** | `all-MiniLM-L6-v2` runs locally; no external embedding API |

---

## 11. Deliverables

| # | Deliverable | Format | Description |
|---|-------------|--------|-------------|
| D1 | Working prototype | App link / notebook / ≤3-min demo video | Deployed app or Colab notebook or demo video |
| D2 | Source list | CSV or MD | List of 5+ URLs used as sources |
| D3 | README | Markdown | Setup steps, scope (AMC + schemes), known limits |
| D4 | Sample Q&A | Markdown/JSON | 5–10 queries with assistant answers + links |
| D5 | Disclaimer snippet | Text | "Facts-only. No investment advice." snippet used in UI |
| D6 | Chunked data | `.txt` file | All chunks saved to a readable `.txt` file for inspection |

---

## 12. User Stories

| # | As a... | I want to... | So that... |
|---|---------|--------------|------------|
| US1 | Retail investor | Ask "What is the expense ratio of HDFC Large Cap Fund?" | I can compare costs across schemes |
| US2 | Retail investor | Ask "What is the ELSS lock-in period?" | I understand when I can redeem |
| US3 | Support agent | Ask "How do I download a capital-gains statement?" | I can guide customers quickly |
| US4 | Retail investor | Ask "Should I buy HDFC Small Cap Fund?" | I get redirected to educational resources, not advice |
| US5 | Content team | See source links for every answer | I can verify and trust the information |

---

## 13. Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | Source pages change structure | Medium | High | Use robust parsers; fallback to cached snapshots |
| R2 | LLM hallucinates facts | Medium | High | Strict prompt: "use ONLY provided context"; citation enforcement |
| R3 | Groq API rate limits | Low | Medium | Retry with backoff; cache frequent queries |
| R4 | ChromaDB persistence issues | Low | Medium | Backup `.txt` chunk file; re-ingestion script |
| R5 | Advice-type queries slip through | Low | Medium | Keyword-based pre-filter + LLM refusal prompt |

---

## 14. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Answer accuracy | ≥90% | Manual evaluation on 10-question sample set |
| Citation rate | 100% | Automated check for source link in every answer |
| Advice refusal rate | 100% | Test with 5 advice-type queries |
| Response latency | <5s | Average over 20 queries |
| Answer length | ≤3 sentences | Automated sentence count |

---

## 15. Timeline / Milestones

| Phase | Duration | Activities |
|-------|----------|------------|
| **Phase 1: Data Ingestion** | Week 1 | Fetch 5 scheme pages + official sources; inspect data; propose chunking strategy; save chunks to `.txt` |
| **Phase 2: RAG Pipeline** | Week 1–2 | Set up ChromaDB; embed chunks; implement retrieval; integrate Groq LLM |
| **Phase 3: UI & Refusal Logic** | Week 2 | Build tiny UI; implement advice refusal; add disclaimer |
| **Phase 4: Testing & Deliverables** | Week 3 | Test sample Q&A; record demo video; write README; finalize source list |

---

## 16. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| Q1 | Which Groq model to use? (`llama-3.3-70b-versatile` vs `mixtral-8x7b-32768`) | TBD | Open |
| Q2 | Should we use LangChain or custom Python for orchestration? | TBD | Open |
| Q3 | Streamlit vs plain HTML/JS for UI? | TBD | Open |
| Q4 | Do we need to scrape SID/KIM PDFs, or are Groww pages sufficient? | TBD | Open |
| Q5 | How to handle scheme pages that require JavaScript rendering? | TBD | Open |

---

## 17. Appendix

### 7.1 Example Queries
1. "What is the expense ratio of HDFC Large Cap Fund?"
2. "What is the exit load for HDFC ELSS Tax Saver Fund?"
3. "What is the minimum SIP amount for HDFC Small Cap Fund?"
4. "What is the lock-in period for ELSS funds?"
5. "What is the riskometer level of HDFC Balanced Advantage Fund?"
6. "What is the benchmark of HDFC Equity Fund?"
7. "How do I download a capital-gains statement?"
8. "Should I buy HDFC Small Cap Fund?" *(advice — should be refused)*
9. "Which fund is best for long-term investment?" *(advice — should be refused)*
10. "What are the charges for redeeming HDFC Large Cap Fund before 1 year?"

### 7.2 Disclaimer Snippet
> **Facts-only. No investment advice.** This assistant provides factual information from official sources only. It does not recommend any scheme or provide investment advice. Please consult a SEBI-registered investment advisor before making investment decisions.

---

*End of Document*
