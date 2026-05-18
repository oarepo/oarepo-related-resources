#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""OARepo related resources resource module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flask import g
from flask_resources import Resource, resource_requestctx, response_handler, route
from invenio_records_resources.resources.records.resource import request_data

if TYPE_CHECKING:
    from collections.abc import Sequence

    from flask_resources.resources import ResourceConfig

    from oarepo_related_resources.services import RelatedResourcesService


class RelatedResourcesResource(Resource):
    """Resource for records from external sources."""

    def __init__(self, config: ResourceConfig, service: RelatedResourcesService):
        """Instantiate the resource."""
        super().__init__(config)
        self.service = service

    def create_url_rules(self) -> Sequence[dict[str, Any]]:
        """Create the URL rules for the record resource."""
        routes = self.config.routes
        return [
            route("POST", routes["item"], self.import_related_resource),
        ]

    @request_data
    @response_handler()
    def import_related_resource(self) -> tuple[dict[str, Any], int]:
        """Create a record from external url."""
        pid = resource_requestctx.data["id"]
        result = self.service.import_related_resource(g.identity, pid)
        return result.to_dict(), 201
