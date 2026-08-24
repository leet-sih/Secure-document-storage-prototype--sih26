"""
search_service.py — metadata + full-text document search.

search_documents(current_user, **filters) -> paginated dict
    ALWAYS scopes to case_service.get_accessible_case_ids(user) — no cross-case leakage.
    Supports: q (PostgreSQL tsvector FTS), doc_type, case_id, date range, uploaded_by,
    tags (array contains), sort, pagination. Excludes deleted/non-ACTIVE docs.
    A case_id the user can't see -> silently empty results (never 403).

Optional: ts_headline snippet + ts_rank relevance when q is present.
Records DOCUMENT_SEARCH_PERFORMED (query + result_count, NEVER the results) — done in blueprint.

Full design: ../../feature_plans/search_plan.md
Semantic/vector search (Qdrant) is roadmap — see ai_retrieval_plan.md.
"""


def search_documents(current_user, **filters) -> dict:
    raise NotImplementedError
