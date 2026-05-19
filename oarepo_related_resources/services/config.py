#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Service configuration for the related-resources service."""

from __future__ import annotations

from invenio_rdm_records.services.schemas import MetadataSchema  # type: ignore[attr-defined]
from invenio_records_resources.services.base.config import ConfiguratorMixin, FromConfig, ServiceConfig

from oarepo_related_resources.resolvers import CrossrefResolver, DataciteResolver, HandleResolver
from oarepo_related_resources.services.permissions import (
    RelatedResourcesPermissionPolicy,
)
from oarepo_related_resources.services.results import RelatedResourceItem

# order implicitly decides priority
DEFAULT_PERSISTENT_IDENTIFIER_RESOLVERS = [
    DataciteResolver,
    CrossrefResolver,
    HandleResolver,
]


class RelatedResourcesServiceConfig(ConfiguratorMixin, ServiceConfig):
    """Default service config for the related resources service."""

    service_id = "related-resources"
    permission_policy_cls = FromConfig(  # type: ignore[reportAssignmentType]
        "RELATED_RESOURCES_PERMISSION_POLICY",
        default=RelatedResourcesPermissionPolicy,
        import_string=True,
    )
    schema = FromConfig("RELATED_RESOURCES_RECORD_SCHEMA", default=MetadataSchema)
    result_item_cls = RelatedResourceItem
    resolvers = FromConfig(
        "RELATED_RESOURCES_PERSISTENT_IDENTIFIER_RESOLVERS", default=DEFAULT_PERSISTENT_IDENTIFIER_RESOLVERS
    )
