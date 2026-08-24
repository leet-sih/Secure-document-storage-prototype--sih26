"""
errors.py — uniform JSON error envelope + Flask error handlers.

EVERY error response has the shape:
    { "error": { "code": "FORBIDDEN", "message": "...", "request_id": "uuid" } }

500s must return a GENERIC message (details go to logs only). request_id ties a client
error to a server log line.

Status/code map (full table in ../../docs/API.md):
    400 VALIDATION_ERROR | 401 UNAUTHORIZED | 403 FORBIDDEN | 404 NOT_FOUND |
    409 CONFLICT | 410 GONE | 422 INTEGRITY_VIOLATION | 423 LOCKED |
    429 RATE_LIMITED | 500 INTERNAL_ERROR

register_error_handlers(app) is called from create_app().
"""

from flask import jsonify


class APIError(Exception):
    """Raise this in services/blueprints for controlled failures.
    Example: raise APIError(409, "CONFLICT", "Case number already exists")."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def error_response(status: int, code: str, message: str):
    """RETURNS: (json_body, status) with a fresh request_id. TODO: attach real request_id."""
    return jsonify({"error": {"code": code, "message": message, "request_id": None}}), status


def register_error_handlers(app) -> None:
    """Register handlers for APIError, marshmallow ValidationError, 404/403/429, and a
    catch-all 500 that logs the traceback and returns a generic body. TODO."""
    pass
