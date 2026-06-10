#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Related Resources Resource Configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from flask_resources import (
    HTTPJSONException,
    ResourceConfig,
    ResponseHandler,
    create_error_handler,
)
from flask_resources.parsers import BaseListSchema
from flask_resources.serializers import JSONSerializer
from flask_resources.serializers.base import MarshmallowSerializer
from invenio_i18n import lazy_gettext as _
from invenio_records_resources.services.base.config import ConfiguratorMixin, FromConfig
from invenio_records_resources.services.errors import PermissionDeniedError

from oarepo_related_resources.errors import (
    PIDDoesNotExistError,
    PIDProcessingError,
    UnsupportedPIDError,
    UpstreamFetchError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from flask import Response
    from marshmallow import Schema


class RelatedResourcesUIJSONSerializer(MarshmallowSerializer):
    """UI JSON serializer for related resources."""

    def __init__(self, object_schema_cls: type[Schema]):
        """Initialise serializer."""
        super().__init__(
            format_serializer_cls=JSONSerializer,
            object_schema_cls=object_schema_cls,
            list_schema_cls=BaseListSchema,
        )

    def dump_obj(self, obj: dict) -> dict:
        """Dump UI metadata while preserving the original response."""
        data = dict(obj)
        ui = self.object_schema.dump(data)
        if not ui and data.get("metadata"):
            ui = self.object_schema.dump(data["metadata"])
        data["ui"] = ui
        return data


class RelatedResourcesResourceConfig(ResourceConfig, ConfiguratorMixin):
    """Related Resources resource config."""

    # Blueprint configuration
    blueprint_name = "related_records"
    url_prefix = "/related-records"
    routes: Mapping[str, str] = {
        "item": "",
    }
    ui_schema = FromConfig(
        "RELATED_RESOURCES_RECORD_UI_SCHEMA",
        default="invenio_rdm_records.resources.serializers.ui.UIRecordSchema",
        import_string=True,
    )

    @property
    def response_handlers(self) -> Mapping[str, ResponseHandler]:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Response handlers."""
        return {
            "application/json": ResponseHandler(JSONSerializer()),
            "application/vnd.inveniordm.v1+json": ResponseHandler(RelatedResourcesUIJSONSerializer(self.ui_schema)),
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
        UpstreamFetchError: create_error_handler(
            lambda e: HTTPJSONException(
                code=cast("UpstreamFetchError", e).error_code,
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
