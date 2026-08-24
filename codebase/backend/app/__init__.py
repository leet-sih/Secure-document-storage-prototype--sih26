"""
app/__init__.py — the Flask application factory.

WHAT THIS FILE DOES:
    create_app() builds and returns a fully-wired Flask app:
      1. Loads config from environment (config.get_config()).
      2. Binds extensions (db, migrate, jwt, limiter, cors) to the app.
      3. Registers all blueprints (auth, users, cases, documents, audit,
         signatures, sharing, share_access, search) under /api/v1.
      4. Registers error handlers (uniform JSON error envelope).
      5. Configures structured logging.

USAGE:
    from app import create_app
    app = create_app()

RETURNS:
    A Flask app instance (used by wsgi.py and the test suite's `client` fixture).

DO NOT create a global `app` here — always go through create_app() (see CLAUDE.md).
"""

from flask import Flask

from app.config import get_config
from app.extensions import db, migrate, jwt, limiter, cors


def create_app(config_object=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or get_config())

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _configure_logging(app)

    return app


def _init_extensions(app: Flask) -> None:
    """Bind extension singletons to this app.
    TODO: cors.init_app(app, origins=app.config["CORS_ORIGINS"]).
    Also ensure the local storage dirs exist (CHUNK_STORAGE_DIR, KMS_DIR)."""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)   # in-memory storage (prototype)
    cors.init_app(app)      # TODO: origins=app.config["CORS_ORIGINS"]


def _register_blueprints(app: Flask) -> None:
    """Register every blueprint under the /api/v1 prefix.

    TODO (each owner registers their own):
        from app.blueprints.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
        ... users, cases, documents, audit, signatures, sharing, search ...
        # share_access is PUBLIC: url_prefix="/api/v1/share"
    """
    pass


def _register_error_handlers(app: Flask) -> None:
    """Wire the handlers in app.core.errors so every error returns the JSON envelope
    { "error": { "code", "message", "request_id" } }. TODO."""
    pass


def _configure_logging(app: Flask) -> None:
    """Set up structlog. Rule: never log document content, passwords, keys, or PII —
    only IDs and event types. TODO."""
    pass
