#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of nma (see https://github.com/EOSC-CZ/nma).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Proxies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import current_app
from werkzeug.local import LocalProxy

if TYPE_CHECKING:
    from .ext import RelatedResourcesImportExtension

    current_related_resources_import_extension: RelatedResourcesImportExtension  # type: ignore[reportRedeclaration]


current_related_resources_import_extension = LocalProxy(
    lambda: current_app.extensions["related-resources-import-extension"]
)  # type: ignore[assignment]
current_resolver_registry = LocalProxy(lambda: current_related_resources_import_extension.resolver_registry)  # type: ignore[has-type]
current_orcid_importer = LocalProxy(lambda: current_related_resources_import_extension.orcid_importer)  # type: ignore[has-type]
