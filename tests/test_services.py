#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import marshmallow as ma
from invenio_rdm_records.services.schemas import MetadataSchema  # type: ignore[attr-defined]

from oarepo_related_resources.resolvers import DataciteResolver

if TYPE_CHECKING:
    from oarepo_related_resources.resolvers.base import ResolverProblem


class PersistentURLDumpingSchema(MetadataSchema):
    """Schema that dumps persistent URL to metadata."""

    persistent_url = ma.fields.String(load_default="here should be persistent url")


class DataciteResolverSavingPersistentURL(DataciteResolver):
    """Test resolver that saves persistent URL to metadata."""

    @override
    def resolve(self, identifier: str) -> tuple[dict[str, Any], list[ResolverProblem]]:
        metadata, problems = super().resolve(identifier)
        metadata["persistent_url"] = identifier
        return metadata, problems


# TODO: perhaps it's a better idea to use dict and register through entrypoints
#  so eg. datacite resolver can be directly overwritten
CUSTOM_PERSISTENT_IDENTIFIER_RESOLVERS = [
    "tests.test_services.DataciteResolverSavingPersistentURL",
    "oarepo_related_resources.resolvers.CrossrefResolver",
    "oarepo_related_resources.resolvers.HandleResolver",
]


def test_base_function(app, users, zenodo_imported_metadata, mock_http, monkeypatch, zenodo_doi):
    service = app.extensions["related-resources-import-extension"].service
    response = service.import_related_resource(users[0].identity, zenodo_doi)
    assert response.to_dict()["metadata"] == zenodo_imported_metadata


def test_custom_schema(app, users, zenodo_imported_metadata, mock_http, monkeypatch, zenodo_doi):
    service = app.extensions["related-resources-import-extension"].service
    monkeypatch.setitem(app.config, "RELATED_RESOURCES_RECORD_SCHEMA", PersistentURLDumpingSchema)
    response = service.import_related_resource(users[0].identity, zenodo_doi)
    assert response.to_dict()["metadata"]["persistent_url"] == "here should be persistent url"


def test_add_persistent_url_to_metadata(app, users, zenodo_imported_metadata, mock_http, monkeypatch, zenodo_doi):
    service = app.extensions["related-resources-import-extension"].service
    monkeypatch.setitem(app.config, "RELATED_RESOURCES_RECORD_SCHEMA", PersistentURLDumpingSchema)
    monkeypatch.setitem(app.config, "RELATED_RESOURCES_RESOLVER_LOAD_SCHEMA", PersistentURLDumpingSchema)
    monkeypatch.setitem(
        app.config, "RELATED_RESOURCES_PERSISTENT_IDENTIFIER_RESOLVERS", CUSTOM_PERSISTENT_IDENTIFIER_RESOLVERS
    )
    response = service.import_related_resource(users[0].identity, zenodo_doi)
    assert response.to_dict()["metadata"]["persistent_url"] == zenodo_doi
