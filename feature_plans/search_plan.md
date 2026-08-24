# Feature Plan: Document Search & Retrieval

## What Is This Feature?

Search allows users to quickly locate documents across their accessible cases using keywords, filters, and full-text matching. Every search result is constrained to cases the user is a member of — no cross-case leakage. The system searches document metadata (filename, title, doc_type, tags, case number) and, optionally, extracted text (full-text search via PostgreSQL tsvector).

---

## Why Metadata-Only for the Prototype?

Document content is stored as encrypted chunks in MinIO. Searching inside document content would require decrypting each chunk, extracting text, and indexing it — that's the AI Retrieval feature (future roadmap). For the prototype:

- **Metadata search**: filename, title, doc_type, case_number, date range, uploaded_by — fast, no decryption needed
- **Full-text search on extracted text**: PostgreSQL `tsvector` over a `search_text` column populated during upload (for plaintext documents like .docx)
- Both are scoped to the user's accessible cases

---

## What Fields Are Searchable?

| Field | Type | Notes |
|-------|------|-------|
| `filename` | Text match (ILIKE) | Partial match supported |
| `title` | Full-text | tsvector indexed |
| `doc_type` | Exact match | From enum |
| `case_number` | Exact + partial | ILIKE |
| `case_title` | Full-text | Joined from cases table |
| `uploaded_by` | Exact UUID or name | Filter |
| `created_at` | Date range | from_date / to_date |
| `file_size_bytes` | Range | For finding large evidence files |
| `tags` | Array contains | PostgreSQL array @> operator |

---

## Database Changes

```sql
-- Add to documents table
ALTER TABLE documents ADD COLUMN tags TEXT[] DEFAULT '{}';
ALTER TABLE documents ADD COLUMN title TEXT;
ALTER TABLE documents ADD COLUMN search_text TEXT;  -- extracted plaintext (for FTS)
ALTER TABLE documents ADD COLUMN search_vector TSVECTOR;  -- computed FTS index

-- Trigger to auto-update search_vector when search_text changes
CREATE OR REPLACE FUNCTION update_document_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector = to_tsvector('english',
        coalesce(NEW.title, '') || ' ' ||
        coalesce(NEW.filename, '') || ' ' ||
        coalesce(NEW.search_text, '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_document_search_vector
    BEFORE INSERT OR UPDATE OF title, filename, search_text
    ON documents
    FOR EACH ROW EXECUTE FUNCTION update_document_search_vector();

-- GIN index for fast tsvector search
CREATE INDEX idx_document_search_vector
    ON documents USING GIN (search_vector);

-- Index for common filter combinations
CREATE INDEX idx_document_case_type_date
    ON documents (case_id, doc_type, created_at DESC)
    WHERE is_deleted = FALSE;

CREATE INDEX idx_document_tags
    ON documents USING GIN (tags);
```

---

## API Endpoint

### GET /api/v1/documents/search

All roles (scoped to accessible cases).

Query parameters:

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Free-text query (searches title, filename, search_text) |
| `doc_type` | string | One of the document type enum values |
| `case_id` | UUID | Limit to a specific case |
| `from_date` | ISO date | Documents uploaded after this date |
| `to_date` | ISO date | Documents uploaded before this date |
| `uploaded_by` | UUID | Filter by uploader |
| `tags` | comma-separated | Documents tagged with all listed tags |
| `page` | int (default 1) | Pagination |
| `limit` | int (default 20, max 100) | Results per page |
| `sort` | string | `created_at_desc` (default), `created_at_asc`, `filename`, `size_desc` |

Response:
```json
{
  "query": "witness statement october",
  "total": 4,
  "page": 1,
  "pages": 1,
  "items": [
    {
      "id": "uuid",
      "filename": "Witness_Statement_Oct15.pdf",
      "title": "Witness Statement - Ram Kumar",
      "doc_type": "WITNESS_STATEMENT",
      "file_size_bytes": 204800,
      "tags": ["witness", "october"],
      "case": {
        "id": "uuid",
        "case_number": "FIR-2026-DL-001",
        "title": "Cybercrime Investigation"
      },
      "uploaded_by": { "id": "uuid", "full_name": "Arjun Sharma" },
      "created_at": "2026-08-20T14:30:00Z",
      "relevance_score": 0.94    ← only present when q is provided
    }
  ]
}
```

---

## Query Building (SQLAlchemy)

```python
# services/search_service.py

def search_documents(
    current_user,
    q: str | None = None,
    doc_type: str | None = None,
    case_id: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    uploaded_by: str | None = None,
    tags: list[str] | None = None,
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at_desc"
) -> dict:

    # Base query — always scope to user's accessible cases
    accessible_case_ids = get_accessible_case_ids(current_user.id)

    query = Document.query.filter(
        Document.case_id.in_(accessible_case_ids),
        Document.is_deleted == False,
        Document.status == "ACTIVE"
    )

    # Full-text search
    if q:
        q_clean = q.strip()[:200]  # sanitize length
        query = query.filter(
            Document.search_vector.op('@@')(
                func.plainto_tsquery('english', q_clean)
            )
        )

    # Filters
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)

    if case_id:
        if case_id not in accessible_case_ids:
            return {"items": [], "total": 0}  # silently return empty
        query = query.filter(Document.case_id == case_id)

    if from_date:
        query = query.filter(Document.created_at >= from_date)

    if to_date:
        query = query.filter(Document.created_at <= to_date)

    if uploaded_by:
        query = query.filter(Document.uploaded_by == uploaded_by)

    if tags:
        query = query.filter(Document.tags.contains(tags))  # @> operator

    # Sorting
    sort_map = {
        "created_at_desc": Document.created_at.desc(),
        "created_at_asc":  Document.created_at.asc(),
        "filename":        Document.filename.asc(),
        "size_desc":       Document.file_size_bytes.desc()
    }
    query = query.order_by(sort_map.get(sort, Document.created_at.desc()))

    # Pagination
    paginated = query.paginate(page=page, per_page=limit, error_out=False)

    return {
        "query": q,
        "total": paginated.total,
        "page": page,
        "pages": paginated.pages,
        "items": [serialize_document_result(doc) for doc in paginated.items]
    }


def get_accessible_case_ids(user_id: str) -> list[str]:
    if user_is_super_admin(user_id):
        return [str(c.id) for c in Case.query.with_entities(Case.id).all()]
    return [
        str(cm.case_id)
        for cm in CaseMember.query
            .filter_by(user_id=user_id, is_active=True)
            .with_entities(CaseMember.case_id)
            .all()
    ]
```

**Security note:** `accessible_case_ids` is computed at query time, not cached — no stale access after membership is revoked.

---

## Relevance Scoring

When `q` is provided, PostgreSQL's `ts_rank` gives a relevance score:

```python
from sqlalchemy import func

if q:
    tsquery = func.plainto_tsquery('english', q_clean)
    rank_col = func.ts_rank(Document.search_vector, tsquery).label('rank')
    query = query.add_columns(rank_col).order_by(rank_col.desc())
```

`ts_rank` scores documents by how many times and how prominently the query terms appear. Title matches rank higher than body matches due to tsvector weight configuration.

---

## Tag System

Tags are free-form labels applied to documents at upload or later:

```json
// Upload with tags
POST /cases/{id}/documents
{
  "doc_type": "WITNESS_STATEMENT",
  "tags": ["witness", "key-evidence", "october-2026"]
}

// Add/update tags on existing document
PATCH /documents/{id}
{ "tags": ["witness", "key-evidence", "redacted"] }
```

Tags must match: `^[a-z0-9\-]+$` (lowercase, alphanumeric, hyphens only)
Max 10 tags per document.
Max 50 characters per tag.

---

## marshmallow Schema

```python
class SearchQuerySchema(Schema):
    q           = fields.Str(load_default=None, validate=validate.Length(max=200))
    doc_type    = fields.Str(load_default=None, validate=validate.OneOf([...doc types...]))
    case_id     = fields.UUID(load_default=None)
    from_date   = fields.DateTime(load_default=None)
    to_date     = fields.DateTime(load_default=None)
    uploaded_by = fields.UUID(load_default=None)
    tags        = fields.List(fields.Str(), load_default=None)
    page        = fields.Int(load_default=1, validate=validate.Range(min=1))
    limit       = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    sort        = fields.Str(
        load_default="created_at_desc",
        validate=validate.OneOf(["created_at_desc", "created_at_asc", "filename", "size_desc"])
    )

    @validates_schema
    def validate_date_range(self, data, **kwargs):
        if data.get('from_date') and data.get('to_date'):
            if data['from_date'] > data['to_date']:
                raise ValidationError("from_date must be before to_date")
```

---

## Frontend Components

| Component | Description |
|-----------|-------------|
| `GlobalSearchBar` | Persistent search bar in the top nav; submits to `/documents/search` |
| `SearchResultsPage` | Renders results with relevance highlights; shows case context for each result |
| `SearchFilters` | Collapsible sidebar: doc_type dropdown, date range pickers, tag filter chips |
| `HighlightedSnippet` | Shows matched text with keywords highlighted (using `ts_headline` from PostgreSQL) |
| `EmptySearchState` | "No documents found" with suggestions |
| `RecentSearches` | Stored in browser session (not backend) — last 5 queries |

### Search Result Highlighting

PostgreSQL's `ts_headline` function extracts the relevant snippet from `search_text`:

```python
from sqlalchemy import func

if q:
    headline_col = func.ts_headline(
        'english',
        Document.search_text,
        func.plainto_tsquery('english', q_clean),
        'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15'
    ).label('headline')
    query = query.add_columns(headline_col)
```

The `<mark>` tags are then rendered as highlighted text in the frontend.

---

## Audit

Every search is recorded:

```python
audit_service.record(
    AuditEventType.DOCUMENT_SEARCH_PERFORMED,
    actor_user_id=current_user.id,
    ip_address=request.remote_addr,
    metadata={
        "query": q,
        "doc_type": doc_type,
        "case_id": str(case_id) if case_id else None,
        "result_count": total
        # Note: never log the search results themselves
    }
)
```

---

## Rate Limiting

```python
@search_bp.route("/search", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def search_documents(): ...
```

60 requests/minute is generous for human use but prevents automated scraping.

---

## Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| Empty query `q=""` | Return all documents (filtered by other params) sorted by date |
| Query with SQL-special chars (`'`, `--`, `;`) | `plainto_tsquery` sanitizes these — no injection risk |
| User has no accessible cases | Return `{items: [], total: 0}` — do not reveal any case IDs |
| `case_id` param for a case user is not a member of | Silently return empty results (not 403 — don't reveal case existence) |
| `from_date` after `to_date` | 400 validation error |
| `limit=0` | 400 "limit must be at least 1" |
| Very long search query (>200 chars) | Truncated by marshmallow validation |
| Tags filter: `["nonexistent-tag"]` | Returns empty results — no error |

---

## Performance

- GIN index on `search_vector` makes `@@` operator O(log n) instead of O(n)
- `accessible_case_ids` list query is fast with index on `case_members(user_id, is_active)`
- For a SUPER_ADMIN with access to all cases, skip the `case_id IN (...)` filter to avoid large IN clauses
- Pagination prevents full-result scans — default `limit=20`

---

## Testing Plan

```
tests/search/
├── test_search_basic.py
│   ├── test_text_search_finds_matching_documents
│   ├── test_text_search_is_case_insensitive
│   ├── test_results_only_include_accessible_cases
│   ├── test_deleted_documents_excluded
│   └── test_empty_query_returns_all_accessible_docs
├── test_search_filters.py
│   ├── test_filter_by_doc_type
│   ├── test_filter_by_date_range
│   ├── test_filter_by_tags
│   ├── test_filter_by_case_id_for_member
│   ├── test_filter_by_case_id_for_non_member_returns_empty
│   └── test_invalid_date_range_returns_400
├── test_search_pagination.py
│   ├── test_pagination_returns_correct_page
│   └── test_limit_capped_at_100
├── test_search_security.py
│   ├── test_sql_injection_in_query_is_safe
│   ├── test_cross_case_access_not_possible
│   └── test_search_creates_audit_event
```

---

## Implementation Order

1. Migration: add `search_vector`, `tags`, `title` to documents; add trigger + GIN index
2. `search_service.py` — query builder with all filters
3. `search_schemas.py` — query + response schemas
4. `documents.py` Blueprint — `GET /documents/search` route
5. Upload pipeline: populate `search_text` for docx/txt files during upload
6. Frontend: GlobalSearchBar + SearchResultsPage + SearchFilters
7. Tests
