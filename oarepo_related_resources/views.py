#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Blueprint factory for the related-resources HTTP API."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Blueprint, Flask


def create_bp(app: Flask) -> Blueprint:
    """Create requests blueprint."""
    return app.extensions["related-resources-import-extension"].resource.as_blueprint()
