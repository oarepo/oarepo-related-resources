#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources resolvers utils."""

from __future__ import annotations

import re
from functools import wraps
from typing import Any

from flask import current_app
from invenio_i18n import lazy_gettext as _

DATE_REGEX = re.compile(r"^(?:\d{4}|\d{4}-\d{2}|\d{4}-\d{2}-\d{2})$")


def validate_date(value: str) -> bool:
    """Validate whether a string matches the expected date format."""
    return bool(DATE_REGEX.fullmatch(value))


def escape_lucene(s: str) -> str:
    """Escape special characters in a string for safe use in Lucene queries."""
    return re.sub(r'([+\-!(){}\[\]^"~*?:\\/])', r"\\\1", s)


def handle_errors(error_placeholder: Any | None = None, alert_user: bool = False) -> Any:
    """Handle errors from resolvers.

    Decorator for metadata resolver functions that:
    - logs any exception that occurs,
    - prevents the error from propagating further,
    - returns the given placeholder if provided,
    otherwise returns None.
    """

    def decorator(func: Any) -> Any:
        """Wrap the given function with error handling logic."""

        @wraps(func)
        def inner(*args: Any, **kwargs: Any) -> Any | None:
            """Execute the wrapped function with safe error handling."""
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if alert_user and "problems" in kwargs:
                    from .base import ResolverProblem, ResolverProblemLevel

                    self = args[0]
                    kwargs["problems"].append(
                        ResolverProblem(
                            resolver=self.name,
                            message=str(_("Unexpected error while parsing the metadata.")),
                            level=ResolverProblemLevel.ERROR,
                            original_exception=e,
                        )
                    )
                current_app.logger.exception("Function '%s' failed with error: '%s'.", func.__name__, e)  # noqa: TRY401
            return error_placeholder  # placeholder or discard

        return inner

    return decorator
