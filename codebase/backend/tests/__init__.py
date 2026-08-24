"""
tests/ — pytest + pytest-flask suite.

Layout (one subpackage per feature, mirroring feature_plans/*_plan.md "Testing Plan"):
    conftest.py           shared fixtures: app, client, db, seeded users, auth headers
    auth/                 login, MFA, tokens
    documents/            upload, download (incl. tamper tests), crypto
    cases/                access control, members, status transitions
    audit/                chain integrity + verify
    signatures/ sharing/ search/

PRIORITY: the security-critical tests are non-negotiable — crypto round-trip, download
tamper detection, audit chain tamper detection, and case-scope 404 (not 403).

Run: pytest    |    Coverage: pytest --cov=app
"""
