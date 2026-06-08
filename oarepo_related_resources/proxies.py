#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
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
current_orcid_importer = LocalProxy(
    lambda: current_related_resources_import_extension.orcid_importer
)  # type: ignore[has-type]
