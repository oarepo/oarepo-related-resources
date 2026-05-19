#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Result item for related resources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from invenio_records_resources.services.base.results import ServiceItemResult

if TYPE_CHECKING:
    from typing import Any

    from flask_principal import Identity

    from oarepo_related_resources.resolvers.base import ResolverProblem
    from oarepo_related_resources.services import RelatedResourcesService


class RelatedResourceItem(ServiceItemResult):  # add service, identity
    """Service result for a single related resource."""

    def __init__(
        self,
        identity: Identity,
        service: RelatedResourcesService,
        metadata: dict[str, Any],
        import_errors: list[ResolverProblem],
        validation_errors: list[dict[str, Any]],
    ):
        """Construct."""
        super().__init__()
        self._identity = identity
        self._service = service
        self._metadata = metadata
        self._import_errors = import_errors
        self._validation_errors = validation_errors

    def to_dict(self) -> dict[str, Any]:
        """Return the result as a dictionary."""
        return {
            "metadata": self._metadata,
            "import_errors": [e.to_dict() for e in self._import_errors],
            "validation_errors": self._validation_errors,
        }
