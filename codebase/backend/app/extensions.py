"""
extensions.py — singleton instances of Flask extensions.

WHY THIS FILE EXISTS:
    To avoid circular imports. Extensions are created here WITHOUT an app, then bound
    to the app inside create_app() via `ext.init_app(app)`. Models and services import
    `db` from here; they must never import the app object.

EXPORTS (import these elsewhere):
    db        — SQLAlchemy() : the ORM session/engine. Models subclass db.Model.
    migrate   — Migrate()    : Flask-Migrate (Alembic) for schema migrations.
    jwt       — JWTManager() : access-token verification.
    limiter   — Limiter()    : in-memory rate limiting (no Redis in the prototype).
    cors      — CORS()       : allows the Vite dev server origin.

STORES: nothing itself — `db` is the gateway to PostgreSQL.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
cors = CORS()
