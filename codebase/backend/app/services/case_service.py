"""
case_service.py — case CRUD + the case-scoped access checks that the whole system relies on.

ACCESS HELPERS (used by documents/search/audit too):
    user_has_access(user_id, case_id) -> bool
    get_case_for_user(case_id, user_id) -> Case | aborts 404   (404, NOT 403, for non-members)
    get_user_role_in_case(user_id, case_id) -> str | None
    get_accessible_case_ids(user_id) -> list[str]              (SUPER_ADMIN -> all)

CRUD:
    create_case(data, creator) -> Case         (auto-adds creator as CASE_OFFICER member)
    list_cases(user, filters, page, limit) -> dict
    update_case(case_id, data, actor) -> Case  (enforces valid status transitions)
    add_member(case_id, user_id, role, actor) -> CaseMember
    remove_member(case_id, user_id, actor) -> None
        Guards: cannot remove the last active CASE_OFFICER; cannot remove self.

STORES: rows in cases + case_members.
Full rules: ../../feature_plans/case_management_plan.md
"""

import uuid
from datetime import datetime, timezone

from app.core.audit_events import AuditEventType
from app.core.errors import APIError
from app.extensions import db
from app.models.case import Case
from app.models.case_member import CaseMember
from app.models.department import Department
from app.models.user import User
from app.services.audit_service import audit_service

# Valid status transitions
_TRANSITIONS = {
    "OPEN": {"UNDER_INVESTIGATION"},
    "UNDER_INVESTIGATION": {"OPEN", "CLOSED"},
    "CLOSED": {"ARCHIVED"},
    "ARCHIVED": set(),
}


# ── Access helpers ─────────────────────────────────────────────────────────────

def user_has_access(user_id: str, case_id: str) -> bool:
    """True if user is SUPER_ADMIN or an active case member."""
    user = db.session.get(User, uuid.UUID(str(user_id)))
    if not user:
        return False
    if user.role == "SUPER_ADMIN":
        return True
    member = (
        CaseMember.query
        .filter_by(case_id=uuid.UUID(str(case_id)), user_id=uuid.UUID(str(user_id)), is_active=True)
        .first()
    )
    return member is not None


def get_case_for_user(case_id, user_id: str) -> Case:
    """Load Case or raise 404 (never 403) for non-members."""
    case = db.session.get(Case, uuid.UUID(str(case_id)))
    if not case:
        raise APIError(404, "NOT_FOUND", "Case not found")
    if not user_has_access(user_id, case_id):
        raise APIError(404, "NOT_FOUND", "Case not found")
    return case


def get_user_role_in_case(user_id: str, case_id: str) -> str | None:
    """Return the user's role within this case, or None if not a member."""
    member = (
        CaseMember.query
        .filter_by(case_id=uuid.UUID(str(case_id)), user_id=uuid.UUID(str(user_id)), is_active=True)
        .first()
    )
    return member.role if member else None


def get_accessible_case_ids(user_id: str) -> list[str]:
    """SUPER_ADMIN gets all case IDs; others get only their active memberships."""
    user = db.session.get(User, uuid.UUID(str(user_id)))
    if not user:
        return []
    if user.role == "SUPER_ADMIN":
        return [str(row.id) for row in Case.query.with_entities(Case.id).all()]
    rows = (
        CaseMember.query
        .filter_by(user_id=uuid.UUID(str(user_id)), is_active=True)
        .with_entities(CaseMember.case_id)
        .all()
    )
    return [str(r.case_id) for r in rows]


# ── Internal helpers ───────────────────────────────────────────────────────────

def _is_case_officer_member(case_id, user_id) -> bool:
    """True if user is an active CASE_OFFICER on this case."""
    m = CaseMember.query.filter_by(
        case_id=uuid.UUID(str(case_id)), user_id=uuid.UUID(str(user_id)),
        role="CASE_OFFICER", is_active=True
    ).first()
    return m is not None


def assert_case_writable(case: Case) -> None:
    """Raise 409 if the case is CLOSED or ARCHIVED (documents/updates forbidden)."""
    if case.status in ("CLOSED", "ARCHIVED"):
        raise APIError(409, "CASE_NOT_WRITABLE", "Case is closed or archived")


def _build_detail(case: Case) -> dict:
    """Assemble the full CaseDetail dict from ORM rows (no schema import needed here)."""
    creator = db.session.get(User, case.created_by)
    lead = db.session.get(User, case.lead_officer_id) if case.lead_officer_id else None
    dept = db.session.get(Department, case.department_id)

    members_q = (
        CaseMember.query
        .filter_by(case_id=case.id, is_active=True)
        .all()
    )
    members = []
    for m in members_q:
        mu = db.session.get(User, m.user_id)
        if not mu:
            continue
        mu_dept = db.session.get(Department, mu.department_id)
        members.append({
            "user_id": m.user_id,
            "email": mu.email,
            "full_name": mu.full_name,
            "role": m.role,
            "department": mu_dept.name if mu_dept else None,
            "added_at": m.added_at,
        })

    # Document summary — soft-fail if document table doesn't exist yet
    doc_summary: dict = {}
    try:
        from app.models.document import Document
        docs = Document.query.filter_by(case_id=case.id).all()
        doc_summary = {
            "total": len(docs),
            "by_status": {},
        }
        for d in docs:
            doc_summary["by_status"][d.status] = doc_summary["by_status"].get(d.status, 0) + 1
    except Exception:
        db.session.rollback()

    def _user_brief(u: User | None):
        if u is None:
            return None
        return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role}

    return {
        "id": case.id,
        "case_number": case.case_number,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "priority": case.priority,
        "category": case.category,
        "created_by": _user_brief(creator),
        "lead_officer": _user_brief(lead),
        "department": {"id": dept.id, "name": dept.name} if dept else None,
        "members": members,
        "document_summary": doc_summary,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "closed_at": case.closed_at,
        "archived_at": case.archived_at,
    }


# ── CRUD ───────────────────────────────────────────────────────────────────────

def create_case(data: dict, creator: User) -> dict:
    """Create a case and auto-add the creator as CASE_OFFICER."""
    existing = Case.query.filter_by(case_number=data["case_number"]).first()
    if existing:
        raise APIError(409, "CONFLICT", "Case number already exists")

    case = Case(
        case_number=data["case_number"],
        title=data["title"],
        description=data.get("description"),
        priority=data.get("priority", "NORMAL"),
        category=data.get("category"),
        created_by=creator.id,
        lead_officer_id=creator.id,
        department_id=creator.department_id,
    )
    db.session.add(case)
    db.session.flush()  # get case.id before adding member

    member = CaseMember(
        case_id=case.id,
        user_id=creator.id,
        role="CASE_OFFICER",
        added_by=creator.id,
    )
    db.session.add(member)
    db.session.commit()

    audit_service.record(
        AuditEventType.CASE_CREATED.value,
        actor_user_id=creator.id,
        target_type="case",
        target_id=case.id,
        case_id=case.id,
        metadata={"case_number": case.case_number, "title": case.title},
    )
    return _build_detail(case)


def list_cases(user: User, filters: dict, page: int, limit: int) -> dict:
    """Paginated case list filtered to user's accessible cases."""
    q = Case.query

    if user.role != "SUPER_ADMIN":
        accessible_ids = get_accessible_case_ids(str(user.id))
        if not accessible_ids:
            return {"cases": [], "total": 0, "page": page, "limit": limit}
        q = q.filter(Case.id.in_([uuid.UUID(i) for i in accessible_ids]))

    if filters.get("status"):
        q = q.filter(Case.status == filters["status"])
    if filters.get("priority"):
        q = q.filter(Case.priority == filters["priority"])
    if filters.get("search"):
        term = f"%{filters['search']}%"
        q = q.filter(
            db.or_(Case.title.ilike(term), Case.case_number.ilike(term))
        )

    total = q.count()
    cases = q.order_by(Case.updated_at.desc()).offset((page - 1) * limit).limit(limit).all()

    items = []
    for c in cases:
        doc_count = 0
        try:
            from app.models.document import Document
            doc_count = Document.query.filter_by(case_id=c.id).count()
        except Exception:
            db.session.rollback()

        member_count = CaseMember.query.filter_by(case_id=c.id, is_active=True).count()
        items.append({
            "id": c.id,
            "case_number": c.case_number,
            "title": c.title,
            "status": c.status,
            "priority": c.priority,
            "category": c.category,
            "document_count": doc_count,
            "member_count": member_count,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        })

    return {"cases": items, "total": total, "page": page, "limit": limit}


def update_case(case_id, data: dict, actor: User) -> dict:
    """Update mutable case fields; enforce status transition rules."""
    case = get_case_for_user(case_id, str(actor.id))

    # Only SUPER_ADMIN and CASE_OFFICER members can update
    if actor.role != "SUPER_ADMIN" and not _is_case_officer_member(case_id, str(actor.id)):
        raise APIError(403, "FORBIDDEN", "Insufficient permissions to update this case")

    new_status = data.get("status")
    if new_status and new_status != case.status:
        allowed = _TRANSITIONS.get(case.status, set())
        if new_status not in allowed:
            raise APIError(409, "INVALID_TRANSITION",
                           f"Cannot transition from {case.status} to {new_status}")
        case.status = new_status
        if new_status == "CLOSED":
            case.closed_at = datetime.now(timezone.utc)
            audit_service.record(
                AuditEventType.CASE_CLOSED.value,
                actor_user_id=actor.id,
                target_type="case",
                target_id=case.id,
                case_id=case.id,
            )
        elif new_status == "ARCHIVED":
            case.archived_at = datetime.now(timezone.utc)

    for field in ("title", "description", "priority", "category"):
        if field in data:
            setattr(case, field, data[field])

    case.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    audit_service.record(
        AuditEventType.CASE_UPDATED.value,
        actor_user_id=actor.id,
        target_type="case",
        target_id=case.id,
        case_id=case.id,
        metadata={k: v for k, v in data.items() if k != "description"},
    )
    return _build_detail(case)


def add_member(case_id, user_id, role: str, actor: User) -> dict:
    """Add a user to a case with the given role."""
    case = get_case_for_user(case_id, str(actor.id))

    if actor.role != "SUPER_ADMIN" and not _is_case_officer_member(case_id, str(actor.id)):
        raise APIError(403, "FORBIDDEN", "Only CASE_OFFICERs can manage members")

    target = db.session.get(User, uuid.UUID(str(user_id)))
    if not target or not target.is_active:
        raise APIError(404, "NOT_FOUND", "User not found")

    existing = CaseMember.query.filter_by(
        case_id=uuid.UUID(str(case_id)), user_id=uuid.UUID(str(user_id))
    ).first()
    if existing and existing.is_active:
        raise APIError(409, "CONFLICT", "User is already a member of this case")

    if existing:
        # Reactivate soft-removed member
        existing.is_active = True
        existing.role = role
        existing.added_by = actor.id
        existing.added_at = datetime.now(timezone.utc)
        existing.removed_at = None
        member = existing
    else:
        member = CaseMember(
            case_id=uuid.UUID(str(case_id)),
            user_id=uuid.UUID(str(user_id)),
            role=role,
            added_by=actor.id,
        )
        db.session.add(member)

    db.session.commit()

    audit_service.record(
        AuditEventType.CASE_MEMBER_ADDED.value,
        actor_user_id=actor.id,
        target_type="user",
        target_id=user_id,
        case_id=case_id,
        metadata={"role": role},
    )

    mu_dept = db.session.get(Department, target.department_id)
    return {
        "user_id": member.user_id,
        "email": target.email,
        "full_name": target.full_name,
        "role": member.role,
        "department": mu_dept.name if mu_dept else None,
        "added_at": member.added_at,
    }


def remove_member(case_id, user_id, actor: User) -> None:
    """Soft-remove a member. Guards: cannot remove last CASE_OFFICER; cannot remove self."""
    case = get_case_for_user(case_id, str(actor.id))

    if actor.role != "SUPER_ADMIN" and not _is_case_officer_member(case_id, str(actor.id)):
        raise APIError(403, "FORBIDDEN", "Only CASE_OFFICERs can manage members")

    if str(user_id) == str(actor.id):
        raise APIError(409, "CONFLICT", "Cannot remove yourself from a case")

    member = CaseMember.query.filter_by(
        case_id=uuid.UUID(str(case_id)), user_id=uuid.UUID(str(user_id)), is_active=True
    ).first()
    if not member:
        raise APIError(404, "NOT_FOUND", "Member not found")

    if member.role == "CASE_OFFICER":
        active_officers = CaseMember.query.filter_by(
            case_id=uuid.UUID(str(case_id)), role="CASE_OFFICER", is_active=True
        ).count()
        if active_officers <= 1:
            raise APIError(409, "CONFLICT", "Cannot remove the last active CASE_OFFICER")

    member.is_active = False
    member.removed_at = datetime.now(timezone.utc)
    db.session.commit()

    audit_service.record(
        AuditEventType.CASE_MEMBER_REMOVED.value,
        actor_user_id=actor.id,
        target_type="user",
        target_id=user_id,
        case_id=case_id,
    )


def transfer_case(case_id, data: dict, actor: User) -> dict:
    """Transfer case to a new department and lead officer (uses CASE_UPDATED event)."""
    case = get_case_for_user(case_id, str(actor.id))

    if case.status in ("CLOSED", "ARCHIVED"):
        raise APIError(409, "CASE_NOT_WRITABLE", "Cannot transfer a closed or archived case")

    if actor.role != "SUPER_ADMIN" and not _is_case_officer_member(case_id, str(actor.id)):
        raise APIError(403, "FORBIDDEN", "Insufficient permissions to transfer this case")

    new_dept_id = uuid.UUID(str(data["to_department_id"]))
    new_lead_id = uuid.UUID(str(data["new_lead_officer_id"]))

    new_dept = db.session.get(Department, new_dept_id)
    if not new_dept:
        raise APIError(404, "NOT_FOUND", "Target department not found")

    new_lead = db.session.get(User, new_lead_id)
    if not new_lead or not new_lead.is_active:
        raise APIError(404, "NOT_FOUND", "New lead officer not found")

    old_dept_id = case.department_id
    case.department_id = new_dept_id
    case.lead_officer_id = new_lead_id
    case.updated_at = datetime.now(timezone.utc)

    # Ensure new lead is a CASE_OFFICER member
    existing = CaseMember.query.filter_by(case_id=case.id, user_id=new_lead_id).first()
    if existing and existing.is_active:
        existing.role = "CASE_OFFICER"
    elif existing:
        existing.is_active = True
        existing.role = "CASE_OFFICER"
        existing.added_by = actor.id
        existing.added_at = datetime.now(timezone.utc)
        existing.removed_at = None
    else:
        db.session.add(CaseMember(
            case_id=case.id, user_id=new_lead_id, role="CASE_OFFICER", added_by=actor.id
        ))

    db.session.commit()

    audit_service.record(
        AuditEventType.CASE_UPDATED.value,
        actor_user_id=actor.id,
        target_type="case",
        target_id=case.id,
        case_id=case.id,
        metadata={
            "action": "transfer",
            "from_department_id": str(old_dept_id),
            "to_department_id": str(new_dept_id),
            "new_lead_officer_id": str(new_lead_id),
        },
    )
    return _build_detail(case)


def get_case_timeline(case_id, user: User) -> list[dict]:
    """Return the 200 most recent audit events for this case, newest first."""
    get_case_for_user(case_id, str(user.id))  # access check

    from app.models.audit_event import AuditEvent
    events = (
        AuditEvent.query
        .filter_by(case_id=str(case_id))
        .order_by(AuditEvent.id.desc())
        .limit(200)
        .all()
    )

    result = []
    for ev in events:
        actor = db.session.get(User, ev.actor_user_id) if ev.actor_user_id else None
        result.append({
            "id": ev.id,
            "event_type": ev.event_type,
            "actor": {
                "id": actor.id,
                "email": actor.email,
                "full_name": actor.full_name,
                "role": actor.role,
            } if actor else None,
            "target_type": ev.target_type,
            "metadata": ev.event_metadata or {},
            "created_at": ev.created_at,
        })
    return result


def get_transfer_options() -> dict:
    """Return all departments and all active CASE_OFFICERs/INVESTIGATORs for transfer form."""
    departments = Department.query.order_by(Department.name.asc()).all()
    officers = (
        User.query
        .filter(User.is_active == True, User.role.in_(["CASE_OFFICER", "INVESTIGATOR"]))
        .order_by(User.full_name.asc())
        .all()
    )
    return {
        "departments": [{"id": d.id, "name": d.name} for d in departments],
        "officers": [
            {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "department_id": u.department_id,
            }
            for u in officers
        ],
    }
