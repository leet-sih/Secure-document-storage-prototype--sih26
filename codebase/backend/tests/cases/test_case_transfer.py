"""Tests for POST /api/v1/cases/{id}/transfer and GET /api/v1/cases/{id}/transfer-options."""
import json
import pytest
from app.models.audit_event import AuditEvent
from app.models.case_member import CaseMember


@pytest.fixture()
def case(client, auth_headers):
    res = client.post(
        "/api/v1/cases",
        data=json.dumps({"case_number": "TRF-001", "title": "Transfer Test"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    return res.get_json()


def _transfer(client, headers, case_id, to_dept_id, new_lead_id):
    return client.post(
        f"/api/v1/cases/{case_id}/transfer",
        data=json.dumps({
            "to_department_id": str(to_dept_id),
            "new_lead_officer_id": str(new_lead_id),
        }),
        content_type="application/json",
        headers=headers,
    )


# ── Happy path ─────────────────────────────────────────────────────────────────

def test_admin_can_transfer(client, auth_headers, users, seed_depts, case):
    res = _transfer(
        client, auth_headers("admin"),
        case["id"],
        seed_depts["forensic"].id,
        users["officer2"].id,
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["lead_officer"]["id"] == str(users["officer2"].id)
    assert body["department"]["id"] == str(seed_depts["forensic"].id)


def test_lead_case_officer_can_transfer(client, auth_headers, users, seed_depts, case):
    # officer is the lead; they should be able to transfer
    res = _transfer(
        client, auth_headers("officer"),
        case["id"],
        seed_depts["forensic"].id,
        users["officer2"].id,
    )
    assert res.status_code == 200


def test_new_lead_added_as_case_officer_member(client, db, auth_headers, users, seed_depts, case):
    _transfer(
        client, auth_headers("admin"),
        case["id"],
        seed_depts["forensic"].id,
        users["officer2"].id,
    )
    member = CaseMember.query.filter_by(
        case_id=case["id"], user_id=users["officer2"].id, is_active=True
    ).first()
    assert member is not None
    assert member.role == "CASE_OFFICER"


def test_previous_lead_retained_as_member(client, db, auth_headers, users, seed_depts, case):
    _transfer(
        client, auth_headers("admin"),
        case["id"],
        seed_depts["forensic"].id,
        users["officer2"].id,
    )
    member = CaseMember.query.filter_by(
        case_id=case["id"], user_id=users["officer"].id, is_active=True
    ).first()
    assert member is not None


def test_case_transferred_audit_recorded(client, db, auth_headers, users, seed_depts, case):
    _transfer(
        client, auth_headers("admin"),
        case["id"],
        seed_depts["forensic"].id,
        users["officer2"].id,
    )
    event = AuditEvent.query.filter_by(
        event_type="CASE_TRANSFERRED", case_id=case["id"]
    ).first()
    assert event is not None
    meta = event.event_metadata
    assert "from_department_id" in meta
    assert "to_department_id" in meta
    assert "from_lead_officer_id" in meta
    assert "to_lead_officer_id" in meta
    # Confirm no PII in metadata (only IDs)
    assert "@" not in str(meta)


# ── Auth / MFA gate ────────────────────────────────────────────────────────────

def test_stale_mfa_returns_401_mfa_required(client, auth_headers, users, seed_depts, case):
    res = _transfer(
        client,
        auth_headers("admin", mfa_verified=False),
        case["id"],
        seed_depts["forensic"].id,
        users["officer2"].id,
    )
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "MFA_REQUIRED"


# ── Validation errors ──────────────────────────────────────────────────────────

def test_new_lead_not_in_target_dept_returns_400(client, auth_headers, users, seed_depts, case):
    # officer is in cyber dept, but we're transferring to forensic
    res = _transfer(
        client, auth_headers("admin"),
        case["id"],
        seed_depts["forensic"].id,
        users["officer"].id,   # officer is in cyber, not forensic
    )
    assert res.status_code == 400
    assert "target department" in res.get_json()["error"]["message"]


def test_inactive_new_lead_returns_400(client, db, auth_headers, users, seed_depts, case):
    users["officer2"].is_active = False
    db.session.commit()
    res = _transfer(
        client, auth_headers("admin"),
        case["id"],
        seed_depts["forensic"].id,
        users["officer2"].id,
    )
    assert res.status_code == 400


def test_archived_case_cannot_be_transferred(client, auth_headers, users, seed_depts, case):
    client.patch(
        f"/api/v1/cases/{case['id']}",
        data=json.dumps({"status": "UNDER_INVESTIGATION"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    client.patch(
        f"/api/v1/cases/{case['id']}",
        data=json.dumps({"status": "CLOSED"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    client.patch(
        f"/api/v1/cases/{case['id']}",
        data=json.dumps({"status": "ARCHIVED"}),
        content_type="application/json",
        headers=auth_headers("admin"),
    )
    res = _transfer(
        client, auth_headers("admin"),
        case["id"],
        seed_depts["forensic"].id,
        users["officer2"].id,
    )
    assert res.status_code == 409
    assert "archived" in res.get_json()["error"]["message"].lower()


def test_non_lead_member_cannot_transfer(client, auth_headers, users, seed_depts, case):
    # Add investigator as a member
    client.post(f"/api/v1/cases/{case['id']}/members",
                data=json.dumps({"user_id": str(users["investigator"].id), "role": "INVESTIGATOR"}),
                content_type="application/json", headers=auth_headers("officer"))

    res = _transfer(
        client, auth_headers("investigator"),
        case["id"],
        seed_depts["forensic"].id,
        users["officer2"].id,
    )
    assert res.status_code == 403


def test_non_member_gets_404_on_transfer(client, auth_headers, users, seed_depts, case):
    res = _transfer(
        client, auth_headers("investigator"),
        case["id"],
        seed_depts["forensic"].id,
        users["officer2"].id,
    )
    # investigator is not a member — 404
    assert res.status_code == 404


# ── Transfer options ───────────────────────────────────────────────────────────

def test_lead_officer_gets_transfer_options(client, auth_headers, case):
    res = client.get(
        f"/api/v1/cases/{case['id']}/transfer-options",
        headers=auth_headers("officer"),
    )
    assert res.status_code == 200
    body = res.get_json()
    assert "departments" in body
    assert "officers" in body
    assert len(body["departments"]) >= 1
    assert len(body["officers"]) >= 1


def test_admin_gets_transfer_options(client, auth_headers, case):
    res = client.get(
        f"/api/v1/cases/{case['id']}/transfer-options",
        headers=auth_headers("admin"),
    )
    assert res.status_code == 200


def test_transfer_options_no_sensitive_fields(client, auth_headers, case):
    res = client.get(
        f"/api/v1/cases/{case['id']}/transfer-options",
        headers=auth_headers("officer"),
    )
    officers = res.get_json()["officers"]
    for o in officers:
        assert "password" not in o
        assert "totp_secret" not in o
        assert "failed_logins" not in o


def test_non_lead_member_cannot_get_transfer_options(client, auth_headers, users, case):
    # Add investigator first
    client.post(f"/api/v1/cases/{case['id']}/members",
                data=json.dumps({"user_id": str(users["investigator"].id), "role": "INVESTIGATOR"}),
                content_type="application/json", headers=auth_headers("officer"))

    res = client.get(
        f"/api/v1/cases/{case['id']}/transfer-options",
        headers=auth_headers("investigator"),
    )
    assert res.status_code == 403


def test_non_member_cannot_get_transfer_options(client, auth_headers, case):
    res = client.get(
        f"/api/v1/cases/{case['id']}/transfer-options",
        headers=auth_headers("investigator"),
    )
    assert res.status_code == 404
