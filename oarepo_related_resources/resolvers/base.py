#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of nma (see https://github.com/EOSC-CZ/nma).
#
# nma is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources base resolver class."""

from __future__ import annotations

import dataclasses
import enum
import unicodedata
from abc import ABC, abstractmethod

from invenio_i18n import gettext
from invenio_i18n import lazy_gettext as _

from oarepo_related_resources.utils import create_session_with_retries


class ResolverProblemLevel(enum.Enum):
    """Define problem severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


CREATORS_PLACEHOLDER = [
    {
        "person_or_org": {
            "name": "Unknown",
            "type": "personal",
            "family_name": "Unknown",
        }
    }
]
PUBLICATION_DATE_PLACEHOLDER = "2025-01-01"
TITLE_PLACEHOLDER = "Unknown title"
RESOURCE_TYPE_PLACEHOLDER = "other"
DEFAULT_TIMEOUT = 10


def get_validation_failed_on_date_format_message(date: str) -> str:
    """Return message for failed publication date format validation."""
    return str(_("Publication date format did not pass validation; format: %(date)s.", date=date))


def get_invalid_publication_date_message(date: str) -> str:
    """Return message for invalid publication date format."""
    return str(_("Invalid publication date format: %(date)s.", date=date))


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


# TODO: if level is error -> generate glitchtip issue
# by logger.error(... resolver problem ...)


class PIDDoesNotExistError(Exception):
    """Raised when a persistent identifier cannot be found.

    This exception indicates that the identifier is syntactically valid,
    but cannot be resolved.
    """

    def __init__(self, identifier: str):
        """Construct."""
        self.identifier = identifier
        super().__init__(
            gettext(
                "Non-existent persistent identifier: '%(identifier)s'.",
                identifier=identifier,
            )
        )


class UnsupportedPIDError(Exception):
    """Raised when a persistent identifier is not supported by any resolver.

    This exception means that the identifier format is not recognized by any
    of the configured resolvers. User should check the identifier or contact
    support.
    """

    def __init__(self, identifier: str):
        """Construct."""
        self.identifier = identifier
        super().__init__(gettext("Unsupported identifier type '%(identifier)s'.", identifier=identifier))


class PIDProcessingError(Exception):
    """Raised when an error occurs while processing a persistent identifier."""

    def __init__(self, identifier: str):
        """Construct."""
        self.identifier = identifier
        super().__init__(
            gettext(
                "Error while processing identifier '%(identifier)s'.",
                identifier=identifier,
            )
        )


class MetadataResolver(ABC):
    """Metadata resolver abstract base class."""

    name: str

    def __init__(self):
        """Construct."""
        self.session = create_session_with_retries(
            total_retries=4,
        )

    @property
    def resolve_timeout(self) -> int:
        """Default timeout (seconds) applied on resolver requests."""
        return DEFAULT_TIMEOUT

    def can_resolve(self, identifier: str) -> bool:
        """Check if this resolver can handle the given identifier.

        This call does not contact any external service, it just parses
        the identifier format.
        """
        _ = identifier
        return False

    @abstractmethod
    def resolve(self, identifier: str) -> tuple[dict | None, list[ResolverProblem]]:
        """Resolve metadata by identifier.

        If the metadata can not be resolved, returns (None, list[ResolverProblem]).
        If the metadata is resolved, returns (metadata_dict, list[ResolverProblem]).
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, identifier: str) -> bool:
        """Check if identifier exists on resolvers api."""
        raise NotImplementedError

    def normalize(self, identifier: str) -> str:
        """Normalize an identifier to canonical form.

        This method ensures identifiers are stored consistently to prevent duplicates.
        Each resolver implements normalization appropriate for its identifier type.

        Args:
            identifier: The identifier to normalize
        Returns:
            The normalized identifier (e.g., lowercased for case-insensitive types)

        """
        # Default implementation: trim whitespace and normalize Unicode
        if identifier.startswith("http://"):
            identifier = identifier.replace("http://", "https://", 1)
        return unicodedata.normalize("NFC", identifier.strip())

    @abstractmethod
    def generate_id(self, identifier: str) -> str:
        """Generate id."""
        raise NotImplementedError
