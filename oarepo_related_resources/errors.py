#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources error classes."""

from __future__ import annotations

from flask_babel import LazyString, gettext


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
        super().__init__(
            gettext(
                "Unsupported identifier type '%(identifier)s'.", identifier=identifier
            )
        )


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


class UpstreamFetchError(Exception):
    """Raised when an error occurs in response from external resource call."""

    def __init__(
        self, message: str | LazyString, url: str, error_code: int, content: str
    ):
        """Construct."""
        self.error_code = error_code
        super().__init__(
            gettext(
                "%(message)s; url - '%(url)s', error code - '%(error_code)s', content - '%(content)s'.",
                message=message,
                url=url,
                error_code=error_code,
                content=content,
            )
        )
