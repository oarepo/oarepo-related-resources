# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

"""Related resources import module."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("oarepo-related-resources")
except PackageNotFoundError:
    __version__ = "0.0.0dev0+unknown"
"""Version of the library."""

__all__ = ("__version__",)
