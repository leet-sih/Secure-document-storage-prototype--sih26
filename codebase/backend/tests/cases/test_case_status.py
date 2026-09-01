"""Tests for status transitions and assert_case_writable."""
import json
import pytest
from app.models.case import Case
from app.services.case_service import assert_case_writable
from app.core.errors import APIError


@pytest.fixture()
def case(client, auth_headers):
    res = client.post(
        "/api/v1/cases",
        data=json.dumps({"case_number": "STS-001", "title": "Status Test"}),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    return res.get_json()


def _patch(client, headers, case_id, status):
    return client.patch(
        f"/api/v1/cases/{case_id}",
        data=json.dumps({"status": status}),
        content_type="application/json",
        headers=headers,
    )


def test_open_to_under_investigation(client, auth_headers, case):
    res = _patch(client, auth_headers("officer"), case["id"], "UNDER_INVESTIGATION")
    assert res.status_code == 200
    assert res.get_json()["status"] == "UNDER_INVESTIGATION"


def test_under_investigation_to_closed(client, auth_headers, case):
    _patch(client, auth_headers("officer"), case["id"], "UNDER_INVESTIGATION")
    res = _patch(client, auth_headers("officer"), case["id"], "CLOSED")
    assert res.status_code == 200
    assert res.get_json()["status"] == "CLOSED"
    assert res.get_json()["closed_at"] is not None


def test_closed_to_archived_requires_super_admin(client, auth_headers, case):
    _patch(client, auth_headers("officer"), case["id"], "UNDER_INVESTIGATION")
    _patch(client, auth_headers("officer"), case["id"], "CLOSED")

    # CASE_OFFICER cannot archive
    res = _patch(client, auth_headers("officer"), case["id"], "ARCHIVED")
    assert res.status_code == 403

    # SUPER_ADMIN can
    res = _patch(client, auth_headers("admin"), case["id"], "ARCHIVED")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ARCHIVED"


def test_closed_to_open_requires_super_admin(client, auth_headers, case):
    _patch(client, auth_headers("officer"), case["id"], "UNDER_INVESTIGATION")
    _patch(client, auth_headers("officer"), case["id"], "CLOSED")

    res = _patch(client, auth_headers("officer"), case["id"], "OPEN")
    assert res.status_code == 403

    res = _patch(client, auth_headers("admin"), case["id"], "OPEN")
    assert res.status_code == 200


def test_illegal_transition_returns_409(client, auth_headers, case):
    # OPEN -> CLOSED (skips UNDER_INVESTIGATION) is not allowed
    res = _patch(client, auth_headers("officer"), case["id"], "CLOSED")
    assert res.status_code == 409
    assert "Illegal status transition" in res.get_json()["error"]["message"]


def test_archived_is_terminal(client, auth_headers, case):
    _patch(client, auth_headers("officer"), case["id"], "UNDER_INVESTIGATION")
    _patch(client, auth_headers("officer"), case["id"], "CLOSED")
    _patch(client, auth_headers("admin"), case["id"], "ARCHIVED")

    res = _patch(client, auth_headers("admin"), case["id"], "CLOSED")
    assert res.status_code == 409


def test_assert_case_writable_on_open(db, users, seed_depts):
    from app.services.case_service import create_case
    detail = create_case({"case_number": "WRT-001", "title": "Writable Test"}, users["officer"])
    case = Case.query.get(detail["id"])
    assert_case_writable(case)   # must not raise


def test_assert_case_writable_on_closed_raises(db, users, seed_depts):
    from app.services.case_service import create_case, update_case
    detail = create_case({"case_number": "WRT-002", "title": "Writable Test 2"}, users["officer"])
    update_case(detail["id"], {"status": "UNDER_INVESTIGATION"}, users["officer"])
    update_case(detail["id"], {"status": "CLOSED"}, users["officer"])
    case = Case.query.get(detail["id"])
    with pytest.raises(APIError) as exc_info:
        assert_case_writable(case)
    assert exc_info.value.status == 409


def test_assert_case_writable_on_archived_raises(db, users, seed_depts):
    from app.services.case_service import create_case, update_case
    detail = create_case({"case_number": "WRT-003", "title": "Writable Test 3"}, users["officer"])
    update_case(detail["id"], {"status": "UNDER_INVESTIGATION"}, users["officer"])
    update_case(detail["id"], {"status": "CLOSED"}, users["officer"])
    update_case(detail["id"], {"status": "ARCHIVED"}, users["admin"])
    case = Case.query.get(detail["id"])
    with pytest.raises(APIError) as exc_info:
        assert_case_writable(case)
    assert exc_info.value.status == 409
