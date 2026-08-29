"""
app/__init__.py — the Flask application factory.
"""

import logging
import os
from datetime import timedelta

from flask import Flask

from app.core.errors import register_error_handlers
from app.extensions import db, migrate, jwt, limiter, cors


def create_app(config_object=None) -> Flask:
    from app.config import get_config

    app = Flask(__name__)
    app.config.from_object(config_object or get_config())
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        seconds=int(app.config.get("JWT_ACCESS_TTL_SECONDS", 28800))
    )
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]

    _init_extensions(app)
    _register_blueprints(app)
    register_error_handlers(app)
    _configure_logging(app)
    _register_health(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    _register_jwt_callbacks()
    limiter.init_app(app)
    cors.init_app(app, origins=app.config.get("CORS_ORIGINS") or ["http://localhost:5173"])
    os.makedirs(app.config.get("CHUNK_STORAGE_DIR") or "./data/chunks", exist_ok=True)
    os.makedirs(app.config.get("KMS_DIR") or "./data/keys", exist_ok=True)


def _register_blueprints(app: Flask) -> None:
    from app.blueprints.auth import auth_bp
    from app.blueprints.users import users_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(users_bp, url_prefix="/api/v1/users")


def _configure_logging(app: Flask) -> None:
    logging.basicConfig(level=getattr(logging, str(app.config.get("LOG_LEVEL", "INFO")).upper(), logging.INFO))
    app.logger.setLevel(app.config.get("LOG_LEVEL", "INFO"))


def _register_jwt_callbacks() -> None:
    from app.core.errors import error_response

    @jwt.expired_token_loader
    def _expired(_header, _payload):
        return error_response(401, "UNAUTHORIZED", "Token expired")

    @jwt.invalid_token_loader
    def _invalid(_reason):
        return error_response(401, "UNAUTHORIZED", "unauthorised")

    @jwt.unauthorized_loader
    def _missing(_reason):
        return error_response(401, "UNAUTHORIZED", "unauthorised")


def _register_health(app: Flask) -> None:
    @app.get("/health")
    def health():
        return {"status": "ok"}
