# Feature Plan: AI-Based Document Retrieval

> **Status:** Post-hackathon roadmap. Do NOT implement for the Sep 2 prototype.
> Prototype milestone: show a "Semantic Search" toggle in the search bar — greyed out with "Coming soon."

---

## What Is This Feature?

Standard keyword search (PostgreSQL FTS) finds documents that contain the exact words in your query. AI-based retrieval finds documents that are *semantically similar* to your query — matching meaning, not just words.

**Example:** A user searches "blood stain analysis on clothing." With keyword search, they find documents containing those exact words. With semantic search, they also find documents about "haematological trace evidence examination" and "textile forensic examination results" — because the meaning is the same even though the words differ.

This is implemented using:
1. **Vector embeddings** — each document (or chunk) is converted to a numerical vector that represents its meaning
2. **Qdrant** — a vector database that stores and searches these vectors efficiently
3. **Hybrid search** — combines vector similarity with keyword ranking for best results
4. **Access control** — vector search results are filtered to the user's accessible cases

---

## How Vector Embeddings Work

A sentence embedding model converts text into a high-dimensional vector (a list of 384 numbers for `all-MiniLM-L6-v2`). Semantically similar texts produce vectors that are close together in this 384-dimensional space (measured by cosine similarity).

```
"blood stain on jacket"  → [0.23, -0.41, 0.87, ...]  (384 floats)
"haematological trace"   → [0.25, -0.39, 0.85, ...]  ← close → high similarity
"FIR registration date"  → [-0.12, 0.55, -0.23, ...] ← far → low similarity
```

---

## Architecture

```
                    [Embedding Pipeline] (runs on document upload)
                              │
 Document chunks              │
 (after decryption)           │
       │                      │
       ▼                      ▼
  Text extraction     SentenceTransformer
  (PyMuPDF / OCR)    .encode(text_chunks)
       │                      │
       └──────────────────────┤
                              ▼
                         Qdrant upsert:
                           vector: [384 floats]
                           payload: {
                             document_id,
                             case_id,
                             chunk_index,
                             doc_type,
                             filename
                           }

                    [Query Pipeline] (on search request)
                              │
  User query: "blood stain"   │
       │                      │
       ▼                      ▼
  Keyword search         SentenceTransformer
  (PostgreSQL FTS)       .encode(query)
       │                      │
       └──────────────────────┤
                              ▼
                         Qdrant search:
                           vector: query_embedding,
                           filter: {case_id IN [accessible_cases]},
                           top: 20
                              │
                    Merge + re-rank results:
                      score = 0.6 * vector_score + 0.4 * bm25_score
                              │
                    Return top-10 with relevance scores
```

---

## Embedding Model: all-MiniLM-L6-v2

| Property | Value |
|----------|-------|
| Dimensions | 384 |
| Max sequence length | 256 tokens (~180 words) |
| Size | 80 MB |
| Inference time | ~5ms per chunk on CPU |
| License | Apache 2.0 (on-premise use OK) |
| Language | English-primary; multilingual variant: `paraphrase-multilingual-MiniLM-L12-v2` |

For Hindi/regional language documents: switch to `paraphrase-multilingual-MiniLM-L12-v2` (768 dims, 420 MB).

---

## Qdrant Setup

```yaml
# docker-compose.yml addition
qdrant:
  image: qdrant/qdrant:v1.11.0
  container_name: dms_qdrant
  volumes:
    - qdrant_storage:/qdrant/storage
  environment:
    - QDRANT__SERVICE__HTTP_PORT=6333
    - QDRANT__SERVICE__GRPC_PORT=6334
  networks:
    - dms_internal
  # No external port exposure — internal only
```

Collection schema:
```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient("qdrant", port=6333)

client.recreate_collection(
    collection_name="document_chunks",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)
```

---

## Embedding Pipeline (Celery Task)

Runs after OCR completes (or after upload for text documents):

```python
@celery.task
def embed_document_task(document_id: str):
    document = Document.query.get(document_id)

    # Get text to embed
    if not document.search_text:
        return  # No text available — skip

    # Split into ~200-word chunks with 50-word overlap
    text_chunks = sliding_window_chunks(
        document.search_text,
        chunk_size=200,      # words
        overlap=50           # words
    )

    # Load model (cached in memory after first load)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Embed all chunks
    embeddings = model.encode(text_chunks, batch_size=32, show_progress_bar=False)

    # Upsert to Qdrant
    points = [
        PointStruct(
            id=str(uuid4()),
            vector=embedding.tolist(),
            payload={
                "document_id": str(document_id),
                "case_id":     str(document.case_id),
                "doc_type":    document.doc_type,
                "filename":    document.filename,
                "chunk_index": i,
                "text":        text_chunks[i]   # stored for snippet display
            }
        )
        for i, embedding in enumerate(embeddings)
    ]

    qdrant_client.upsert(collection_name="document_chunks", points=points)

    document.embedding_status = "DONE"
    db.session.commit()
```

---

## Hybrid Search Query

```python
def semantic_search(query: str, accessible_case_ids: list[str], limit: int = 20) -> list[dict]:
    # Step 1: Embed the query
    model = get_cached_model()
    query_vector = model.encode([query])[0].tolist()

    # Step 2: Vector search in Qdrant (filtered to accessible cases)
    vector_results = qdrant_client.search(
        collection_name="document_chunks",
        query_vector=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="case_id",
                    match=MatchAny(any=accessible_case_ids)
                )
            ]
        ),
        limit=50,   # fetch more than needed for re-ranking
        with_payload=True
    )

    # Step 3: BM25 keyword search (PostgreSQL)
    keyword_results = db.session.execute(
        text("""
            SELECT d.id, ts_rank(d.search_vector, q) AS bm25_score
            FROM documents d, plainto_tsquery('english', :query) q
            WHERE d.search_vector @@ q
              AND d.case_id = ANY(:case_ids)
              AND d.is_deleted = FALSE
            ORDER BY bm25_score DESC
            LIMIT 50
        """),
        {"query": query, "case_ids": accessible_case_ids}
    ).fetchall()

    bm25_scores = {str(row.id): float(row.bm25_score) for row in keyword_results}
    bm25_max = max(bm25_scores.values()) if bm25_scores else 1.0

    # Step 4: Re-rank by combining scores
    doc_scores = {}
    for result in vector_results:
        doc_id = result.payload["document_id"]
        vector_score = result.score  # cosine similarity, 0-1
        bm25_norm = bm25_scores.get(doc_id, 0) / bm25_max  # normalize 0-1
        combined = 0.6 * vector_score + 0.4 * bm25_norm
        if doc_id not in doc_scores or doc_scores[doc_id]["score"] < combined:
            doc_scores[doc_id] = {
                "score": combined,
                "snippet": result.payload.get("text", "")[:300]
            }

    # Step 5: Sort and return
    ranked = sorted(doc_scores.items(), key=lambda x: x[1]["score"], reverse=True)
    return [{"document_id": doc_id, **data} for doc_id, data in ranked[:limit]]
```

---

## Access Control in Vector Search

**Critical:** Qdrant's payload filter (`case_id IN [accessible_cases]`) is applied at the vector database level. This means:
- Only vectors from the user's accessible cases are considered in the search
- The semantic search cannot leak document existence across case boundaries
- This filter must always be applied — never search without it

---

## Database Changes

```sql
ALTER TABLE documents ADD COLUMN embedding_status TEXT DEFAULT 'NOT_APPLICABLE';
-- Values: NOT_APPLICABLE, PENDING, IN_PROGRESS, DONE, FAILED

ALTER TABLE documents ADD COLUMN embedding_model TEXT;
-- Tracks which model version created the embeddings (for re-embedding on model upgrade)
```

---

## API Changes

### GET /api/v1/documents/search

Add `mode` parameter:
- `mode=keyword` (default) — PostgreSQL FTS only
- `mode=semantic` — vector search only
- `mode=hybrid` (recommended when available) — combined

Add `semantic_available: true/false` to response so the frontend knows whether to show the semantic toggle.

---

## UI

| Component | Description |
|-----------|-------------|
| `SemanticToggle` | In search bar: "Keyword / Semantic / Hybrid" toggle; greyed out if `semantic_available=false` |
| `RelevanceScore` | Shows match percentage next to each result when in semantic mode |
| `SemanticSnippet` | Shows the specific passage from the document that matched, not just filename |

---

## Limitations & Mitigations

| Limitation | Mitigation |
|-----------|-----------|
| Model doesn't understand Hindi well | Switch to multilingual model for Hindi documents |
| Context window (256 tokens) smaller than full document | Sliding window chunking with overlap |
| Embedding model loaded into memory for each worker | Use a dedicated embedding worker (Celery pool of 1) with model loaded at start |
| Qdrant storage grows with documents | Implement periodic re-embedding for model upgrades; retention policy |
| Cold start (model load ~2 seconds) | Warm up model on worker startup, not on first request |

---

## Implementation Order (When Ready)

1. Qdrant Docker service + collection schema init
2. `backend/app/core/embeddings.py` — model wrapper with caching
3. `embed_document_task` Celery task
4. Wire into upload pipeline: queue after OCR (or directly after upload for text docs)
5. `search_service.py` — add semantic and hybrid modes
6. Handle document deletion: `qdrant_client.delete(filter=document_id)` on soft-delete
7. Frontend: SemanticToggle + RelevanceScore + SemanticSnippet
8. Add `embedding_status` column + migration

---

## Dependencies

```
sentence-transformers==3.3.*   # SentenceTransformer model
qdrant-client==1.11.*          # Qdrant Python client
torch==2.5.*                   # Required by sentence-transformers (CPU version)
```

CPU-only torch to keep Docker image smaller:
```dockerfile
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Model download (first run only):
```python
# On worker startup
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')  # downloads to ~/.cache/
```
