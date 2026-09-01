"""
errors.py — uniform JSON error envelope + Flask error handlers.
"""

import uuid

from flask import jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def error_response(status: int, code: str, message: str):
    return jsonify(
        {"error": {"code": code, "message": message, "request_id": str(uuid.uuid4())}}
    ), status


def register_error_handlers(app) -> None:
    @app.errorhandler(APIError)
    def _api_error(err: APIError):
        return error_response(err.status, err.code, err.message)

    @app.errorhandler(ValidationError)
    def _validation(err: ValidationError):
        app.logger.debug("marshmallow_validation_error fields=%s", err.messages)
        # In development, surface the field errors; in production keep it generic.
        if app.debug:
            import json as _json
            return error_response(400, "VALIDATION_ERROR", _json.dumps(err.messages))
        return error_response(400, "VALIDATION_ERROR", "Invalid request")

    @app.errorhandler(429)
    def _rate(_err):
        return error_response(429, "RATE_LIMITED", "Too many requests")

    @app.errorhandler(HTTPException)
    def _http(err: HTTPException):
        code_map = {
            400: "VALIDATION_ERROR",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            410: "GONE",
            422: "INTEGRITY_VIOLATION",
            423: "LOCKED",
        }
        code = code_map.get(err.code or 500, "INTERNAL_ERROR")
        message = err.description if err.code and err.code < 500 else "An internal error occurred"
        if err.code == 500:
            message = "An internal error occurred"
        return error_response(err.code or 500, code, str(message))

    @app.errorhandler(Exception)
    def _catch(err: Exception):
        if isinstance(err, APIError):
            return error_response(err.status, err.code, err.message)
        if isinstance(err, ValidationError):
            return error_response(400, "VALIDATION_ERROR", "Invalid request")
        if isinstance(err, HTTPException):
            return _http(err)
        app.logger.exception("unhandled_error")
        return error_response(500, "INTERNAL_ERROR", "An internal error occurred")
