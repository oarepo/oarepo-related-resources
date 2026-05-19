#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Conftest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import requests
from invenio_app.factory import create_api

DATA_DIR = Path(__file__).parent / "data"

if TYPE_CHECKING:
    from typing import Any

pytest_plugins = [
    "pytest_oarepo.fixtures",
    "pytest_oarepo.users",
]


@pytest.fixture
def datacite_response():
    return json.loads((DATA_DIR / "datacite_response.json").read_text())


@pytest.fixture
def crossref_response():
    return json.loads((DATA_DIR / "crossref_response.json").read_text())


@pytest.fixture
def handle_response():
    return (DATA_DIR / "handle_response.html").read_text()


@pytest.fixture
def zenodo_doi():
    return "https://doi.org/10.5281/zenodo.19032692"


@pytest.fixture
def crossref_doi():
    return "https://doi.org/10.1575/1912/1099"


@pytest.fixture
def nonexistent_doi():
    return "https://doi.org/10.1234/x"


@pytest.fixture
def handle():
    return "http://hdl.handle.net/11234/1-6144"


@pytest.fixture
def zenodo_imported_metadata():
    return {
        "creators": [
            {
                "person_or_org": {
                    "family_name": "Houghton",
                    "given_name": "Frank",
                    "name": "Houghton, Frank",
                    "type": "personal",
                }
            }
        ],
        "publisher": "Radical Statistics",
        "resource_type": {"id": "dataset"},
        "publication_date": "2025",
        "title": "Unknown Knowns: The non-enforcement of gambling legislation in Ireland and the "
        "function of opaque and divided information systems",
        "version": "Published",
    }


@pytest.fixture
def handle_imported_metadata():
    return {
        "creators": [
            {
                "person_or_org": {
                    "family_name": "Mírovský",
                    "given_name": "Jiří",
                    "name": "Mírovský, Jiří",
                    "type": "personal",
                }
            }
        ],
        "publication_date": "2026-04-30",
        "resource_type": {"id": "dataset"},
        "title": "SiR 2.0",
    }


@pytest.fixture
def crossref_imported_metadata():
    return {
        "creators": [
            {
                "person_or_org": {
                    "family_name": "Montgomery",
                    "given_name": "Raymond B.",
                    "name": "Montgomery, Raymond B.",
                    "type": "personal",
                }
            }
        ],
        "publication_date": "2017-05-10",
        "resource_type": {"id": "dataset"},
        "title": "Observations of vertical humidity distribution above the ocean surface and their relation to "
        "evaporation",
    }


class MockResponse:
    """Minimal stand-in for ``requests.Response`` used in tests."""

    def __init__(
        self,
        payload: dict | None = None,
        content: bytes = b"ok",
        status_code: int = 200,
        text: str | None = None,
    ):
        """Store the JSON payload, raw content, and status code for the mocked response."""
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content
        self.text = text if text is not None else (content.decode("utf-8", errors="replace"))

    def json(self) -> dict:
        """Return the stored JSON payload."""
        return self._payload


@pytest.fixture
def mock_http(monkeypatch, datacite_response, handle_response, crossref_response):
    """URL-keyed mock for ``requests.Session.get``."""
    routes: dict[str, MockResponse | BaseException] = {
        "https://api.datacite.org/dois/10.5281/zenodo.19032692": MockResponse(payload=datacite_response),
        "https://hdl.handle.net/11234/1-6144": MockResponse(content=handle_response.encode("utf-8")),
        "https://api.crossref.org/works/doi/10.1575/1912/1099": MockResponse(payload=crossref_response),
    }

    def _get(self, *args: Any, **kwargs: Any) -> MockResponse:
        url = kwargs.get("url") or (args[0] if args else None)
        if url not in routes:
            return MockResponse(status_code=404, payload={"errors": [{"status": "404", "title": "Not found"}]})
        entry = routes[url]
        if isinstance(entry, BaseException):
            raise entry
        if callable(entry) and not isinstance(entry, MockResponse):
            return entry(url, kwargs)
        return entry

    monkeypatch.setattr(requests.Session, "get", _get)
    return routes


@pytest.fixture
def service(app):
    return app.extensions["related-resources-import-extension"].service


@pytest.fixture(scope="module")
def create_app(instance_path, entry_points):
    """Application factory fixture."""
    return create_api  # type: ignore [no-any-return]


@pytest.fixture(scope="module")
def app_config(app_config):
    app_config["APP_RDM_ADMIN_EMAIL_RECIPIENT"] = "bugsmasher@cesnet.cz"
    return app_config
