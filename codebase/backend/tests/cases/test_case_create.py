"""Tests for POST /api/v1/cases — case creation."""
import json
import pytest
from app.models.case import Case
from app.models.case_member import CaseMember
from app.models.audit_event import AuditEvent


@pytest.fixture()
def case_payload():
    return {
        "case_number": "CR-2026-0001",
        "title": "Test Investigation",
        "priority": "HIGH",
        "category": "CYBERCRIME",
    }


def test_case_officer_can_create(client, auth_headers, case_payload):
    res = client.post(
        "/api/v1/cases",
        data=json.dumps(case_payload),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["case_number"] == "CR-2026-0001"
    assert body["status"] == "OPEN"


def test_super_admin_can_create(client, auth_headers, case_payload):
    payload = {**case_payload, "case_number": "CR-2026-0002"}
    res = client.post(
        "/api/v1/cases",
        data=json.dumps(payload),
        content_type="application/json",
        headers=auth_headers("admin"),
    )
    assert res.status_code == 201


def test_investigator_cannot_create(client, auth_headers, case_payload):
    payload = {**case_payload, "case_number": "CR-2026-0003"}
    res = client.post(
        "/api/v1/cases",
        data=json.dumps(payload),
        content_type="application/json",
        headers=auth_headers("investigator"),
    )
    assert res.status_code == 403


def test_duplicate_case_number_returns_409(client, auth_headers, case_payload):
    client.post(
        "/api/v1/cases",
        data=json.dumps(case_payload),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    res = client.post(
        "/api/v1/cases",
        data=json.dumps(case_payload),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "CONFLICT"


def test_creator_auto_added_as_case_officer(client, db, auth_headers, users, case_payload):
    res = client.post(
        "/api/v1/cases",
        data=json.dumps(case_payload),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    assert res.status_code == 201
    case_id = res.get_json()["id"]
    member = CaseMember.query.filter_by(
        case_id=case_id, user_id=users["officer"].id, is_active=True
    ).first()
    assert member is not None
    assert member.role == "CASE_OFFICER"


def test_lead_officer_id_equals_created_by(client, auth_headers, case_payload, users):
    res = client.post(
        "/api/v1/cases",
        data=json.dumps(case_payload),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    body = res.get_json()
    assert body["lead_officer"]["id"] == str(users["officer"].id)
    assert body["created_by"]["id"] == str(users["officer"].id)


def test_create_records_audit_event(client, db, auth_headers, users, case_payload):
    res = client.post(
        "/api/v1/cases",
        data=json.dumps(case_payload),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    case_id = res.get_json()["id"]
    event = AuditEvent.query.filter_by(
        event_type="CASE_CREATED", case_id=case_id
    ).first()
    assert event is not None
    assert str(event.actor_user_id) == str(users["officer"].id)
