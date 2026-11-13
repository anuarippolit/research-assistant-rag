# Research Assistant RAG

A self-hosted, NotebookLM-style assistant for PDFs. Upload lecture slides or papers, then:

- **Chat** with them. Every claim carries a citation like `[3_Core_NCC_PERC.pdf, p. 55]`, and when the answer is not in the sources, the assistant says so instead of guessing.
- **Understand slides**: a vision step turns formulas and diagrams into searchable text.
- **Summarize** one document or the whole collection.
- **Extract** a comparison table (features x documents) with a page number and a quote for every cell.

Built as a learning project: FastAPI, Qdrant, local embeddings, Claude (Haiku 5.5). Single-user and local by design (no auth, you bring your own Anthropic API key).

## How it works

```
Upload PDF -> parse pages -> drop build-step slides -> describe each slide with a vision model
           -> chunk -> embed (bge-small) -> Qdrant (vectors)      SQLite (sources, summaries)

Chat:      question -> embed -> top-k chunks (optionally within chosen sources) -> Claude -> answer + [file, p. N]
Summarize: all chunks of a source (reading order) -> Claude -> summary (cached in SQLite)
Extract:   per (source, feature): top-5 chunks -> Claude -> JSON {value, page, evidence} -> table
```

Key design points:

- **Ingestion runs in the background.** `POST /sources` answers at once; the client watches the source `status` (`pending` -> `processing` -> `ready` / `failed`).
- **Vision step.** Each page is rendered to PNG and described by Claude (formulas rewritten as text, diagrams in words). The description is appended to the page text before chunking, so a text-only embedding model can find "the slide with the circles and triangles".
- **Build-step removal.** Slides that build up step by step produce near-duplicate pages. A page is dropped when at least 80% of its words appear on the next page, so retrieval returns more distinct slides.
- **Citations are checked, not trusted.** The prompt forces `[file, p. N]` labels, and the eval script verifies them against the retrieved chunks.
- **Prompt-injection hygiene.** Source text is wrapped in tags and the system prompt states that it is data, not instructions.

## Quick start

Requirements: Docker and an Anthropic API key.

```bash
git clone https://github.com/anuarippolit/research-assistant-rag.git
cd research-assistant-rag
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
docker compose up --build
```

Open http://localhost:8000/docs. The first start downloads the embedding model (cached in `./hf_cache`). Data lives in `./data` (SQLite, uploaded PDFs) and `./qdrant_storage` (vectors), so it survives `docker compose down`.

```bash
# upload (processing runs in the background; vision takes about 2 minutes for a 60-slide lecture)
curl -F "file=@lecture.pdf" http://localhost:8000/sources
curl http://localhost:8000/sources                      # watch "status" until "ready"

# chat
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"question": "What are the core components of supervised learning?", "k": 5}'

# summary of all ready sources (cached; add "refresh": true to recompute)
curl -X POST http://localhost:8000/summarize -H "Content-Type: application/json" -d '{}'

# comparison table
curl -X POST http://localhost:8000/extract -H "Content-Type: application/json" \
  -d '{"features": ["loss function", "activation function", "learning rate"]}'
```

| Endpoint | What it does |
|---|---|
| `POST /sources` | Upload a PDF, start background ingestion |
| `GET /sources`, `GET /sources/{id}` | List sources / one source with its status |
| `DELETE /sources/{id}` | Remove the file, vectors, record and summary |
| `POST /chat` | Question -> answer with citations (`source_ids` limits the search) |
| `POST /summarize` | Summary of the chosen sources (default: all ready ones) |
| `POST /extract` | Feature table over the chosen sources |

## Evaluation

Retrieval and answers are evaluated separately (`eval/`), on questions written from the three lecture PDFs (165 chunks): answerable questions with expected page ranges, and unanswerable ones that must be refused.

| Version | Answerable questions | recall@1 / @3 / @5 | Distinct slides in top-5 | False refusals | Wrong citations |
|---|---|---|---|---|---|
| Baseline | 30 | 0.80 / 0.90 / 0.90 | 3.40 | 4 / 30 | 0 / 26 |
| + build-step removal | 30 | 0.80 / 0.87 / 0.87 | 4.83 | 3 / 30 | 1 / 27 |
| + vision v1 | 36 | 0.86 / 0.89 / 0.89 | 4.72 | 2 / 36 | 2 / 34 |
| + vision v2 (final prompt) | 36 | 0.78 / 0.94 / 0.94 | 4.81 | 2 / 36 | 0 / 34 |

Correct refusals on unanswerable questions: 8 / 8 in every version.

Notes on reading the table:
- The answerable question set grew between rows (30 -> 36; plus 8 unanswerable ones), so rows are not perfectly comparable. Two eval labels were wrong and were fixed by content, not to improve the score (one page range was too narrow, one included build steps).
- Build-step removal lowered recall@5 slightly but raised the number of distinct slides in the top 5 (3.40 -> 4.81), which gives the model more evidence to answer from.
- A "false refusal" is usually a retrieval miss, not a model problem. The two remaining ones (NCC as a linear classifier; a one-line fact about the year of backpropagation) are known misses.

Extract was checked by hand on 3 lectures x 3 features: about 7 of 9 cells were correct with a page and a quote. One cell was wrong (a chain-rule formula returned as the loss function, because the real loss slide was not in the top 5) and one `null` was probably a false negative.

## Design decisions and trade-offs

- **RAG for chat, full document for summaries.** Chat needs search across many documents. A summary needs the whole document, and one lecture is about 25K tokens, so it goes into one call (Haiku 5.5 has a 1M-token context). Summaries are computed lazily and cached.
- **For a small corpus, long context beats retrieval for extract.** Pasting the whole slide deck into the model is simpler, about a cent per request and avoids retrieval misses. RAG pays off when the corpus does not fit in the context, when the same documents are queried many times, and when verifiable citations matter. Extract currently uses the top-5 chunks; moving it to the full document is the first planned improvement.
- **Local embeddings** (`BAAI/bge-small-en-v1.5`, 384 dimensions, cosine) keep indexing free and offline; only generation and vision call the API.
- **Qdrant plus SQLite.** SQLite is the bookkeeping (files, statuses, summaries); Qdrant holds vectors. On delete, vectors go first and the SQLite record last, so no orphaned vectors remain.

## Limitations and next steps

- Single user, local use; no authentication or multi-tenancy.
- Extract: read the whole document instead of the top-5 chunks; verify that each `evidence` quote really occurs in the source; compare both modes on accuracy, tokens and cost.
- Retrieval: cross-encoder reranker, hybrid (keyword + vector) search, query rewriting. "Relation" questions such as "how is the perceptron related to NCC" miss today.
- Vision: only slides with extractable text are described (image-only pages are skipped); parallel calls and a description cache would cut the 2-minute indexing time; a flag to turn vision off.
- Summaries: hierarchical (map-reduce / RAPTOR-style) summaries for documents that do not fit in the context.
- Cleanup: strip repeated slide headers, normalize ligatures, detect duplicate uploads by hash, custom errors for 404 / 409 responses.
- Later: an agentic layer where Claude chooses between chat, summarize and extract through tool use.

## Project layout

```
app/
  main.py            FastAPI app, startup (DB, collection, embedding model)
  config.py          settings from environment / .env
  schemas.py         request and response models
  api/               HTTP layer: sources, chat, summarize, extract
  core/              parsing, chunking, vision, embeddings, ingestion, prompts, llm, chat, summarize, extract
  db/                sqlite.py (sources, summaries), vector_store.py (Qdrant)
eval/                questions.json, run_retrieval.py, run_answers.py
scripts/             numpy_search.py (brute-force numpy search) and compare_search.py (numpy vs Qdrant), learning tools
```

Run the eval (needs the three lectures ingested; `run_answers` calls Claude and costs money, always pass a new label so earlier results are not overwritten):

```bash
python -m eval.run_retrieval
python -m eval.run_answers my_label
```
