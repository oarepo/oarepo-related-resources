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


def test_datacite_import(app, logged_client, users, mock_http, zenodo_imported_metadata, zenodo_doi):
    response = logged_client(users[0]).post("/related-records", json={"identifier": zenodo_doi})
    jsn = response.json
    metadata = jsn["metadata"]
    assert metadata == zenodo_imported_metadata
    assert response.status_code == 201


def test_handle_import(app, logged_client, users, mock_http, handle_imported_metadata, handle):
    response = logged_client(users[0]).post("/related-records", json={"identifier": handle})
    jsn = response.json
    metadata = jsn["metadata"]
    assert metadata == handle_imported_metadata
    assert response.status_code == 201


def test_crossref_import(app, logged_client, users, mock_http, crossref_imported_metadata, crossref_doi):
    response = logged_client(users[0]).post("/related-records", json={"identifier": crossref_doi})
    jsn = response.json
    metadata = jsn["metadata"]
    assert metadata == crossref_imported_metadata
    assert response.status_code == 201


def test_unathorized(app, client, mock_http, zenodo_doi):
    resp = client.post("/related-records", json={"id": zenodo_doi})
    assert resp.status_code == 403


def test_invalid_identifier(app, logged_client, users, mock_http):
    resp = logged_client(users[0]).post("/related-records", json={"id": "invalid"})
    assert resp.status_code == 404
    assert resp.json["message"] == "Unsupported identifier type 'invalid'."


def test_nonexistent_doi(app, logged_client, users, mock_http, nonexistent_doi):
    resp = logged_client(users[0]).post("/related-records", json={"id": nonexistent_doi})
    assert resp.status_code == 404
    assert resp.json["message"] == "Non-existent persistent identifier: 'https://doi.org/10.1234/x'."
