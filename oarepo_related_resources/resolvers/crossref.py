#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of nma (see https://github.com/EOSC-CZ/nma).
#
# nma is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources Crossref DOI resolver."""

from __future__ import annotations

import re
from http import HTTPStatus

from defusedxml.ElementTree import fromstring
from flask import current_app
from idutils.normalizers import normalize_doi
from idutils.validators import is_doi
from invenio_access.permissions import system_identity
from invenio_i18n import lazy_gettext as _
from invenio_vocabularies.proxies import current_service as vocabulary_service
from marshmallow_utils.fields import EDTFDateString

from ..resolvers import MetadataResolver
from .base import (
    CREATORS_PLACEHOLDER,
    PUBLICATION_DATE_PLACEHOLDER,
    RESOURCE_TYPE_PLACEHOLDER,
    TITLE_PLACEHOLDER,
    ResolverProblem,
    ResolverProblemLevel,
)
from .utils import handle_errors

"""Crossref resolver to retrieve RDM-like metadata based on PID.

Article with announcement of changes to REST API rate limits
https://doi.org/10.64000/wadve-3tj60

public pool rate limit: 5 requests per second

example: https://api.crossref.org/works/doi/10.64000/wadve-3tj60

polite pool rate limit: 10 requests per second
available by adding query parameter mailto to API URL
But currently returns "Resource not found."

example: https://api.crossref.org/works/doi/10.64000/wadve-3tj60&mailto=info@eosc.cz
"""

MIN_TITLE_LENGTH = 3
HTTP_OK = 200
HTTP_NOT_FOUND = 404


class CrossrefResolver(MetadataResolver):
    """Crossref resolver."""

    name = "Crossref"

    def can_resolve(self, identifier: str) -> bool:
        """Check if the identifier is a valid DOI."""
        return bool(is_doi(identifier))

    def resolve(self, identifier: str) -> tuple[dict | None, list[ResolverProblem]]:
        """Resolve metadata associated with a given identifier using the Crossref API."""
        crossref_url = current_app.config["CROSSREF_URL"]
        doi = normalize_doi(identifier)

        url = f"{crossref_url}/{doi}"
        response = self.session.get(url=url, timeout=self.resolve_timeout)
        if response.status_code != HTTP_OK:
            if response.status_code == HTTP_NOT_FOUND:
                return {}, [
                    ResolverProblem(
                        resolver=self.name,
                        message=str(
                            _(
                                "The identifier looks like a DOI, but \
                        it was not found in the CrossRef registry."
                            )
                        ),
                        level=ResolverProblemLevel.ERROR,
                    )
                ]
            current_app.logger.error(
                "Unexpected error while resolving the CrossRef DOI. Response code: %s, content: %s",
                response.status_code,
                response.content,
            )
            return {}, [
                ResolverProblem(
                    resolver=self.name,
                    message=str(_("Unexpected error while resolving the DOI. Please fill the metadata manually.")),
                    level=ResolverProblemLevel.ERROR,
                )
            ]

        metadata = {}
        problems: list[ResolverProblem] = []
        data = response.json()
        crossref_metadata = data.get("message", {})

        crossref_titles = crossref_metadata.get("title", [])
        metadata["title"] = self.resolve_title(titles=crossref_titles, problems=problems)

        crossref_authors = crossref_metadata.get("author", [])
        metadata["creators"] = self.resolve_crossref_authors(authors=crossref_authors, problems=problems)

        publication_date_parts = crossref_metadata.get("deposited", {}).get("date-parts")
        metadata["publication_date"] = self.resolve_crossref_publication_date(
            publication_date_parts=publication_date_parts, problems=problems
        )
        metadata["resource_type"] = {"id": RESOURCE_TYPE_PLACEHOLDER}

        crossref_abstract = crossref_metadata.get("abstract")
        if crossref_abstract:
            metadata["description"] = self.resolve_crossref_abstract(jats_snippet=crossref_abstract)

        return metadata, problems

    @handle_errors(error_placeholder=TITLE_PLACEHOLDER, alert_user=True)
    def resolve_title(self, titles: list, problems: list) -> str:
        """Extract the main title from Crossref metadata and validate its length."""
        for title in titles:
            if len(title) < MIN_TITLE_LENGTH:
                problems.append(
                    ResolverProblem(
                        resolver=self.name,
                        message=str(
                            _(
                                "The title is too short. "
                                "A minimum of 3 characters is required to meet repository requirements."
                            )
                        ),
                        level=ResolverProblemLevel.WARNING,
                    )
                )
                return f"Incompatible title: {title} (please provide a corrected title)"
            return str(title)
        problems.append(
            ResolverProblem(
                resolver=self.name,
                message=str(_("Missing title.")),
                level=ResolverProblemLevel.WARNING,
            )
        )
        return TITLE_PLACEHOLDER  # should never happen

    @handle_errors(error_placeholder=CREATORS_PLACEHOLDER, alert_user=True)
    def resolve_crossref_authors(self, authors: list, problems: list) -> list:
        """Extract and map author information from Crossref metadata."""
        if len(authors) == 0:
            problems.append(
                ResolverProblem(
                    resolver=self.name,
                    message=str(_("Missing creators.")),
                    level=ResolverProblemLevel.WARNING,
                )
            )
            return CREATORS_PLACEHOLDER
        creator_list = []
        for crossref_author in authors:
            creator_obj = {
                "name": crossref_author.get("family", ""),
                "family_name": crossref_author.get("family", ""),
                "type": "personal",
            }
            if crossref_author.get("given"):
                creator_obj["given_name"] = crossref_author.get("given", "")
                creator_obj["name"] += ", " + crossref_author.get("given", "")
            if crossref_author.get("ORCID"):
                orcid_id = crossref_author.get("ORCID", "").removeprefix("https://orcid.org/")
                creator_obj["identifiers"] = [{"identifier": orcid_id, "scheme": "orcid"}]
            creator_list.append({"person_or_org": creator_obj})
        return creator_list

    @handle_errors(PUBLICATION_DATE_PLACEHOLDER)
    def resolve_crossref_publication_date(self, *, publication_date_parts: list | None, problems: list) -> str:
        """Parse and validate publication date parts into an EDTF-compatible string."""
        if not publication_date_parts:
            return PUBLICATION_DATE_PLACEHOLDER
        try:
            parts = publication_date_parts[0]
            if not isinstance(parts, (list, tuple)):
                return PUBLICATION_DATE_PLACEHOLDER
            publication_date = "-".join(f"{x:02d}" for x in parts[:3])
            edtf_date_string = EDTFDateString()
            edtf_date_string.deserialize(publication_date)
        except Exception as e:  # noqa: BLE001
            problems.append(
                ResolverProblem(
                    resolver=self.name,
                    message=_("Invalid publication date-parts format: %s.") % publication_date_parts,
                    level=ResolverProblemLevel.WARNING,
                    original_exception=e,
                )
            )
            return PUBLICATION_DATE_PLACEHOLDER
        return publication_date

    @handle_errors(RESOURCE_TYPE_PLACEHOLDER)
    def resolve_crossref_resource_type(self, *, resource_type: dict, problems: list) -> dict:
        """Resolve and validate the Crossref resource type against the vocabulary."""
        vocabulary_id = "resourceTypeGeneral"
        _type = resource_type.get("type", RESOURCE_TYPE_PLACEHOLDER).lower()
        try:
            vocabulary_service.read(system_identity, (vocabulary_id, _type))  # type: ignore[arg-type]

        except Exception as e:
            problems.append(
                ResolverProblem(
                    resolver=self.name,
                    message=_(
                        "The provided resource type %s could not be parsed. The default value 'other' has been applied."
                    )
                    % _type,
                    level=ResolverProblemLevel.WARNING,
                    original_exception=e,
                )
            )
            current_app.logger.exception(
                "Record '%s' was not found in the '%s' vocabulary.",
                _type,
                vocabulary_id,
            )
            return {"id": RESOURCE_TYPE_PLACEHOLDER}
        else:
            return {"id": _type}

    @handle_errors()
    def resolve_crossref_abstract(self, jats_snippet: str) -> str:
        """Parse and extract plain text abstract from a JATS XML snippet."""
        # Crossref often gives fragments, so wrap in a root element
        wrapped = f"<root xmlns:jats='http://www.ncbi.nlm.nih.gov/JATS1'>{jats_snippet}</root>"
        root = fromstring(wrapped)

        parts = []
        for el in root.iter():
            # skip the "Abstract" label/title
            if el.tag.endswith("title"):
                continue
            # capture paragraph text (and any nested text)
            if el.tag.endswith("p"):
                text = "".join(el.itertext()).strip()
                if text:
                    parts.append(text)

        return "\n\n".join(parts).strip()

    def exists(self, identifier: str) -> bool:
        """Check if the DOI exists in the Crossref registry."""
        crossref_url = current_app.config["CROSSREF_URL"]
        doi = normalize_doi(identifier)

        url = f"{crossref_url}/{doi}"
        response = self.session.get(url=url, timeout=self.resolve_timeout)
        return bool(response.status_code == HTTPStatus.OK)

    def generate_id(self, identifier: str) -> str:
        """Generate an internal DOI-based identifier from a DOI URL."""
        pattern = r"https://doi.org/(.*)"
        m = re.match(pattern, identifier)
        if m:
            return f"doi/{m.group(1)}"
        raise ValueError(f"Could not generate pid from url: {identifier}")

    def normalize(self, identifier: str) -> str:
        """DOIs are case-insensitive, so we lowercase them."""
        return super().normalize(identifier).lower()
