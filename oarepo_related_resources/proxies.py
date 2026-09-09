# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

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
current_orcid_importer = LocalProxy(lambda: current_related_resources_import_extension.orcid_importer)  # type: ignore[has-type]
