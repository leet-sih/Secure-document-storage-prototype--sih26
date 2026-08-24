"""
conftest.py — shared pytest fixtures.

FIXTURES TO PROVIDE (implement during Phase 1):
    app        Flask app built with a TESTING config (separate test DB, KMS=env stub).
    client     app.test_client() for HTTP-level tests.
    db_session Fresh schema per test (create_all / drop_all or transaction rollback).
    users      A dict of seeded users keyed by role for RBAC tests.
    auth_headers(role) -> {"Authorization": "Bearer <token>"} helper.

Keep tests hermetic: no real Vault, no shared state between tests. Use the env KMS stub
and a disposable Postgres (or SQLite where Postgres-specific features aren't exercised —
note: tsvector/advisory locks/ARRAY need real Postgres).
"""

import pytest


@pytest.fixture
def app():
    """TODO: return create_app(TestingConfig) with app context + schema setup/teardown."""
    raise NotImplementedError


@pytest.fixture
def client(app):
    return app.test_client()
