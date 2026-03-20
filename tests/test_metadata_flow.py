#
# Copyright (C) 2026 CESNET z.s.p.o.
#
# oarepo-rdm is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Test metadata flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from oarepo_related_resources.ext import RelatedResourcesImportExtension
from oarepo_related_resources.resolvers.crossref import CrossrefResolver
from oarepo_related_resources.resolvers.datacite import DataciteResolver
from oarepo_related_resources.resolvers.handle import HandleResolver

if TYPE_CHECKING:
    from typing import Any

    from flask import Flask

    from oarepo_related_resources.resolvers.base import MetadataResolver


class _MockResponse:
    def __init__(
        self,
        payload: dict | None = None,
        content: bytes = b"ok",
        status_code: int = 200,
    ):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content

    def json(self) -> dict:
        """Return payload."""
        return self._payload


class _MockSession:
    def __init__(self, responses: list[_MockResponse]):
        self.responses = responses

    def get(self, *, url: str, timeout: int, **kwargs: Any) -> _MockResponse:
        _, _, _ = url, timeout, kwargs
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


def _resolver(app: Flask, resolver_cls: MetadataResolver) -> MetadataResolver:
    """Get resolver."""
    ext = RelatedResourcesImportExtension(app)
    return next(r for r in ext.persistent_identifiers_resolvers if isinstance(r, resolver_cls))


def test_mock_zenodo_doi_returns_metadata(app: Flask):
    doi = "https://doi.org/10.5281/zenodo.19032692"
    resolver = _resolver(app, DataciteResolver)
    resolver.session = _MockSession(
        [
            _MockResponse(
                payload={
                    "data": {
                        "attributes": {
                            "titles": [{"title": "Zenodo mock dataset"}],
                            "creators": [{"name": "Novak, Eva", "nameType": "Personal"}],
                            "publicationYear": "2025",
                            "types": {"resourceTypeGeneral": "Dataset"},
                        }
                    }
                }
            )
        ]
    )

    metadata, _ = resolver.resolve(doi)

    assert metadata == {
        "title": "Zenodo mock dataset",
        "creators": [
            {
                "person_or_org": {
                    "type": "personal",
                    "name": "Novak, Eva",
                    "given_name": "Eva",
                    "family_name": "Novak",
                }
            }
        ],
        "publication_date": "2025",
        "resource_type": {"id": "other"},
        "identifiers": [],
    }


def test_mock_crossref_doi_returns_metadata(app: Flask):
    doi = "https://doi.org/10.1038/s41586-020-2649-2"
    resolver = _resolver(app, CrossrefResolver)
    resolver.session = _MockSession(
        [
            _MockResponse(
                payload={
                    "message": {
                        "title": ["Crossref mock article"],
                        "author": [{"family": "Smith", "given": "John"}],
                        "deposited": {"date-parts": [[2023, 7, 15]]},
                    }
                }
            )
        ]
    )

    metadata, _ = resolver.resolve(doi)

    assert metadata == {
        "title": "Crossref mock article",
        "creators": [
            {
                "person_or_org": {
                    "name": "Smith, John",
                    "family_name": "Smith",
                    "type": "personal",
                    "given_name": "John",
                }
            }
        ],
        "publication_date": "2023-07-15",
        "resource_type": {"id": "other"},
    }


def test_mock_handle_returns_metadata(app: Flask):
    pid = "https://hdl.handle.net/11234/1"
    resolver = _resolver(app, HandleResolver)
    resolver.session = _MockSession(
        [
            _MockResponse(
                content=b"""
                <html>
                  <head>
                    <meta name=\"citation_title\" content=\"Handle mock dataset\" />
                    <meta name=\"citation_author\" content=\"Novak, Eva\" />
                    <meta name=\"citation_publication_date\" content=\"2024-03-15\" />
                  </head>
                  <body></body>
                </html>
                """
            )
        ]
    )

    metadata, _ = resolver.resolve(pid)

    assert metadata == {
        "title": "Handle mock dataset",
        "creators": [
            {
                "person_or_org": {
                    "name": "Novak, Eva",
                    "type": "personal",
                    "given_name": "Eva",
                    "family_name": "Novak",
                }
            }
        ],
        "publication_date": "2024-03-15",
        "resource_type": {"id": "other"},
    }
