#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

from unittest.mock import Mock

import oarepo_related_resources.services as services
from oarepo_related_resources.resolvers import (
    CrossrefResolver,
    DataciteResolver,
    HandleResolver,
)
from oarepo_related_resources.resolvers import datacite as datacite_module


def test_datacite_resolver_builds_expected_upstream_url(app, zenodo_doi):
    """`DATACITE_URL` + normalized DOI suffix produces the upstream API URL."""
    resolver = DataciteResolver()
    assert (
        resolver._create_fetch_url(zenodo_doi)  # noqa SLF001
        == "https://api.datacite.org/dois/10.5281/zenodo.19032692"
    )


def test_datacite_descriptions_and_subjects(app, monkeypatch):
    resolver = DataciteResolver()
    resolver.metadata = {
        "descriptions": [
            {"descriptionType": "Abstract", "description": "Main abstract"},
            {"descriptionType": "Methods", "description": "Used methods", "lang": "en"},
            {"descriptionType": "Other", "description": "Missing language"},
        ],
        "subjects": [
            {"subject": "biology"},
            {"subject": "biology"},
            {"subject": "chemistry"},
            "invalid",
        ],
    }
    monkeypatch.setattr(datacite_module, "vocabulary_entry_exists", Mock(return_value=True))
    monkeypatch.setattr(datacite_module, "resolve_language", Mock(return_value="eng"))

    resolver.resolve_description()
    resolver.resolve_additional_descriptions()
    resolver.resolve_subjects()

    assert resolver.processed_metadata == {
        "description": "Main abstract",
        "additional_descriptions": [
            {
                "type": {"id": "methods"},
                "description": "Used methods",
                "lang": {"id": "eng"},
            }
        ],
        "subjects": [{"subject": "biology"}, {"subject": "chemistry"}],
    }


def test_datacite_related_titles_and_contributors(app, monkeypatch):
    resolver = DataciteResolver()
    resolver.metadata = {
        "titles": [
            {"title": "Main title"},
            {"title": "Translated title", "titleType": "TranslatedTitle", "lang": "cs"},
        ],
        "relatedIdentifiers": [
            {
                "relatedIdentifier": "10.1234/related",
                "relatedIdentifierType": "DOI",
                "relationType": "References",
                "resourceTypeGeneral": "Dataset",
            }
        ],
        "contributors": [{"name": "Lovelace, Ada", "contributorType": "Editor"}],
    }
    monkeypatch.setattr(
        datacite_module,
        "lookup_vocabulary_by_prop",
        Mock(side_effect=["translated-title", "references", "editor"]),
    )
    monkeypatch.setattr(
        datacite_module,
        "lookup_vocabulary_by_prop_handle_multiple",
        Mock(return_value="dataset"),
    )
    monkeypatch.setattr(datacite_module, "resolve_language", Mock(return_value="ces"))

    resolver.resolve_additional_titles()
    resolver.resolve_related_identifiers()
    resolver.resolve_contributors()

    assert resolver.processed_metadata == {
        "additional_titles": [
            {
                "title": "Translated title",
                "type": {"id": "translated-title"},
                "lang": {"id": "ces"},
            }
        ],
        "related_identifiers": [
            {
                "identifier": "10.1234/related",
                "scheme": "doi",
                "relation_type": {"id": "references"},
                "resource_type": {"id": "dataset"},
            }
        ],
        "contributors": [
            {
                "person_or_org": {
                    "name": "Lovelace, Ada",
                    "type": "personal",
                    "given_name": "Ada",
                    "family_name": "Lovelace",
                },
                "role": {"id": "editor"},
            }
        ],
    }


def test_datacite_affiliations_and_name_identifiers(app, monkeypatch):
    resolver = DataciteResolver()
    monkeypatch.setattr(services, "resolve_orcid", Mock(return_value={"id": "0000-0001"}))

    assert (
        resolver._resolve_datacite_affiliations(  # noqa: SLF001
            [
                "Institute",
                "Institute",
                {"affiliationIdentifierScheme": "ROR", "affiliationIdentifier": "01abc"},
                {"name": "Named institute"},
            ]
        ),
        resolver._resolve_datacite_name_identifiers(  # noqa: SLF001
            name_identifiers=[
                {"nameIdentifier": "https://orcid.org/0000-0001", "nameIdentifierScheme": "ORCID"},
                {"nameIdentifier": "https://orcid.org/0000-0001", "nameIdentifierScheme": "ORCID"},
                {"nameIdentifier": "ignored", "nameIdentifierScheme": "unknown"},
            ]
        ),
    ) == (
        [{"name": "Institute"}, {"id": "01abc"}, {"name": "Named institute"}],
        [{"identifier": "0000-0001", "scheme": "orcid"}],
    )


def test_crossref_resolver_builds_expected_upstream_url(app, crossref_doi):
    """`DATACITE_URL` + normalized DOI suffix produces the upstream API URL."""
    resolver = CrossrefResolver()
    assert (
        resolver._create_fetch_url(crossref_doi)  # noqa SLF001
        == "https://api.crossref.org/works/doi/10.1575/1912/1099"
    )


def test_crossref_resolve_description(app):
    resolver = CrossrefResolver()
    resolver.metadata = {
        "abstract": """
            <jats:title>Abstract</jats:title>
            <jats:p>First paragraph with <jats:bold>bold text</jats:bold>.</jats:p>
            <jats:p>Second paragraph.</jats:p>
        """
    }

    resolver.resolve_description()

    assert resolver.processed_metadata == {
        "description": "First paragraph with bold text.\n\nSecond paragraph."
    }


def test_handle_resolver_builds_expected_upstream_url(app, handle):
    """`DATACITE_URL` + normalized DOI suffix produces the upstream API URL."""
    resolver = HandleResolver()
    assert (
        resolver._create_fetch_url(handle)  # noqa SLF001
        == "https://hdl.handle.net/11234/1-6144"
    )
