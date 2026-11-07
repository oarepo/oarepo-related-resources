# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Minimal resolver metadata mappers for the tests - the real ones are the model's (ccmm-invenio)."""

from __future__ import annotations

from typing import Any

from oarepo_related_resources.resolvers.base import ResolverProblem, ResolverProblemLevel


def map_datacite(attributes: dict[str, Any]) -> tuple[dict[str, Any], list[ResolverProblem]]:
    """Map the few fields the tests check and report one problem."""
    metadata = {
        "title": attributes["titles"][0]["title"],
        "creators": [
            {
                "person_or_org": {
                    "name": creator["name"],
                    "type": "personal",
                    "given_name": creator["givenName"],
                    "family_name": creator["familyName"],
                }
            }
            for creator in attributes["creators"]
        ],
        "publisher": attributes["publisher"],
        "publication_date": str(attributes["publicationYear"]),
        "resource_type": {"id": "dataset"},
        "version": attributes["version"],
    }
    problems = [ResolverProblem(resolver="Datacite", message="test problem", level=ResolverProblemLevel.INFO)]
    return metadata, problems


def map_crossref(work: dict[str, Any]) -> tuple[dict[str, Any], list[ResolverProblem]]:
    """Map the title and publisher of a Crossref work."""
    return {"title": work["title"][0], "publisher": work["publisher"], "resource_type": {"id": "dataset"}}, []


def map_handle(head: Any) -> tuple[dict[str, Any], list[ResolverProblem]]:
    """Map the citation title of a landing page ``<head>``."""
    return {"title": head.xpath('//meta[@name="citation_title"]/@content')[0], "resource_type": {"id": "dataset"}}, []
