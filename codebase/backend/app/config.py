"""
config.py — centralized configuration, loaded from environment variables.
PRAMAAN — Secure Evidence Vault (leet / SIH26)

WHAT THIS FILE DOES:
    Defines Config classes read by create_app(). Every value comes from an env var
    (see ../.env.example). NEVER hardcode secrets here.

PROTOTYPE NOTE:
    Kept intentionally small. No Redis / MinIO / Vault / Celery config — the prototype uses
    a two-server topology (PostgreSQL on Server A, chunk store on Server B) with a local file
    KMS. Those get upgraded when we scale up (see docs/ARCHITECTURE.md "Future / production").

KEY SEPARATION (important):
    SECRET_KEY     — Flask cookie/session signing ONLY.
    KMS_WRAPPING_KEY — wraps document master keys in the local file KMS. NEVER the same value
                      as SECRET_KEY. Two separate jobs, two separate secrets.
    JWT_SECRET     — signs JWT access tokens. Also separate.

EXPORTS:
    Config, DevelopmentConfig, ProductionConfig, get_config()
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parents[1]
_codebase_dir = Path(__file__).resolve().parents[2]
load_dotenv(_backend_dir / ".env")
load_dotenv(_codebase_dir / ".env")


class Config:
    # ── Flask ──
    SECRET_KEY = os.environ["SECRET_KEY"]       # cookie/session signing ONLY
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # ── Database ──
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT (prototype: access token only, no refresh flow) ──
    JWT_SECRET_KEY = os.environ["JWT_SECRET"]
    JWT_ACCESS_TTL_SECONDS = int(os.environ.get("JWT_ACCESS_TTL_SECONDS", 28800))  # 8h for demo

    # ── MFA / lockout / step-up ──
    MFA_ISSUER = os.environ.get("MFA_ISSUER", "PRAMAAN")
    MFA_STEP_UP_MINUTES = int(os.environ.get("MFA_STEP_UP_MINUTES", 15))  # step-up window
    ACCOUNT_LOCKOUT_THRESHOLD = int(os.environ.get("ACCOUNT_LOCKOUT_THRESHOLD", 5))
    ACCOUNT_LOCKOUT_MINUTES = int(os.environ.get("ACCOUNT_LOCKOUT_MINUTES", 15))

    # ── Chunk store (two-server topology) ──
    # CHUNK_STORE_BACKEND selects the driver: "local" (dev) or "sftp" (Server B demo).
    # document_service never changes — dispatch is internal to storage/chunk_store.py.
    CHUNK_STORE_BACKEND = os.environ.get("CHUNK_STORE_BACKEND", "local")
    CHUNK_STORE_HOST = os.environ.get("CHUNK_STORE_HOST", "")    # Server B hostname (sftp)
    CHUNK_STORAGE_DIR = os.environ.get("CHUNK_STORAGE_DIR", "./data/chunks")
    CHUNK_STORE_USER = os.environ.get("CHUNK_STORE_USER", "")
    CHUNK_STORE_KEYFILE = os.environ.get("CHUNK_STORE_KEYFILE", "")  # SSH key, no passwords

    # ── KMS (local file store — prototype; Vault in production) ──
    KMS_DIR = os.environ.get("KMS_DIR", "./data/keys")
    KMS_WRAPPING_KEY = os.environ["KMS_WRAPPING_KEY"]   # wraps master keys; NOT SECRET_KEY

    # ── Uploads ──
    MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", 500))   # 500 MB prototype limit
    CHUNK_SIZE_BYTES = int(os.environ.get("CHUNK_SIZE_BYTES", 1048576))  # 1 MB
    MAX_CONTENT_LENGTH = MAX_FILE_SIZE_MB * 1024 * 1024

    # ── Email OTP (Gmail SMTP — share link recipient verification) ──
    GMAIL_USER = os.environ.get("GMAIL_USER", "")
    GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

    # ── CORS (allow the Vite dev server) ──
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

    # ── Rate limiting (in-memory for the prototype; Redis-backed in production) ──
    RATELIMIT_STORAGE_URI = "memory://"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


def get_config():
    env = os.environ.get("ENVIRONMENT", "development")
    return ProductionConfig if env == "production" else DevelopmentConfig
