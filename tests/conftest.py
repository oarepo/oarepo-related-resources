#
# Copyright (C) 2026 CESNET z.s.p.o.
#
# oarepo-rdm is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Conftest."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from flask import Flask

if TYPE_CHECKING:
    from typing import Any


class _DummyDomain:
    """Minimal mock of a Babel domain used for testing.

    Provides basic gettext and ngettext implementations with
    simple string interpolation support.
    """

    def gettext(self, message: str, **variables: Any) -> str:
        """Return the translated message.

        If variables are provided, apply %-style string formatting.
        """
        if variables:
            return message % variables
        return message

    def ngettext(self, singular: str, plural: str, n: int, **variables: Any) -> str:
        """Return singular or plural form."""
        message = singular if n == 1 else plural
        if variables:
            return message % variables
        return message


class _DummyBabel:
    """Minimal mock of Flask-Babel extension for testing."""

    domain: _DummyDomain = _DummyDomain()


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["PERSISTENT_IDENTIFIER_RESOLVERS"] = [
        "oarepo_related_resources.resolvers.DataciteResolver",
        "oarepo_related_resources.resolvers.CrossrefResolver",
        "oarepo_related_resources.resolvers.HandleResolver",
    ]
    app.config["DATACITE_URL"] = "https://api.datacite.test/dois"
    app.config["CROSSREF_URL"] = "https://api.crossref.test/works/doi"
    app.config["HANDLE_URL"] = "https://hdl.handle.net"
    app.extensions["babel"] = _DummyBabel()
    with app.app_context():
        yield app
