"""Tests for GET /api/v1/cases and GET /api/v1/cases/{id} access control."""
import json
import pytest
from app.models.audit_event import AuditEvent
from app.services import case_service


@pytest.fixture()
def created_case(client, auth_headers):
    res = client.post(
        "/api/v1/cases",
        data=json.dumps({"case_number": "ACC-001", "title": "Access Test Case"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    assert res.status_code == 201
    return res.get_json()


def test_member_can_access_detail(client, auth_headers, created_case):
    res = client.get(
        f"/api/v1/cases/{created_case['id']}",
        headers=auth_headers("officer"),
    )
    assert res.status_code == 200
    assert res.get_json()["id"] == created_case["id"]


def test_non_member_gets_404_not_403(client, auth_headers, created_case):
    res = client.get(
        f"/api/v1/cases/{created_case['id']}",
        headers=auth_headers("investigator"),
    )
    assert res.status_code == 404


def test_super_admin_sees_all_cases(client, auth_headers, created_case):
    res = client.get(
        f"/api/v1/cases/{created_case['id']}",
        headers=auth_headers("admin"),
    )
    assert res.status_code == 200


def test_case_accessed_audit_recorded(client, db, auth_headers, created_case, users):
    client.get(
        f"/api/v1/cases/{created_case['id']}",
        headers=auth_headers("officer"),
    )
    event = AuditEvent.query.filter_by(
        event_type="CASE_ACCESSED", case_id=created_case["id"]
    ).first()
    assert event is not None


def test_archived_case_non_admin_gets_404(client, db, auth_headers, created_case, users):
    # Add investigator first so they have access pre-archival
    client.post(
        f"/api/v1/cases/{created_case['id']}/members",
        data=json.dumps({"user_id": str(users["investigator"].id), "role": "INVESTIGATOR"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )

    # Transition to CLOSED then ARCHIVED (requires admin)
    client.patch(
        f"/api/v1/cases/{created_case['id']}",
        data=json.dumps({"status": "UNDER_INVESTIGATION"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    client.patch(
        f"/api/v1/cases/{created_case['id']}",
        data=json.dumps({"status": "CLOSED"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    client.patch(
        f"/api/v1/cases/{created_case['id']}",
        data=json.dumps({"status": "ARCHIVED"}),
        content_type="application/json",
        headers=auth_headers("admin"),
    )

    # Investigator (former member) should now get 404
    res = client.get(
        f"/api/v1/cases/{created_case['id']}",
        headers=auth_headers("investigator"),
    )
    assert res.status_code == 404


def test_auditor_can_access_archived(client, db, auth_headers, created_case, users):
    # Transition to ARCHIVED
    client.patch(
        f"/api/v1/cases/{created_case['id']}",
        data=json.dumps({"status": "UNDER_INVESTIGATION"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    client.patch(
        f"/api/v1/cases/{created_case['id']}",
        data=json.dumps({"status": "CLOSED"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    client.patch(
        f"/api/v1/cases/{created_case['id']}",
        data=json.dumps({"status": "ARCHIVED"}),
        content_type="application/json",
        headers=auth_headers("admin"),
    )
    res = client.get(
        f"/api/v1/cases/{created_case['id']}",
        headers=auth_headers("auditor"),
    )
    assert res.status_code == 200


def test_get_accessible_case_ids_returns_memberships(db, users, seed_depts):
    from app.services.case_service import create_case, get_accessible_case_ids
    case = create_case(
        {"case_number": "AID-001", "title": "Accessible ID Test"},
        users["officer"],
    )
    ids = get_accessible_case_ids(str(users["officer"].id))
    assert case["case_number"] == "AID-001"
    assert str(case["id"]) in ids


def test_super_admin_get_accessible_returns_all(db, users, seed_depts):
    from app.services.case_service import create_case, get_accessible_case_ids
    create_case({"case_number": "ALL-001", "title": "All Cases Test"}, users["officer"])
    ids_admin = get_accessible_case_ids(str(users["admin"].id))
    ids_officer = get_accessible_case_ids(str(users["officer"].id))
    assert len(ids_admin) >= len(ids_officer)
