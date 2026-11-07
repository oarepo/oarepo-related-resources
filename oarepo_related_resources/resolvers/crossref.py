# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Related resources Crossref DOI resolver.

The resolver fetches the DOI's Crossref work (the ``message`` of the Crossref REST API response); its
mapping to the record metadata belongs to the model and is configured with
``RELATED_RESOURCES_CROSSREF_MAPPER`` (see ``MetadataResolver.resolve_metadata``).

Article with announcement of changes to REST API rate limits
https://doi.org/10.64000/wadve-3tj60

public pool rate limit: 5 requests per second

example: https://api.crossref.org/works/doi/10.64000/wadve-3tj60

polite pool rate limit: 10 requests per second
available by adding query parameter mailto to API URL
But currently returns "Resource not found."

example: https://api.crossref.org/works/doi/10.64000/wadve-3tj60&mailto=info@eosc.cz
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from invenio_i18n import lazy_gettext as _

from .base import DoiResolverBase

if TYPE_CHECKING:
    from requests import Response


class CrossrefResolver(DoiResolverBase):
    """Crossref resolver."""

    provider = "Crossref"

    not_found_message = _("The identifier looks like a DOI, but it was not found in the CrossRef registry.")
    unexpected_error_message = _("Unexpected error while resolving the DOI. Please fill the metadata manually.")

    @override
    def get_metadata(self, response: Response) -> Any:
        """Return the Crossref work of the DOI."""
        return response.json().get("message", {})
