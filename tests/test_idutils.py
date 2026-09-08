#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Tests for related resource identifier utilities."""

from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from flask import Flask
from lxml import etree
from marshmallow import ValidationError

from invenio_vocabularies.datastreams.datastreams import StreamEntry

from oarepo_related_resources.services import idutils


def resolved_identifier(identifier, *, vocabulary, **kwargs):
    """Return a predictable vocabulary identifier."""
    return {"id": f"{vocabulary}:{identifier}"}


def ignore_ror(*args, **kwargs):
    """Stand in for resolving ROR records created from ORCID data."""


def test_default():
    data = {"value": 0, "empty": None, "object": {"id": "existing"}}

    assert (
        idutils.get_with_default(data, "value", 10),
        idutils.get_with_default(data, "empty", 10),
        idutils.get_with_default(None, "value", 10),
        idutils.get_object(data, "object"),
        idutils.get_object(data, "missing"),
    ) == (0, 10, 10, {"id": "existing"}, {})


def test_create_vocabulary_item(monkeypatch):
    service = Mock()
    service.read.return_value.to_dict.return_value = {"id": "existing", "title": "Already there"}
    service.create.return_value.to_dict.return_value = {"id": "new"}
    registry = Mock()
    registry.get.return_value = service
    monkeypatch.setattr(idutils, "current_service_registry", registry)

    assert (
        idutils.create_vocabulary_item("names", {"id": "existing"}),
    ) == (
        {"id": "existing", "title": "Already there"},
    )

    service.read.side_effect = Exception
    assert idutils.create_vocabulary_item("names", {"id": "new"}, uow="uow") == {"id": "new"}


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


def test_orcid_to_names_with_ror(monkeypatch):
    xml = etree.fromstring(
        b"""
        <record
            xmlns:common="http://www.orcid.org/ns/common"
            xmlns:activities="http://www.orcid.org/ns/activities"
            xmlns:employment="http://www.orcid.org/ns/employment"
        >
          <activities:employments>
            <activities:affiliation-group>
              <employment:employment-summary>
                <common:organization>
                  <common:name>URL Institute</common:name>
                  <common:disambiguated-organization>
                    <common:disambiguation-source>ROR</common:disambiguation-source>
                    <common:disambiguated-organization-identifier>https://ror.org/01url</common:disambiguated-organization-identifier>
                  </common:disambiguated-organization>
                </common:organization>
              </employment:employment-summary>
              <employment:employment-summary>
                <common:organization>
                  <common:name>ID Institute</common:name>
                  <common:disambiguated-organization>
                    <common:disambiguation-source>ROR</common:disambiguation-source>
                    <common:disambiguated-organization-identifier>02plain</common:disambiguated-organization-identifier>
                  </common:disambiguated-organization>
                </common:organization>
              </employment:employment-summary>
            </activities:affiliation-group>
          </activities:employments>
        </record>
        """
    )
    monkeypatch.setattr(idutils, "resolve_ror", ignore_ror)

    assert object.__new__(idutils.ORCIDImporter).orcid_to_names(xml) == {
        "identifiers": [],
        "affiliations": [
            {"name": "URL Institute", "id": "01url"},
            {"name": "ID Institute", "id": "02plain"},
        ],
    }


def test_orcid_resolve(monkeypatch):
    xml = b"""
        <record xmlns:common="http://www.orcid.org/ns/common">
          <common:orcid-identifier><common:path>0000-0001</common:path></common:orcid-identifier>
        </record>
    """
    existing = {
        "id": "0000-0002",
        "identifiers": [{"identifier": "0000-0002", "scheme": "orcid"}],
    }
    service = Mock()
    service.search.return_value = [existing]
    service.read.side_effect = Exception
    service.create.return_value.to_dict.return_value = {
        "id": "0000-0001",
        "identifiers": [{"identifier": "0000-0001", "scheme": "orcid"}],
    }
    registry = Mock()
    registry.get.return_value = service
    boto_client = Mock()
    boto_client.get_object.return_value = {"Body": Mock(read=Mock(return_value=xml))}
    importer = object.__new__(idutils.ORCIDImporter)
    importer.boto_client = boto_client
    monkeypatch.setattr(idutils, "current_service_registry", registry)
    app = Flask(__name__)
    app.config["ORCID_PUBLIC_DUMP_S3_BUCKET_NAME"] = "orcid-dump"

    with app.app_context():
        result = (
            importer.resolve("https://orcid.org/0000-0002", "names"),
            importer.resolve("http://orcid.org/0000-0001", "names", check_existing=False),
        )

    assert result == (
        existing,
        {
            "id": "0000-0001",
            "identifiers": [{"identifier": "0000-0001", "scheme": "orcid"}],
        },
    )
    assert boto_client.get_object.call_args.kwargs == {
        "Bucket": "orcid-dump",
        "Key": "001/0000-0001.xml",
    }


def test_orcid_resolve_without_creation(monkeypatch):
    xml = b'<record xmlns:common="http://www.orcid.org/ns/common"/>'
    importer = object.__new__(idutils.ORCIDImporter)
    importer.boto_client = Mock(
        get_object=Mock(return_value={"Body": Mock(read=Mock(return_value=xml))})
    )
    registry = Mock()
    registry.get.return_value = Mock()
    monkeypatch.setattr(idutils, "current_service_registry", registry)
    app = Flask(__name__)
    app.config["ORCID_PUBLIC_DUMP_S3_BUCKET_NAME"] = "orcid-dump"

    with app.app_context():
        result = importer.resolve(
            "0000-0003",
            "names",
            parent={"given_name": "Grace", "family_name": "Hopper"},
            create_vocabulary_record=False,
            check_existing=False,
        )

    assert result == {
        "name": "Hopper, Grace",
        "given_name": "Grace",
        "family_name": "Hopper",
        "identifiers": [],
    }


def test_orcid_resolve_missing_record(monkeypatch):
    importer = object.__new__(idutils.ORCIDImporter)
    importer.boto_client = Mock()
    importer.boto_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "GetObject"
    )
    registry = Mock()
    registry.get.return_value = Mock()
    monkeypatch.setattr(idutils, "current_service_registry", registry)
    app = Flask(__name__)
    app.config["ORCID_PUBLIC_DUMP_S3_BUCKET_NAME"] = "orcid-dump"

    with app.app_context(), pytest.raises(ValidationError, match="ORCID 0000-0004 could not be resolved"):
        importer.resolve("0000-0004", "names", check_existing=False, path="metadata.creators.0")


def test_resolve_ror_rejects_error_response(monkeypatch):
    registry = Mock()
    registry.get.return_value = Mock()
    session = Mock()
    session.get.return_value = Mock(status_code=404)
    monkeypatch.setattr(idutils, "current_service_registry", registry)
    app = Flask(__name__)
    app.config["ROR_CLIENT_ID"] = "client-id"

    with app.app_context(), pytest.raises(ValidationError, match="ROR ID missing could not be resolved"):
        idutils.resolve_ror(
            "missing",
            "affiliations",
            check_existing=False,
            path="metadata.affiliations.0",
            session=session,
        )
