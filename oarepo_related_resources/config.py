#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources import config."""

from __future__ import annotations

import importlib.metadata

DATACITE_URL = "https://api.datacite.org/dois"
HANDLE_URL = "https://hdl.handle.net"
CROSSREF_URL = "https://api.crossref.org/works/doi"

ORCID_PUBLIC_DUMP_S3_BUCKET_NAME = "v3.0-summaries"

RELATED_RESOURCES_SERVICE_CLASS = "oarepo_related_resources.services.RelatedResourcesService"
RELATED_RESOURCES_SERVICE_CONFIG_CLASS = "oarepo_related_resources.services.RelatedResourcesServiceConfig"
RELATED_RESOURCES_RESOURCE_CLASS = "oarepo_related_resources.resources.RelatedResourcesResource"
RELATED_RESOURCES_RESOURCE_CONFIG_CLASS = "oarepo_related_resources.resources.RelatedResourcesResourceConfig"

try:
    importlib.metadata.version("ccmm-invenio")
    RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE = "c_ddb1"
    RELATED_RESOURCES_RECORD_UI_SCHEMA = "ccmm_invenio.serializers.related_resources_ui.CCMMRelatedResourceUISchema"
except importlib.metadata.PackageNotFoundError:
    RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE = "dataset"
    RELATED_RESOURCES_RECORD_UI_SCHEMA = "invenio_rdm_records.resources.serializers.ui.UIRecordSchema"
RELATED_RESOURCES_DEFAULT_TIMEOUT = 10
