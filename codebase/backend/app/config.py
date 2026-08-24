"""
config.py — centralized configuration, loaded from environment variables.

WHAT THIS FILE DOES:
    Defines Config classes read by create_app(). Every value comes from an env var
    (see ../.env.example). NEVER hardcode secrets here.

PROTOTYPE NOTE:
    Kept intentionally small. No Redis / MinIO / Vault / Celery config — the prototype uses
    the local filesystem for chunks and a local file KMS for keys. Those get added back when
    we scale up (see docs/ARCHITECTURE.md "Future / production").

EXPORTS:
    Config, DevelopmentConfig, ProductionConfig, get_config()
"""

import os


class Config:
    # ── Flask ──
    SECRET_KEY = os.environ["SECRET_KEY"]
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # ── Database ──
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT (prototype: access token only, no refresh flow) ──
    JWT_SECRET_KEY = os.environ["JWT_SECRET"]
    JWT_ACCESS_TTL_SECONDS = int(os.environ.get("JWT_ACCESS_TTL_SECONDS", 28800))  # 8h for demo

    # ── MFA / lockout ──
    MFA_ISSUER = os.environ.get("MFA_ISSUER", "SecureDMS")
    ACCOUNT_LOCKOUT_THRESHOLD = int(os.environ.get("ACCOUNT_LOCKOUT_THRESHOLD", 5))
    ACCOUNT_LOCKOUT_MINUTES = int(os.environ.get("ACCOUNT_LOCKOUT_MINUTES", 15))

    # ── Local storage (prototype replacements for MinIO + Vault) ──
    CHUNK_STORAGE_DIR = os.environ.get("CHUNK_STORAGE_DIR", "./data/chunks")
    KMS_DIR = os.environ.get("KMS_DIR", "./data/keys")

    # ── Uploads ──
    MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", 100))
    CHUNK_SIZE_BYTES = int(os.environ.get("CHUNK_SIZE_BYTES", 1048576))  # 1 MB
    MAX_CONTENT_LENGTH = MAX_FILE_SIZE_MB * 1024 * 1024

    # ── CORS (allow the Vite dev server) ──
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

    # ── Rate limiting (in-memory for the prototype) ──
    RATELIMIT_STORAGE_URI = "memory://"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


def get_config():
    env = os.environ.get("ENVIRONMENT", "development")
    return ProductionConfig if env == "production" else DevelopmentConfig
