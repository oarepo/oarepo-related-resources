# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Related resources Handle resolver.

The resolver fetches the landing page the Handle resolves to; the mapping of its ``<head>`` (the citation /
Dublin Core ``<meta>`` tags) to the record metadata belongs to the model and is configured with
``RELATED_RESOURCES_HANDLE_MAPPER`` (see ``MetadataResolver.resolve_metadata``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from idutils.normalizers import normalize_handle
from idutils.validators import is_handle
from invenio_i18n import lazy_gettext as _
from lxml import html

from .base import MetadataResolver

if TYPE_CHECKING:
    from requests import Response

HTTP_BAD_REQUEST = 400


class HandleResolver(MetadataResolver):
    """Resolver for Handle persistent identifiers."""

    provider = "Handle"
    scheme_url = "https://hdl.handle.net"
    exists_allow_redirects = False
    resolves_identifier = staticmethod(lambda url: bool(is_handle(url)))
    normalize_identifier = staticmethod(normalize_handle)

    not_found_message = _("The identifier looks like a Handle, but it was not found in the Handle registry.")
    unexpected_error_message = _("Unexpected error while resolving the Handle. Please fill the metadata manually.")

    @override
    def _fetch_response_alive(self, status_code: int) -> bool:
        """Handle considers any 2xx/3xx response (incl. redirects) as live."""
        return 200 <= status_code < HTTP_BAD_REQUEST  # noqa PLR2004

    @override
    def get_metadata(self, response: Response) -> Any:
        """Return the ``<head>`` element (an lxml ``HtmlElement``) of the landing page."""
        tree = html.fromstring(response.content)
        return tree.xpath("/html/head")[0]
