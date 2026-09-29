# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Related resources services."""

from __future__ import annotations

from .config import RelatedResourcesServiceConfig
from .idutils import resolve_identifier, resolve_identifiers, resolve_orcid, resolve_ror
from .service import RelatedResourcesService

__all__ = [
    "RelatedResourcesService",
    "RelatedResourcesServiceConfig",
    "resolve_identifier",
    "resolve_identifiers",
    "resolve_orcid",
    "resolve_ror",
]
