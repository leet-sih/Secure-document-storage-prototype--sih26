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

DEMO_EMAIL = "officer@ncrb.gov.in"
DEMO_PASSWORD = "ChangeMe!2345"


def run() -> None:
    dept = Department.query.filter_by(name="Cybercrime Unit").one_or_none()
    if dept is None:
        dept = Department(name="Cybercrime Unit", dept_type="POLICE")
        db.session.add(dept)
        db.session.flush()

    user = User.query.filter_by(email=DEMO_EMAIL).one_or_none()
    if user is None:
        db.session.add(
            User(
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                full_name="Demo Case Officer",
                employee_id="NCRB-DEMO-001",
                role="CASE_OFFICER",
                department_id=dept.id,
                is_first_login=True,
            )
        )
    db.session.commit()
    print(f"Demo login: {DEMO_EMAIL} / {DEMO_PASSWORD} (TOTP setup required on first login)")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        run()
