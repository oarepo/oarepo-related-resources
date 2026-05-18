#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Related resources import extension."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from invenio_base.utils import obj_or_import_string

from . import config
from .services.idutils import ORCIDImporter

if TYPE_CHECKING:  # pragma: no cover
    from flask import Flask


class RelatedResourcesImportExtension:
    """Related resources extension."""

    def __init__(self, app: Flask | None = None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Flask application initialization."""
        self.app = app
        self.init_config(app)
        self.init_services(app)
        self.init_resources(app)

        app.extensions["related-resources-import-extension"] = self

    def init_config(self, app: Flask) -> None:
        """Initialize the configuration for the extension."""
        app.config.setdefault("DATACITE_URL", config.DATACITE_URL)
        app.config.setdefault("HANDLE_URL", config.HANDLE_URL)
        app.config.setdefault("CROSSREF_URL", config.CROSSREF_URL)
        app.config.setdefault("ORCID_PUBLIC_DUMP_S3_BUCKET_NAME", config.ORCID_PUBLIC_DUMP_S3_BUCKET_NAME)
        app.config.setdefault("RELATED_RESOURCES_SERVICE_CLASS", config.RELATED_RESOURCES_SERVICE_CLASS)
        app.config.setdefault(
            "RELATED_RESOURCES_SERVICE_CONFIG_CLASS",
            config.RELATED_RESOURCES_SERVICE_CONFIG_CLASS,
        )
        app.config.setdefault("RELATED_RESOURCES_RESOURCE_CLASS", config.RELATED_RESOURCES_RESOURCE_CLASS)
        app.config.setdefault(
            "RELATED_RESOURCES_RESOURCE_CONFIG_CLASS",
            config.RELATED_RESOURCES_RESOURCE_CONFIG_CLASS,
        )
        app.config.setdefault("RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE", config.RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE)
        app.config.setdefault("RELATED_RESOURCES_DEFAULT_TIMEOUT", config.RELATED_RESOURCES_DEFAULT_TIMEOUT)

    def init_services(self, app: Flask) -> None:
        """Initialize the services for the extension."""
        self.service = obj_or_import_string(app.config["RELATED_RESOURCES_SERVICE_CLASS"])(  # type: ignore[reportOptionalCall]
            obj_or_import_string(app.config["RELATED_RESOURCES_SERVICE_CONFIG_CLASS"]).build(app)  # type: ignore[reportOptionalMemberAccess]
        )

    def init_resources(self, app: Flask) -> None:
        """Instantiate the resource for the extension."""
        self.resource = obj_or_import_string(app.config["RELATED_RESOURCES_RESOURCE_CLASS"])(  # type: ignore[reportOptionalCall]
            obj_or_import_string(app.config["RELATED_RESOURCES_RESOURCE_CONFIG_CLASS"]),
            self.service,
        )

    @cached_property
    def orcid_importer(self) -> ORCIDImporter:
        """Return ORCID importer reading ORCID public dumps from AWS S3."""
        return ORCIDImporter(
            self.app.config["ORCID_AWS_ACCESS_KEY_ID"],
            self.app.config["ORCID_AWS_SECRET_ACCESS_KEY"],
        )
