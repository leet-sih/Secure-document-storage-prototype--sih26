"""
search.py — document search. Prefix: /api/v1/documents

ROUTES:
    GET /search   [auth, rate-limited]   metadata + full-text search, scoped to accessible cases

Validates with SearchQuerySchema, calls search_service.search_documents, records
DOCUMENT_SEARCH_PERFORMED (query + result_count only, never the results). See search_plan.md.
"""

from flask import Blueprint

search_bp = Blueprint("search", __name__)

# TODO: implement route.
# from app.extensions import limiter
# from app.core.rate_limit import SEARCH_LIMITS
# from app.schemas.search_schemas import SearchQuerySchema
# from app.services import search_service
