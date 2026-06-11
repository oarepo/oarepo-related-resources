#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Service for importing related resources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from flask import current_app
from invenio_records_resources.services import ServiceSchemaWrapper
from invenio_records_resources.services.base.service import Service
from requests.exceptions import RetryError
from urllib3.exceptions import MaxRetryError

from oarepo_related_resources.errors import (
    PIDDoesNotExistError,
    PIDProcessingError,
    UnsupportedPIDError,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from flask_principal import Identity

    from oarepo_related_resources.resolvers import MetadataResolver
    from oarepo_related_resources.resolvers.base import ResolverProblem
    from oarepo_related_resources.services.results import RelatedResourceItem


class RelatedResourcesService(Service):
    """Service for importing related resources."""

    @property
    def resolvers(self) -> Generator[MetadataResolver]:
        """Return the list of resolvers."""
        return (res() for res in self.config.resolvers)  # type: ignore[reportOptionalCall]

    @property
    def schema(self) -> ServiceSchemaWrapper:
        """Returns the data schema instance."""
        return ServiceSchemaWrapper(self, schema=self.config.schema)

    def _find_resolver(self, identifier: str) -> MetadataResolver:
        url_format_resolvable = False
        for resolver in self.resolvers:
            if resolver.resolves_identifier(identifier):
                url_format_resolvable = True
                if resolver.identifier_exists_at_fetch_url(identifier):
                    return resolver
        if url_format_resolvable:
            raise PIDDoesNotExistError(identifier)
        raise UnsupportedPIDError(identifier)

    def _resolve(self, identifier: str) -> tuple[dict[str, Any], list[ResolverProblem]]:
        """Resolve metadata with the first matching resolver.

        Returns ``(metadata, problems)`` where ``metadata`` is the resolver's
        flat metadata dict with the original ``identifier_url`` injected, and
        ``problems`` is the list of ResolverProblems collected during resolution.
        """
        try:
            resolver = self._find_resolver(identifier)
        except UnsupportedPIDError:
            raise
        except PIDDoesNotExistError:
            raise
        except Exception as e:
            if isinstance(e, RetryError) and e.args:
                e = e.args[0]
            if isinstance(e, MaxRetryError):
                e = getattr(e, "reason", e)
            current_app.logger.exception(
                "Unexpected error while finding resolver for id: %s",
                identifier,
            )
            raise PIDProcessingError(identifier) from e
        identifier_url = resolver.create_identifier_url(identifier)

        try:
            metadata, problems = resolver.resolve(identifier_url)
        except Exception:
            current_app.logger.exception("Exception calling resolver %s %s", resolver, identifier_url)
            raise

        return metadata, problems

    def import_related_resource(self, identity: Identity, identifier_url: str) -> RelatedResourceItem:
        """Resolve the PID and return the loaded metadata along with any validation/import errors."""
        self.require_permission(identity, "import_related")
        record_data, import_errors = self._resolve(identifier_url)
        data, validation_errors = self.schema.load(
            record_data,
            raise_errors=False,
        )
        return cast(
            "RelatedResourceItem",
            self.config.result_item_cls(
                identity=identity,
                service=self,
                metadata=data,
                import_errors=import_errors,
                validation_errors=validation_errors,
            ),
        )
