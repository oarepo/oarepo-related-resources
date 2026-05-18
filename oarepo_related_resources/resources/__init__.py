#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources services."""

from __future__ import annotations

from oarepo_related_resources.resources.config import RelatedResourcesResourceConfig
from oarepo_related_resources.resources.resource import RelatedResourcesResource

__all__ = [
    "RelatedResourcesResource",
    "RelatedResourcesResourceConfig",
]
