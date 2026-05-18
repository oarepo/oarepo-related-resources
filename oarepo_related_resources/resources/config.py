#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Related Resources Resource Configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask_resources import HTTPJSONException, ResourceConfig, create_error_handler
from invenio_i18n import lazy_gettext as _
from invenio_records_resources.services.errors import PermissionDeniedError

from oarepo_related_resources.errors import PIDDoesNotExistError, PIDProcessingError, UnsupportedPIDError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from flask import Response


class RelatedResourcesResourceConfig(ResourceConfig):
    """Related Resources resource config."""

    # Blueprint configuration
    blueprint_name = "related_records"
    url_prefix = "/related-records"
    routes: Mapping[str, str] = {
        "item": "",
    }
    error_handlers: Mapping[type[Exception], Callable[[Exception], Response]] = {  # type: ignore[reportIncompatibleVariableOverride]
        PIDDoesNotExistError: create_error_handler(
            lambda e: HTTPJSONException(
                code=404,
                description=str(e),
            )
        ),
        UnsupportedPIDError: create_error_handler(
            lambda e: HTTPJSONException(
                code=404,
                description=str(e),
            )
        ),
        PIDProcessingError: create_error_handler(
            lambda e: HTTPJSONException(
                code=500,  # ??
                description=str(e),
            )
        ),
        PermissionDeniedError: create_error_handler(  # TODO: or import invenio ErrorHandlersMixin
            HTTPJSONException(
                code=403,
                description=_("Permission denied."),
            )
        ),
    }
