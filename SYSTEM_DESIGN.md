# System Design: AI Research Assistant (RAG)

Self-hosted research assistant: upload sources (PDFs, presentations), then
query, summarize, or extract structured data across them.

**Goal:** learning project + portfolio piece. Not a SaaS — single-tenant,
self-hosted, run via one Docker command, user supplies their own Anthropic
API key.

---

## 1. Scope (v1)

Three modes over one shared source library:

1. **Chat** — ask questions across your uploaded sources (RAG)
2. **Summarize** — full-document summary of one source (no retrieval)
3. **Compare / Extract** — pick features, get a comparison table across
   multiple sources

Explicitly **out of scope for v1** (documented as future work, not built):
- Auth / multi-user accounts
- Hybrid search / reranking
- Persistent multi-turn chat history
- Celery/Redis for heavy async jobs
- Hosted live demo (v1 = self-hosted only)

---

## 2. Tech Stack

| Piece | Choice | Why |
|---|---|---|
| Backend | Python + FastAPI | ML/RAG ecosystem is Python-first |
| Interface | Swagger/OpenAPI (`/docs`) | No separate frontend for v1 |
| LLM | Claude API (Anthropic) | User's own key, via `.env` |
| Embeddings | Local, open-source (`sentence-transformers`, e.g. `bge-small-en-v1.5`) | Runs on CPU inside the container — no second API key needed |
| Vector DB | Qdrant (separate Docker service) | Real vector-DB-as-a-service, good filtering support |
| Metadata storage | SQLite | File-based, no extra container, fine for single-tenant |
| PDF parsing | PyMuPDF (`fitz`) | Handles text extraction + can render pages as images (fallback for tables/scans) |
| Presentation parsing | `python-pptx` | Slide text extraction |
| Background jobs | FastAPI `BackgroundTasks` | Good enough for v1; note Celery+Redis as a scaling upgrade |
| Deployment | Docker Compose (`app` + `qdrant`), `.env` for API key | One command to run |

---

## 3. Data Model

### SQLite (app-level bookkeeping)

**`sources`**
| field | type | notes |
|---|---|---|
| id | str | source_id |
| filename | str | |
| file_type | str | pdf / pptx |
| status | str | pending / processing / ready / failed |
| created_at | datetime | |

**`extraction_results`**
| field | type | notes |
|---|---|---|
| id | str | |
| source_ids | json | which sources this table covers |
| features | json | requested feature list |
| result | json | the extracted table itself |
| created_at | datetime | |

### Qdrant (per-chunk vector + payload)

Each point = one chunk of text.

```json
{
  "vector": [0.021, -0.183, ...],
  "payload": {
    "source_id": "doc_3",
    "filename": "smith_2023.pdf",
    "page": 5,
    "chunk_index": 12,
    "text": "..."
  }
}
```

---

## 4. Ingestion Pipeline

*What happens to one new file, from upload to "ready to search."*

1. `POST /sources` receives file → row created in `sources` (`status=pending`)
   → respond immediately, don't make the client wait
2. Background task runs:
   - **Parse** — extract raw text (PyMuPDF / python-pptx), per page/slide
   - **Chunk** — split into ~500–800 token pieces, ~100 token overlap
   - **Embed** — run each chunk through the local embedding model
   - **Upsert** — write vector + payload into Qdrant, one point per chunk
3. Update `sources.status = ready` (or `failed`, with an error message)

This must complete before Chat/Compare can use that source.

---

## 5. The Three Modes

### Chat (RAG)
`POST /chat` — `{ query: str, source_ids?: [str] }`

1. Embed the query
2. Search Qdrant (top-k similarity, optionally filtered to `source_ids`)
3. Build a prompt: retrieved chunks + question
4. Generate answer, cite which source/page each fact came from

### Summarize (no retrieval)
`POST /sources/{id}/summarize`

Feeds the source's full parsed text directly to the LLM — no chunk search.
Works because a single source is assumed to fit in context (an article, a
deck). This is the "NotebookLM-style" mode for exam prep.

### Compare / Extract (structured extraction)
`POST /extract` — `{ source_ids: [str], features: [{name, description}] }`

Per source:
- If short enough → send full text
- If too long → run one retrieval query per feature (scoped to that
  `source_id`), merge the retrieved chunks
- One LLM call per source, forced JSON output:
  ```json
  { "source_id": "doc_3", "features": { "sample_size": "42", "method": "RCT" } }
  ```
- If a feature isn't found in the source, the model returns `null` —
  never guesses

Collect one JSON object per source → assemble into a table (rows =
sources, columns = features) → exportable as CSV.

Batch the feature list into groups of ~10–20 per call if extraction
quality drops with too many fields at once.

---

## 6. Source Management (API)

- `POST /sources` — upload a file, kicks off ingestion
- `GET /sources` — list all sources + status
- `GET /sources/{id}` — one source's details
- `DELETE /sources/{id}` — remove source row + its chunks from Qdrant

---

## 7. Suggested Repo Structure

```
research-assistant/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── sources.py
│   │   ├── chat.py
│   │   ├── summarize.py
│   │   └── extract.py
│   ├── core/
│   │   ├── ingestion.py      # parse -> chunk -> embed -> upsert
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   └── llm.py            # Claude API calls, prompts per mode
│   ├── db/
│   │   ├── sqlite.py
│   │   └── qdrant_client.py
│   └── models.py             # pydantic schemas
├── docker-compose.yml        # services: app, qdrant
├── Dockerfile
├── .env.example              # ANTHROPIC_API_KEY=
├── requirements.txt
└── README.md
```

---

## 8. Why RAG Alone Wasn't Enough (design note for README)

Classic RAG (retrieve-then-answer) is built for point questions, not
whole-corpus analysis. Summarizing a document or extracting features
across 20 sources doesn't benefit from retrieval — it needs the model to
see the (right-sized) whole thing. This project deliberately routes each
task to the right strategy instead of forcing everything through one RAG
pipeline: retrieval for Q&A, full-context for summarization, structured
per-document extraction for comparison tables.
