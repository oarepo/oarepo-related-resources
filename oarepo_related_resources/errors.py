#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of nma (see https://github.com/EOSC-CZ/nma).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources error classes."""

from __future__ import annotations

from flask_babel import gettext


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
