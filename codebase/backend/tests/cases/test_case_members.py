"""Tests for POST/DELETE /api/v1/cases/{id}/members."""
import json
import pytest
from app.models.case_member import CaseMember
from app.services.case_service import user_has_access


@pytest.fixture()
def case(client, auth_headers):
    res = client.post(
        "/api/v1/cases",
        data=json.dumps({"case_number": "MBR-001", "title": "Member Test"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    return res.get_json()


def test_add_member(client, auth_headers, users, case):
    res = client.post(
        f"/api/v1/cases/{case['id']}/members",
        data=json.dumps({"user_id": str(users["investigator"].id), "role": "INVESTIGATOR"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["role"] == "INVESTIGATOR"


def test_duplicate_active_member_returns_409(client, auth_headers, users, case):
    payload = {"user_id": str(users["investigator"].id), "role": "INVESTIGATOR"}
    client.post(f"/api/v1/cases/{case['id']}/members", data=json.dumps(payload),
                content_type="application/json", headers=auth_headers("officer"))
    res = client.post(f"/api/v1/cases/{case['id']}/members", data=json.dumps(payload),
                      content_type="application/json", headers=auth_headers("officer"))
    assert res.status_code == 409
    assert "already a member" in res.get_json()["error"]["message"]


def test_soft_removed_member_reactivated_on_readd(client, db, auth_headers, users, case):
    """Re-adding a soft-removed member reactivates the existing row."""
    payload = {"user_id": str(users["investigator"].id), "role": "INVESTIGATOR"}
    client.post(f"/api/v1/cases/{case['id']}/members", data=json.dumps(payload),
                content_type="application/json", headers=auth_headers("officer"))

    # Add a second officer so we can remove the investigator without tripping guards
    client.post(f"/api/v1/cases/{case['id']}/members",
                data=json.dumps({"user_id": str(users["officer2"].id), "role": "CASE_OFFICER"}),
                content_type="application/json", headers=auth_headers("officer"))

    # Remove investigator (soft delete)
    client.delete(
        f"/api/v1/cases/{case['id']}/members/{users['investigator'].id}",
        headers=auth_headers("officer"),
    )

    # Re-add — should reactivate, not insert a new row
    res = client.post(f"/api/v1/cases/{case['id']}/members", data=json.dumps(payload),
                      content_type="application/json", headers=auth_headers("officer"))
    assert res.status_code == 201

    rows = CaseMember.query.filter_by(
        case_id=case["id"], user_id=users["investigator"].id
    ).all()
    assert len(rows) == 1
    assert rows[0].is_active is True


def test_remove_member_soft_deletes(client, db, auth_headers, users, case):
    client.post(f"/api/v1/cases/{case['id']}/members",
                data=json.dumps({"user_id": str(users["investigator"].id), "role": "INVESTIGATOR"}),
                content_type="application/json", headers=auth_headers("officer"))

    res = client.delete(
        f"/api/v1/cases/{case['id']}/members/{users['investigator'].id}",
        headers=auth_headers("officer"),
    )
    assert res.status_code == 204

    row = CaseMember.query.filter_by(
        case_id=case["id"], user_id=users["investigator"].id
    ).first()
    assert row is not None
    assert row.is_active is False
    assert row.removed_at is not None


def test_cannot_remove_self(client, auth_headers, users, case):
    res = client.delete(
        f"/api/v1/cases/{case['id']}/members/{users['officer'].id}",
        headers=auth_headers("officer"),
    )
    assert res.status_code == 409
    assert "yourself" in res.get_json()["error"]["message"]


def test_cannot_remove_last_case_officer(client, auth_headers, users, case):
    # Add investigator to ensure case has another member
    client.post(f"/api/v1/cases/{case['id']}/members",
                data=json.dumps({"user_id": str(users["investigator"].id), "role": "INVESTIGATOR"}),
                content_type="application/json", headers=auth_headers("officer"))

    # Try to remove the only officer (using admin to bypass the self-check)
    res = client.delete(
        f"/api/v1/cases/{case['id']}/members/{users['officer'].id}",
        headers=auth_headers("admin"),
    )
    assert res.status_code == 409
    assert "last case officer" in res.get_json()["error"]["message"]


def test_removed_member_loses_access(client, db, auth_headers, users, case):
    client.post(f"/api/v1/cases/{case['id']}/members",
                data=json.dumps({"user_id": str(users["investigator"].id), "role": "INVESTIGATOR"}),
                content_type="application/json", headers=auth_headers("officer"))

    assert user_has_access(str(users["investigator"].id), case["id"]) is True

    client.delete(
        f"/api/v1/cases/{case['id']}/members/{users['investigator'].id}",
        headers=auth_headers("officer"),
    )

    assert user_has_access(str(users["investigator"].id), case["id"]) is False


def test_cannot_remove_lead_officer(client, auth_headers, users, case):
    """Cannot remove the current lead_officer_id user without first transferring."""
    # Add officer2 as another CASE_OFFICER so last-officer guard won't fire
    client.post(f"/api/v1/cases/{case['id']}/members",
                data=json.dumps({"user_id": str(users["officer2"].id), "role": "CASE_OFFICER"}),
                content_type="application/json", headers=auth_headers("officer"))

    # officer is the lead; admin tries to remove them
    res = client.delete(
        f"/api/v1/cases/{case['id']}/members/{users['officer'].id}",
        headers=auth_headers("admin"),
    )
    assert res.status_code == 409
    assert "lead officer" in res.get_json()["error"]["message"].lower()
