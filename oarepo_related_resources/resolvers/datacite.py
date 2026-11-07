# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Related resources DataCite DOI resolver.

The resolver fetches the DOI's DataCite attributes; their mapping to the record metadata belongs to the
model and is configured with ``RELATED_RESOURCES_DATACITE_MAPPER`` (see ``MetadataResolver.resolve_metadata``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from flask import current_app
from invenio_i18n import lazy_gettext as _

from .base import DoiResolverBase

if TYPE_CHECKING:
    from requests import Response


class DataciteResolver(DoiResolverBase):
    """Datacite resolver."""

    provider = "Datacite"

    not_found_message = _("The identifier looks like a DOI, but it was not found in the DataCite registry.")
    unexpected_error_message = _("Unexpected error while resolving the DOI. Please fill the metadata manually.")

    @override
    def get_metadata(self, response: Response) -> dict:
        """Return the DataCite attributes object of the DOI."""
        return response.json()["data"]["attributes"]  # type: ignore[no-any-return]

    @override
    def _create_fetch_url(self, identifier: str) -> str:
        """Build the resolver's API URL for `identifier`."""
        return (
            f"{current_app.config[self.fetch_url_config_key]}/{self.normalize_identifier(identifier)}?affiliation=true"
        )
