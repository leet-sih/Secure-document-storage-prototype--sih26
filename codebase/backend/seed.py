"""
seed.py — demo data seeder with idempotency guard.

USAGE:
    python seed.py          # seeds only if not already seeded
    python seed.py --wipe   # wipes ALL rows (keeps schema) then re-seeds

Last seed timestamp is stored in .seed_state next to this file.
Ask Claude "when was the last seed?" to read it.

Run AFTER `flask db upgrade`.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from app import create_app
from app.core.security import hash_password
from app.extensions import db
from app.models.department import Department
from app.models.user import User

STATE_FILE = Path(__file__).parent / ".seed_state"

# ── Departments ───────────────────────────────────────────────────────────────

DEPARTMENTS = [
    ("Cybercrime Unit",         "POLICE"),
    ("Narcotics Control Bureau","POLICE"),
    ("Delhi District Court",    "COURT"),
    ("Central Forensic Lab",    "FORENSIC"),
    ("Legal Affairs Division",  "LEGAL"),
]

# ── Users ─────────────────────────────────────────────────────────────────────
# (email, password, full_name, employee_id, role, dept_name)
# Passwords are intentionally varied — simple ones for quick demo login.
# All accounts start with is_first_login=True (password change + TOTP on first login).

USERS = [
    # SUPER_ADMIN
    ("admin@ncrb.gov.in",           "Admin@1234",   "System Administrator",   "NCRB-ADMIN-001",  "SUPER_ADMIN",   "Cybercrime Unit"),

    # CASE_OFFICERs
    ("officer.sharma@police.in",    "officer123",   "SI Ramesh Sharma",       "DL-CO-001",       "CASE_OFFICER",  "Cybercrime Unit"),
    ("officer.gupta@police.in",     "Gupta456",     "SI Priya Gupta",         "NCB-CO-002",      "CASE_OFFICER",  "Narcotics Control Bureau"),

    # INVESTIGATORs
    ("inv.patel@police.in",         "patel2024",    "ASI Kiran Patel",        "DL-INV-001",      "INVESTIGATOR",  "Cybercrime Unit"),
    ("inv.singh@police.in",         "singh123",     "HC Manpreet Singh",      "NCB-INV-002",     "INVESTIGATOR",  "Narcotics Control Bureau"),
    ("inv.rao@forensics.in",        "rao2024",      "Dr. Lakshmi Rao",        "CFL-INV-003",     "INVESTIGATOR",  "Central Forensic Lab"),

    # PROSECUTOR
    ("prosecutor@court.in",         "prosec123",    "Adv. Sunita Menon",      "DDC-PRO-001",     "PROSECUTOR",    "Delhi District Court"),

    # AUDITOR
    ("auditor@ncrb.gov.in",         "audit2024",    "Audit Officer Verma",    "NCRB-AUD-001",    "AUDITOR",       "Legal Affairs Division"),

    # VIEWER
    ("viewer@ncrb.gov.in",          "view1234",     "Observer Kapoor",        "NCRB-VIEW-001",   "VIEWER",        "Legal Affairs Division"),
]


# ── Wipe ──────────────────────────────────────────────────────────────────────

def _wipe() -> None:
    from sqlalchemy import text
    # Order matters for FK constraints
    tables = ["audit_events", "case_members", "cases", "users", "departments"]
    for t in tables:
        try:
            db.session.execute(text(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE"))
        except Exception:
            db.session.rollback()
    db.session.commit()
    print("  Wiped: audit_events, case_members, cases, users, departments")


# ── Seed ──────────────────────────────────────────────────────────────────────

def _seed() -> None:
    # Departments
    dept_map: dict[str, Department] = {}
    for name, dtype in DEPARTMENTS:
        dept = Department.query.filter_by(name=name).one_or_none()
        if dept is None:
            dept = Department(name=name, dept_type=dtype)
            db.session.add(dept)
            db.session.flush()
        dept_map[name] = dept

    # Users
    created = []
    for email, password, full_name, emp_id, role, dept_name in USERS:
        if User.query.filter_by(email=email).one_or_none() is None:
            db.session.add(User(
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                employee_id=emp_id,
                role=role,
                department_id=dept_map[dept_name].id,
                is_first_login=True,
            ))
            created.append((role, email, password, full_name))

    db.session.commit()

    # Print summary
    print()
    print(f"  {'ROLE':<17} {'EMAIL':<31} PASSWORD")
    print("  " + "-" * 65)
    for role, email, password, _ in created:
        print(f"  {role:<17} {email:<31} {password}")
    print()
    print("  All accounts: is_first_login=True => password change + TOTP setup on first login.")
    print()


# ── State file ────────────────────────────────────────────────────────────────

def _read_state() -> dict | None:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return None
    return None


def _write_state(wipe: bool) -> None:
    now = datetime.now(timezone.utc)
    STATE_FILE.write_text(json.dumps({
        "seeded_at": now.isoformat(),
        "seeded_at_local": now.astimezone().strftime("%d %b %Y %H:%M:%S %Z"),
        "wipe": wipe,
        "users": len(USERS),
        "departments": len(DEPARTMENTS),
    }, indent=2))


# ── Entry point ───────────────────────────────────────────────────────────────

def run(wipe: bool = False) -> None:
    state = _read_state()

    if not wipe and state:
        print(f"  Already seeded on {state['seeded_at_local']}. Use --wipe to re-seed.")
        return

    if wipe:
        print("  Wiping existing data…")
        _wipe()

    print("  Seeding…")
    _seed()
    _write_state(wipe)
    print(f"  Done. Seed state saved to {STATE_FILE.name}")


if __name__ == "__main__":
    wipe = "--wipe" in sys.argv
    app = create_app()
    with app.app_context():
        run(wipe=wipe)
