# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

from __future__ import annotations

from unittest.mock import Mock

import pytest
from lxml import html

import oarepo_related_resources.services as services
from oarepo_related_resources.resolvers import (
    CrossrefResolver,
    DataciteResolver,
    HandleResolver,
)
from oarepo_related_resources.resolvers import datacite as datacite_module
from oarepo_related_resources.resolvers import handle as handle_module


def test_datacite_resolver_builds_expected_upstream_url(app, zenodo_doi):
    """`DATACITE_URL` + normalized DOI suffix produces the upstream API URL."""
    resolver = DataciteResolver()
    assert (
        resolver._create_fetch_url(zenodo_doi)
        == "https://api.datacite.org/dois/10.5281/zenodo.19032692?affiliation=true"
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
        resolver._resolve_datacite_affiliations(
            [
                "Institute",
                "Institute",
                {"affiliationIdentifierScheme": "ROR", "affiliationIdentifier": "01abc"},
                {"name": "Named institute"},
            ]
        ),
        resolver._resolve_datacite_name_identifiers(
            name_identifiers=[
                {"nameIdentifier": "https://orcid.org/0000-0001", "nameIdentifierScheme": "ORCID"},
                {"nameIdentifier": "https://orcid.org/0000-0001", "nameIdentifierScheme": "ORCID"},
                {"nameIdentifier": "ignored", "nameIdentifierScheme": "unknown"},
            ]
        ),
    ) == (
        [{"name": "Institute"}, {"name": "01abc"}, {"name": "Named institute"}],
        [{"identifier": "0000-0001", "scheme": "orcid"}],
    )


def test_crossref_resolver_builds_expected_upstream_url(app, crossref_doi):
    """`DATACITE_URL` + normalized DOI suffix produces the upstream API URL."""
    resolver = CrossrefResolver()
    assert resolver._create_fetch_url(crossref_doi) == "https://api.crossref.org/works/doi/10.1575/1912/1099"


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

    assert resolver.processed_metadata == {"description": "First paragraph with bold text.\n\nSecond paragraph."}


def test_handle_resolver_builds_expected_upstream_url(app, handle):
    """`DATACITE_URL` + normalized DOI suffix produces the upstream API URL."""
    resolver = HandleResolver()
    assert resolver._create_fetch_url(handle) == "https://hdl.handle.net/11234/1-6144"


def test_handle_resolve_additional_descriptions(app, monkeypatch):
    resolver = HandleResolver()
    resolver.metadata = html.fromstring(
        """
        <html><head>
          <meta name="DCTERMS.abstract" content="English abstract" xml:lang="en">
          <meta name="DCTERMS.abstract" content="Abstract without language">
        </head></html>
        """
    )
    monkeypatch.setattr(handle_module, "resolve_language", Mock(side_effect=["eng", None]))

    resolver.resolve_additional_descriptions()

    assert resolver.processed_metadata == {
        "additional_descriptions": [
            {
                "lang": {"id": "eng"},
                "type": {"id": "abstract"},
                "description": "English abstract",
            },
            {
                "type": {"id": "abstract"},
                "description": "Abstract without language",
            },
        ]
    }


def test_handle_parse_loose_date(app):
    resolver = HandleResolver()

    assert resolver._parse_loose_date("January 2, 2020") == "2020-01-02"
    assert str(resolver.problems[0].message) == (
        "Publication date format did not pass validation; format: January 2, 2020."
    )


def test_handle_rejects_invalid_date(app):
    resolver = HandleResolver()

    assert resolver._parse_loose_date("not a date") is None
    assert str(resolver.problems[0].message) == "Invalid publication date format: not a date."


@pytest.mark.parametrize(
    ("titles", "title"),
    [
        # DataCite REST API sends the titleType of the main title as null
        ([{"title": "Main", "titleType": None}, {"title": "Alt", "titleType": "AlternativeTitle"}], "Main"),
        # no main title - the first title is used
        ([{"title": None}, {"title": "Alt", "titleType": "AlternativeTitle"}], "Alt"),
    ],
)
def test_datacite_title(app, monkeypatch, titles, title):
    resolver = DataciteResolver()
    resolver.metadata = {"titles": titles}
    monkeypatch.setattr(datacite_module, "lookup_vocabulary_by_prop", Mock(return_value="alternative-title"))

    resolver.resolve_title()
    resolver.resolve_additional_titles()

    assert resolver.processed_metadata["title"] == title
    # a title is never repeated in the additional titles
    assert title not in [t["title"] for t in resolver.processed_metadata.get("additional_titles", [])]


def test_datacite_additional_title_without_value_is_omitted(app, monkeypatch):
    resolver = DataciteResolver()
    resolver.metadata = {"titles": [{"title": "Main"}, {"title": None, "titleType": "AlternativeTitle"}]}
    monkeypatch.setattr(datacite_module, "lookup_vocabulary_by_prop", Mock(return_value="alternative-title"))

    resolver.resolve_title()
    resolver.resolve_additional_titles()

    assert "additional_titles" not in resolver.processed_metadata


def test_datacite_invalid_values_are_omitted(app, monkeypatch):
    """Values the record schema would reject are dropped, the rest of the record is kept."""
    resolver = DataciteResolver()
    resolver.metadata = {
        "relatedIdentifiers": [
            {"relationType": "IsCitedBy", "relatedIdentifierType": "DOI"},
            {"relationType": "References", "relatedIdentifier": ["10.1234/a"], "relatedIdentifierType": "DOI"},
            {"relationType": "References", "relatedIdentifier": "10.1234/valid", "relatedIdentifierType": "DOI"},
        ],
        "dates": [{"date": "", "dateType": "Issued"}, {"date": "2020-01-31", "dateType": "Issued"}],
        "identifiers": [
            {"identifier": "CEH:EIDC:#1406898956642", "identifierType": "URN"},
            {"identifier": "urn:nbn:cz:123", "identifierType": "URN"},
        ],
    }
    monkeypatch.setattr(
        datacite_module, "lookup_vocabulary_by_prop", Mock(side_effect=lambda _vocab, value: value.lower())
    )
    monkeypatch.setattr(datacite_module, "lookup_vocabulary_by_prop_handle_multiple", Mock(return_value=None))

    resolver.resolve_related_identifiers()
    resolver.resolve_dates()
    resolver.resolve_identifiers()

    assert resolver.processed_metadata == {
        "related_identifiers": [
            {"identifier": "10.1234/valid", "scheme": "doi", "relation_type": {"id": "references"}},
        ],
        "dates": [{"date": "2020-01-31", "type": {"id": "issued"}}],
        "identifiers": [{"identifier": "urn:nbn:cz:123", "scheme": "urn"}],
    }
    # dropped values are reported, but not as errors
    assert len(resolver.problems) == 4
    assert {p.level for p in resolver.problems} == {datacite_module.ResolverProblemLevel.INFO}
