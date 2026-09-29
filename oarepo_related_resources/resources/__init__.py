# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Related resources services."""

from __future__ import annotations

from oarepo_related_resources.resources.config import RelatedResourcesResourceConfig
from oarepo_related_resources.resources.resource import RelatedResourcesResource

__all__ = [
    "RelatedResourcesResource",
    "RelatedResourcesResourceConfig",
]
