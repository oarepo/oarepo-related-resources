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
