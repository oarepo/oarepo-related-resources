# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Related resources resolvers."""

from __future__ import annotations

from .base import MetadataResolver
from .crossref import CrossrefResolver
from .datacite import DataciteResolver
from .handle import HandleResolver

__all__ = ["CrossrefResolver", "DataciteResolver", "HandleResolver", "MetadataResolver"]
