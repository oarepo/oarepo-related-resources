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

from typing import TYPE_CHECKING, Any, override

from defusedxml.ElementTree import fromstring
from invenio_i18n import lazy_gettext as _

from ..config import RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE
from .base import (
    DoiResolverBase,
)
from .utils import build_person_or_org, handle_errors

if TYPE_CHECKING:
    from requests import Response

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


class CrossrefResolver(DoiResolverBase):
    """Crossref resolver."""

    provider = "Crossref"

    not_found_message = _("The identifier looks like a DOI, but it was not found in the CrossRef registry.")
    unexpected_error_message = _("Unexpected error while resolving the DOI. Please fill the metadata manually.")

    fields_to_resolve = (
        "title",
        "creators",
        "publication_date",
        "resource_type",
        "description",
    )

    @override
    def get_metadata(self, response: Response) -> Any:
        return response.json().get("message", {})

    @handle_errors(alert_user=True)
    def resolve_title(self) -> None:
        """Extract the main title from Crossref metadata."""
        titles = self.metadata.get("title", [])
        if titles:
            self.processed_metadata["title"] = titles[0]

    @handle_errors(alert_user=True)
    def resolve_creators(self) -> None:
        """Extract and map author information from Crossref metadata."""
        creator_list = []
        for crossref_author in self.metadata.get("author", []):
            family = crossref_author.get("family", "")
            given = crossref_author.get("given") or None
            name = f"{family}, {given}" if given else family
            identifiers = None
            orcid = crossref_author.get("ORCID")
            if orcid:
                identifiers = [
                    {
                        "identifier": orcid.removeprefix("https://orcid.org/"),
                        "scheme": "orcid",
                    }
                ]

            creator_list.append(build_person_or_org(name=name, family=family, given=given, identifiers=identifiers))
        if creator_list:
            self.processed_metadata["creators"] = creator_list

    @handle_errors()
    def resolve_publication_date(self) -> None:
        """Parse and validate publication date parts into an EDTF-compatible string."""
        publication_date_parts = self.metadata.get("deposited", {}).get("date-parts")
        if not publication_date_parts:
            return
        try:
            parts = publication_date_parts[0]
            if not isinstance(parts, (list, tuple)):
                return
            publication_date = "-".join(f"{x:02d}" for x in parts[:3])
        except Exception as e:  # noqa: BLE001
            self._add_problem(
                _("Invalid publication date-parts format: %s.") % publication_date_parts,
                exc=e,
            )
            return
        self.processed_metadata["publication_date"] = publication_date

    @handle_errors()
    def resolve_resource_type(self) -> None:
        """Set the resource type placeholder for Crossref records."""
        self.processed_metadata["resource_type"] = {"id": RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE}

    @handle_errors()
    def resolve_description(self) -> None:
        """Parse and extract plain text abstract from a JATS XML snippet."""
        jats_snippet = self.metadata.get("abstract")
        if not jats_snippet:
            return

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

        description = "\n\n".join(parts).strip()
        if description:
            self.processed_metadata["description"] = description
