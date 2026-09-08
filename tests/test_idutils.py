#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Tests for related resource identifier utilities."""

from lxml import etree

from oarepo_related_resources.services import idutils


def resolved_identifier(identifier, *, vocabulary, **kwargs):
    """Return a predictable vocabulary identifier."""
    return {"id": f"{vocabulary}:{identifier}"}


def test_default():
    data = {"value": 0, "empty": None, "object": {"id": "existing"}}

    assert (
        idutils.get_with_default(data, "value", 10),
        idutils.get_with_default(data, "empty", 10),
        idutils.get_with_default(None, "value", 10),
        idutils.get_object(data, "object"),
        idutils.get_object(data, "missing"),
    ) == (0, 10, 10, {"id": "existing"}, {})


def test_dict_lookup():
    data = {
        "metadata": {
            "creators": [
                {"identifiers": [{"identifier": "first"}, {"identifier": "second"}]},
                {"identifiers": [{"identifier": "third"}]},
                {"name": "without identifiers"},
            ]
        }
    }

    assert list(idutils.dict_lookup_with_arrays(data, "metadata.creators.identifiers")) == [
        (
            {"identifier": "first"},
            {"identifiers": [{"identifier": "first"}, {"identifier": "second"}]},
            "metadata.creators.0.identifiers.0",
        ),
        (
            {"identifier": "second"},
            {"identifiers": [{"identifier": "first"}, {"identifier": "second"}]},
            "metadata.creators.0.identifiers.1",
        ),
        (
            {"identifier": "third"},
            {"identifiers": [{"identifier": "third"}]},
            "metadata.creators.1.identifiers.0",
        ),
    ]


def test_resolve_identifiers(monkeypatch):
    data = {
        "metadata": {
            "creators": [
                {
                    "person_or_org": {
                        "identifiers": [
                            {"identifier": "0000-0001", "scheme": "orcid"},
                            {"identifier": "unchanged", "scheme": "other"},
                        ]
                    },
                    "affiliations": [{"id": "01abc", "scheme": "ror"}],
                }
            ],
            "funding": [{"funder": {"id": "02def"}, "award": {"identifiers": [{"id": "03ghi"}]}}],
        }
    }
    monkeypatch.setattr(
        idutils,
        "identifier_resolvers",
        {
            ("names", "orcid"): resolved_identifier,
            ("affiliations", "ror"): resolved_identifier,
            ("funders", None): resolved_identifier,
        },
    )

    idutils.resolve_identifiers(data)

    assert data == {
        "metadata": {
            "creators": [
                {
                    "person_or_org": {
                        "identifiers": [
                            {"identifier": "names:0000-0001", "scheme": "orcid"},
                            {"identifier": "unchanged", "scheme": "other"},
                        ]
                    },
                    "affiliations": [{"id": "affiliations:01abc", "scheme": "ror"}],
                }
            ],
            "funding": [
                {
                    "funder": {"id": "funders:02def"},
                    "award": {"identifiers": [{"id": "funders:03ghi"}]},
                }
            ],
        }
    }


def test_orcid_to_names():
    xml = etree.fromstring(
        b"""
        <record
            xmlns:common="http://www.orcid.org/ns/common"
            xmlns:person="http://www.orcid.org/ns/person"
            xmlns:personal-details="http://www.orcid.org/ns/personal-details"
            xmlns:activities="http://www.orcid.org/ns/activities"
            xmlns:employment="http://www.orcid.org/ns/employment"
        >
          <common:orcid-identifier><common:path>0000-0001-2345-6789</common:path></common:orcid-identifier>
          <person:person>
            <person:name>
              <personal-details:given-names>Ada</personal-details:given-names>
              <personal-details:family-name>Lovelace</personal-details:family-name>
            </person:name>
          </person:person>
          <activities:employments>
            <activities:affiliation-group>
              <employment:employment-summary>
                <common:organization><common:name>Analytical Engine Institute</common:name></common:organization>
              </employment:employment-summary>
              <employment:employment-summary>
                <common:organization><common:name>Analytical Engine Institute</common:name></common:organization>
              </employment:employment-summary>
            </activities:affiliation-group>
          </activities:employments>
        </record>
        """
    )
    importer = object.__new__(idutils.ORCIDImporter)

    assert importer.orcid_to_names(xml) == {
        "id": "0000-0001-2345-6789",
        "name": "Lovelace, Ada",
        "given_name": "Ada",
        "family_name": "Lovelace",
        "identifiers": [{"identifier": "0000-0001-2345-6789", "scheme": "orcid"}],
        "affiliations": [{"name": "Analytical Engine Institute"}],
    }

