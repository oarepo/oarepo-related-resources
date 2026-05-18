#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources resolvers."""

from __future__ import annotations

from .base import MetadataResolver
from .crossref import CrossrefResolver
from .datacite import DataciteResolver
from .handle import HandleResolver

__all__ = ["CrossrefResolver", "DataciteResolver", "HandleResolver", "MetadataResolver"]
