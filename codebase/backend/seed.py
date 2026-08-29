"""
seed.py — idempotent demo/dev data. Run AFTER `flask db upgrade`.

USAGE (from codebase/backend, with .env loaded):
    python seed.py
"""

from app import create_app
from app.core.security import hash_password
from app.extensions import db
from app.models.department import Department
from app.models.user import User

# The ONLY seeded account is a single SUPER_ADMIN (the bootstrap admin).
# Every other user is provisioned by this admin via the "Create User" flow.
ADMIN_EMAIL = "admin@ncrb.gov.in"
ADMIN_PASSWORD = "ChangeMe!2345"

# Departments are seeded because the create-user form needs one to assign, and there
# is no department-management UI yet.
DEPARTMENTS = [
    ("Cybercrime Unit", "POLICE"),
    ("Sessions Court", "COURT"),
    ("Forensic Lab", "FORENSIC"),
]


def _ensure_department(name: str, dept_type: str) -> Department:
    dept = Department.query.filter_by(name=name).one_or_none()
    if dept is None:
        dept = Department(name=name, dept_type=dept_type)
        db.session.add(dept)
        db.session.flush()
    return dept


def _ensure_user(email: str, password: str, full_name: str, employee_id: str, role: str, dept: Department) -> None:
    if User.query.filter_by(email=email).one_or_none() is None:
        db.session.add(
            User(
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                employee_id=employee_id,
                role=role,
                department_id=dept.id,
                is_first_login=True,
            )
        )


def run() -> None:
    depts = {name: _ensure_department(name, dtype) for name, dtype in DEPARTMENTS}

    _ensure_user(
        ADMIN_EMAIL, ADMIN_PASSWORD, "System Administrator", "NCRB-ADMIN-001",
        "SUPER_ADMIN", depts["Cybercrime Unit"],
    )
    db.session.commit()
    print(f"Admin login: {ADMIN_EMAIL} / {ADMIN_PASSWORD} (SUPER_ADMIN)")
    print("Requires password change + TOTP setup on first login.")
    print("All other users are created by the admin via User Admin -> Create User.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        run()
