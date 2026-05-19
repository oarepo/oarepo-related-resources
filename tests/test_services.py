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
import pytest
from invenio_rdm_records.services.schemas import MetadataSchema  # type: ignore[attr-defined]
from invenio_records_permissions import BasePermissionPolicy
from invenio_records_permissions.generators import Disable
from invenio_records_resources.services.errors import PermissionDeniedError

from oarepo_related_resources.resolvers import CrossrefResolver, DataciteResolver, HandleResolver

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


class DenyAllPolicy(BasePermissionPolicy):
    """Permission policy denying ``can_import_related`` for everyone."""

    can_import_related = (Disable(),)


CUSTOM_PERSISTENT_IDENTIFIER_RESOLVERS = [
    DataciteResolverSavingPersistentURL,
    CrossrefResolver,
    HandleResolver,
]


def test_custom_policy_denies_authenticated_user(
    app, service, logged_client, users, monkeypatch, mock_http, zenodo_doi
):
    """A policy denying ``can_import_related`` for everyone → 403 even for a logged-in user."""
    monkeypatch.setitem(app.config, "RELATED_RESOURCES_PERMISSION_POLICY", DenyAllPolicy)
    with pytest.raises(PermissionDeniedError):
        service.import_related_resource(users[0].identity, zenodo_doi)


def test_base_function(service, users, zenodo_imported_metadata, mock_http, monkeypatch, zenodo_doi):
    response = service.import_related_resource(users[0].identity, zenodo_doi)
    assert response.to_dict()["metadata"] == zenodo_imported_metadata


def test_custom_schema(app, service, users, zenodo_imported_metadata, mock_http, monkeypatch, zenodo_doi):
    monkeypatch.setitem(app.config, "RELATED_RESOURCES_RECORD_SCHEMA", PersistentURLDumpingSchema)
    response = service.import_related_resource(users[0].identity, zenodo_doi)
    assert response.to_dict()["metadata"]["persistent_url"] == "here should be persistent url"


def test_add_persistent_url_to_metadata(
    app, service, users, zenodo_imported_metadata, mock_http, monkeypatch, zenodo_doi
):
    monkeypatch.setitem(app.config, "RELATED_RESOURCES_RECORD_SCHEMA", PersistentURLDumpingSchema)
    monkeypatch.setitem(
        app.config, "RELATED_RESOURCES_PERSISTENT_IDENTIFIER_RESOLVERS", CUSTOM_PERSISTENT_IDENTIFIER_RESOLVERS
    )
    response = service.import_related_resource(users[0].identity, zenodo_doi)
    assert response.to_dict()["metadata"]["persistent_url"] == zenodo_doi
