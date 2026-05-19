#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Tests for ``RelatedResourcesResource``.

These tests exercise the HTTP resource end-to-end against Flask's test
client without bringing up the full Invenio stack. The conftest ``app``
fixture builds a bare Flask app; here we initialize the extension on top
of it, swap the auto-built service for a fake one (so the resolver
pipeline is bypassed), register the blueprint, and POST through
``test_client``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.conftest import MockResponse

if TYPE_CHECKING:
    from collections.abc import Callable


def test_datacite_import(app, logged_client, users, mock_http, zenodo_imported_metadata, zenodo_doi):
    response = logged_client(users[0]).post("/related-records", json={"identifier": zenodo_doi})
    assert response.json["metadata"] == zenodo_imported_metadata
    assert response.status_code == 200


def test_datacite_import_errors(app, logged_client, users, mock_http, zenodo_imported_metadata, zenodo_doi):
    response = logged_client(users[0]).post("/related-records", json={"identifier": zenodo_doi})
    assert len(response.json["validation_errors"]) == 1
    assert len(response.json["import_errors"]) == 1


def test_datacite_import_normalized_identifier(
    app, logged_client, users, mock_http, zenodo_imported_metadata, zenodo_doi
):
    response = logged_client(users[0]).post(
        "/related-records", json={"identifier": zenodo_doi[len("https://doi.org/") :]}
    )
    assert response.json["metadata"] == zenodo_imported_metadata
    assert response.status_code == 200


def test_handle_import(app, logged_client, users, mock_http, handle_imported_metadata, handle):
    response = logged_client(users[0]).post("/related-records", json={"identifier": handle})
    assert response.json["metadata"] == handle_imported_metadata
    assert response.status_code == 200


def test_handle_import_normalized_identifier(app, logged_client, users, mock_http, handle_imported_metadata, handle):
    response = logged_client(users[0]).post(
        "/related-records", json={"identifier": handle[len("http://hdl.handle.net/") :]}
    )
    assert response.json["metadata"] == handle_imported_metadata
    assert response.status_code == 200


def test_crossref_import(app, logged_client, users, mock_http, crossref_imported_metadata, crossref_doi):
    response = logged_client(users[0]).post("/related-records", json={"identifier": crossref_doi})
    assert response.json["metadata"] == crossref_imported_metadata
    assert response.status_code == 200


def test_crossref_import_normalized_identifier(
    app, logged_client, users, mock_http, crossref_imported_metadata, crossref_doi
):
    response = logged_client(users[0]).post(
        "/related-records", json={"identifier": crossref_doi[len("https://doi.org/") :]}
    )
    assert response.json["metadata"] == crossref_imported_metadata
    assert response.status_code == 200


def test_unathorized(app, client, mock_http, zenodo_doi):
    resp = client.post("/related-records", json={"identifier": zenodo_doi})
    assert resp.status_code == 403


def test_invalid_identifier(app, logged_client, users, mock_http):
    resp = logged_client(users[0]).post("/related-records", json={"identifier": "invalid"})
    assert resp.status_code == 404
    assert resp.json["message"] == "Unsupported identifier type 'invalid'."


def test_nonexistent_doi(app, logged_client, users, mock_http, nonexistent_doi):
    resp = logged_client(users[0]).post("/related-records", json={"identifier": nonexistent_doi})
    assert resp.status_code == 404
    assert resp.json["message"] == "Non-existent persistent identifier: 'https://doi.org/10.1234/x'."


def _alive_then(status_code: int, *, content: bytes = b"upstream error") -> Callable:
    counter = {"n": 0}

    def _route(url, kwargs) -> MockResponse:
        counter["n"] += 1
        if counter["n"] == 1:
            return MockResponse(payload={"data": {"attributes": {}}})
        return MockResponse(status_code=status_code, content=content, text=content.decode())

    return _route


def test_non_string_id_routed_through_pid_processing_error(app, logged_client, users, mock_http):
    """An ``id`` of the wrong type currently produces a ``PIDProcessingError`` → 500, not a request-shape error."""
    resp = logged_client(users[0]).post("/related-records", json={"identifier": 42})
    assert resp.status_code == 500
    assert "Error while processing identifier" in resp.json["message"]


def test_upstream_503_end_to_end_returns_503(app, logged_client, users, mock_http, zenodo_doi):
    """``UpstreamFetchError`` reaches the HTTP layer with its ``error_code`` preserved."""
    mock_http["https://api.datacite.org/dois/10.5281/zenodo.19032692"] = _alive_then(503)
    resp = logged_client(users[0]).post("/related-records", json={"identifier": zenodo_doi})
    assert resp.status_code == 503
    assert resp.content_type.startswith("application/json")
