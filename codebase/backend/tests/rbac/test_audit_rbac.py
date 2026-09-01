"""RBAC tests for audit-log access."""


def test_super_admin_can_view_system_audit(client, auth_headers):
    response = client.get(
        "/api/v1/audit",
        headers=auth_headers("admin"),
    )

    assert response.status_code == 200


def test_auditor_can_view_system_audit(client, auth_headers):
    response = client.get(
        "/api/v1/audit",
        headers=auth_headers("auditor"),
    )

    assert response.status_code == 200


def test_case_officer_cannot_view_system_audit(client, auth_headers):
    response = client.get(
        "/api/v1/audit",
        headers=auth_headers("officer"),
    )

    assert response.status_code == 403


def test_case_officer_can_view_own_case_audit(client, auth_headers):
    case_response = client.post(
        "/api/v1/cases",
        json={
            "case_number": "RBAC-AUDIT-001",
            "title": "Audit Access Test",
        },
        headers=auth_headers("officer"),
    )
    assert case_response.status_code == 201
    case = case_response.get_json()

    response = client.get(
        f"/api/v1/audit/cases/{case['id']}",
        headers=auth_headers("officer"),
    )

    assert response.status_code == 200


def test_unassigned_case_officer_gets_404_for_case_audit(
    client, auth_headers, users
):
    from app.services import case_service

    case = case_service.create_case(
        {
            "case_number": "RBAC-AUDIT-002",
            "title": "Other Officer Case",
        },
        users["admin"],
    )

    response = client.get(
        f"/api/v1/audit/cases/{case['id']}",
        headers=auth_headers("officer"),
    )

    assert response.status_code == 404