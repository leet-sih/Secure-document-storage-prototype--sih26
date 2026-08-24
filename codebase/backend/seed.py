"""
seed.py — idempotent demo/dev data seeding. Run AFTER `flask db upgrade`.

WHAT IT CREATES (re-runnable without duplicating — check-then-insert):
    - Departments: Cybercrime Unit (POLICE), Sessions Court (COURT), Forensic Lab (FORENSIC)
    - One SUPER_ADMIN (credentials printed once to stdout)
    - One user per role (CASE_OFFICER, INVESTIGATOR, PROSECUTOR, AUDITOR, VIEWER)
    - 2 sample cases with members assigned
    - A few sample documents per case (so search/audit/signatures have data on demo day)
    - The genesis AuditEvent (SYSTEM_INIT)

WHY: judges see a populated system instantly; the pre-demo smoke test (docs/EDGE_CASES.md)
depends on this data existing.

USAGE: python seed.py
"""

from app import create_app
from app.extensions import db  # noqa: F401


def run() -> None:
    """Idempotently create demo data. TODO: implement per the list above."""
    raise NotImplementedError


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        run()
