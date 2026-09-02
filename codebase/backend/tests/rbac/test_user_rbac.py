"""RBAC tests for system user administration."""

import json


def test_super_admin_can_list_users(client, auth_headers):
    response = client.get(
        "/api/v1/users",
        headers=auth_headers("admin"),
    )

    assert response.status_code == 200


def test_case_officer_cannot_list_users(client, auth_headers):
    response = client.get(
        "/api/v1/users",
        headers=auth_headers("officer"),
    )

    assert response.status_code == 403


def test_investigator_cannot_list_users(client, auth_headers):
    response = client.get(
        "/api/v1/users",
        headers=auth_headers("investigator"),
    )

    assert response.status_code == 403