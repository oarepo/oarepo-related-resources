# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Permission policy for the related-resources import service."""

from __future__ import annotations

from invenio_records_permissions.generators import AuthenticatedUser
from invenio_records_permissions.policies.base import BasePermissionPolicy


class RelatedResourcesPermissionPolicy(BasePermissionPolicy):
    """Permission policy allowing any authenticated user to import related resources."""

    can_import_related = (AuthenticatedUser(),)
