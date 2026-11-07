# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Related resources import config."""

from __future__ import annotations

DATACITE_URL = "https://api.datacite.org/dois"
HANDLE_URL = "https://hdl.handle.net"
CROSSREF_URL = "https://api.crossref.org/works/doi"

ORCID_PUBLIC_DUMP_S3_BUCKET_NAME = "v3.0-summaries"

RELATED_RESOURCES_SERVICE_CLASS = "oarepo_related_resources.services.RelatedResourcesService"
RELATED_RESOURCES_SERVICE_CONFIG_CLASS = "oarepo_related_resources.services.RelatedResourcesServiceConfig"
RELATED_RESOURCES_RESOURCE_CLASS = "oarepo_related_resources.resources.RelatedResourcesResource"
RELATED_RESOURCES_RESOURCE_CONFIG_CLASS = "oarepo_related_resources.resources.RelatedResourcesResourceConfig"

RELATED_RESOURCES_RECORD_UI_SCHEMA = "invenio_rdm_records.resources.serializers.ui.UIRecordSchema"
"""UI schema of the resolved related records; a model with its own record shape sets its own one
(ccmm-invenio does so in its ``invenio_config.module``)."""

RELATED_RESOURCES_DEFAULT_TIMEOUT = 10

# RELATED_RESOURCES_<PROVIDER>_MAPPER (RELATED_RESOURCES_DATACITE_MAPPER, RELATED_RESOURCES_CROSSREF_MAPPER,
# RELATED_RESOURCES_HANDLE_MAPPER): the mapping of a resolver's metadata (its ``get_metadata``: the DataCite
# attributes, the Crossref work, the landing page ``<head>`` of a Handle) to the record metadata, a callable
# (or its import string) ``(metadata) -> (record metadata, list[ResolverProblem])``. It belongs to the model,
# so there is no default here: ccmm-invenio sets them in its ``invenio_config.module``.
