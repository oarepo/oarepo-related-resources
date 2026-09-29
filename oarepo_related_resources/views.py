# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Blueprint factory for the related-resources HTTP API."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Blueprint, Flask


def create_bp(app: Flask) -> Blueprint:
    """Create requests blueprint."""
    return app.extensions["related-resources-import-extension"].resource.as_blueprint()
