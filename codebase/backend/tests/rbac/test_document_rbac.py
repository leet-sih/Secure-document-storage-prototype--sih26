"""RBAC tests for case-scoped document access."""

import io
import json

import pytest


@pytest.fixture()
def case_with_document(client, auth_headers):
    case_response = client.post(
        "/api/v1/cases",
        data=json.dumps({
            "case_number": "RBAC-DOC-001",
            "title": "RBAC Document Test",
        }),
        content_type="application/json",
        headers=auth_headers("officer"),
    )
    assert case_response.status_code == 201
    case = case_response.get_json()

    upload_response = client.post(
        f"/api/v1/cases/{case['id']}/documents",
        data={
            "file": (io.BytesIO(b"%PDF-1.4 test evidence"), "evidence.pdf"),
            "doc_type": "EVIDENCE_RECORD",
        },
        content_type="multipart/form-data",
        headers=auth_headers("officer"),
    )
    assert upload_response.status_code == 201

    return case, upload_response.get_json()

def test_case_officer_can_list_own_case_documents(
    client, auth_headers, case_with_document
):
    case, _document = case_with_document

    response = client.get(
        f"/api/v1/cases/{case['id']}/documents",
        headers=auth_headers("officer"),
    )

    assert response.status_code == 200


def test_unassigned_investigator_gets_404(
    client, auth_headers, case_with_document
):
    case, _document = case_with_document

    response = client.get(
        f"/api/v1/cases/{case['id']}/documents",
        headers=auth_headers("investigator"),
    )

    assert response.status_code == 404


def test_auditor_cannot_list_case_documents(
    client, auth_headers, case_with_document
):
    case, _document = case_with_document

    response = client.get(
        f"/api/v1/cases/{case['id']}/documents",
        headers=auth_headers("auditor"),
    )

    assert response.status_code == 403