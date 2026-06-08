#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources base resolver class."""

from __future__ import annotations

import dataclasses
import enum
from abc import ABC, abstractmethod
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from flask import current_app
from idutils.normalizers import normalize_doi
from idutils.validators import is_doi
from invenio_i18n import lazy_gettext as _

from oarepo_related_resources.errors import UpstreamFetchError
from oarepo_related_resources.session import create_session_with_retries

if TYPE_CHECKING:
    from collections.abc import Callable

    from flask_babel import LazyString
    from requests import Response


class ResolverProblemLevel(enum.StrEnum):
    """Define problem severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclasses.dataclass
class ResolverProblem:
    """Resolver problem base class."""

    resolver: str
    """Name of the resolver that produced this problem."""

    message: str
    """Human-readable message describing the problem."""

    level: ResolverProblemLevel
    """Severity level of the problem."""

    original_exception: Exception | None = None
    """Original exception that caused the problem, if any."""

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict representation."""
        return {
            "resolver": self.resolver,
            "message": self.message,
            "level": self.level.value,
            "original_exception": str(self.original_exception)
            if self.original_exception
            else None,
        }


# TODO: if level is error -> generate glitchtip issue
# by logger.error(... resolver problem ...)


class MetadataResolver(ABC):
    """Metadata resolver abstract base class."""

    provider: str
    """Registry/API that resolves the identifier (e.g. ``"Datacite"``, ``"Crossref"``, ``"Handle"``)."""

    scheme_url: str

    resolves_identifier: Callable[[str], bool]
    """Return True if the given identifier in url form is in a format resolved by this resolver."""

    normalize_identifier: Callable[[str], str]
    """Function returning the value of the identifier itself, eg. https://doi.org/10.5281/zenodo.19032692
    -> 10.5281/zenodo.19032692"""

    not_found_message: str | LazyString = _("Identifier was not found in the registry.")
    """User-facing lazy message returned in fetch() on a 404 response. Subclasses should override."""

    unexpected_error_message: str | LazyString = _(
        "Unexpected error while resolving the identifier. Please fill the metadata manually."
    )
    """User-facing lazy message returned in fetch() on any non-200 response. Subclasses should override."""

    exists_allow_redirects: bool = True
    """If False, identifier_exists_at_fetch_url() does not follow redirects."""

    @property
    def fetch_url_config_key(self) -> str:
        """Flask config key holding the resolver's API base URL."""
        return f"{self.provider.upper()}_URL"

    @property
    def resolve_timeout(self) -> int:
        """Default timeout (seconds) applied on resolver requests."""
        return current_app.config["RELATED_RESOURCES_DEFAULT_TIMEOUT"]  # type: ignore[no-any-return]

    def __init__(self):
        """Construct."""
        self.metadata: Any = None
        self.session = create_session_with_retries(
            total_retries=4,
        )
        self.problems: list[ResolverProblem] = []
        self.processed_metadata: dict[str, Any] = {}

    def _add_problem(
        self,
        message: Any,
        *,
        level: ResolverProblemLevel = ResolverProblemLevel.WARNING,
        exc: Exception | None = None,
    ) -> None:
        """Append a ResolverProblem to ``problems`` carrying this resolver's provider."""
        self.problems.append(
            ResolverProblem(
                resolver=self.provider,
                message=str(message),
                level=level,
                original_exception=exc,
            )
        )

    def _fetch_response_alive(self, status_code: int) -> bool:
        """Return True if the identifier API response ``status_code`` indicates the PID is live."""
        return status_code == HTTPStatus.OK

    def _create_fetch_url(self, identifier: str) -> str:
        """Build the resolver's API URL for `identifier`."""
        return f"{current_app.config[self.fetch_url_config_key]}/{self.normalize_identifier(identifier)}"

    def create_identifier_url(self, identifier: str) -> str:
        """Return identifier url in normalized form."""
        return f"{self.scheme_url}/{self.normalize_identifier(identifier)}"

    def identifier_exists_at_fetch_url(self, identifier: str) -> bool:
        """Check if identifier exists on the resolver's API.

        self.fetch is not used here due to difference in handling of redirects in HandleResolver. -
        """
        url = self._create_fetch_url(identifier)
        response = self.session.get(
            url=url,
            timeout=self.resolve_timeout,
            allow_redirects=self.exists_allow_redirects,
        )
        return self._fetch_response_alive(response.status_code)

    def fetch(self, identifier: str, *, allow_redirects: bool = True) -> Response:
        """GET response from identifier API."""
        url = self._create_fetch_url(identifier)
        response = self.session.get(
            url=url, timeout=self.resolve_timeout, allow_redirects=allow_redirects
        )
        if response.status_code == HTTPStatus.OK:
            return response  # type: ignore[no-any-return]
        if response.status_code == HTTPStatus.NOT_FOUND:
            error_message = self.not_found_message
        else:
            current_app.logger.error(
                "Unexpected error while resolving %s. Response code: %s, content: %s",
                url,
                response.status_code,
                response.content,
            )
            error_message = self.unexpected_error_message
        raise UpstreamFetchError(
            error_message, url, response.status_code, response.text
        )

    @abstractmethod
    def get_metadata(self, response: Response) -> Any:
        """Extract raw metadata from the resolver's API response."""
        raise NotImplementedError

    @abstractmethod
    def resolve_metadata(self) -> tuple[dict[str, Any], list[ResolverProblem]]:
        """Map the resolver's metadata from identifier API response to the expected format."""
        raise NotImplementedError

    def resolve(self, identifier: str) -> tuple[dict[str, Any], list[ResolverProblem]]:
        """Resolve metadata by identifier.

        If the metadata is resolved, returns (metadata_dict, list[ResolverProblem]).
        If the metadata can not be resolved, raise UpstreamFetchError.
        """
        response = self.fetch(identifier)
        self.metadata = self.get_metadata(response)
        return self.resolve_metadata()


class DoiResolverBase(MetadataResolver):
    """Shared base for DOI-backed resolvers (DataCite, Crossref)."""

    scheme_url = "https://doi.org"
    resolves_identifier = staticmethod(lambda identifier: bool(is_doi(identifier)))
    normalize_identifier = staticmethod(normalize_doi)
