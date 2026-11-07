# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""The base of the resolver metadata mappers (``RELATED_RESOURCES_<PROVIDER>_MAPPER``).

A mapper is a callable ``(metadata) -> (record metadata, list[ResolverProblem])``. With `ResolverMapping`
it is a subclass setting ``provider`` and implementing ``resolve_metadata`` (usually calling a
``handle_errors``-decorated ``resolve_*`` method per field), plus a function returning
``Subclass(metadata).resolve_metadata()`` - the callable configured as the mapper. See the README
("Metadata mapping") and ``TitleMapping`` in ``tests/test_resolvers.py``; ccmm-invenio's DataCite,
Crossref and Handle mappings are real-world examples.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .base import ProblemReporter, ResolverProblem


class ResolverMapping(ProblemReporter, ABC):
    """Map the metadata of one resolved identifier to record metadata.

    The ``resolve_*`` methods of a subclass fill parts of `processed_metadata`; decorated with
    `oarepo_related_resources.resolvers.utils.handle_errors` a failing one is logged and skipped, so one bad
    value does not lose the whole record. Values that can not be mapped are reported with ``_add_problem``.
    """

    def __init__(self, metadata: Any):
        """Create the mapping of the resolver's ``metadata`` (what its ``get_metadata`` returns)."""
        self.metadata = metadata
        self.processed_metadata: dict[str, Any] = {}
        self.problems = []

    @abstractmethod
    def resolve_metadata(self) -> tuple[dict[str, Any], list[ResolverProblem]]:
        """Map the whole metadata, return the record metadata and the problems."""
        raise NotImplementedError
